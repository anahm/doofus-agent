import argparse
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import urljoin

import duckdb
import requests
from bs4 import BeautifulSoup

DEFAULT_USER_AGENT = "doofus-agent-careers-scraper/1.0"
DEFAULT_DB_PATH = "careers.duckdb"


@dataclass(frozen=True)
class JobListing:
    title: str
    location: str | None
    url: str | None


def _get_db_url() -> str:
    return os.environ.get("CAREERS_DB_URL") or os.environ.get("CAREERS_DB_PATH") or DEFAULT_DB_PATH


def _fetch_html(url: str, user_agent: str) -> str:
    response = requests.get(url, headers={"User-Agent": user_agent}, timeout=30)
    response.raise_for_status()
    return response.text


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def _parse_jobs(
    html: str,
    source_url: str,
    job_selector: str,
    title_selector: str | None,
    location_selector: str | None,
    link_selector: str | None,
) -> list[JobListing]:
    soup = BeautifulSoup(html, "html.parser")
    job_nodes = soup.select(job_selector)
    jobs: list[JobListing] = []

    for node in job_nodes:
        title_node = node.select_one(title_selector) if title_selector else None
        location_node = node.select_one(location_selector) if location_selector else None
        link_node = node.select_one(link_selector) if link_selector else None

        if link_node is None:
            link_node = node.find("a")

        title_text = _clean_text(title_node.get_text() if title_node else node.get_text())
        location_text = _clean_text(location_node.get_text() if location_node else None)
        href = link_node.get("href") if link_node else None

        if not title_text:
            continue

        full_url = urljoin(source_url, href) if href else None
        jobs.append(JobListing(title=title_text, location=location_text, url=full_url))

    return jobs


def _init_db(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(
        """
        create table if not exists careers (
            title varchar,
            location varchar,
            url varchar,
            source_url varchar,
            scraped_at timestamp
        )
        """
    )


def _store_jobs(
    connection: duckdb.DuckDBPyConnection,
    jobs: Iterable[JobListing],
    source_url: str,
    replace_existing: bool,
) -> int:
    _init_db(connection)

    if replace_existing:
        connection.execute("delete from careers where source_url = ?", [source_url])

    rows = [
        (
            job.title,
            job.location,
            job.url,
            source_url,
            datetime.now(timezone.utc),
        )
        for job in jobs
    ]

    if rows:
        connection.executemany(
            "insert into careers (title, location, url, source_url, scraped_at) values (?, ?, ?, ?, ?)",
            rows,
        )

    return len(rows)


def scrape_and_store(
    source_url: str,
    job_selector: str,
    title_selector: str | None,
    location_selector: str | None,
    link_selector: str | None,
    db_url: str,
    replace_existing: bool,
    user_agent: str,
) -> int:
    html = _fetch_html(source_url, user_agent)
    jobs = _parse_jobs(
        html,
        source_url,
        job_selector,
        title_selector,
        location_selector,
        link_selector,
    )

    connection = duckdb.connect(db_url)
    try:
        inserted = _store_jobs(connection, jobs, source_url, replace_existing)
    finally:
        connection.close()

    return inserted


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scrape open career listings and store them in DuckDB/MotherDuck.",
    )
    parser.add_argument("--url", required=True, help="Careers page URL to scrape.")
    parser.add_argument(
        "--job-selector",
        required=True,
        help="CSS selector that matches each job listing entry.",
    )
    parser.add_argument(
        "--title-selector",
        default=None,
        help="Optional CSS selector inside each job entry for the job title.",
    )
    parser.add_argument(
        "--location-selector",
        default=None,
        help="Optional CSS selector inside each job entry for the location.",
    )
    parser.add_argument(
        "--link-selector",
        default=None,
        help="Optional CSS selector inside each job entry for the job link.",
    )
    parser.add_argument(
        "--db-url",
        default=_get_db_url(),
        help="DuckDB or MotherDuck connection string (default: env CAREERS_DB_URL or careers.duckdb).",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete existing rows for the URL before inserting.",
    )
    parser.add_argument(
        "--user-agent",
        default=os.environ.get("CAREERS_USER_AGENT", DEFAULT_USER_AGENT),
        help="Custom user agent for scraping.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    inserted = scrape_and_store(
        source_url=args.url,
        job_selector=args.job_selector,
        title_selector=args.title_selector,
        location_selector=args.location_selector,
        link_selector=args.link_selector,
        db_url=args.db_url,
        replace_existing=args.replace,
        user_agent=args.user_agent,
    )

    print(f"Inserted {inserted} jobs into {args.db_url}.")


if __name__ == "__main__":
    main()
