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
    
    async def run_scraper(scraper, source_name):
        prelim_jobs = await scraper.search(keywords, filters)
        click.echo(f"Found {len(prelim_jobs)} preliminary jobs from {source_name}. Fetching details and scoring...")
        
        from ijt.scoring import score_job
        scored_jobs = []
        for prelim in prelim_jobs:
            try:
                full_job = await scraper.get_job_details(prelim.url)
                if not full_job.title: full_job.title = prelim.title
                if not full_job.company: full_job.company = prelim.company
                if not full_job.location or full_job.location == "Unknown": full_job.location = prelim.location
                
                result = await score_job(full_job, config)
                
                if result.is_eligible:
                    full_job.relevance_score = result.score
                    full_job.matched_keywords = result.matched_keywords
                    scored_jobs.append(full_job)
                    click.echo(f"  [+] {full_job.company} - {full_job.title} (Score: {result.score})")
                else:
                    click.echo(f"  [-] Dropped {full_job.company} - {full_job.title} (Reason: {result.reason})")
            except Exception as e:
                click.echo(f"  [!] Error processing {prelim.url}: {e}")
                
        return scored_jobs
    
    if source in ['linkedin', 'all']:
        from ijt.scrapers.linkedin import LinkedInScraper
        session_dir = Path(config.scraper.get("linkedin", {}).get("session_dir", "data/sessions/linkedin_session"))
        scraper = LinkedInScraper(session_dir)
        jobs.extend(asyncio.run(run_scraper(scraper, "linkedin")))
        
    if source in ['handshake', 'all']:
        from ijt.scrapers.handshake import HandshakeScraper
        session_dir = Path(config.scraper.get("handshake", {}).get("session_dir", "data/sessions/handshake_session"))
        school_url = config.scraper.get("handshake", {}).get("school_url", "https://app.joinhandshake.com")
        scraper = HandshakeScraper(session_dir, school_url)
        jobs.extend(asyncio.run(run_scraper(scraper, "handshake")))
        
    click.echo(f"\nScraped {len(jobs)} eligible jobs in total.")
    for job in sorted(jobs, key=lambda j: j.relevance_score, reverse=True):
        click.echo(f" - {job.title} at {job.company} (Score: {job.relevance_score})")

@cli.command()
@click.option('--source', type=click.Choice(['linkedin', 'handshake', 'all']), default='all', help="Source to scrape")
@click.option('--max', 'max_jobs', type=int, help="Maximum number of jobs to scrape per source")
def run(source, max_jobs):
    """Full pipeline: scrape → tailor → save."""
    from ijt.config import load_config
    import json
    from ijt.pipeline import run_pipeline
    from ijt.db.store import get_db_connection
    
    click.echo("Starting full IJT pipeline...")
    config_path = Path("config.yaml")
    if not config_path.exists():
        click.echo("Error: config.yaml not found.")
        return
        
    resume_path = Path("resume.json")
    if not resume_path.exists():
        click.echo("Error: resume.json not found.")
        return
        
    config = load_config(config_path)
    with open(resume_path, "r", encoding="utf-8") as f:
        resume_data = json.load(f)
        
    db_path = Path("data/ijt.db")
    
    async def _run():
        db = await get_db_connection(db_path)
        try:
            sources = ['linkedin', 'handshake'] if source == 'all' else [source]
            await run_pipeline(config, resume_data, db, sources, max_jobs)
        finally:
            await db.close()
            
    asyncio.run(_run())

@cli.command()
@click.argument('application_folder')
def open(application_folder):
    """Open an application folder in Finder."""
    import subprocess
    from ijt.config import load_config
    
    config_path = Path("config.yaml")
    apps_dir = Path("applications")
    if config_path.exists():
        config = load_config(config_path)
        if hasattr(config, "output") and "applications_dir" in config.output:
            apps_dir = Path(config.output["applications_dir"])
            
    target_path = apps_dir / application_folder
    
    if not target_path.exists():
        click.echo(f"Error: Application folder '{target_path}' does not exist.")
        return
        
    click.echo(f"Opening {target_path} in Finder...")
    subprocess.run(["open", str(target_path)])

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
