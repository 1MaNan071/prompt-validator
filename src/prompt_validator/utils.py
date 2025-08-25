# src/prompt_validator/utils.py

import json
from typing import Dict, List, Any
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from rich.panel import Panel

def generate_report(results: List[Dict[str, Any]], output_format: str = "both") -> str:
    """
    Generates a validation report in JSON format and displays a CLI report.
    """
    report_data = {
        "summary": {
            "total_files": len(results),
            "files_with_issues": len([r for r in results if r.get("issues")]),
            "total_issues": sum(len(r.get("issues", [])) for r in results)
        },
        "details": results
    }
    
    json_report = json.dumps(report_data, indent=2)
    
    if output_format in ["cli", "both"]:
        display_cli_report(results)
    
    return json_report

def display_cli_report(results: List[Dict[str, Any]]):
    """
    Displays a detailed validation report in the CLI using rich tables.
    """
    console = Console()
    
    # --- Summary ---
    total_files = len(results)
    files_with_issues = len([r for r in results if r.get("issues")])
    
    rprint(Panel(
        f"[bold]Total Files Analyzed:[/] {total_files}\n"
        f"[bold]Files with Issues:[/] {files_with_issues}",
        title="[bold blue]Validation Summary[/bold blue]",
        expand=False
    ))

    if not files_with_issues:
        rprint("\n[bold green]✅ All prompts passed validation. No issues found.[/bold green]")
        return

    # --- Detailed Table ---
    table = Table(
        title="[bold]Detailed Validation Report[/bold]",
        show_header=True, 
        header_style="bold magenta"
    )
    table.add_column("File", style="cyan", width=20)
    table.add_column("Issue Type", style="yellow", width=20)
    table.add_column("Description", style="red", width=40)
    table.add_column("Suggestion", style="green", width=40)
    
    for result in results:
        file_name = result["file"]
        issues = result.get("issues", [])
        
        if not issues:
            table.add_row(file_name, "[green]✔ No Issues[/green]", "All validations passed", "N/A")
        else:
            for i, issue in enumerate(issues):
                # Only show the filename for the first issue of a file
                display_filename = file_name if i == 0 else ""
                table.add_row(
                    display_filename,
                    issue.get("issue_type", "N/A"),
                    issue.get("description", "N/A"),
                    issue.get("suggestion", "N/A")
                )
        # Add a separator after each file's issues for clarity
        if issues:
            table.add_row("", "", "", "", end_section=True)
            
    console.print(table)

def save_report(report_data: str, output_file: str):
    """
    Saves the JSON report data to a file.
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_data)
        rprint(f"\n[bold green]✅ JSON report saved successfully to:[/] {output_file}")
    except Exception as e:
        rprint(f"\n[bold red]❌ Error saving report to {output_file}:[/] {e}")