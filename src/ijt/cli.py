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
    from ijt.config import load_config
    
    click.echo(f"Opening browser to log into {source}...")
    config_path = Path("config.yaml")
    config = load_config(config_path) if config_path.exists() else None
    
    if source == 'linkedin':
        from ijt.scrapers.linkedin import LinkedInScraper
        session_dir = Path("data/sessions/linkedin_session")
        if config and hasattr(config, "scraper") and "linkedin" in config.scraper:
            session_dir = Path(config.scraper["linkedin"].get("session_dir", session_dir))
        scraper = LinkedInScraper(session_dir)
        asyncio.run(scraper.login())
    elif source == 'handshake':
        from ijt.scrapers.handshake import HandshakeScraper
        session_dir = Path("data/sessions/handshake_session")
        school_url = "https://app.joinhandshake.com"
        if config and hasattr(config, "scraper") and "handshake" in config.scraper:
            session_dir = Path(config.scraper["handshake"].get("session_dir", session_dir))
            school_url = config.scraper["handshake"].get("school_url", school_url)
        scraper = HandshakeScraper(session_dir, school_url)
        asyncio.run(scraper.login())
        
@cli.command()
@click.option('--source', type=click.Choice(['linkedin', 'handshake', 'all']), default='all', help="Source to scrape")
@click.option('--max', 'max_jobs', type=int, help="Maximum number of jobs to scrape per source")
def scrape(source, max_jobs):
    """Scrape job listings only (no tailoring)."""
    from ijt.config import load_config
    import json
    import dataclasses
    
    click.echo(f"Scraping jobs from {source}...")
    config_path = Path("config.yaml")
    if not config_path.exists():
        click.echo("Error: config.yaml not found.")
        return
        
    config = load_config(config_path)
    keywords = config.search.get("keywords", [])
    
    if max_jobs is None:
        max_jobs = config.search.get("max_results_per_source", 50)
        
    filters = dict(config.search)
    filters["max_results_per_source"] = max_jobs
    
    jobs = []
    
    if source in ['linkedin', 'all']:
        from ijt.scrapers.linkedin import LinkedInScraper
        session_dir = Path(config.scraper.get("linkedin", {}).get("session_dir", "data/sessions/linkedin_session"))
        scraper = LinkedInScraper(session_dir)
        jobs.extend(asyncio.run(scraper.search(keywords, filters)))
        
    if source in ['handshake', 'all']:
        from ijt.scrapers.handshake import HandshakeScraper
        session_dir = Path(config.scraper.get("handshake", {}).get("session_dir", "data/sessions/handshake_session"))
        school_url = config.scraper.get("handshake", {}).get("school_url", "https://app.joinhandshake.com")
        scraper = HandshakeScraper(session_dir, school_url)
        jobs.extend(asyncio.run(scraper.search(keywords, filters)))
        
    click.echo(f"Scraped {len(jobs)} jobs in total.")
    for job in jobs:
        click.echo(f" - {job.title} at {job.company} ({job.url})")


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



@cli.command()
@click.argument('job_file', type=click.Path(exists=True))
def tailor(job_file):
    """Tailor resume for a job using the provided job description file."""
    import json
    import asyncio
    from ijt.config import load_config
    from ijt.tailor.client import tailor_for_job
    
    click.echo(f"Tailoring resume for job in {job_file}...")
    
    config_path = Path("config.yaml")
    if not config_path.exists():
        click.echo("Error: config.yaml not found.")
        return
        
    config = load_config(config_path)
    
    resume_path = Path("resume.json")
    if not resume_path.exists():
        click.echo("Error: resume.json not found.")
        return
        
    with open(resume_path, "r", encoding="utf-8") as f:
        resume_data = json.load(f)
        
    with open(job_file, "r", encoding="utf-8") as f:
        job_data = json.load(f)
        
    # Run tailor
    try:
        result = asyncio.run(tailor_for_job(resume_data, job_data, config.llm))
        
        output_file = Path("tailored_resume.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            
        click.echo(f"Tailored resume saved to {output_file}")
    except Exception as e:
        click.echo(f"Error during tailoring: {e}")

if __name__ == '__main__':
    cli()
