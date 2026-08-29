# IJT — Intern Jobscraping & Tailoring

> **A free, fully local CLI tool for macOS that automates internship discovery and resume tailoring.**

IJT uses Playwright to scrape job postings from LinkedIn and Handshake, evaluate and score them against your requirements, and a local LLM (via Ollama) to automatically tailor your resume for specific jobs. It outputs clean, ATS-friendly PDFs using Jinja2 and WeasyPrint.

## Prerequisites

1. **[uv](https://github.com/astral-sh/uv)** (Python package manager)
2. **[Ollama](https://ollama.ai/)** (Local LLM runner)
3. **System Dependencies for WeasyPrint**: `brew install pango fontconfig glib libffi`

## Setup & Installation

1. **Clone & Install Dependencies**:
   ```bash
   uv sync
   ```

2. **Install Playwright Browsers**:
   ```bash
   uv run playwright install chromium
   ```

3. **Pull the Local LLM Model**:
   *Make sure the Ollama app is running, then download the model (Warning: ~32GB).*
   ```bash
   ollama pull qwen3.6:27b-q8_0
   ```

4. **Initialize the Project**:
   ```bash
   uv run ijt init
   ```
   *This sets up the SQLite database at `data/ijt.db`.*

## Authentication

IJT uses saved browser sessions rather than hardcoded credentials to avoid anti-bot detection.

Log in manually once for each platform. IJT will open a browser, wait for you to log in, and prompt you to press `ENTER` in your terminal to save the session securely:
```bash
uv run ijt login linkedin
uv run ijt login handshake
```

## Usage

### Full Pipeline (Scrape + Tailor)
Run the full orchestration pipeline. This command scrapes jobs, scores them against your criteria, tailors a resume using Ollama, and renders PDFs for you to submit.
```bash
uv run ijt run
uv run ijt run --dry-run   # Preview matches without saving to disk or DB
```

### Scraping Jobs Only
Scrape jobs, automatically fetch full descriptions, and filter/score them based on your `config.yaml`.
```bash
uv run ijt scrape
uv run ijt scrape --source linkedin --max 10
```

### Application Tracking
Track your job applications locally in the SQLite database.
```bash
# View tracked applications as a rich table
uv run ijt list

# Sort applications by deadline or relevance score
uv run ijt list --sort relevance
uv run ijt list --sort deadline

# Filter applications
uv run ijt list --status not_applied

# Update an application's status
uv run ijt status Google_SWE_Intern_2026 applied

# Open application folder in Finder
uv run ijt open Google_SWE_Intern_2026
```

### Previewing Resumes
Render your base resume into an ATS-friendly PDF and open it immediately for preview.
```bash
uv run ijt resume --preview
```

## Resiliency Features
- **Network Retries**: Built-in exponential backoff for Playwright operations if pages fail to load or timeout.
- **LLM Validation**: The LLM output is strictly validated against the `resume.json` schema. If it hallucinates structural changes or invalid JSON, IJT will automatically issue corrective prompts and retry (up to 3 times).

## Security Note
**Never** commit your `data/sessions/` folder to git, as it contains sensitive authentication cookies.
