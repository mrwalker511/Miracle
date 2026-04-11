"""Main entry point for the autonomous coding agent.

Enhanced with:
- Reprompter integration for structured task input
- Code review and security audit options
- Better task structuring before execution
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_loader import get_config_loader
from src.llm.client import LLMClient
from src.memory.db_manager import DatabaseManager
from src.memory.vector_store import VectorStore
from src.orchestrator import Orchestrator
from src.ui.logger import get_logger, setup_logging
from src.preprocessing import Reprompter, StructuredTask, ClarificationQuestion
from src.preprocessing.reprompter import ClarificationPriority

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
    help="Problem type (web_app, mobile_app, desktop_app, api, cli_tool, data_pipeline, ml_model, devops, game, embedded, etc.)",
)
@click.option("--language", "-l", default=None, help="Runtime language (python, node, javascript, typescript, java, csharp, go, rust, ruby, php, swift, kotlin, elixir)")
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
    asyncio.run(_run_async(task, problem_type, language, max_iterations, workspace, enable_review, enable_audit, skip_reprompter))


async def _run_async(
    task: str,
    problem_type: str,
    language: str | None,
    max_iterations: int,
    workspace: str | None,
    enable_review: bool,
    enable_audit: bool,
    skip_reprompter: bool,
):
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
        # Default language based on problem type
        if str(problem_type).lower() in {"node", "javascript", "typescript"}:
            language = "node"
        elif str(problem_type).lower() in {"java", "jvm"}:
            language = "java"
        elif str(problem_type).lower() in {"csharp", "dotnet", "c#"}:
            language = "csharp"
        elif str(problem_type).lower() in {"go", "golang"}:
            language = "go"
        elif str(problem_type).lower() in {"rust"}:
            language = "rust"
        elif str(problem_type).lower() in {"ruby", "rails"}:
            language = "ruby"
        elif str(problem_type).lower() in {"php"}:
            language = "php"
        elif str(problem_type).lower() in {"swift", "ios"}:
            language = "swift"
        elif str(problem_type).lower() in {"kotlin"}:
            language = "kotlin"
        elif str(problem_type).lower() in {"elixir"}:
            language = "elixir"
        else:
            language = "python"

    language = str(language).lower()

    # Initialize components
    try:
        llm_client = LLMClient(configs)
        db_manager = DatabaseManager(configs)
        vector_store = VectorStore(db_manager, llm_client)
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
                llm_client=llm_client,
                auto_fill_defaults=True,
                min_clarity_score=7,
            )

            structured_task, questions = await reprompter.process(task)

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
    task_id = await db_manager.create_task(
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
            llm_client=llm_client,
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

        result = await orchestrator.run()

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
        await db_manager.close()

    logger.info("application_completed")


@cli.command()
def history():
    """View task history."""
    asyncio.run(_history_async())

async def _history_async():
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

        tasks = await db_manager.execute_query(query)
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
            await db_manager.close()
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


@cli.command()
@click.argument('task_id')
@click.option("--max-iterations", "-m", default=15, help="Maximum iterations")
def resume(task_id: str, max_iterations: int):
    """Resume an interrupted task."""
    asyncio.run(_resume_async(task_id, max_iterations))

async def _resume_async(task_id: str, max_iterations: int):
    try:
        config_loader = get_config_loader()
        configs = config_loader.load_all_configs()
        setup_logging(configs.get("settings", {}).get("logging", {}))
        db_manager = DatabaseManager(configs)
        
        query = "SELECT task_id, description, goal, metadata, total_iterations, status FROM tasks WHERE task_id = %s"
        tasks = await db_manager.execute_query(query, (task_id,))
        if not tasks:
            console.print(f"[red]Task {task_id} not found.[/red]")
            return
            
        task = tasks[0]
        if task['status'] in ('success', 'failed'):
            console.print(f"[yellow]Task {task_id} is already completed (status: {task['status']}).[/yellow]")
            return
            
        console.print(f"\n[green]Resuming Task:[/green] {task['description']}")
        
        # We need a workspace and state. For now, since StateSaver requires workspace path,
        # we'll use the workspace_root from configs and task metadata.
        workspace_root = Path(configs.get('settings', {}).get('sandbox', {}).get('workspace_root', './sandbox/workspace'))
        if isinstance(task['metadata'], str):
            import json
            metadata = json.loads(task['metadata'])
        else:
            metadata = task['metadata'] or {}
            
        # Initialization
        llm_client = LLMClient(configs)
        vector_store = VectorStore(db_manager, llm_client)
        
        orchestrator = Orchestrator(
            task_id=task['task_id'],
            task_description=task['description'],
            goal=task['goal'],
            config=configs,
            db_manager=db_manager,
            vector_store=vector_store,
            llm_client=llm_client,
            max_iterations=max_iterations,
            problem_type=metadata.get('problem_type', 'general'),
            language=metadata.get('language', 'python')
        )
        
        # Load checkpoint context if exists
        state_saver = StateSaver()
        # Find which workspace was used. If task has code_files generated in metadata or last iteration... We do simple lookup.
        # Actually simplest to just start from db iteration state.
        last_iter_q = "SELECT iteration_number, phase, code_snapshot, test_code, test_results, reflection, hypothesis FROM iterations WHERE task_id = %s ORDER BY iteration_number DESC LIMIT 1"
        iterations = await db_manager.execute_query(last_iter_q, (task_id,))
        if iterations:
            last_iter = iterations[0]
            orchestrator.current_iteration = last_iter['iteration_number']
            
            # Map phase to state
            phase_map = {
                'planning': OrchestrationState.PLANNING,
                'coding': OrchestrationState.CODING,
                'testing': OrchestrationState.TESTING,
                'reflecting': OrchestrationState.REFLECTING
            }
            orchestrator.state = phase_map.get(last_iter['phase'], OrchestrationState.PLANNING)
            
            # Restore context fragments
            orchestrator.context['iteration'] = orchestrator.current_iteration
            if last_iter['code_snapshot']:
                # Basic restoration, can't map back perfectly to multiple files unless stored in json
                pass
            if last_iter['test_results']:
                orchestrator.context['test_results'] = last_iter['test_results'] if not isinstance(last_iter['test_results'], str) else json.loads(last_iter['test_results'])
            if last_iter['reflection'] or last_iter['hypothesis']:
                orchestrator.context['previous_errors'] = last_iter['hypothesis']
                
            console.print(f"[dim]Continuing from iteration {orchestrator.current_iteration} (phase: {last_iter['phase']})[/dim]\n")
        else:
            console.print("[dim]No previous iterations found. Starting from beginning.[/dim]\n")

        result = await orchestrator.run()

        if result.get("success"):
            console.print(Panel.fit(f"[bold green]TASK COMPLETED[/bold green]\nIterations: {result.get('iterations')}"))
        else:
            console.print(Panel.fit(f"[bold red]TASK FAILED[/bold red]\nStatus: {result.get('status')}"))
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
    finally:
        try:
            await db_manager.close()
        except:
            pass

@cli.command()
def metrics():
    """View system performance metrics."""
    asyncio.run(_metrics_async())

async def _metrics_async():
    try:
        config_loader = get_config_loader()
        configs = config_loader.load_all_configs()
        db_manager = DatabaseManager(configs)

        query = "SELECT problem_type, total_tasks, successful, success_rate, avg_iterations FROM success_rate_by_type"

        metrics_data = await db_manager.execute_query(query)
        if not metrics_data:
            console.print("[yellow]No metrics found. Complete a task first.[/yellow]")
            return

        from rich.table import Table
        table = Table(title="System Performance Metrics")
        table.add_column("Problem Type", style="cyan")
        table.add_column("Total Tasks", justify="right")
        table.add_column("Successful", justify="right", style="green")
        table.add_column("Success Rate", justify="right")
        table.add_column("Avg Iterations", justify="right")
        
        for row in metrics_data:
            rate = float(row['success_rate']) * 100
            table.add_row(
                str(row['problem_type']),
                str(row['total_tasks']),
                str(row['successful']),
                f"{rate:.1f}%",
                str(row['avg_iterations'])
            )

        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error fetching metrics: {e}[/red]")
    finally:
        try:
            await db_manager.close()
        except:
            pass

@cli.command()
def config():
    """View current active configuration."""
    config_loader = get_config_loader()
    configs = config_loader.load_all_configs()
    
    from rich.tree import Tree
    tree = Tree("[bold cyan]Active Configuration[/bold cyan]")
    
    for section, values in configs.items():
        section_node = tree.add(f"[green]{section}[/green]")
        if isinstance(values, dict):
            for k, v in values.items():
                if isinstance(v, dict):
                    sub_node = section_node.add(f"[yellow]{k}[/yellow]")
                    for sub_k, sub_v in v.items():
                        # Mask sensitive values
                        if any(sensitive in sub_k.lower() for sensitive in ['key', 'secret', 'password']):
                            sub_v = "********"
                        sub_node.add(f"{sub_k}: {sub_v}")
                else:
                    if any(sensitive in k.lower() for sensitive in ['key', 'secret', 'password']):
                        v = "********"
                    section_node.add(f"{k}: {v}")
    
    console.print(tree)


if __name__ == "__main__":
    cli()
