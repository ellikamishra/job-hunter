"""
Background scheduler that runs daily scraping for all active saved searches.
Can be run standalone: python scheduler.py
Or started as a background thread from the Streamlit app.
"""
import threading
import time
from datetime import datetime

import requests

from companies_db import get_companies_for_location
from db import (
    get_active_searches, get_uploaded_companies,
    save_job_results, get_unnotified_jobs, mark_jobs_notified,
)
from notifier import send_job_notification
from scraper import scrape_company_jobs


def run_search(search: dict) -> int:
    """
    Execute a single saved search and store results.
    Returns the number of NEW jobs found.
    """
    user_id = search["user_id"]
    search_id = search["id"]
    skills = search["skills"]
    locations = search["locations"]
    experience = search["experience"]
    categories = search["categories"]
    source_mode = search["source_mode"]
    scrape_location = search["scrape_location"]
    company_limit = search["company_limit"]
    field = search.get("field", "")

    print(f"\n[Scheduler] Running search #{search_id} '{search['name']}' for user {search.get('email', user_id)}")

    # Load companies based on source mode
    if source_mode == "Upload Excel file":
        companies = get_uploaded_companies(search_id)
        if not companies:
            print(f"  [!] No uploaded companies for search #{search_id}")
            return 0
    else:
        cats = categories if categories else None
        companies = get_companies_for_location([scrape_location], cats)

    if not companies:
        print(f"  [!] No companies found for search #{search_id}")
        return 0

    companies = companies[:company_limit]

    # Scrape each company
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    })

    all_jobs = []
    for company in companies:
        try:
            jobs = scrape_company_jobs(
                company, skills, locations, experience, session, field=field,
            )
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"  [!] Error scraping {company.get('name', '?')}: {e}")
        time.sleep(0.5)

    if not all_jobs:
        print(f"  [=] No jobs found for search #{search_id}")
        return 0

    # Save results (deduplicates by link)
    new_count = save_job_results(user_id, search_id, all_jobs)
    print(f"  [=] Search #{search_id}: {len(all_jobs)} total, {new_count} new")

    # Send notification if enabled and there are new unnotified jobs
    if search.get("notify_email") and new_count > 0:
        email = search.get("email", "")
        if email:
            unnotified = get_unnotified_jobs(search_id)
            if unnotified:
                sent = send_job_notification(email, search["name"], unnotified)
                if sent:
                    mark_jobs_notified(search_id)

    return new_count


def run_all_searches():
    """Run all active saved searches."""
    print(f"\n{'='*60}")
    print(f"[Scheduler] Daily scrape started at {datetime.now().isoformat()}")
    print(f"{'='*60}")

    searches = get_active_searches()
    if not searches:
        print("[Scheduler] No active searches found.")
        return

    print(f"[Scheduler] Found {len(searches)} active search(es)")

    total_new = 0
    for search in searches:
        try:
            new = run_search(search)
            total_new += new
        except Exception as e:
            print(f"[Scheduler] Error in search #{search['id']}: {e}")

    print(f"\n[Scheduler] Done. Total new jobs across all searches: {total_new}")


def start_scheduler_thread(interval_hours: int = 24):
    """Start the scheduler as a daemon thread that runs every `interval_hours`."""
    def _loop():
        while True:
            try:
                run_all_searches()
            except Exception as e:
                print(f"[Scheduler] Unexpected error: {e}")
            # Sleep until next run
            time.sleep(interval_hours * 3600)

    t = threading.Thread(target=_loop, daemon=True, name="job-hunter-scheduler")
    t.start()
    print(f"[Scheduler] Background thread started (interval: {interval_hours}h)")
    return t


if __name__ == "__main__":
    # Run once immediately when called directly
    run_all_searches()
