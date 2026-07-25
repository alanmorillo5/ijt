# IJT — Intern Jobscraping & Tailoring

> **A free, fully local CLI tool for macOS that automates internship discovery and resume tailoring.**

IJT uses Playwright to scrape job postings from LinkedIn and Handshake, and a local LLM (via Ollama) to automatically tailor your resume for each specific job. It outputs clean, ATS-friendly PDFs using Jinja2 and WeasyPrint.

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
   *This creates `config.yaml`, `resume.json`, and sets up the SQLite database at `data/ijt.db`.*

## Authentication

IJT uses saved browser sessions rather than hardcoded credentials. Log in manually once:
```bash
uv run ijt login linkedin
uv run ijt login handshake
```

## Usage

```bash
# Full pipeline: Scrape new jobs → Tailor resumes → Save PDFs
uv run ijt run

# Scrape only (no tailoring)
uv run ijt scrape

# Tailor resumes for any scraped jobs that haven't been tailored yet
uv run ijt tailor

# View all tracked applications (sorted by closest deadline)
uv run ijt list

# Update an application's status
uv run ijt status Google_SWE_Intern_2026 applied
```

## Security Note
**Never** commit your `data/sessions/` folder to git, as it contains sensitive authentication cookies.
