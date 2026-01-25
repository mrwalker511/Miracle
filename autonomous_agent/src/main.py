"""Main entry point for the autonomous coding agent.

Enhanced with:
- Reprompter integration for structured task input
- Code review and security audit options
- Better task structuring before execution
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_loader import get_config_loader
from src.llm.openai_client import OpenAIClient
from src.memory.db_manager import DatabaseManager
from src.memory.vector_store import VectorStore
from src.orchestrator import Orchestrator
from src.ui.logger import get_logger, setup_logging
from src.utils.reprompter import Reprompter, StructuredTask, ClarificationPriority

console = Console()


@click.group()
def cli():
    """Autonomous Coding Agent - Build code autonomously with AI."""


@cli.command()
@click.option("--task", "-t", help="Task description")
@click.option(
    "--problem-type",
    "-p",
    default="general",
    help="Problem type (web_app, cli_tool, data_pipeline, etc.)",
)
@click.option("--language", "-l", default=None, help="Runtime language (python, node)")
@click.option("--max-iterations", "-m", default=15, help="Maximum iterations")
@click.option("--workspace", "-w", default=None, help="Path to workspace directory (overrides config)")
@click.option("--enable-review", is_flag=True, help="Enable code review phase")
@click.option("--enable-audit", is_flag=True, help="Enable security audit phase")
@click.option("--skip-reprompter", is_flag=True, help="Skip task structuring with reprompter")
def run(
    task: str,
    problem_type: str,
    language: str | None,
    max_iterations: int,
    workspace: str | None,
    enable_review: bool,
    enable_audit: bool,
    skip_reprompter: bool,
):
    """Start a new autonomous coding task."""

    console.print(
        Panel.fit(
            "[bold cyan]AUTONOMOUS CODING AGENT v0.1.0[/bold cyan]\n"
            "[dim]Build code autonomously with AI[/dim]",
            border_style="cyan",
        )
    )

    # Load configuration
    try:
        config_loader = get_config_loader()
        configs = config_loader.load_all_configs()

        # Override workspace if provided via CLI
        if workspace:
            workspace_path = Path(workspace).resolve()
            if "settings" not in configs:
                configs["settings"] = {}
            if "sandbox" not in configs["settings"]:
                configs["settings"]["sandbox"] = {}

            configs["settings"]["sandbox"]["workspace_root"] = str(workspace_path)
            console.print(f"[green]Using workspace: {workspace_path}[/green]")

    except Exception as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        return

    # Setup logging
    logging_config = configs.get("settings", {}).get("logging", {})
    setup_logging(logging_config)
    logger = get_logger("main")

    logger.info("application_started")

    if not task:
        task = Prompt.ask("\n[cyan]?[/cyan] Enter your coding task")

    if not language:
        language = "node" if str(problem_type).lower().startswith("node") else "python"

    language = str(language).lower()

    # Initialize components
    try:
        openai_client = OpenAIClient(configs)
        db_manager = DatabaseManager(configs)
        vector_store = VectorStore(db_manager, openai_client)
    except Exception as e:
        console.print(f"[red]Error initializing components: {e}[/red]")
        logger.error("initialization_failed", error=str(e))
        return

    # Process task through reprompter for better structuring
    structured_task: StructuredTask | None = None
    goal = task

    if not skip_reprompter:
        try:
            console.print("\n[dim]Analyzing task for better structuring...[/dim]")
            reprompter = Reprompter(
                openai_client=openai_client,
                auto_fill_defaults=True,
                min_clarity_score=7,
            )

            structured_task, questions = reprompter.process(task)

            # Handle clarifying questions
            if questions:
                blocking_questions = [q for q in questions if q.priority == ClarificationPriority.BLOCKING]

                if blocking_questions:
                    console.print("\n[yellow]Some clarification would help:[/yellow]")
                    answers = {}

                    for q in blocking_questions:
                        if q.options:
                            answer = Prompt.ask(
                                f"  [cyan]?[/cyan] {q.question}",
                                choices=q.options,
                                default=q.default_answer or q.options[0]
                            )
                        else:
                            answer = Prompt.ask(
                                f"  [cyan]?[/cyan] {q.question}",
                                default=q.default_answer or ""
                            )
                        answers[q.question] = answer

                    # Refine task with answers
                    structured_task = reprompter.refine_with_answers(structured_task, answers)

            # Use structured task info
            if structured_task:
                goal = structured_task.goal
                language = structured_task.language or language
                problem_type = structured_task.complexity.value if structured_task.complexity else problem_type

                console.print(f"\n[green]Task structured:[/green]")
                console.print(f"  Title: {structured_task.title}")
                console.print(f"  Goal: {structured_task.goal}")
                console.print(f"  Complexity: {structured_task.complexity.value}")

        except Exception as e:
            logger.warning("reprompter_failed", error=str(e))
            console.print(f"[yellow]Reprompter skipped: {e}[/yellow]")
            # Continue with original task

    console.print(f"\nTask: {task}")
    console.print(f"Problem type: {problem_type}")
    console.print(f"Language: {language}")

    if enable_review:
        console.print("[cyan]Code review: enabled[/cyan]")
    if enable_audit:
        console.print("[cyan]Security audit: enabled[/cyan]")

    # Create task in database
    task_id = db_manager.create_task(
        description=task,
        goal=goal,
        metadata={
            "problem_type": problem_type,
            "language": language,
            "structured_task": structured_task.to_xml() if structured_task else None,
        },
    )

    console.print(f"\nTask created (ID: {task_id})")

    try:
        orchestrator = Orchestrator(
            task_id=task_id,
            task_description=task,
            goal=goal,
            config=configs,
            db_manager=db_manager,
            vector_store=vector_store,
            openai_client=openai_client,
            max_iterations=max_iterations,
            problem_type=problem_type,
            language=language,
            enable_code_review=enable_review,
            enable_security_audit=enable_audit,
        )

        phases = ["planning", "coding", "testing"]
        if enable_review:
            phases.insert(2, "reviewing")
        if enable_audit:
            phases.insert(-1, "auditing")

        console.print(f"\n[yellow]Starting autonomous execution (max {max_iterations} iterations)...[/yellow]")
        console.print(f"[dim]Phases: {' -> '.join(phases)}[/dim]\n")

        result = orchestrator.run()

        if result.get("success"):
            console.print(
                Panel.fit(
                    "[bold green]TASK COMPLETED SUCCESSFULLY[/bold green]\n\n"
                    f"Iterations: {result.get('iterations', 0)}\n"
                    f"Files created: {len(result.get('code_files', {}))}\n"
                    f"Workspace: {result.get('workspace', 'N/A')}",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel.fit(
                    "[bold red]TASK FAILED[/bold red]\n\n"
                    f"Status: {result.get('status', 'unknown')}\n"
                    f"Iterations: {result.get('iterations', 0)}\n"
                    f"Message: {result.get('message', 'No details available')}",
                    border_style="red",
                )
            )

    except Exception as e:
        console.print(f"\n[red]Error during execution: {e}[/red]")
        logger.error("execution_failed", error=str(e), exc_info=True)

    finally:
        db_manager.close()

    logger.info("application_completed")


@cli.command()
def history():
    """View task history."""

    try:
        config_loader = get_config_loader()
        configs = config_loader.load_all_configs()
        db_manager = DatabaseManager(configs)

        query = """
            SELECT task_id, description, status, total_iterations, created_at, completed_at
            FROM tasks
            ORDER BY created_at DESC
            LIMIT 10
        """

        tasks = db_manager.execute_query(query)
        if not tasks:
            console.print("[yellow]No tasks found[/yellow]")
            return

        console.print("\n[bold cyan]Recent Tasks:[/bold cyan]\n")

        for task in tasks:
            status_color = {
                "success": "green",
                "failed": "red",
                "running": "yellow",
                "paused": "blue",
            }.get(task["status"], "white")

            console.print(
                f"[{status_color}]*[/{status_color}] "
                f"{task['description'][:60]}... "
                f"([{status_color}]{task['status']}[/{status_color}], "
                f"{task['total_iterations']} iterations)"
            )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    finally:
        try:
            db_manager.close()
        except Exception:
            pass


@cli.command()
def setup():
    """Setup database and initialize agent."""

    console.print(
        Panel.fit(
            "[bold cyan]Setting up Autonomous Coding Agent[/bold cyan]",
            border_style="cyan",
        )
    )

    console.print("\n1. Starting PostgreSQL with pgvector...")
    console.print("   Run: [cyan]docker-compose up -d postgres[/cyan]")

    console.print("\n2. Database schema will be initialized automatically")

    console.print("\n3. Configure your environment:")
    console.print("   - Copy .env.example to .env")
    console.print("   - Set your OPENAI_API_KEY")
    console.print("   - Set DB_PASSWORD")

    console.print("\nSetup instructions displayed")


if __name__ == "__main__":
    cli()
