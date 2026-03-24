# Job Hunter

**[Live App](https://jobhunterwin.streamlit.app/)**

An automated job hunting tool that scrapes engineering jobs from 150+ companies, saves your search preferences, and sends email notifications when new relevant postings appear.

---

## Features

### User Accounts & Authentication
- Sign up and log in with email and password
- Per-user saved searches and job results
- Session management with secure password hashing

### Field-Aware Job Discovery
- Select your field of study — Computer Science, Data Science, Quant/Finance, Electrical Engineering, Electronics, Machine Learning/AI, or Finance/Fintech
- Skills are auto-suggested based on your selected field
- Role filtering ensures only positions relevant to your field are shown (e.g., a CS student won't see accounting roles)

### Multi-Source Scraping Engine
- **Greenhouse API** — Scrapes jobs from companies using Greenhouse ATS
- **Lever API** — Scrapes jobs from companies using Lever ATS
- **Ashby API** — Scrapes jobs from companies using Ashby ATS
- **Direct HTML scraping** — Parses career pages that don't use a known ATS
- **Google search fallback** — Finds individual job postings via Google when other methods fail
- **LinkedIn & Google company discovery** — Automatically discovers hiring companies from the web based on your skills and location

### Smart Filtering
- **Skills filter** — 80+ built-in skills (Python, C++, Go, Kubernetes, Machine Learning, etc.) plus custom skill input
- **Location filter** — Filter by city (New York, San Francisco, London, Bangalore, etc.), Remote, or Hybrid
- **Experience level filter** — Intern, Entry Level, Mid Level, Senior, Staff/Principal, or Any
- **Date filter** — View jobs posted within the last 1 day, 7 days, 15 days, 30 days, or 3 months
- **Title search** — Free-text search within job titles on the results page
- **Contextual skill matching** — Ambiguous skills like "Go", "R", and "C" are matched using surrounding context to avoid false positives

### Intelligent Experience Matching
- Extracts the qualifications/requirements section from job descriptions for more accurate experience-level detection
- Maps years-of-experience ranges to experience levels (e.g., 0-1 years = Intern, 5-8 years = Senior)
- Falls back to keyword matching (e.g., "senior engineer", "staff developer") when year info isn't available
- Jobs with no experience info are kept (benefit of the doubt)

### Three Company Source Modes
1. **Auto-generate from location** — Uses a curated local database of 150+ companies across Big Tech, Startups, Quant/HFT, Trading Firms, and Fintech, filtered by your selected locations
2. **Discover from web** — Automatically finds companies hiring for your skills via LinkedIn and Google searches
3. **Upload Excel file** — Upload your own company list (columns: company name, career URL, optional location and category)

### Real-Time Scraping Dashboard
- Live progress bar showing scraping progress across all companies
- Real-time status updates showing which company is being scraped
- Live results table that populates as jobs are found — browse and apply while scraping is still running
- Detailed scrape log viewable in an expandable section
- Results history — previous scrape runs are kept in memory and can be restored

### Results & Export
- Interactive results table with sortable columns
- Filter results by company, experience level, location, and posted date
- Direct "Apply" links to job postings
- Download filtered results as CSV
- Results survive navigation between pages

### Saved Searches & Automation
- Save any search configuration (skills, locations, experience, source mode, company list)
- Saved searches are automatically re-run every 24 hours by a background scheduler
- Pause/resume individual saved searches
- Run any saved search on demand with "Run Now"
- View historical job results for each saved search
- Delete searches you no longer need

### Email Notifications
- Get notified by email when new jobs are found by your saved searches
- Toggle notifications on/off per saved search
- HTML-formatted emails with a table of new jobs and direct apply links
- Supports two email backends: **Resend API** (recommended) and **SMTP** (fallback)

---

## Live Demo

The app is deployed and accessible at: **[https://jobhunterwin.streamlit.app/](https://jobhunterwin.streamlit.app/)**

---

## Quick Start

### Prerequisites

- Python 3.8+

### Installation

```bash
git clone https://github.com/ellikamishra/job-hunter.git
cd job-hunter
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Run

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

---

## How It Works

1. **Sign up / Log in** with your email
2. **Select your field** (Computer Science, Data Science, Quant, EE, etc.)
3. **Configure filters** — skills, locations, experience level, company source
4. **Run a scrape** — results populate in real-time
5. **Save the search** — it will automatically re-run every 24 hours
6. **Get notified** — new jobs are emailed to you (requires email configuration)

---

## Email Notifications Setup

Job Hunter supports two email backends. It tries Resend first, then falls back to SMTP.

### Option 1: Resend API (Recommended)

[Resend](https://resend.com) is a modern email API that's simple to set up and works well with Streamlit Cloud.

#### Environment variables

```bash
export RESEND_API_KEY=re_your_api_key_here
export RESEND_FROM="Job Hunter <jobs@yourdomain.com>"
```

#### Or in `.streamlit/secrets.toml`

```toml
[resend]
api_key = "re_your_api_key_here"
from_email = "Job Hunter <jobs@yourdomain.com>"
```

#### Resend setup steps

1. Create an account at [resend.com](https://resend.com)
2. Add and verify your sending domain (or use Resend's test domain for development)
3. Generate an API key from the Resend dashboard
4. Set the `RESEND_API_KEY` and `RESEND_FROM` variables as shown above
5. The `from_email` must use a verified domain (e.g., `jobs@yourdomain.com`)

> **Streamlit Cloud**: Add these as secrets in your app's settings at `https://share.streamlit.io` under **Settings > Secrets**.

### Option 2: SMTP (Fallback)

#### Environment variables

```bash
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=your-email@gmail.com
export SMTP_PASSWORD=your-app-password
export SMTP_FROM=your-email@gmail.com
```

#### Or in `.streamlit/secrets.toml`

```toml
[smtp]
host = "smtp.gmail.com"
port = 587
user = "your-email@gmail.com"
password = "your-app-password"
from_email = "your-email@gmail.com"
```

For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833) (not your regular password).

---

## Project Structure

```
job-hunter/
  app.py           — Streamlit web UI (login, field selection, scraper, saved searches)
  db.py            — SQLite database (users, saved searches, uploaded companies, job results)
  scheduler.py     — Background scheduler for daily automated scraping
  notifier.py      — Email notification sender (Resend + SMTP)
  scraper.py       — Multi-strategy job scraper
  config.py        — URL patterns, experience levels, field-skill mappings
  companies_db.py  — Curated company database (~150 companies)
  csv_io.py        — CSV output handling
  excel_io.py      — Excel input handling
  main.py          — CLI entry point
  data/            — SQLite database (auto-created, gitignored)
```

---

## CLI Usage

```bash
# Scrape big tech companies in New York
python main.py --scrape-location "New York" --categories big_tech --skills Python C++

# Remote-friendly startups
python main.py --scrape-location remote --categories startup --skills Go Kubernetes

# Custom company list
python main.py --input companies.xlsx --skills "System Design" --experience senior mid
```

---

## Standalone Scheduler

Run the scheduler independently (e.g., via cron) to execute all active saved searches:

```bash
python scheduler.py
```

---

## License

MIT
