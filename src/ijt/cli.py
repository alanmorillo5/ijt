import click
from pathlib import Path
import asyncio

from ijt.db.store import init_db

@click.group()
def cli():
    """IJT — Intern Jobscraping & Tailoring"""
    pass

@cli.command()
def init():
    """Initialize IJT in the current directory."""
    click.echo("Initializing IJT project...")
    db_path = Path("data/ijt.db")
    asyncio.run(init_db(db_path))
    click.echo("Done. Database created at data/ijt.db")

@cli.command()
@click.argument('source', type=click.Choice(['linkedin', 'handshake']))
def login(source):
    """Open a browser to log in manually and save the session."""
    click.echo(f"Opening browser to log into {source}...")

@cli.command()
def list():
    """List all tracked applications with status."""
    click.echo("Listing tracked applications...")

@cli.command()
@click.argument('application_folder')
@click.argument('status')
def status(application_folder, status):
    """Update application status."""
    click.echo(f"Updating {application_folder} to {status}...")

@cli.command()
@click.option('--preview', is_flag=True, help="Render base resume as PDF and open it")
def resume(preview):
    """Validate or preview base resume."""
    from ijt.renderer.pdf import render_resume_to_pdf
    import json
    import subprocess
    
    resume_path = Path("resume.json")
    if not resume_path.exists():
        click.echo("Error: resume.json not found.")
        return
        
    with open(resume_path, "r", encoding="utf-8") as f:
        resume_data = json.load(f)
        
    click.echo("resume.json is valid.")
    
    if preview:
        template_dir = Path("templates")
        output_path = Path("resume_preview.pdf")
        
        click.echo("Rendering PDF preview...")
        render_resume_to_pdf(resume_data, template_dir, output_path)
        click.echo(f"PDF saved to {output_path}")
        
        # Open on macOS
        subprocess.run(["open", str(output_path)])

if __name__ == '__main__':
    cli()
