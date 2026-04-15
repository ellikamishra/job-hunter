"""
Job Hunter — Streamlit UI with user accounts, saved searches, and notifications.
Run with: streamlit run app.py
"""
import csv
import io
import os
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import requests
import streamlit as st
import pandas as pd

from companies_db import (
    get_companies_for_location,
    LOCATION_ALIASES,
    COMPANIES_DB,
)
from config import EXPERIENCE_LEVELS, FIELD_SKILLS
from db import (
    create_user, authenticate,
    save_search, update_search, get_searches, get_search, delete_search,
    save_uploaded_companies, get_uploaded_companies,
    save_job_results, get_job_results,
    get_unnotified_jobs, mark_jobs_notified,
)
from excel_io import read_companies
from notifier import is_smtp_configured, send_job_notification
from scraper import scrape_company_jobs, discover_companies_from_web

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Job Hunter",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Constants ─────────────────────────────────────────────────────────────────
VALID_CATEGORIES = ["big_tech", "startup", "quant", "trading", "fintech"]

CATEGORY_LABELS = {
    "big_tech": "Big Tech",
    "startup":  "Startups",
    "quant":    "Quant / HFT",
    "trading":  "Trading Firms",
    "fintech":  "Fintech",
}

EXPERIENCE_LABELS = {
    "intern": "Intern",
    "entry":  "Entry Level",
    "mid":    "Mid Level",
    "senior": "Senior",
    "staff":  "Staff / Principal",
    "any":    "Any",
}

COMMON_SKILLS = sorted([
    "Python", "C++", "C", "Java", "Go", "Rust", "TypeScript", "JavaScript",
    "Scala", "Kotlin", "Swift", "R", "MATLAB", "Haskell", "OCaml",
    "Distributed Systems", "System Design", "Low Latency", "High Frequency Trading",
    "Kubernetes", "Docker", "Terraform", "AWS", "GCP", "Azure",
    "Linux", "gRPC", "Kafka", "Redis", "Spark", "Flink",
    "Machine Learning", "Deep Learning", "LLM", "NLP", "Computer Vision",
    "PyTorch", "TensorFlow", "JAX", "Reinforcement Learning",
    "Data Engineering", "SQL", "dbt", "Airflow", "Pandas", "NumPy",
    "Quantitative Research", "Algorithmic Trading", "Market Making",
    "Statistical Modeling", "Time Series", "Options Pricing",
    "Risk Management", "Fixed Income", "Derivatives",
    "React", "Next.js", "Node.js", "GraphQL", "REST API",
    "PostgreSQL", "MongoDB", "Elasticsearch",
    "Security", "Cryptography", "Penetration Testing",
    "Embedded Systems", "Firmware", "FPGA", "Verilog", "VHDL",
    "PCB Design", "Signal Processing", "ASIC Design", "CUDA",
])

FIELD_ICONS = {
    "Computer Science":       "CS",
    "Data Science":           "DS",
    "Quant / Finance":        "QF",
    "Electrical Engineering":  "EE",
    "Electronics":            "EL",
    "Machine Learning / AI":  "ML",
    "Finance / Fintech":      "FT",
}

COMMON_JOB_LOCATIONS = sorted([
    "Remote", "New York", "San Francisco", "Seattle", "Austin",
    "Boston", "Chicago", "Los Angeles", "London", "Singapore",
    "Bangalore", "Toronto", "Berlin", "Amsterdam", "Hybrid",
])

CANONICAL_LOCATIONS = sorted(
    [loc.title() for loc in LOCATION_ALIASES.keys()]
)

ALL_DB_LOCATIONS = sorted({
    loc.title()
    for _, _, locs, _ in COMPANIES_DB
    for loc in locs
})

DATE_FILTER_OPTIONS = ["Any", "Last 1 day", "Last 7 days", "Last 15 days", "Last 30 days", "Last 3 months"]
DATE_FILTER_DAYS = {
    "Last 1 day": 1,
    "Last 7 days": 7,
    "Last 15 days": 15,
    "Last 30 days": 30,
    "Last 3 months": 90,
}


