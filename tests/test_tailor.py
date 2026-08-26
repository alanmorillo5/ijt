import json
import asyncio
from pathlib import Path
from ijt.config import load_config
from ijt.tailor.client import tailor_for_job
import traceback

async def main():
    config = load_config(Path("config.yaml"))
    with open("resume.json", "r") as f:
        resume_data = json.load(f)
    with open("fixtures/sample_job.json", "r") as f:
        job_data = json.load(f)
    try:
        res = await tailor_for_job(resume_data, job_data, config.llm)
        print("Success!")
    except Exception as e:
        traceback.print_exc()

asyncio.run(main())
