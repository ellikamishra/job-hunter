# Job Hunter

An automated job hunting tool that scrapes engineering jobs, saves your search preferences, and sends email notifications when new relevant postings appear.

## Features

- **User accounts** — Sign up with email, save multiple search configurations
- **Daily automated scraping** — Background scheduler runs your saved searches every 24 hours
- **Email notifications** — Get notified when new jobs matching your filters are found
- **Save uploaded Excel lists** — Upload your target company list once; it's re-scraped daily
- **Multi-source scraping** — Greenhouse, Lever, Ashby APIs, LinkedIn, career pages, and Google
- **Smart filtering** — Filter by skills, location, experience level, and field of study
- **Field-aware role filtering** — Only shows roles relevant to your selected field (CS, Data Science, EE, etc.)
- **150+ built-in companies** — Curated database across big tech, startups, quant, trading, and fintech
- **Live results** — Browse and apply to jobs while scraping is still in progress

## Quick Start

### Prerequisites

- Python 3.8+

### Installation

```bash
git clone https://github.com/<your-username>/job-hunter.git
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

## How It Works

1. **Sign up / Log in** with your email
2. **Select your field** (Computer Science, Data Science, Quant, EE, etc.)
3. **Configure filters** — skills, locations, experience level, company categories
4. **Run a scrape** — results populate in real-time
5. **Save the search** — it will automatically re-run every 24 hours
6. **Get notified** — new jobs are emailed to you (requires SMTP configuration)

## Email Notifications (SMTP Setup)

To enable email notifications, set these environment variables or add them to `.streamlit/secrets.toml`:

### Environment variables

```bash
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=your-email@gmail.com
export SMTP_PASSWORD=your-app-password
export SMTP_FROM=your-email@gmail.com
```

### Or in `.streamlit/secrets.toml`

```toml
[smtp]
host = "smtp.gmail.com"
port = 587
user = "your-email@gmail.com"
password = "your-app-password"
from_email = "your-email@gmail.com"
```

For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833) (not your regular password).

## Project Structure

```
job-hunter/
  app.py           — Streamlit web UI (login, field selection, scraper, saved searches)
  db.py            — SQLite database (users, saved searches, uploaded companies, job results)
  scheduler.py     — Background scheduler for daily automated scraping
  notifier.py      — Email notification sender (SMTP)
  scraper.py       — Multi-strategy job scraper
  config.py        — URL patterns, experience levels, field-skill mappings
  companies_db.py  — Curated company database (~150 companies)
  csv_io.py        — CSV output handling
  excel_io.py      — Excel input handling
  main.py          — CLI entry point
  data/            — SQLite database (auto-created, gitignored)
```

## CLI Usage

```bash
# Scrape big tech companies in New York
python main.py --scrape-location "New York" --categories big_tech --skills Python C++

# Remote-friendly startups
python main.py --scrape-location remote --categories startup --skills Go Kubernetes

# Custom company list
python main.py --input companies.xlsx --skills "System Design" --experience senior mid
```

## Standalone Scheduler

Run the scheduler independently (e.g., via cron) to execute all active saved searches:

```bash
python scheduler.py
```

## License

MIT
