# src/prompt_validator/main.py

import click
import os
from .validator import PromptValidator
from .utils import generate_report, save_report
from rich import print as rprint

@click.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--auto-fix', is_flag=True, help='Automatically apply suggested fixes after confirmation.')
@click.option('--output', '-o', type=click.Path(), help='Output file for the JSON report.')
@click.option('--format', type=click.Choice(['json', 'cli', 'both']), default='both', help='Format for the report.')
def validate(directory, auto_fix, output, format):
    """
    Validates all .txt prompt files in a specified DIRECTORY.
    """
    rprint(f"[bold blue]Starting validation for prompts in:[/] {directory}")
    
    validator = PromptValidator()
    results = validator.validate_directory(directory)
    
   
    json_report = generate_report(results, format)
    
    if output:
        save_report(json_report, output)
    
   
    if auto_fix:
        rprint("\n[bold yellow]-- Auto-Fix Mode --[/bold yellow]")
        prompts_to_fix = [r for r in results if r.get("suggestion")]
        
        if not prompts_to_fix:
            rprint("[green]No suggestions available to apply.[/green]")
            return
            
        for result in prompts_to_fix:
            file_path = os.path.join(directory, result['file'])
            
           
            if click.confirm(f"\nApply suggested fix to [cyan]{result['file']}[/cyan]?"):
                try:
                    validator.update_prompt_file(file_path, result["suggestion"])
                    rprint(f"[green] Successfully updated:[/] {result['file']}")
                except Exception as e:
                    rprint(f"[red] Failed to update {result['file']}:[/] {e}")
            else:
                rprint(f"[yellow]Skipped update for:[/] {result['file']}")

if __name__ == '__main__':
    validate()