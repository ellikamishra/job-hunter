-- Supabase Postgres schema for Job Hunter
-- Run this once in the Supabase SQL Editor

CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    email       TEXT    UNIQUE NOT NULL,
    password    TEXT    NOT NULL,
    salt        TEXT    NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS saved_searches (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    name            TEXT    NOT NULL DEFAULT 'My Search',
    field           TEXT    NOT NULL DEFAULT '',
    skills          TEXT    NOT NULL DEFAULT '[]',
    locations       TEXT    NOT NULL DEFAULT '[]',
    experience      TEXT    NOT NULL DEFAULT '[]',
    categories      TEXT    NOT NULL DEFAULT '[]',
    source_mode     TEXT    NOT NULL DEFAULT 'Auto-generate from location',
    scrape_location TEXT    NOT NULL DEFAULT 'any',
    company_limit   INTEGER NOT NULL DEFAULT 50,
    notify_email    INTEGER NOT NULL DEFAULT 1,
    active          INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS uploaded_companies (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    search_id   INTEGER REFERENCES saved_searches(id),
    name        TEXT    NOT NULL,
    domain      TEXT    NOT NULL,
    career_url  TEXT    NOT NULL DEFAULT '',
    uploaded_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS job_results (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    search_id   INTEGER NOT NULL REFERENCES saved_searches(id),
    company     TEXT    NOT NULL,
    title       TEXT    NOT NULL,
    location    TEXT    NOT NULL DEFAULT '',
    experience  TEXT    NOT NULL DEFAULT '',
    skills      TEXT    NOT NULL DEFAULT '',
    posted_date TEXT    NOT NULL DEFAULT '',
    link        TEXT    NOT NULL,
    found_at    TIMESTAMP NOT NULL DEFAULT NOW(),
    notified    INTEGER NOT NULL DEFAULT 0
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_job_link_search
    ON job_results(search_id, link);
