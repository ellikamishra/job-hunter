"""
CSV output utilities for job scraper results.
"""
import csv
import os


COLUMNS = ["Company Name", "Job Title", "Location", "Experience", "Skills Matched", "Posted Date", "Link"]


def write_results_csv(filepath: str, jobs: list[dict]) -> None:
    """Write job results to a CSV file."""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=COLUMNS,
            extrasaction="ignore",
        )
        writer.writeheader()
        for job in jobs:
            writer.writerow({
                "Company Name":   job.get("company", ""),
                "Job Title":      job.get("title", ""),
                "Location":       job.get("location", "N/A"),
                "Experience":     job.get("experience", "Not specified"),
                "Skills Matched": job.get("skills_matched", ""),
                "Posted Date":    job.get("posted_date", ""),
                "Link":           job.get("link", ""),
            })
    print(f"\n[+] Results saved to: {filepath}")
    print(f"[+] Total jobs found: {len(jobs)}")
