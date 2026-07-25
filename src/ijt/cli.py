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

if __name__ == '__main__':
    cli()
