from __future__ import annotations

import hashlib
import json
import os
import urllib.parse
import urllib.request

from pipeline.models import SourceItem


def collect(queries: list[dict[str, str]], since: str, per_query: int = 30) -> list[SourceItem]:
    token = os.getenv("AI_RADAR_GITHUB_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ai-signal-radar/0.1",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    items: list[SourceItem] = []
    for configured in queries:
        query = configured["query"].format(since=since)
        params = urllib.parse.urlencode({"q": query, "sort": "stars", "order": "desc", "per_page": per_query})
        request = urllib.request.Request(f"https://api.github.com/search/repositories?{params}", headers=headers)
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
        for repo in payload.get("items", []):
            url = repo["html_url"]
            repo_id = repo.get("id") or hashlib.sha256(url.encode()).hexdigest()[:16]
            items.append(
                SourceItem(
                    id=f"github:{repo_id}",
                    source_id="github",
                    source_type="repository",
                    title=repo["full_name"],
                    url=url,
                    published_at=repo.get("created_at", ""),
                    summary=(repo.get("description") or "")[:1200],
                    authors=[repo.get("owner", {}).get("login", "")],
                    tags=repo.get("topics", []),
                    projects=[repo["full_name"]],
                    metadata={
                        "stars": repo.get("stargazers_count", 0),
                        "forks": repo.get("forks_count", 0),
                        "pushed_at": repo.get("pushed_at"),
                        "license": (repo.get("license") or {}).get("spdx_id"),
                        "query_id": configured["id"],
                    },
                )
            )
    return items
