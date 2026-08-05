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

## Configuration & Scoring System

IJT features a powerful filtering and ranking engine configured in `config.yaml`. 

```yaml
search:
  scoring_engine: "regex" # Fast local text matching, or use "llm" for deep contextual evaluation
  keywords:
    - "software engineer intern"
  
  # Strict Requirements (Knock-Outs): Jobs violating these are instantly discarded.
  eligibility_filters:
    graduation_year: 2028
    graduation_year_variance: 1 # Will accept graduation dates between 2027 and 2029
    major: "Computer Science"
    must_be_internship: true
    
  # Soft Requirements (Scoring): Adds +1.0 point for matches, deducts -0.5 points for misses.
  bonus_keywords:
    - "software"
    - "cloud"
    - "react"
    - "python"
  preferred_locations:
    - "Austin, TX"
    - "Remote"
```

## Usage

### Scraping Jobs
Scrape jobs, automatically fetch full descriptions, and filter/score them based on your `config.yaml`.
```bash
# Scrape from both LinkedIn and Handshake using config limits
uv run ijt scrape

# Scrape from a specific source with a custom limit
uv run ijt scrape --source linkedin --max 10
uv run ijt scrape --source handshake --max 5
```

### Tailoring Resumes
Tailor your base resume (`resume.json`) for a specific job using the local LLM. It verifies the output schema and handles retries automatically.
```bash
uv run ijt tailor path/to/job_file.json
```

### Previewing Resumes
Render your base resume into an ATS-friendly PDF and open it immediately for preview.
```bash
uv run ijt resume --preview
```

### Application Tracking (Basics)
```bash
# View tracked applications
uv run ijt list

# Update an application's status
uv run ijt status Google_SWE_Intern_2026 applied
```

## Security Note
**Never** commit your `data/sessions/` folder to git, as it contains sensitive authentication cookies.
