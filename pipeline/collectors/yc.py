from __future__ import annotations

import json
import re
import urllib.request
from datetime import date, timedelta
from html.parser import HTMLParser
from typing import Any

from pipeline.models import SourceItem
from pipeline.normalize import compact_text


USER_AGENT = "ai-signal-radar/0.1 (+https://github.com/mcravi8/ai-signal-radar)"


def _published_date(value: str | None) -> str:
    text = compact_text(value or "")
    if not text:
        return ""
    if re.match(r"^\d{4}-\d{2}-\d{2}", text):
        return text
    match = re.match(r"^(?:about )?(\d+)\s+(hour|day|month|year)s?$", text, re.I)
    if not match:
        return ""
    amount, unit = int(match.group(1)), match.group(2).lower()
    days = amount * {"hour": 0, "day": 1, "month": 30, "year": 365}[unit]
    return (date.today() - timedelta(days=days)).isoformat()


class _DataPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.pages: list[str] = []

    def handle_starttag(self, _tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key == "data-page" and value:
                self.pages.append(value)


def _fetch_page(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8", errors="replace")
    parser = _DataPageParser()
    parser.feed(body)
    if not parser.pages:
        raise ValueError(f"YC page did not expose public data-page metadata: {url}")
    return json.loads(parser.pages[0])


def parse_companies(page: dict[str, Any], limit: int = 50) -> list[SourceItem]:
    companies = page.get("props", {}).get("companies", [])[:limit]
    items = []
    for company in companies:
        company_id = company.get("id")
        slug = company.get("slug")
        if not company_id or not slug:
            continue
        name = compact_text(company.get("name", ""))
        batch = compact_text(company.get("batch_name", "")).upper()
        one_liner = compact_text(company.get("one_liner", ""))
        description = compact_text(company.get("long_description", ""))
        summary = f"{one_liner}. {description}".strip(" .")[:1200]
        tags = [compact_text(tag) for tag in company.get("tags", []) if compact_text(tag)]
        if batch:
            tags.append(f"yc-batch:{batch.lower()}")
        items.append(
            SourceItem(
                id=f"yc-company:{company_id}",
                source_id="yc-companies",
                source_type="company-directory",
                title=f"{name} ({batch})" if batch else name,
                url=f"https://www.ycombinator.com/companies/{slug}",
                published_at=date.today().isoformat(),
                summary=summary,
                tags=tags,
                projects=[name] if name else [],
                sponsor_status="first-party-directory",
                metadata={
                    "batch": batch,
                    "status": company.get("ycdc_status"),
                    "team_size": company.get("team_size"),
                    "location": company.get("location"),
                    "github_url": company.get("github_url"),
                    "date_basis": "first-observed",
                },
            )
        )
    return items


def parse_jobs(page: dict[str, Any], terms: list[str], limit: int = 50) -> list[SourceItem]:
    jobs = page.get("props", {}).get("jobPostings", [])[:limit]
    pattern = re.compile(r"\b(?:" + "|".join(re.escape(term) for term in terms) + r")\b", re.I)
    items = []
    for job in jobs:
        searchable = " ".join(
            str(value or "")
            for value in (
                job.get("title"),
                job.get("role"),
                job.get("roleSpecificType"),
                job.get("companyOneLiner"),
                " ".join(job.get("skills", [])),
            )
        )
        if not pattern.search(searchable):
            continue
        job_id = job.get("id")
        if not job_id:
            continue
        company = compact_text(job.get("companyName", ""))
        title = compact_text(job.get("title", ""))
        role = compact_text(job.get("prettyRole") or job.get("role") or "")
        location = compact_text(job.get("location", ""))
        summary = compact_text(
            f"{company} is hiring for {title}. {job.get('companyOneLiner', '')} "
            f"Role: {role}. Location: {location}. Skills: {', '.join(job.get('skills', []))}."
        )[:1200]
        job_url = job.get("url") or f"https://www.ycombinator.com/jobs/{job_id}"
        if str(job_url).startswith("/"):
            job_url = f"https://www.ycombinator.com{job_url}"
        items.append(
            SourceItem(
                id=f"yc-job:{job_id}",
                source_id="yc-jobs",
                source_type="job-posting",
                title=f"{company}: {title}" if company else title,
                url=str(job_url),
                published_at=_published_date(job.get("createdAt")),
                summary=summary,
                tags=["job-posting", role, *[compact_text(skill) for skill in job.get("skills", []) if compact_text(skill)]],
                projects=[company] if company else [],
                sponsor_status="first-party-job-board",
                metadata={
                    "company": company,
                    "batch": job.get("companyBatchName"),
                    "role": role,
                    "location": location,
                    "created_at": job.get("createdAt"),
                    "date_basis": "approximate-public-age",
                },
            )
        )
    return items


def collect_companies(url: str, limit: int = 50) -> list[SourceItem]:
    return parse_companies(_fetch_page(url), limit=limit)


def collect_jobs(url: str, terms: list[str], limit: int = 50) -> list[SourceItem]:
    return parse_jobs(_fetch_page(url), terms=terms, limit=limit)
