"""CLI entry point for Ratchet."""

import sys
from pathlib import Path

# Add project root to path for benchmark module imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import typer
from rich.console import Console
from rich.table import Table
from typing import Optional
import json

app = typer.Typer(
    name="ratchet",
    help="Agent harness evaluation framework. Every failure becomes a permanent fix.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def run(
    version: str = typer.Option(..., "--version", "-v", help="Agent version: v0, v1, v2, v3"),
    task: str = typer.Option(..., "--task", "-t", help="Scenario name to run"),
    practice: bool = typer.Option(False, "--practice", "-p", help="Run against practice scenarios"),
):
    """Run one version against one scenario."""
    from benchmark.runner import run_single_trial
    
    valid_versions = ["v0", "v1", "v2", "v3"]
    if version not in valid_versions:
        console.print(f"[red]Invalid version '{version}'. Must be one of: {valid_versions}[/red]")
        raise typer.Exit(1)
    
    console.print(f"[bold]Running {version} against {task}...[/bold]")
    result = run_single_trial(version, task, is_practice=practice)
    
    status = "[green]✓ PASSED[/green]" if result["task_success"] else "[red]✗ FAILED[/red]"
    catastrophe = "[red]⚠ CATASTROPHIC FAILURE[/red]" if result["catastrophic_failure"] else "[green]No catastrophe[/green]"
    
    console.print(f"\nResult: {status}")
    console.print(f"Safety:  {catastrophe}")
    console.print(f"Turns:   {result['total_turns']}")
    console.print(f"Reason:  {result['termination_reason']}")


@app.command()
def bench(
    all_versions: bool = typer.Option(False, "--all-versions", "-a", help="Run all 4 versions"),
    version: Optional[str] = typer.Option(None, "--version", "-v", help="Run specific version only"),
    trials: int = typer.Option(3, "--trials", "-n", help="Number of trials per scenario"),
):
    """Run benchmark: all versions against all scenarios."""
    from benchmark.runner import run_benchmark
    from ratchet.agent.loop import get_active_model, MODEL_CONFIGS
    
    if not all_versions and not version:
        console.print("[red]Specify --all-versions or --version[/red]")
        raise typer.Exit(1)
    
    versions = ["v0", "v1", "v2", "v3"] if all_versions else [version]
    
    active_model = get_active_model()
    model_config = MODEL_CONFIGS.get(active_model, MODEL_CONFIGS["deepseek"])
    console.print(f"[bold]Model: {active_model} ({model_config['model']})[/bold]")
    if "extra_params" in model_config and model_config["extra_params"]:
        console.print(f"[dim]Extra params: {model_config['extra_params']}[/dim]")
    console.print(f"[bold]Running benchmark: {versions}, {trials} trials each[/bold]\n")
    results = run_benchmark(versions, trials_per_scenario=trials)
    
    _print_results_table(results)
    
    # Save to model-specific results file
    results_filename = f"results_{active_model}.json"
    results_path = Path(__file__).parent.parent / "benchmark" / results_filename
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    console.print(f"\n[dim]Results saved to {results_path}[/dim]")


@app.command()
def report():
    """Generate report.html from results.json."""
    from ratchet.report.generator import generate_report
    
    results_path = Path(__file__).parent.parent / "benchmark" / "results.json"
    if not results_path.exists():
        console.print("[red]No results.json found. Run 'ratchet bench' first.[/red]")
        raise typer.Exit(1)
    
    output_path = Path(__file__).parent.parent / "report.html"
    generate_report(results_path, output_path)
    console.print(f"[green]Report generated: {output_path}[/green]")


def _print_results_table(results: dict):
    """Print results as a rich table."""
    table = Table(title="Benchmark Results")
    table.add_column("Version", style="cyan")
    table.add_column("Task Success", justify="right")
    table.add_column("Catastrophic Failures", justify="right", style="red")
    
    for version, data in results["summary"].items():
        success_rate = f"{data['task_success_count']}/{data['total_trials']}"
        catastrophes = str(data["catastrophic_failure_count"])
        table.add_row(version, success_rate, catastrophes)
    
    console.print(table)


if __name__ == "__main__":
    app()
