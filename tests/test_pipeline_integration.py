import pytest
import pytest_asyncio
import aiosqlite
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from ijt.pipeline import run_pipeline
from ijt.db.store import init_db
from ijt.config import load_config
from ijt.scrapers.base import ScrapedJob

@pytest_asyncio.fixture
async def test_db(tmp_path):
    db_path = tmp_path / "test_ijt.db"
    await init_db(db_path)
    db = await aiosqlite.connect(db_path)
    yield db
    await db.close()

@pytest.fixture
def mock_config(tmp_path):
    config_dict = {
        "search": {
            "keywords": ["software engineer"],
            "max_results_per_source": 2,
            "scoring_engine": "regex"
        },
        "scraper": {
            "linkedin": {"session_dir": str(tmp_path)},
            "handshake": {"session_dir": str(tmp_path), "school_url": "https://test.joinhandshake.com"}
        },
        "output": {
            "applications_dir": str(tmp_path / "applications")
        }
    }
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        import yaml
        yaml.dump(config_dict, f)
    return load_config(config_file)

@pytest.fixture
def mock_resume():
    return {"personal": {"name": "Test User"}, "skills": {"languages": ["Python"]}}

@pytest.mark.asyncio
@patch('ijt.scrapers.linkedin.LinkedInScraper')
@patch('ijt.scrapers.handshake.HandshakeScraper')
@patch('ijt.pipeline.tailor_for_job')
@patch('ijt.pipeline.render_resume_to_pdf')
async def test_pipeline_success(mock_render, mock_tailor, MockHandshake, MockLinkedIn, test_db, mock_config, mock_resume):
    # Setup mock scrapers
    mock_li_instance = AsyncMock()
    mock_li_instance.search.return_value = [
        ScrapedJob(title="SWE Intern", company="Google", location="Remote", url="https://li.com/1", source="linkedin", description="test", posted_date=None, deadline_month=None, deadline_year=None, requirements=[])
    ]
    mock_li_instance.get_job_details.return_value = ScrapedJob(
        title="SWE Intern", company="Google", location="Remote", url="https://li.com/1", source="linkedin", description="Must know Python", posted_date=None, deadline_month=None, deadline_year=None, requirements=["Python"]
    )
    MockLinkedIn.return_value = mock_li_instance
    MockHandshake.return_value = AsyncMock(search=AsyncMock(return_value=[])) # Return empty for handshake
    
    # Setup mock tailor
    mock_tailor.return_value = {"tailored": "resume"}
    
    # Run pipeline
    await run_pipeline(mock_config, mock_resume, test_db, sources=['linkedin'])
    
    # Assert LLM / PDF called
    assert mock_tailor.called
    assert mock_render.called
    
    # Assert DB populated
    async with test_db.execute("SELECT count(*) FROM jobs") as cursor:
        job_count = (await cursor.fetchone())[0]
        assert job_count == 1
        
    async with test_db.execute("SELECT count(*) FROM seen_urls") as cursor:
        seen_count = (await cursor.fetchone())[0]
        assert seen_count == 1

@pytest.mark.asyncio
@patch('ijt.scrapers.linkedin.LinkedInScraper')
@patch('ijt.scrapers.handshake.HandshakeScraper')
@patch('ijt.pipeline.tailor_for_job')
async def test_pipeline_deduplication(mock_tailor, MockHandshake, MockLinkedIn, test_db, mock_config, mock_resume):
    # Setup mock scrapers
    mock_li_instance = AsyncMock()
    mock_li_instance.search.return_value = [
        ScrapedJob(title="SWE Intern", company="Google", location="Remote", url="https://li.com/seen", source="linkedin", description="", posted_date=None, deadline_month=None, deadline_year=None, requirements=[])
    ]
    MockLinkedIn.return_value = mock_li_instance
    MockHandshake.return_value = AsyncMock(search=AsyncMock(return_value=[]))
    
    # Pre-populate DB with seen URL
    from ijt.pipeline import generate_job_id
    from ijt.db.store import mark_url_seen
    await mark_url_seen(test_db, generate_job_id("https://li.com/seen"), "https://li.com/seen", "linkedin")
    
    # Run pipeline
    await run_pipeline(mock_config, mock_resume, test_db, sources=['linkedin'])
    
    # Should not call tailor since URL is seen and skipped
    assert not mock_tailor.called
    assert not mock_li_instance.get_job_details.called

@pytest.mark.asyncio
@patch('ijt.scrapers.linkedin.LinkedInScraper')
@patch('ijt.scrapers.handshake.HandshakeScraper')
@patch('ijt.pipeline.tailor_for_job')
async def test_pipeline_error_handling(mock_tailor, MockHandshake, MockLinkedIn, test_db, mock_config, mock_resume):
    mock_li_instance = AsyncMock()
    mock_li_instance.search.return_value = [
        ScrapedJob(title="SWE Intern", company="ErrorCorp", location="Remote", url="https://li.com/err", source="linkedin", description="test", posted_date=None, deadline_month=None, deadline_year=None, requirements=[])
    ]
    mock_li_instance.get_job_details.return_value = ScrapedJob(
        title="SWE Intern", company="ErrorCorp", location="Remote", url="https://li.com/err", source="linkedin", description="test", posted_date=None, deadline_month=None, deadline_year=None, requirements=[]
    )
    MockLinkedIn.return_value = mock_li_instance
    MockHandshake.return_value = AsyncMock(search=AsyncMock(return_value=[]))
    
    # Make tailor raise an error
    mock_tailor.side_effect = Exception("LLM generation failed")
    
    # Run pipeline
    await run_pipeline(mock_config, mock_resume, test_db, sources=['linkedin'])
    
    # Assert DB marks job as error
    async with test_db.execute("SELECT status FROM jobs WHERE company='ErrorCorp'") as cursor:
        status = (await cursor.fetchone())[0]
        assert status == "error"