# ── Helpers ───────────────────────────────────────────────────────────────────
class _StdoutCapture:
    def __init__(self):
        self.lines: list[str] = []
        self._orig = sys.stdout

    def write(self, text: str):
        self._orig.write(text)
        if text.strip():
            self.lines.append(text.rstrip())

    def flush(self):
        self._orig.flush()

    def __enter__(self):
        sys.stdout = self
        return self

    def __exit__(self, *_):
        sys.stdout = self._orig


def _jobs_to_df(jobs: list[dict]) -> pd.DataFrame:
    rows = [
        {
            "Company":         j.get("company", ""),
            "Job Title":       j.get("title", ""),
            "Location":        j.get("location", "N/A"),
            "Experience":      j.get("experience", "Not specified"),
            "Skills Matched":  j.get("skills_matched", j.get("skills", "")),
            "Posted Date":     j.get("posted_date", ""),
            "Link":            j.get("link", ""),
        }
        for j in jobs
    ]
    df = pd.DataFrame(rows, columns=["Company", "Job Title", "Location",
                                      "Experience", "Skills Matched",
                                      "Posted Date", "Link"])
    df["Posted Date"] = pd.to_datetime(df["Posted Date"], errors="coerce")
    cutoff_3mo = datetime.now() - timedelta(days=90)
    df = df[df["Posted Date"].isna() | (df["Posted Date"] >= cutoff_3mo)]
    df = df.sort_values("Posted Date", ascending=False, na_position="last")
    df = df.reset_index(drop=True)
    return df


def _df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


