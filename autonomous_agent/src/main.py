"""Main entry point for the autonomous coding agent."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_loader import get_config_loader
from src.llm.openai_client import OpenAIClient
from src.memory.db_manager import DatabaseManager
from src.memory.vector_store import VectorStore
from src.orchestrator import Orchestrator
from src.ui.logger import get_logger, setup_logging

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
def run(task: str, problem_type: str, language: str | None, max_iterations: int):
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

    console.print(f"\nTask: {task}")
    console.print(f"Problem type: {problem_type}")
    console.print(f"Language: {language}")

    # Initialize components
    try:
        openai_client = OpenAIClient(configs)
        db_manager = DatabaseManager(configs)
        vector_store = VectorStore(db_manager, openai_client)
    except Exception as e:
        console.print(f"[red]Error initializing components: {e}[/red]")
        logger.error("initialization_failed", error=str(e))
        return

    # Create task
    task_id = db_manager.create_task(
        description=task,
        goal=task,
        metadata={"problem_type": problem_type, "language": language},
    )

    console.print(f"\nTask created (ID: {task_id})")

    try:
        orchestrator = Orchestrator(
            task_id=task_id,
            task_description=task,
            goal=task,
            config=configs,
            db_manager=db_manager,
            vector_store=vector_store,
            openai_client=openai_client,
            max_iterations=max_iterations,
            problem_type=problem_type,
            language=language,
        )

        console.print(f"\n[yellow]Starting autonomous execution (max {max_iterations} iterations)...[/yellow]\n")

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
