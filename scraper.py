"""
Core scraper module.
Uses multiple strategies:
  1. Direct HTML scraping of career pages
  2. Greenhouse / Lever / Ashby JSON APIs (no JS needed)
  3. Google search fallback for finding individual job postings
"""
import json
import re
import threading
import time
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests
from bs4 import BeautifulSoup

from config import (
    CAREER_URL_PATTERNS, ATS_PATTERNS, REQUEST_TIMEOUT,
    REQUEST_HEADERS, CAREER_PATH_KEYWORDS, EXPERIENCE_LEVELS,
    KNOWN_ATS_SLUGS, FIELD_ROLE_KEYWORDS,
)


def _normalize_date(raw) -> str:
    """Return ISO date string (YYYY-MM-DD) or empty string."""
    if not raw:
        return ""
    if isinstance(raw, (int, float)):
        try:
            return datetime.fromtimestamp(raw / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        except Exception:
            return ""
    if isinstance(raw, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                    "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%d"):
            try:
                return datetime.strptime(raw.strip()[:26], fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
    return ""


def _get_page(url, session):
    try:
        resp = session.get(url, timeout=REQUEST_TIMEOUT, headers=REQUEST_HEADERS, allow_redirects=True)
        if resp.status_code == 200:
            return BeautifulSoup(resp.text, "lxml")
    except (requests.RequestException, Exception):
        pass
    return None


def _get_json(url, session):
    try:
        resp = session.get(url, timeout=REQUEST_TIMEOUT, headers={**REQUEST_HEADERS, "Accept": "application/json"}, allow_redirects=True)
        if resp.status_code == 200:
            return resp.json()
    except (requests.RequestException, json.JSONDecodeError, Exception):
        pass
    return None


def _is_career_page(soup, url):
    url_lower = url.lower()
    if any(kw in url_lower for kw in CAREER_PATH_KEYWORDS):
        return True
    text = soup.get_text(separator=" ", strip=True).lower()
    career_signals = ["open positions", "job openings", "current openings",
                      "join our team", "we're hiring", "career opportunities",
                      "view all jobs", "search jobs", "apply now", "explore careers"]
    return sum(1 for s in career_signals if s in text) >= 2


def _extract_min_years(text_lower: str) -> int | None:
    """
    Return the minimum years of experience mentioned in the text, or None
    if no experience requirement can be identified.
    Patterns tried in priority order (most specific first).
    """
    patterns = [
        # "9+ years"  /  "9 + years"
        r'(\d+)\s*\+\s*years?',
        # "2-5 years"  /  "2 to 5 years"
        r'(\d+)\s*(?:-|to)\s*\d+\s*years?',
        # "at least 5 years"  /  "minimum 3 years"  /  "min. 4 years"
        r'(?:at\s+least|minimum|min\.?|require[sd]?)\s+(\d+)\s*\+?\s*years?',
        # "5 years of relevant/industry/work experience"
        r'(\d+)\s*years?\s+of\s+[\w\s]*?experience',
        # "5 years experience"  (no "of")
        r'(\d+)\s*years?\s+experience',
        # "experience of 5 years"
        r'experience\s+of\s+(\d+)\s*\+?\s*years?',
    ]
    for pat in patterns:
        m = re.search(pat, text_lower)
        if m:
            # For patterns with one group, group(1) is the year number.
            # For the "X-Y years" pattern the first capture is the minimum.
            return int(m.group(1))
    return None


def _extract_experience_from_text(text: str) -> str:
    text_lower = text.lower()
    years = _extract_min_years(text_lower)
    if years is not None:
        for level, cfg in EXPERIENCE_LEVELS.items():
            if level == "any":
                continue
            lo, hi = cfg["year_range"]
            if lo <= years <= hi:
                return f"{level.capitalize()} ({years}+ yrs)"
        return f"{years}+ years"
    for level, cfg in EXPERIENCE_LEVELS.items():
        if level == "any":
            continue
        for kw in cfg["keywords"]:
            if kw in text_lower:
                return level.capitalize()
    return "Not specified"


def _extract_location_from_text(text):
    text_lower = text.lower()
    if "remote" in text_lower:
        return "Hybrid/Remote" if "hybrid" in text_lower else "Remote"
    match = re.search(r'(?:location|located?\s+(?:in|at)|based\s+in)[:\s]+([A-Z][a-zA-Z\s,]+?)(?:\.|;|\n|$)', text)
    if match:
        return match.group(1).strip()
    return ""


def _matches_skills(text, skills):
    text_lower = text.lower()
    matched = []
    for skill in skills:
        skill_lower = skill.lower()
        if " " in skill_lower:
            if skill_lower in text_lower:
                matched.append(skill)
        else:
            if re.search(r'\b' + re.escape(skill_lower) + r'\b', text_lower):
                matched.append(skill)
    return matched


def _matches_experience(text: str, exp_levels: list[str]) -> bool:
    """
    Return True when the job text matches any of the requested experience levels.
    Strictly rejects jobs that match HIGHER levels than requested.
    Jobs with no experience info pass only if no higher-level keywords are found.
    """
    if not exp_levels or "any" in [e.lower() for e in exp_levels]:
        return True
    text_lower = text.lower()
    years = _extract_min_years(text_lower)

    requested = {e.lower() for e in exp_levels}

    # All ordered levels (excluding "any")
    _ORDERED_LEVELS = ["intern", "entry", "mid", "senior", "staff"]
    # Levels NOT requested
    excluded = {lvl for lvl in _ORDERED_LEVELS if lvl not in requested}

    # If years are found, check if they fall in a requested range
    if years is not None:
        for level in requested:
            if level not in EXPERIENCE_LEVELS:
                continue
            lo, hi = EXPERIENCE_LEVELS[level]["year_range"]
            if lo <= years <= hi:
                return True
        # Years found but don't match any requested level → reject
        return False

    # No year info — check keywords
    # First, reject if any EXCLUDED level's keywords match
    for lvl in excluded:
        if lvl not in EXPERIENCE_LEVELS:
            continue
        for kw in EXPERIENCE_LEVELS[lvl]["keywords"]:
            if kw in text_lower:
                return False

    # Accept if any REQUESTED level's keywords match
    for lvl in requested:
        if lvl not in EXPERIENCE_LEVELS:
            continue
        for kw in EXPERIENCE_LEVELS[lvl]["keywords"]:
            if kw in text_lower:
                return True

    # No experience info at all — include (benefit of doubt)
    return True


def _matches_location(text, locations):
    if not locations or "any" in [l.lower() for l in locations]:
        return True
    text_lower = text.lower()
    return any(loc.lower() in text_lower for loc in locations)


def _try_greenhouse_api(slug, session, company_name, skills, locations, exp_levels):
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    data = _get_json(url, session)
    if not data or "jobs" not in data:
        return []
    jobs = []
    for item in data["jobs"]:
        title = item.get("title", "")
        location = item.get("location", {}).get("name", "")
        link = item.get("absolute_url", "")
        content_text = ""
        if item.get("id"):
            detail = _get_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{item['id']}", session)
            if detail and detail.get("content"):
                content_text = BeautifulSoup(detail["content"], "lxml").get_text(separator=" ", strip=True)
            time.sleep(0.1)
        full_text = f"{title} {location} {content_text}"
        skill_matches = _matches_skills(full_text, skills) if skills else []
        if skills and not skill_matches:
            continue
        if not _matches_location(location, locations):
            continue
        if not _matches_experience(full_text, exp_levels):
            continue
        jobs.append({"company": company_name, "title": title, "location": location or "See posting",
                     "experience": _extract_experience_from_text(full_text),
                     "skills_matched": ", ".join(skill_matches) if skill_matches else "General match",
                     "posted_date": _normalize_date(item.get("updated_at", "")),
                     "link": link})
    return jobs


def _try_lever_api(slug, session, company_name, skills, locations, exp_levels):
    data = _get_json(f"https://api.lever.co/v0/postings/{slug}?mode=json", session)
    if not data or not isinstance(data, list):
        return []
    jobs = []
    for item in data:
        title = item.get("text", "")
        categories = item.get("categories", {})
        location = categories.get("location", "")
        link = item.get("hostedUrl", "") or item.get("applyUrl", "")
        desc_plain = item.get("descriptionPlain", "")
        lists_text = ""
        for lst in item.get("lists", []):
            lists_text += " " + lst.get("text", "")
            lists_text += " " + " ".join(
                BeautifulSoup(li.get("content", ""), "lxml").get_text()
                for li in lst.get("items", []) if isinstance(li, dict))
        full_text = f"{title} {location} {categories.get('commitment','')} {categories.get('team','')} {desc_plain} {lists_text}"
        skill_matches = _matches_skills(full_text, skills) if skills else []
        if skills and not skill_matches:
            continue
        if not _matches_location(location, locations):
            continue
        if not _matches_experience(full_text, exp_levels):
            continue
        jobs.append({"company": company_name, "title": title, "location": location or "See posting",
                     "experience": _extract_experience_from_text(full_text),
                     "skills_matched": ", ".join(skill_matches) if skill_matches else "General match",
                     "posted_date": _normalize_date(item.get("createdAt", 0)),
                     "link": link})
    return jobs


def _try_ashby_api(slug, session, company_name, skills, locations, exp_levels):
    data = _get_json("https://api.ashbyhq.com/posting-api/job-board/" + slug, session)
    if not data or "jobs" not in data:
        return []
    jobs = []
    for item in data["jobs"]:
        title = item.get("title", "")
        location = item.get("location", "")
        link = item.get("jobUrl", "") or item.get("applicationUrl", "")
        full_text = f"{title} {location} {item.get('department', '')}"
        skill_matches = _matches_skills(full_text, skills) if skills else []
        if skills and not skill_matches:
            continue
        if not _matches_location(location, locations):
            continue
        if not _matches_experience(full_text, exp_levels):
            continue
        jobs.append({"company": company_name, "title": title, "location": location or "See posting",
                     "experience": _extract_experience_from_text(full_text),
                     "skills_matched": ", ".join(skill_matches) if skill_matches else "General match",
                     "posted_date": _normalize_date(item.get("publishedAt", "") or item.get("updatedAt", "")),
                     "link": link})
    return jobs


_JOB_BOARD_DOMAINS = [
    "greenhouse.io", "lever.co", "ashbyhq.com", "jobs.ashbyhq.com",
    "linkedin.com/jobs", "smartrecruiters.com", "workday.com",
    "myworkdayjobs.com", "boards.greenhouse.io", "api.lever.co",
    "indeed.com/viewjob", "simplify.jobs",
]

_SKIP_TITLES = {
    "click here", "here", "apply", "apply now", "learn more", "view",
    "details", "read more", "see all", "view all", "more", "next",
    "previous", "home", "about", "contact", "back", "jobs", "careers",
}


def _is_valid_job_url(url: str) -> bool:
    """Return True only for absolute URLs pointing to known job boards."""
    return url.startswith("http") and any(d in url for d in _JOB_BOARD_DOMAINS)


def _portal_skills_label(skills: list[str]) -> str:
    """Label for portal results where skills were used as search terms, not matched in card text."""
    return f"Searched: {', '.join(skills)}" if skills else "General match"


# Keywords that confirm a role is engineering/technical
_TECH_ROLE_INCLUDE = [
    "engineer", "developer", "programmer", "architect", "scientist",
    "devops", "sre", "site reliability", "backend", "frontend", "fullstack",
    "full stack", "full-stack", "infrastructure", "platform",
    "machine learning", "deep learning", "ml", "ai engineer",
    "quantitative", "quant", "software", "systems", "firmware", "embedded",
    "compiler", "algorithm", "security engineer", "application security",
    "cloud engineer", "network engineer", "database administrator", "dba",
    "data engineer", "research scientist", "applied scientist",
    "research engineer", "solutions engineer", "technical lead",
    "tech lead", "staff engineer", "principal engineer",
]

# Keywords that indicate clearly non-engineering roles — excluded even if no tech keyword present
_NON_TECH_ROLE_EXCLUDE = [
    "recruiter", "recruiting", "talent acquisition",
    "hr ", "human resource", "people partner", "people analyst",
    "marketing", "brand manager", "growth manager", "growth associate",
    "sales", "account executive", "account manager", "client partner",
    "client solutions", "business development",
    "administrative", "executive assistant", "office manager",
    "publicity", "communications manager", "public relations",
    "legal counsel", "paralegal", "compliance officer",
    "credit analyst", "financial analyst", "accountant", "accounting",
    "sourcing specialist", "sourcer",
    "documentary", "editorial", "content manager",
    "executive researcher",  # IBM role from CSV - not tech
]


def _is_technical_role(title: str, field: str = "") -> bool:
    """
    Return True if the job title looks like an engineering/technical role.
    When a field is specified, uses field-specific include/exclude keywords
    for stricter filtering.
    """
    t = title.lower()
    # Explicit exclusion wins first
    if any(kw in t for kw in _NON_TECH_ROLE_EXCLUDE):
        return False

    # Field-specific filtering (stricter)
    if field and field in FIELD_ROLE_KEYWORDS:
        field_cfg = FIELD_ROLE_KEYWORDS[field]
        # Reject if matches field-specific exclusions
        if any(kw in t for kw in field_cfg["exclude"]):
            return False
        # Must match at least one field-specific include keyword
        return any(kw in t for kw in field_cfg["include"])

    # Generic: must match at least one engineering keyword
    return any(kw in t for kw in _TECH_ROLE_INCLUDE)


def _fetch_linkedin_description(url, session):
    """Fetch a LinkedIn job page and extract the description text."""
    try:
        resp = session.get(url, timeout=REQUEST_TIMEOUT, headers=REQUEST_HEADERS)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "lxml")
        # LinkedIn guest view puts description in a specific div
        desc_el = soup.find("div", class_=lambda c: c and "description" in c)
        if desc_el:
            return desc_el.get_text(separator=" ", strip=True)
        # Fallback: look for any show-more section
        desc_el = soup.find("div", class_=lambda c: c and "show-more" in c)
        if desc_el:
            return desc_el.get_text(separator=" ", strip=True)
        return ""
    except Exception:
        return ""


def _parse_linkedin_cards(soup, company_name, skills, locations, exp_levels,
                          field="", session=None) -> list[dict]:
    """Extract job dicts from a LinkedIn jobs-guest HTML response.
    When field is set, applies field-specific role filtering.
    When session is provided, fetches job descriptions to verify experience."""
    candidates: list[dict] = []
    for card in soup.find_all("div", class_=lambda c: c and "base-card" in c):
        title_el    = card.find("h3", class_=lambda c: c and "base-search-card__title" in c)
        company_el  = card.find("h4", class_=lambda c: c and "base-search-card__subtitle" in c)
        location_el = card.find("span", class_=lambda c: c and "job-search-card__location" in c)
        link_el     = card.find("a", class_=lambda c: c and "base-card__full-link" in c)
        if not title_el or not link_el:
            continue
        title         = title_el.get_text(strip=True)
        card_company  = company_el.get_text(strip=True)  if company_el  else ""
        card_location = location_el.get_text(strip=True) if location_el else ""
        time_el = card.find("time")
        posted_date = _normalize_date(time_el.get("datetime", "")) if time_el else ""
        link = link_el.get("href", "").split("?")[0]
        if not link.startswith("http"):
            continue
        # Skip clearly different companies (soft match handles subsidiaries like "Google DeepMind")
        if card_company and company_name.lower() not in card_company.lower():
            continue
        # Only keep engineering / technical roles (field-aware)
        if not _is_technical_role(title, field):
            continue
        if not _matches_location(card_location or "", locations):
            continue
        candidates.append({
            "title": title, "card_company": card_company,
            "card_location": card_location, "posted_date": posted_date,
            "link": link,
        })

    # Fetch job descriptions to verify experience and field relevance
    jobs: list[dict] = []
    for cand in candidates:
        title = cand["title"]
        card_location = cand["card_location"]
        link = cand["link"]

        # Try to fetch description for experience verification
        desc = ""
        if session and exp_levels:
            desc = _fetch_linkedin_description(link, session)
            time.sleep(0.1)

        full_text = f"{title} {cand['card_company']} {card_location} {desc}"

        # Re-check experience with actual description
        if not _matches_experience(full_text, exp_levels):
            continue

        # If field is set, verify description mentions relevant skills/terms
        if field and desc and field in FIELD_ROLE_KEYWORDS:
            field_includes = FIELD_ROLE_KEYWORDS[field]["include"]
            desc_lower = desc.lower()
            title_lower = title.lower()
            # At least one field keyword must appear in title or description
            if not any(kw in title_lower or kw in desc_lower for kw in field_includes):
                continue

        jobs.append({
            "company":        company_name,
            "title":          title,
            "location":       card_location or "See posting",
            "experience":     _extract_experience_from_text(full_text),
            "skills_matched": _portal_skills_label(skills),
            "posted_date":    cand["posted_date"],
            "link":           link,
        })
    return jobs


def _try_linkedin_jobs(company_name, skills, locations, exp_levels, session, field=""):
    """
    Search LinkedIn's public guest job API (no auth required).
    Skills are baked into the search query — we do NOT re-match keywords against
    card text because LinkedIn cards contain no job description.
    Paginates up to 3 pages (~30 results) and supplements with a company-only
    search to catch roles whose titles don't mention specific skill keywords.
    """
    loc = locations[0] if locations else ""
    skill_str = " ".join(skills) if skills else ""
    seen_links: set[str] = set()
    all_jobs: list[dict] = []

    def _fetch_page(query: str, start: int) -> list[dict]:
        try:
            resp = session.get(
                "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search",
                params={"keywords": query, "location": loc, "start": start, "count": 25},
                headers={**REQUEST_HEADERS, "Accept": "text/html,application/xhtml+xml,*/*"},
                timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code != 200:
                return []
            return _parse_linkedin_cards(
                BeautifulSoup(resp.text, "lxml"), company_name, skills, locations, exp_levels,
                field=field, session=session
            )
        except Exception:
            return []

    # Pass 1: company + skills query, up to 3 pages
    query_with_skills = f'"{company_name}" {skill_str}'.strip()
    for start in [0, 25, 50]:
        batch = _fetch_page(query_with_skills, start)
        for j in batch:
            if j["link"] not in seen_links:
                seen_links.add(j["link"])
                all_jobs.append(j)
        if not batch:  # no more results on this page
            break
        time.sleep(0.15)

    # Pass 2: company-only query (catches roles whose titles lack skill keywords)
    # Only run if skills were provided AND we got few results from pass 1
    if skills and len(all_jobs) < 10:
        query_company_only = f'"{company_name}"'
        for start in [0, 25]:
            batch = _fetch_page(query_company_only, start)
            for j in batch:
                if j["link"] not in seen_links:
                    seen_links.add(j["link"])
                    all_jobs.append(j)
            if not batch:
                break
            time.sleep(0.15)

    return all_jobs


def _try_remotive_jobs(company_name, skills, locations, exp_levels, session):
    """
    Search Remotive.com public JSON API — good for remote roles at any company.
    Only runs when locations include 'remote'.
    """
    is_remote = any("remote" in loc.lower() for loc in locations) if locations else False
    if not is_remote:
        return []
    search = " ".join(skills[:5]) if skills else company_name
    try:
        resp = session.get(
            "https://remotive.com/api/remote-jobs",
            params={"search": search, "limit": 50},
            headers={**REQUEST_HEADERS, "Accept": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        raw_jobs = data.get("jobs", [])
        jobs: list[dict] = []
        for item in raw_jobs:
            title        = item.get("title", "")
            card_company = item.get("company_name", "")
            link         = item.get("url", "")
            desc         = item.get("description", "")
            if not title or not link or not link.startswith("http"):
                continue
            if card_company and company_name.lower() not in card_company.lower():
                continue
            full_text = f"{title} {card_company} remote {desc[:500]}"
            skill_matches = _matches_skills(full_text, skills) if skills else []
            if skills and not skill_matches:
                continue
            if not _matches_experience(full_text, exp_levels):
                continue
            jobs.append({
                "company":        company_name,
                "title":          title,
                "location":       "Remote",
                "experience":     _extract_experience_from_text(full_text),
                "skills_matched": ", ".join(skill_matches) if skill_matches else _portal_skills_label(skills),
                "posted_date":    _normalize_date(item.get("publication_date", "")),
                "link":           link,
            })
        return jobs
    except Exception:
        return []


# Stubs kept for forward-compatibility — these sites block automated scraping
def _try_indeed_jobs(company_name, skills, locations, exp_levels, session):   return []
def _try_wellfound_jobs(company_name, skills, locations, exp_levels, session): return []
def _try_simplify_jobs(company_name, skills, locations, exp_levels, session):  return []


def _google_search_jobs(company_name, skills, locations, session):
    # Use ALL skills in query (no truncation)
    skill_query = " OR ".join(f'"{s}"' for s in skills) if skills else ""
    loc_query = " OR ".join(f'"{l}"' for l in locations) if locations else ""
    sites = " OR ".join(f"site:{d}" for d in [
        "boards.greenhouse.io", "jobs.lever.co", "jobs.ashbyhq.com",
        "linkedin.com/jobs", "smartrecruiters.com", "myworkdayjobs.com",
        "simplify.jobs",
    ])
    query = f'"{company_name}" jobs {skill_query} {loc_query} ({sites})'
    try:
        resp = session.get(
            "https://www.google.com/search",
            params={"q": query, "num": 20},
            timeout=REQUEST_TIMEOUT,
            headers=REQUEST_HEADERS,
            allow_redirects=True,
        )
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "lxml")
        jobs, seen = [], set()
        for a_tag in soup.find_all("a", href=True):
            raw_href = a_tag["href"]
            if "/url?q=" in raw_href:
                m = re.search(r'/url\?q=([^&]+)', raw_href)
                href = urllib.parse.unquote(m.group(1)) if m else raw_href
            else:
                href = raw_href
            if not _is_valid_job_url(href):
                continue
            if href in seen:
                continue
            link_text = a_tag.get_text(separator=" ", strip=True)
            if not link_text or link_text.lower() in _SKIP_TITLES or len(link_text) < 5:
                path = urllib.parse.urlparse(href).path.rstrip("/").split("/")[-1]
                link_text = path.replace("-", " ").replace("_", " ").title() or "Job Posting"
            seen.add(href)
            jobs.append({
                "company":        company_name,
                "title":          link_text[:200],
                "location":       "See posting",
                "experience":     "Not specified",
                "skills_matched": "Google search match",
                "posted_date":    "",
                "link":           href,
            })
        return jobs
    except Exception:
        return []


def discover_career_page(company, session):
    if company.get("career_url"):
        return [company["career_url"]]
    domain = company["domain"]
    slug = domain.split(".")[0]
    found_urls = []
    for pattern in CAREER_URL_PATTERNS:
        url = pattern.format(domain=domain)
        soup = _get_page(url, session)
        if soup and _is_career_page(soup, url):
            found_urls.append(url)
            break
        time.sleep(0.15)
    if not found_urls:
        for pattern in ATS_PATTERNS:
            url = pattern.format(slug=slug)
            soup = _get_page(url, session)
            if soup:
                found_urls.append(url)
                break
            time.sleep(0.15)
    if not found_urls:
        homepage_url = f"https://www.{domain}"
        soup = _get_page(homepage_url, session)
        if soup:
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"].lower()
                text = a_tag.get_text(strip=True).lower()
                if any(kw in href or kw in text for kw in CAREER_PATH_KEYWORDS):
                    found_urls.append(urllib.parse.urljoin(homepage_url, a_tag["href"]))
                    break
    return found_urls


def _extract_jobs_from_page(url, soup, company_name, skills, locations, exp_levels):
    jobs, seen_links = [], set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        full_url = urllib.parse.urljoin(url, href)
        if full_url in seen_links:
            continue
        if href.startswith("#") or href.startswith("mailto:") or href.startswith("javascript:"):
            continue
        if any(skip in href.lower() for skip in ["login","signup","register","privacy","terms",
               "cookie","blog","news","about-us","contact","facebook.com","twitter.com",
               "linkedin.com/company","instagram.com","youtube.com"]):
            continue
        link_text = a_tag.get_text(separator=" ", strip=True)
        parent = a_tag.parent
        context_text = ""
        for _ in range(3):
            if parent:
                context_text = parent.get_text(separator=" ", strip=True)
                parent = parent.parent
                if len(context_text) > 50:
                    break
        combined_text = f"{link_text} {context_text}"
        if len(link_text) < 3:
            continue
        if link_text.lower() in ["apply","apply now","learn more","view","details","read more",
                                  "see all","view all","more","next","previous","home","about","contact","back"]:
            continue
        href_lower = href.lower()
        is_job_link = (any(kw in href_lower for kw in ["job","position","opening","career","role",
                          "apply","requisition","req","posting","/jv/","greenhouse","lever.co","workday","smartrecruiters"])
                       or any(kw in link_text.lower() for kw in ["engineer","developer","manager","analyst","designer",
                              "scientist","architect","lead","director","specialist","coordinator","consultant","intern","associate"]))
        if not is_job_link:
            continue
        skill_matches = _matches_skills(combined_text, skills) if skills else []
        if skills and not skill_matches:
            continue
        extracted_location = _extract_location_from_text(combined_text) or ""
        if not _matches_location(extracted_location, locations):
            continue
        if not _matches_experience(combined_text, exp_levels):
            continue
        seen_links.add(full_url)
        jobs.append({"company": company_name, "title": link_text[:200],
                     "location": extracted_location or "See posting",
                     "experience": _extract_experience_from_text(combined_text),
                     "skills_matched": ", ".join(skill_matches) if skill_matches else "General match",
                     "posted_date": "",
                     "link": full_url})
    return jobs


def _crawl_subpages(base_url, soup, session, company_name, skills, locations, exp_levels, max_pages=5):
    jobs, visited, to_visit = [], {base_url}, []
    for a_tag in soup.find_all("a", href=True):
        text = a_tag.get_text(strip=True).lower()
        href = a_tag["href"].lower()
        if any(kw in text or kw in href for kw in ["all jobs","all positions","view all","see all",
               "all openings","search jobs","job search","page=2","page/2","next"]):
            full_url = urllib.parse.urljoin(base_url, a_tag["href"])
            if full_url not in visited:
                to_visit.append(full_url)
    for url in to_visit[:max_pages]:
        if url in visited:
            continue
        visited.add(url)
        time.sleep(0.2)
        sub_soup = _get_page(url, session)
        if sub_soup:
            jobs.extend(_extract_jobs_from_page(url, sub_soup, company_name, skills, locations, exp_levels))
    return jobs


def scrape_company_jobs(company, skills, locations, exp_levels, session, field=""):
    company_name = company["name"]
    domain = company["domain"]
    slug = domain.split(".")[0]
    print(f"\n{'='*60}")
    print(f"[*] Scraping: {company_name} ({domain})")
    print(f"{'='*60}")
    all_jobs: list[dict] = []

    # ── Strategy 1: Known ATS slug (Greenhouse / Lever / Ashby) ──────────────
    known = KNOWN_ATS_SLUGS.get(domain, {})
    if known:
        platform  = known["platform"]
        known_slug = known["slug"]
        print(f"  [>] Known ATS: {platform} slug '{known_slug}'")
        api_map = {"greenhouse": _try_greenhouse_api, "lever": _try_lever_api, "ashby": _try_ashby_api}
        if platform in api_map:
            r = api_map[platform](known_slug, session, company_name, skills, locations, exp_levels)
            if r:
                print(f"  [+] {platform} API: {len(r)} jobs")
                all_jobs.extend(r)

    # ── Strategy 2: Generic ATS slug guessing ─────────────────────────────────
    if not all_jobs:
        for api_name, api_func in [("Greenhouse", _try_greenhouse_api),
                                    ("Lever",      _try_lever_api),
                                    ("Ashby",      _try_ashby_api)]:
            if all_jobs:
                break
            print(f"  [>] Trying {api_name} slug '{slug}'…")
            r = api_func(slug, session, company_name, skills, locations, exp_levels)
            if r:
                print(f"  [+] {api_name}: {len(r)} jobs")
                all_jobs.extend(r)

    # ── Strategy 3: Alt slugs (company name variants) ─────────────────────────
    if not all_jobs:
        alt_slugs = ({
            company_name.lower().replace(" ", ""),
            company_name.lower().replace(" ", "-"),
            company_name.lower().replace(" ", "_"),
        } - {slug})
        for alt in alt_slugs:
            if all_jobs:
                break
            for api_func in [_try_greenhouse_api, _try_lever_api, _try_ashby_api]:
                r = api_func(alt, session, company_name, skills, locations, exp_levels)
                if r:
                    print(f"  [+] ATS with slug '{alt}': {len(r)} jobs")
                    all_jobs.extend(r)
                    break
                time.sleep(0.2)

    # ── Stage A4: HTML career page (if ATS APIs all failed) ──────────────────
    if not all_jobs:
        career_urls = discover_career_page(company, session)
        if career_urls:
            for career_url in career_urls:
                print(f"  [>] Career page: {career_url}")
                soup = _get_page(career_url, session)
                if not soup:
                    continue
                page_jobs = _extract_jobs_from_page(career_url, soup, company_name, skills, locations, exp_levels)
                sub_jobs  = _crawl_subpages(career_url, soup, session, company_name, skills, locations, exp_levels)
                n = len(page_jobs) + len(sub_jobs)
                if n:
                    print(f"  [+] HTML scrape: {n} jobs")
                all_jobs.extend(page_jobs)
                all_jobs.extend(sub_jobs)
        else:
            print(f"  [!] No career page found")

    # ── Stage B: Job portals — ALWAYS run (supplement ATS/HTML results) ──────
    # LinkedIn: works reliably with pagination across up to 3 pages
    print(f"  [>] LinkedIn (paginated)…")
    r = _try_linkedin_jobs(company_name, skills, locations, exp_levels, session, field=field)
    if r:
        print(f"  [+] LinkedIn: {len(r)} jobs")
        all_jobs.extend(r)

    # Remotive: free JSON API — only for remote searches
    if any("remote" in loc.lower() for loc in locations) if locations else False:
        print(f"  [>] Remotive (remote jobs)…")
        r = _try_remotive_jobs(company_name, skills, locations, exp_levels, session)
        if r:
            print(f"  [+] Remotive: {len(r)} jobs")
            all_jobs.extend(r)

    # ── Stage C: Google (only if everything above is empty) ──────────────────
    if not all_jobs:
        print(f"  [>] Google search fallback…")
        r = _google_search_jobs(company_name, skills, locations, session)
        if r:
            print(f"  [+] Google: {len(r)} results")
            all_jobs.extend(r)

    # ── Final: drop bad URLs, deduplicate ─────────────────────────────────────
    all_jobs = [j for j in all_jobs if j.get("link", "").startswith("http")]
    seen: set[str] = set()
    unique_jobs = [j for j in all_jobs if j["link"] not in seen and not seen.add(j["link"])]
    print(f"  [=] Total unique jobs for {company_name}: {len(unique_jobs)}")
    return unique_jobs


# ── Dynamic company discovery ─────────────────────────────────────────────────

def discover_companies_from_web(
    skills: list[str],
    locations: list[str],
    max_companies: int = 50,
    session: requests.Session | None = None,
    progress_callback=None,
) -> list[dict]:
    """
    Discover companies hiring for given skills + locations by scraping LinkedIn
    and Google with many diverse queries and pagination.

    Each returned dict has: {"name", "domain", "career_url" (optional)}
    """
    if session is None:
        session = requests.Session()
        session.headers.update(REQUEST_HEADERS)

    found: dict[str, dict] = {}   # domain → company dict (dedup by domain)
    loc_str = locations[0] if locations else ""

    def _log(msg: str):
        print(msg)
        if progress_callback:
            progress_callback(msg)

    def _add(name: str, domain: str | None = None):
        if not name or len(name) < 2:
            return
        d = domain or _company_name_to_domain(name)
        if d and d not in found:
            found[d] = {"name": name, "domain": d}
            _log(f"  [+] Discovered: {name} ({d})")

    def _linkedin_search(query: str, pages: int = 3):
        """Search LinkedIn and extract company names from job cards."""
        for page in range(pages):
            if len(found) >= max_companies:
                return
            start = page * 25
            try:
                resp = session.get(
                    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search",
                    params={"keywords": query, "location": loc_str, "start": start, "count": 25},
                    headers={**REQUEST_HEADERS, "Accept": "text/html,*/*"},
                    timeout=REQUEST_TIMEOUT,
                )
                if resp.status_code != 200:
                    return
                soup = BeautifulSoup(resp.text, "lxml")
                cards = soup.find_all("div", class_=lambda c: c and "base-card" in c)
                if not cards:
                    return  # no more results
                for card in cards:
                    company_el = card.find("h4", class_=lambda c: c and "base-search-card__subtitle" in c)
                    if company_el:
                        _add(company_el.get_text(strip=True))
                    if len(found) >= max_companies:
                        return
            except Exception:
                return
            time.sleep(0.15)

    # ── Strategy 1: LinkedIn — individual skill queries (high diversity) ───────
    _log("[>] Discovering companies via LinkedIn (by skill)…")
    # Search each skill individually — finds different companies per skill
    for skill in skills:
        if len(found) >= max_companies:
            break
        _linkedin_search(f'"{skill}" engineer', pages=2)

    # ── Strategy 2: LinkedIn — combined skill queries with locations ───────────
    _log("[>] LinkedIn: combined skill + location queries…")
    skill_combos = []
    # Pairs of skills for more targeted results
    for i in range(0, len(skills), 2):
        pair = skills[i:i+2]
        skill_combos.append(" ".join(f'"{s}"' for s in pair))
    # Also the full skill string
    all_skills_str = " OR ".join(f'"{s}"' for s in skills[:5]) if skills else ""
    skill_combos.append(all_skills_str)

    for combo in skill_combos:
        if len(found) >= max_companies:
            break
        for loc in locations[:3]:
            if len(found) >= max_companies:
                break
            _linkedin_search(f'{combo} {loc}', pages=2)

    # ── Strategy 3: LinkedIn — role-based queries (catches companies
    #    that don't mention specific skills in the job title) ──────────────────
    _log("[>] LinkedIn: role-based queries…")
    role_queries = [
        "software engineer", "backend developer", "fullstack engineer",
        "systems engineer", "data engineer", "ML engineer",
        "quantitative developer", "platform engineer", "infrastructure engineer",
        "DevOps engineer", "SRE", "frontend developer",
    ]
    for role in role_queries:
        if len(found) >= max_companies:
            break
        _linkedin_search(role, pages=1)

    # ── Strategy 4: Google — diverse queries across job boards ─────────────────
    _log("[>] Discovering companies via Google…")
    google_queries = []
    # Individual skill queries across job boards
    for skill in skills[:6]:
        google_queries.append(f'"{skill}" jobs {loc_str} (site:greenhouse.io OR site:lever.co OR site:jobs.ashbyhq.com)')
        google_queries.append(f'"{skill}" engineer hiring {loc_str} site:linkedin.com/jobs')
    # Broader queries
    google_queries.extend([
        f'{all_skills_str} jobs {loc_str} site:linkedin.com/jobs',
        f'{all_skills_str} careers {loc_str} site:greenhouse.io OR site:lever.co',
        f'software engineer {loc_str} hiring 2026 site:linkedin.com/jobs',
        f'startup hiring {all_skills_str} {loc_str}',
        f'{all_skills_str} {loc_str} careers site:smartrecruiters.com OR site:myworkdayjobs.com',
    ])
    for gq in google_queries:
        if len(found) >= max_companies:
            break
        try:
            resp = session.get(
                "https://www.google.com/search",
                params={"q": gq, "num": 20},
                headers=REQUEST_HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "lxml")
            for a_tag in soup.find_all("a", href=True):
                raw_href = a_tag["href"]
                if "/url?q=" in raw_href:
                    m = re.search(r'/url\?q=([^&]+)', raw_href)
                    href = urllib.parse.unquote(m.group(1)) if m else ""
                else:
                    continue  # skip Google's own links
                if not href.startswith("http"):
                    continue
                # Extract company from job board URLs
                name, domain = _extract_company_from_url(href)
                if name and domain and domain not in found:
                    found[domain] = {"name": name, "domain": domain}
                    _log(f"  [+] Discovered: {name} ({domain})")
                if len(found) >= max_companies:
                    break
        except Exception:
            continue
        time.sleep(0.2)

    _log(f"[=] Discovered {len(found)} unique companies")
    return list(found.values())


def _company_name_to_domain(name: str) -> str:
    """Best-effort: turn a company name into a plausible domain."""
    # Clean up common suffixes
    cleaned = re.sub(r'\s*(Inc\.?|Corp\.?|LLC|Ltd\.?|Co\.?|Group|Technologies|Labs?)$', '', name, flags=re.IGNORECASE).strip()
    if not cleaned:
        return ""
    slug = cleaned.lower().replace(" ", "").replace(",", "").replace("&", "and")
    slug = re.sub(r'[^a-z0-9]', '', slug)
    if len(slug) < 2:
        return ""
    return f"{slug}.com"


def _extract_company_from_url(url: str) -> tuple[str, str]:
    """Extract (company_name, domain) from a job-board URL."""
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or ""
    path = parsed.path

    # boards.greenhouse.io/COMPANY/...
    if "greenhouse.io" in host:
        m = re.match(r'/([a-zA-Z0-9_-]+)', path)
        if m:
            slug = m.group(1)
            name = slug.replace("-", " ").replace("_", " ").title()
            return name, f"{slug.lower()}.com"

    # jobs.lever.co/COMPANY/...
    if "lever.co" in host:
        m = re.match(r'/([a-zA-Z0-9_-]+)', path)
        if m:
            slug = m.group(1)
            name = slug.replace("-", " ").replace("_", " ").title()
            return name, f"{slug.lower()}.com"

    # jobs.ashbyhq.com/COMPANY
    if "ashbyhq.com" in host:
        m = re.match(r'/([a-zA-Z0-9_-]+)', path)
        if m:
            slug = m.group(1)
            name = slug.replace("-", " ").replace("_", " ").title()
            return name, f"{slug.lower()}.com"

    # linkedin.com/jobs/view/TITLE-at-COMPANY-ID
    if "linkedin.com" in host and "-at-" in path:
        m = re.search(r'-at-([a-z0-9-]+?)-\d+$', path)
        if m:
            slug = m.group(1)
            name = slug.replace("-", " ").title()
            return name, f"{slug.replace('-', '')}.com"

    return "", ""