# ── Session state init ────────────────────────────────────────────────────────
for key, default in {
    "page": "login",
    "user": None,
    "selected_field": None,
    "default_skills": [],
    "suggested_skills": [],
    "results_df": pd.DataFrame(),
    "log_lines": [],
    "custom_skills": [],
    "custom_job_locs": [],
    "editing_search": None,
    "last_scrape_empty": False,
    "results_history": [],  # list of (timestamp, description, df) — capped at 1 to limit memory
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN / SIGNUP PAGE
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.user is None:
    st.markdown("# Job Hunter")
    st.markdown("### Automated job scraping with daily notifications")
    st.markdown("---")

    tab_login, tab_signup = st.tabs(["Log In", "Sign Up"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_pw")
            submitted = st.form_submit_button("Log In", use_container_width=True, type="primary")
            if submitted:
                if not email or not password:
                    st.error("Please enter both email and password.")
                else:
                    user = authenticate(email, password)
                    if user:
                        st.session_state.user = user
                        st.session_state.page = "landing"
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")

    with tab_signup:
        with st.form("signup_form"):
            new_email = st.text_input("Email", key="signup_email")
            new_pw = st.text_input("Password", type="password", key="signup_pw")
            confirm_pw = st.text_input("Confirm Password", type="password", key="signup_pw2")
            submitted = st.form_submit_button("Create Account", use_container_width=True, type="primary")
            if submitted:
                if not new_email or not new_pw:
                    st.error("Please fill in all fields.")
                elif new_pw != confirm_pw:
                    st.error("Passwords do not match.")
                elif len(new_pw) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    uid = create_user(new_email, new_pw)
                    if uid:
                        st.success("Account created! You can now log in.")
                    else:
                        st.error("An account with this email already exists.")

    st.stop()


# ── User is logged in from here on ────────────────────────────────────────────
user = st.session_state.user


# ══════════════════════════════════════════════════════════════════════════════
# LANDING PAGE — Field selection
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "landing":
    # Top bar
    col_title, col_user = st.columns([6, 2])
    with col_title:
        st.markdown("# Job Hunter")
        st.markdown("### Find engineering jobs across 150+ companies")
    with col_user:
        st.caption(f"Logged in as **{user['email']}**")
        c1, c2 = st.columns(2)
        if c1.button("My Searches", use_container_width=True):
            st.session_state.page = "my_searches"
            st.rerun()
        if c2.button("Log Out", use_container_width=True):
            st.session_state.user = None
            st.session_state.page = "login"
            st.rerun()

    st.markdown("---")
    st.markdown("#### What's your field?")
    st.caption("Pick your field to see relevant skills as options. You can mix and match skills from any field on the next page.")

    cols = st.columns(3)
    fields = list(FIELD_SKILLS.keys())

    for i, field in enumerate(fields):
        col = cols[i % 3]
        icon = FIELD_ICONS.get(field, "??")
        skills_preview = ", ".join(FIELD_SKILLS[field][:5]) + "..."
        with col:
            st.markdown(f"**[{icon}] {field}**")
            st.caption(skills_preview)
            if st.button(f"Select", key=f"field_{field}", use_container_width=True):
                st.session_state.selected_field = field
                field_skills = [s for s in FIELD_SKILLS[field] if s in COMMON_SKILLS]
                other_skills = []
                for other_field, other_list in FIELD_SKILLS.items():
                    if other_field != field:
                        for s in other_list:
                            if s in COMMON_SKILLS and s not in field_skills and s not in other_skills:
                                other_skills.append(s)
                st.session_state.suggested_skills = field_skills + other_skills
                st.session_state.default_skills = []
                st.session_state.page = "scraper"
                st.rerun()

    st.markdown("---")
    st.markdown("**Or skip field selection** and pick skills manually:")
    if st.button("Skip -- go to scraper", use_container_width=False):
        st.session_state.selected_field = None
        st.session_state.default_skills = []
        st.session_state.suggested_skills = []
        st.session_state.page = "scraper"
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# MY SEARCHES PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "my_searches":
    col_title, col_user = st.columns([6, 2])
    with col_title:
        st.markdown("# My Saved Searches")
    with col_user:
        st.caption(f"Logged in as **{user['email']}**")
        c1, c2 = st.columns(2)
        if c1.button("New Search", use_container_width=True, type="primary"):
            st.session_state.page = "landing"
            st.rerun()
        if c2.button("Log Out", use_container_width=True):
            st.session_state.user = None
            st.session_state.page = "login"
            st.rerun()

    st.markdown("---")

    searches = get_searches(user["id"])

    if not searches:
        st.info("You don't have any saved searches yet. Run a scrape and save it to enable daily notifications!")
    else:
        for s in searches:
            with st.expander(
                f"{'[Active]' if s['active'] else '[Paused]'} {s['name']} -- "
                f"{s['field'] or 'Any field'} | "
                f"Skills: {', '.join(s['skills'][:3])}{'...' if len(s['skills']) > 3 else ''} | "
                f"Updated: {s['updated_at'][:10]}",
                expanded=False,
            ):
                col1, col2 = st.columns(2)
                col1.markdown(f"**Field:** {s['field'] or 'Any'}")
                col1.markdown(f"**Skills:** {', '.join(s['skills']) or 'Any'}")
                col1.markdown(f"**Locations:** {', '.join(s['locations']) or 'Any'}")
                col2.markdown(f"**Experience:** {', '.join(s['experience']) or 'Any'}")
                col2.markdown(f"**Source:** {s['source_mode']}")
                col2.markdown(f"**Notifications:** {'On' if s['notify_email'] else 'Off'}")

                if s["source_mode"] == "Upload Excel file":
                    uploaded = get_uploaded_companies(s["id"])
                    if uploaded:
                        col1.markdown(f"**Uploaded companies:** {len(uploaded)}")

                # Job history
                jobs = get_job_results(s["id"])
                if jobs:
                    st.markdown(f"**{len(jobs)}** jobs found so far")
                    if st.button(f"View Results", key=f"view_{s['id']}", use_container_width=True):
                        st.session_state.results_df = _jobs_to_df(jobs)
                        st.session_state.page = "results"
                        st.session_state.viewing_search_id = s["id"]
                        st.rerun()

                # Actions
                act_cols = st.columns(4)
                # Toggle active
                if s["active"]:
                    if act_cols[0].button("Pause", key=f"pause_{s['id']}", use_container_width=True):
                        update_search(s["id"], active=0)
                        st.rerun()
                else:
                    if act_cols[0].button("Resume", key=f"resume_{s['id']}", use_container_width=True):
                        update_search(s["id"], active=1)
                        st.rerun()

                # Toggle notifications
                notif_label = "Notif Off" if s["notify_email"] else "Notif On"
                if act_cols[1].button(notif_label, key=f"notif_{s['id']}", use_container_width=True):
                    turning_on = not s["notify_email"]
                    update_search(s["id"], notify_email=turning_on)
                    if turning_on and not is_smtp_configured():
                        st.warning("Email notifications enabled, but the server's email service is not yet configured. You won't receive emails until an admin sets up SMTP.")
                    st.rerun()

                # Run now
                if act_cols[2].button("Run Now", key=f"run_{s['id']}", use_container_width=True):
                    from scheduler import run_search
                    full_search = get_search(s["id"])
                    full_search["email"] = user["email"]
                    with st.spinner("Running search..."):
                        new_count = run_search(full_search)
                    st.success(f"Done! {new_count} new job(s) found.")
                    st.rerun()

                # Delete
                if act_cols[3].button("Delete", key=f"del_{s['id']}", use_container_width=True):
                    delete_search(s["id"])
                    st.rerun()

    st.markdown("---")
    st.caption(
        "Active searches are automatically scraped once every 24 hours. "
        "If email notifications are enabled, you'll receive an email when new jobs are found."
    )


# ══════════════════════════════════════════════════════════════════════════════
# RESULTS PAGE (viewing saved search results)
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "results":
    if st.button("Back to My Searches"):
        st.session_state.page = "my_searches"
        st.rerun()

    df = st.session_state.results_df
    if df.empty:
        st.info("No results to display.")
    else:
        st.subheader(f"Results -- {len(df)} jobs")

        with st.expander("Filter / search results", expanded=False):
            fc1, fc2, fc3, fc4 = st.columns(4)
            company_filter = fc1.multiselect("Company", options=sorted(df["Company"].unique()), default=[])
            exp_filter = fc2.multiselect("Experience", options=sorted(df["Experience"].unique()), default=[])
            loc_filter = fc3.multiselect("Location", options=sorted(df["Location"].unique()), default=[])
            date_filter = fc4.selectbox("Posted within", options=DATE_FILTER_OPTIONS, index=0)
            title_search = st.text_input("Search in Job Title", placeholder="e.g. engineer, quant, analyst")

        filtered = df.copy()
        if company_filter:
            filtered = filtered[filtered["Company"].isin(company_filter)]
        if exp_filter:
            filtered = filtered[filtered["Experience"].isin(exp_filter)]
        if loc_filter:
            filtered = filtered[filtered["Location"].isin(loc_filter)]
        if title_search:
            filtered = filtered[filtered["Job Title"].str.contains(title_search, case=False, na=False)]
        if date_filter != "Any":
            days = DATE_FILTER_DAYS[date_filter]
            cutoff = datetime.now() - timedelta(days=days)
            filtered = filtered[filtered["Posted Date"] >= cutoff]

        st.caption(f"Showing {len(filtered)} of {len(df)} jobs")

        st.dataframe(
            filtered, use_container_width=True, height=520,
            column_config={
                "Company":        st.column_config.TextColumn("Company", width="medium"),
                "Job Title":      st.column_config.TextColumn("Job Title", width="large"),
                "Location":       st.column_config.TextColumn("Location", width="medium"),
                "Experience":     st.column_config.TextColumn("Experience", width="medium"),
                "Skills Matched": st.column_config.TextColumn("Skills Matched", width="medium"),
                "Posted Date":    st.column_config.DateColumn("Posted Date", format="YYYY-MM-DD", width="small"),
                "Link":           st.column_config.LinkColumn("Apply Link", width="medium", display_text="Apply"),
            },
            hide_index=True,
        )

        csv_bytes = _df_to_csv_bytes(filtered)
        st.download_button(
            label="Download CSV",
            data=csv_bytes,
            file_name=f"jobs_{time.strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            type="primary",
        )


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPER PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "scraper":
    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.title("Job Hunter")
        st.caption(f"Logged in as **{user['email']}**")
        if st.session_state.selected_field:
            st.caption(f"Field: **{st.session_state.selected_field}**")

        nav_cols = st.columns(3)
        if nav_cols[0].button("Change field", use_container_width=True):
            st.session_state.page = "landing"
            # Keep results_df so user doesn't lose previous results
            st.rerun()
        if nav_cols[1].button("My Searches", use_container_width=True):
            st.session_state.page = "my_searches"
            st.rerun()
        if nav_cols[2].button("Log Out", use_container_width=True):
            st.session_state.user = None
            st.session_state.page = "login"
            st.rerun()

        st.divider()

        # ── Source mode ──────────────────────────────────────────────────────
        source_mode = st.radio(
            "Company source",
            ["Auto-generate from location", "Discover from web", "Upload Excel file"],
            index=0,
            help=(
                "**Auto-generate**: uses our curated 150+ company database. "
                "**Discover from web**: dynamically finds companies hiring for your skills. "
                "**Upload Excel**: provide your own list (saved for daily scraping)."
            ),
        )

        st.divider()

        uploaded_file = None
        scrape_location = ""
        selected_categories = list(VALID_CATEGORIES)

        if source_mode == "Auto-generate from location":
            scrape_location = st.selectbox(
                "Location",
                options=["any"] + ALL_DB_LOCATIONS,
                index=0,
            )
            selected_categories = st.multiselect(
                "Company categories",
                options=VALID_CATEGORIES,
                default=VALID_CATEGORIES,
                format_func=lambda c: CATEGORY_LABELS[c],
            )

        elif source_mode == "Discover from web":
            st.info("Companies will be discovered dynamically based on your skills and locations.")

        else:
            uploaded_file = st.file_uploader(
                "Upload Excel (.xlsx)",
                type=["xlsx"],
                help="Must have columns: Company Name, Domain, Career URL (optional). "
                     "Your list will be saved for daily automated scraping.",
            )

        st.divider()

        # ── Skills ───────────────────────────────────────────────────────────
        st.subheader("Skills filter")
        if st.session_state.suggested_skills:
            skill_options = st.session_state.suggested_skills + [
                s for s in COMMON_SKILLS if s not in st.session_state.suggested_skills
            ]
        else:
            skill_options = COMMON_SKILLS
        selected_skills = st.multiselect(
            "Skills (field-relevant shown first)" if st.session_state.selected_field else "Common skills",
            options=skill_options,
            default=st.session_state.default_skills,
        )
        custom_skill_input = st.text_input("Add custom skill", placeholder="e.g. CUDA, FIX Protocol", key="custom_skill_input")
        if st.button("+ Add skill", use_container_width=True):
            skill = custom_skill_input.strip()
            if skill and skill not in st.session_state.custom_skills:
                st.session_state.custom_skills.append(skill)

        if st.session_state.custom_skills:
            st.caption("Custom skills: " + ", ".join(st.session_state.custom_skills))
            if st.button("Clear custom skills", use_container_width=True):
                st.session_state.custom_skills = []

        all_skills = selected_skills + st.session_state.custom_skills

        st.divider()

        # ── Job location filter ──────────────────────────────────────────────
        st.subheader("Job location filter")
        selected_job_locs = st.multiselect("Locations", options=COMMON_JOB_LOCATIONS, default=[])
        custom_loc_input = st.text_input("Add custom location", placeholder="e.g. Hyderabad, Dublin", key="custom_loc_input")
        if st.button("+ Add location", use_container_width=True):
            loc = custom_loc_input.strip()
            if loc and loc not in st.session_state.custom_job_locs:
                st.session_state.custom_job_locs.append(loc)

        if st.session_state.custom_job_locs:
            st.caption("Custom locations: " + ", ".join(st.session_state.custom_job_locs))
            if st.button("Clear custom locations", use_container_width=True):
                st.session_state.custom_job_locs = []

        all_job_locs = selected_job_locs + st.session_state.custom_job_locs

        st.divider()

        # ── Experience ───────────────────────────────────────────────────────
        st.subheader("Experience level")
        selected_exp = st.multiselect(
            "Levels",
            options=list(EXPERIENCE_LEVELS.keys()),
            default=[],
            format_func=lambda e: EXPERIENCE_LABELS.get(e, e),
        )

        st.divider()

        # ── Company limit ────────────────────────────────────────────────────
        st.subheader("Company limit")
        company_limit = st.number_input("Max companies", min_value=1, max_value=500, value=50, step=10)

        st.divider()

        with st.expander("Advanced settings"):
            delay = st.slider("Delay between companies (s)", 0.0, 5.0, 1.0, 0.5)

        st.divider()

        # ── Save search toggle ───────────────────────────────────────────────
        save_this_search = st.checkbox(
            "Save this search for daily scraping",
            value=True,
            help="Save your filter settings. The search will run automatically every 24 hours "
                 "and notify you via email when new jobs are found.",
        )
        if save_this_search:
            search_name = st.text_input("Search name", value=f"{st.session_state.selected_field or 'General'} search")
            enable_notifications = st.checkbox("Email notifications for new jobs", value=True)
            if enable_notifications and not is_smtp_configured():
                st.warning("Email notifications are not available yet — the server's email service is not configured. Your search will still run, but you won't receive emails until an admin sets up SMTP.")

        st.divider()
        run_btn = st.button("Start Scraping", use_container_width=True, type="primary")

    # ── Main area ────────────────────────────────────────────────────────────
    st.title("Job Hunter")

    with st.container():
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Skills", len(all_skills) if all_skills else "Any")
        c2.metric("Job Locations", len(all_job_locs) if all_job_locs else "Any")
        c3.metric("Experience", len(selected_exp) if selected_exp else "Any")
        if source_mode == "Auto-generate from location":
            c4.metric("Companies (DB)", len(get_companies_for_location(
                [scrape_location],
                selected_categories if selected_categories else None,
            )))
        elif source_mode == "Discover from web":
            c4.metric("Source", "Web discovery")
        else:
            c4.metric("Source", "Excel upload")

    st.divider()

    # ── Run ──────────────────────────────────────────────────────────────────
    if run_btn:
        if source_mode == "Upload Excel file" and uploaded_file is None:
            st.error("Please upload an Excel file.")
            st.stop()
        if source_mode == "Discover from web" and not all_skills:
            st.error("Please add at least one skill so we know what jobs to discover.")
            st.stop()

        # Load companies
        uploaded_companies_list = []
        if source_mode == "Auto-generate from location":
            cats = selected_categories if selected_categories else None
            companies = get_companies_for_location([scrape_location], cats)
            if not companies:
                st.warning("No companies found for that location/category combination.")
                st.stop()

        elif source_mode == "Discover from web":
            discover_placeholder = st.empty()
            discover_placeholder.info("Discovering companies from LinkedIn & Google...")
            discover_log = []

            def _discover_progress(msg):
                discover_log.append(msg)
                discover_placeholder.code("\n".join(discover_log[-15:]), language=None)

            session = requests.Session()
            session.headers.update({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            })
            discovered = discover_companies_from_web(
                skills=all_skills, locations=all_job_locs,
                max_companies=int(company_limit), session=session,
                progress_callback=_discover_progress,
            )
            n_web = len(discovered)
            if n_web == 0:
                discover_placeholder.warning(
                    "Web discovery returned 0 companies — LinkedIn and Google likely blocked "
                    "the automated requests (403 / CAPTCHA). Falling back to the local database."
                )

            db_companies = get_companies_for_location(
                all_job_locs if all_job_locs else ["any"], None
            )
            seen_domains = {c["domain"] for c in discovered}
            n_db_added = 0
            for dbc in db_companies:
                if dbc["domain"] not in seen_domains:
                    discovered.append(dbc)
                    seen_domains.add(dbc["domain"])
                    n_db_added += 1

            companies = discovered
            if not companies:
                discover_placeholder.empty()
                st.warning("Could not discover any companies.")
                st.stop()
            discover_placeholder.success(
                f"Found **{len(companies)}** companies "
                f"({n_web} discovered + {n_db_added} from DB)"
            )

        else:
            try:
                suffix = ".xlsx"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                companies = read_companies(tmp_path)
                uploaded_companies_list = companies.copy()
                os.unlink(tmp_path)
            except Exception as e:
                st.error(f"Failed to read Excel file: {e}")
                st.stop()
            if not companies:
                st.warning("No companies found in the uploaded file.")
                st.stop()

        companies = companies[:int(company_limit)]
        exp_levels = selected_exp if selected_exp else []

        st.info(
            f"Scraping **{len(companies)}** companies | "
            f"Skills: **{', '.join(all_skills) if all_skills else 'Any'}** | "
            f"Job locations: **{', '.join(all_job_locs) if all_job_locs else 'Any'}** | "
            f"Experience: **{', '.join(selected_exp) if selected_exp else 'Any'}**"
        )

        progress_bar = st.progress(0, text="Starting...")
        live_status = st.empty()
        live_table = st.empty()
        log_expander = st.expander("Live scrape log", expanded=False)
        log_placeholder = log_expander.empty()

        all_jobs: list[dict] = []
        log_lines: list[str] = []
        completed_count = 0
        selected_field = st.session_state.get("selected_field", "") or ""

        def _scrape_one_company(company):
            session = requests.Session()
            session.headers.update({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            })
            cap = _StdoutCapture()
            jobs = []
            try:
                with cap:
                    jobs = scrape_company_jobs(
                        company, all_skills, all_job_locs, exp_levels, session,
                        field=selected_field
                    )
            except Exception as e:
                cap.lines.append(f"  [!] Error: {e}")
            return company, jobs, cap.lines

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(_scrape_one_company, c): c for c in companies}
            for future in as_completed(futures):
                company, jobs, lines = future.result()
                all_jobs.extend(jobs)
                log_lines.extend(lines)
                completed_count += 1
                pct = int((completed_count / len(companies)) * 100)
                progress_bar.progress(pct, text=f"[{completed_count}/{len(companies)}] {company['name']} done")
                log_placeholder.code("\n".join(log_lines[-80:]), language=None)
                if all_jobs:
                    live_status.caption(f"**{len(all_jobs)}** jobs found so far -- browse and apply while scraping continues!")
                    live_df = _jobs_to_df(all_jobs)
                    live_table.dataframe(
                        live_df, use_container_width=True, height=400,
                        column_config={
                            "Company":        st.column_config.TextColumn("Company", width="medium"),
                            "Job Title":      st.column_config.TextColumn("Job Title", width="large"),
                            "Location":       st.column_config.TextColumn("Location", width="medium"),
                            "Experience":     st.column_config.TextColumn("Experience", width="small"),
                            "Skills Matched": st.column_config.TextColumn("Skills", width="medium"),
                            "Posted Date":    st.column_config.DateColumn("Posted", format="YYYY-MM-DD", width="small"),
                            "Link":           st.column_config.LinkColumn("Apply", width="small", display_text="Apply"),
                        },
                        hide_index=True,
                    )

        progress_bar.progress(100, text="Done!")
        live_status.empty()
        live_table.empty()
        if all_jobs:
            st.success(f"Scraping complete -- **{len(all_jobs)}** jobs found across {len(companies)} companies")
            st.session_state.last_scrape_empty = False
        else:
            st.warning(
                f"Scraping complete -- **0 jobs** found across {len(companies)} companies. "
                "Try broadening your skills/location filters, or switch to "
                "**Auto-generate from location** mode which uses the local company database."
            )
            st.session_state.last_scrape_empty = True
        st.session_state.results_df = _jobs_to_df(all_jobs)
        st.session_state.log_lines = log_lines
        # Save to history so results survive navigation
        if all_jobs:
            desc = f"{len(all_jobs)} jobs | {', '.join(all_skills[:3]) if all_skills else 'Any skills'}"
            st.session_state.results_history.insert(0, (
                time.strftime("%H:%M:%S"),
                desc,
                st.session_state.results_df.copy(),
            ))
            st.session_state.results_history = st.session_state.results_history[:1]

        # ── Save search if requested ─────────────────────────────────────────
        if save_this_search and all_jobs:
            sid = save_search(
                user_id=user["id"],
                name=search_name,
                field=selected_field,
                skills=all_skills,
                locations=all_job_locs,
                experience=exp_levels,
                categories=selected_categories,
                source_mode=source_mode,
                scrape_location=scrape_location,
                company_limit=int(company_limit),
                notify_email=enable_notifications,
            )
            # Save uploaded companies if applicable
            if source_mode == "Upload Excel file" and uploaded_companies_list:
                save_uploaded_companies(user["id"], sid, uploaded_companies_list)

            # Store initial job results
            new_count = save_job_results(user["id"], sid, all_jobs)

            # Send email notification for the initial scrape results
            if enable_notifications and new_count > 0:
                notify_email = user.get("email", "")
                if notify_email:
                    unnotified = get_unnotified_jobs(sid)
                    if unnotified:
                        sent = send_job_notification(notify_email, search_name, unnotified)
                        if sent:
                            mark_jobs_notified(sid)
                            st.success(f"Email notification sent to {notify_email} with {len(unnotified)} job(s).")
                        else:
                            st.warning("Could not send email notification. Check SMTP settings.")

            st.info(
                f"Search saved! {new_count} job(s) stored. "
                f"This search will run automatically every 24 hours."
            )

    # ── Results ──────────────────────────────────────────────────────────────
    if not st.session_state.results_df.empty:
        df = st.session_state.results_df

        st.subheader(f"Results -- {len(df)} jobs")

        with st.expander("Filter / search results", expanded=False):
            fc1, fc2, fc3, fc4 = st.columns(4)
            company_filter = fc1.multiselect("Company", options=sorted(df["Company"].unique()), default=[])
            exp_filter = fc2.multiselect("Experience", options=sorted(df["Experience"].unique()), default=[])
            loc_filter = fc3.multiselect("Location", options=sorted(df["Location"].unique()), default=[])
            date_filter = fc4.selectbox("Posted within", options=DATE_FILTER_OPTIONS, index=0)
            title_search = st.text_input("Search in Job Title", placeholder="e.g. engineer, quant, analyst")

        filtered = df.copy()
        if company_filter:
            filtered = filtered[filtered["Company"].isin(company_filter)]
        if exp_filter:
            filtered = filtered[filtered["Experience"].isin(exp_filter)]
        if loc_filter:
            filtered = filtered[filtered["Location"].isin(loc_filter)]
        if title_search:
            filtered = filtered[filtered["Job Title"].str.contains(title_search, case=False, na=False)]
        if date_filter != "Any":
            days = DATE_FILTER_DAYS[date_filter]
            cutoff = datetime.now() - timedelta(days=days)
            filtered = filtered[filtered["Posted Date"] >= cutoff]

        st.caption(f"Showing {len(filtered)} of {len(df)} jobs")

        st.dataframe(
            filtered, use_container_width=True, height=520,
            column_config={
                "Company":        st.column_config.TextColumn("Company", width="medium"),
                "Job Title":      st.column_config.TextColumn("Job Title", width="large"),
                "Location":       st.column_config.TextColumn("Location", width="medium"),
                "Experience":     st.column_config.TextColumn("Experience", width="medium"),
                "Skills Matched": st.column_config.TextColumn("Skills Matched", width="medium"),
                "Posted Date":    st.column_config.DateColumn("Posted Date", format="YYYY-MM-DD", width="small"),
                "Link":           st.column_config.LinkColumn("Apply Link", width="medium", display_text="Apply"),
            },
            hide_index=True,
        )

        st.divider()
        dl_col1, dl_col2, _ = st.columns([2, 2, 4])
        csv_bytes = _df_to_csv_bytes(filtered)
        dl_col1.download_button(
            label="Download filtered CSV",
            data=csv_bytes,
            file_name=f"jobs_{time.strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary",
        )
        all_csv_bytes = _df_to_csv_bytes(df)
        dl_col2.download_button(
            label="Download all results CSV",
            data=all_csv_bytes,
            file_name=f"jobs_all_{time.strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    elif not run_btn:
        if st.session_state.last_scrape_empty:
            st.warning(
                "Your last scrape returned **0 jobs**. This can happen when:\n"
                "- **Discover from web** mode: LinkedIn/Google blocked the automated requests (403/CAPTCHA)\n"
                "- Skill or location filters were too narrow\n\n"
                "**Tip:** Try **Auto-generate from location** mode in the sidebar — it uses a curated "
                "local database and doesn't depend on external sites."
            )
            st.session_state.last_scrape_empty = False

        # Show previous results if available
        if st.session_state.results_history:
            st.subheader("Previous results")
            st.caption("Your past scrape runs (kept in memory). Click to restore.")
            for i, (ts, desc, hist_df) in enumerate(st.session_state.results_history):
                col_desc, col_btn = st.columns([4, 1])
                col_desc.markdown(f"**{ts}** — {desc}")
                if col_btn.button("Restore", key=f"restore_{i}", use_container_width=True):
                    st.session_state.results_df = hist_df
                    st.rerun()
            st.divider()

        if not st.session_state.last_scrape_empty:
            st.markdown(
                """
                ### How to use

                1. **Choose a company source** in the sidebar
                2. **Add skills** from the dropdown or type custom ones
                3. **Set job location filter** to narrow postings by city/remote
                4. **Select experience levels** -- intern through staff
                5. **Check "Save this search"** to enable daily automated scraping
                6. Hit **Start Scraping** and watch results populate in real time
                7. You'll receive email notifications when new jobs are found (if SMTP is configured)
                """
            )
