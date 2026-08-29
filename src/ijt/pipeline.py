import asyncio
import hashlib
import json
import logging
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from ijt.logging import get_logger
from ijt.db.store import is_url_seen, mark_url_seen, save_job, update_job_status
from ijt.scoring import score_job
from ijt.tailor.client import tailor_for_job
from ijt.renderer.pdf import render_resume_to_pdf

console = Console()

def generate_job_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()

def get_folder_name(job) -> str:
    # Google_SWE_Intern_2026
    company_clean = "".join(c if c.isalnum() else "_" for c in job.company).strip("_")
    title_clean = "".join(c if c.isalnum() else "_" for c in job.title).strip("_")
    year = job.deadline_year if job.deadline_year else datetime.now().year
    return f"{company_clean}_{title_clean}_{year}"

async def run_pipeline(config, resume_data, db, sources: list[str], max_jobs: int = None, dry_run: bool = False):
    logger = get_logger("pipeline")
    logger.info("Starting pipeline run")

    keywords = config.search.get("keywords", [])
    if max_jobs is None:
        max_jobs = config.search.get("max_results_per_source", 50)
        
    filters = dict(config.search)
    filters["max_results_per_source"] = max_jobs

    scrapers = []
    if 'linkedin' in sources or 'all' in sources:
        from ijt.scrapers.linkedin import LinkedInScraper
        session_dir = Path(config.scraper.get("linkedin", {}).get("session_dir", "data/sessions/linkedin_session"))
        scrapers.append(("linkedin", LinkedInScraper(session_dir)))
        
    if 'handshake' in sources or 'all' in sources:
        from ijt.scrapers.handshake import HandshakeScraper
        session_dir = Path(config.scraper.get("handshake", {}).get("session_dir", "data/sessions/handshake_session"))
        school_url = config.scraper.get("handshake", {}).get("school_url", "https://app.joinhandshake.com")
        scrapers.append(("handshake", HandshakeScraper(session_dir, school_url)))

    all_scraped_jobs = []
    
    # 1. Scrape
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        for source_name, scraper in scrapers:
            task = progress.add_task(f"Scraping from {source_name}...", total=None)
            try:
                prelim_jobs = await scraper.search(keywords, filters)
                logger.info(f"Scraped {len(prelim_jobs)} preliminary jobs from {source_name}")
                
                # 2. Deduplicate
                unseen_prelim_jobs = []
                for job in prelim_jobs:
                    url_hash = generate_job_id(job.url)
                    if not await is_url_seen(db, url_hash):
                        unseen_prelim_jobs.append(job)
                        
                logger.info(f"After dedup: {len(unseen_prelim_jobs)} new, {len(prelim_jobs) - len(unseen_prelim_jobs)} skipped")
                
                # Fetch details and score
                for prelim in unseen_prelim_jobs:
                    try:
                        full_job = await scraper.get_job_details(prelim.url)
                        # Merge preliminary details if missing
                        if not full_job.title: full_job.title = prelim.title
                        if not full_job.company: full_job.company = prelim.company
                        if not full_job.location or full_job.location == "Unknown": full_job.location = prelim.location
                        
                        # 3. Filter expired (Not implemented natively, but we can do it here if needed)
                        current_date = datetime.now()
                        if full_job.deadline_year and full_job.deadline_year < current_date.year:
                            logger.info(f"Job {full_job.company} expired based on year")
                            await mark_url_seen(db, generate_job_id(full_job.url), full_job.url, source_name)
                            continue
                            
                        # 4. Score
                        result = await score_job(full_job, config)
                        if result.is_eligible:
                            full_job.relevance_score = result.score
                            full_job.matched_keywords = result.matched_keywords
                            all_scraped_jobs.append(full_job)
                            logger.info(f"Job eligible: {full_job.company} - {full_job.title} (Score: {result.score})")
                        else:
                            logger.info(f"Job not eligible: {full_job.company} - {full_job.title} (Reason: {result.reason})")
                            
                        # Mark seen so we don't fetch again
                        await mark_url_seen(db, generate_job_id(full_job.url), full_job.url, source_name)
                        
                    except Exception as e:
                        logger.error(f"Error fetching details for {prelim.url}: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Error scraping {source_name}: {e}", exc_info=True)
            finally:
                progress.update(task, completed=True)

    if not all_scraped_jobs:
        console.print("[yellow]No new eligible jobs found to process.[/yellow]")
        return
        
    console.print(f"[green]Found {len(all_scraped_jobs)} new eligible jobs![/green]")
    
    # 5. Tailor (sorted by soonest deadline)
    all_scraped_jobs.sort(key=lambda j: (j.deadline_year or 9999, j.deadline_month or 99))
    
    successes, failures = 0, 0
    apps_dir = Path(config.output.get("applications_dir", "./applications")) if hasattr(config, "output") else Path("./applications")
    apps_dir.mkdir(parents=True, exist_ok=True)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Tailoring resumes...", total=len(all_scraped_jobs))
        
        for job in all_scraped_jobs:
            job_id = generate_job_id(job.url)
            logger.info(f"Tailoring for: {job.company} - {job.title}", extra={"job_id": job_id})
            
            try:
                if dry_run:
                    console.print(f"[yellow][DRY RUN][/yellow] Would tailor and save application for {job.company} - {job.title}")
                    successes += 1
                    progress.advance(task)
                    continue

                # Fresh LLM session per job
                # Ensure job is a dictionary for tailor_for_job since it expects job_data
                from dataclasses import asdict
                job_dict = asdict(job)
                
                tailored_resume = await tailor_for_job(resume_data, job_dict, config.llm)
                logger.debug("LLM response received", extra={"job_id": job_id})
                
                # 6. Render PDF
                folder_name = get_folder_name(job)
                job_dir = apps_dir / folder_name
                job_dir.mkdir(parents=True, exist_ok=True)
                
                pdf_path = job_dir / "resume.pdf"
                render_resume_to_pdf(tailored_resume, Path("templates"), pdf_path)
                logger.info(f"PDF rendered: {pdf_path}", extra={"job_id": job_id})
                
                # Save job_info.json
                with open(job_dir / "job_info.json", "w", encoding="utf-8") as f:
                    json.dump(job_dict, f, indent=2)
                
                # 7. Save to DB
                await save_job(db, job_id, job, folder_name, status='not_applied')
                successes += 1
                
            except Exception as e:
                failures += 1
                logger.error(f"Failed to process job: {job.company} - {job.title}", extra={"job_id": job_id, "error_type": type(e).__name__}, exc_info=True)
                # Save error status
                await save_job(db, job_id, job, "", status='error')
                
            progress.advance(task)
            
    logger.info(f"Pipeline complete: {successes} succeeded, {failures} failed")
    console.print(f"\n[bold]Pipeline Complete![/bold] {successes} tailored, {failures} failed.")
