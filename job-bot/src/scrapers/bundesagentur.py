import json
import logging
import random
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

API_BASE = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6"
SEARCH_URL = f"{API_BASE}/jobs"
PUBLIC_DETAIL_BASE = "https://www.arbeitsagentur.de/jobsuche/jobdetail"

DEFAULT_KEYWORDS = [
    "Supply Chain",
    "Logistik",
    "Operations Manager",
    "Beschaffung",
    "Lager",
    "Einkauf",
]

API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0)",
    "Accept": "application/json",
    "X-API-Key": "jobboerse-jobsuche",
}

HTML_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9",
}


def _polite_sleep() -> None:
    time.sleep(random.uniform(1.0, 2.0))


def _safe_get_location(item: dict) -> Optional[str]:
    locs = item.get("stellenlokationen") or []
    if not locs:
        return None
    adr = locs[0].get("adresse") or {}
    parts = [adr.get("ort"), adr.get("region"), adr.get("land")]
    parts = [p for p in parts if p]
    return ", ".join(parts) if parts else None


def _fetch_description(referenznummer: str) -> Optional[str]:
    url = f"{PUBLIC_DETAIL_BASE}/{referenznummer}"
    try:
        resp = requests.get(url, headers=HTML_HEADERS, timeout=20)
        if resp.status_code != 200:
            logger.debug("BA detail page %s -> %d", referenznummer, resp.status_code)
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        state_tag = soup.find(id="ng-state")
        if not state_tag:
            return None
        state = json.loads(state_tag.text)
        job_detail = state.get("jobdetail") or {}
        return job_detail.get("stellenangebotsBeschreibung") or None
    except Exception as e:
        logger.debug("BA description fetch failed for %s: %s", referenznummer, e)
        return None


def _parse_item(item: dict, fetch_details: bool = True) -> Optional[dict]:
    ref = item.get("referenznummer")
    title = item.get("stellenangebotsTitel") or item.get("hauptberuf")
    if not ref or not title:
        return None

    company = item.get("firma")
    location = _safe_get_location(item)
    public_url = f"{PUBLIC_DETAIL_BASE}/{ref}"

    description: Optional[str] = None
    if fetch_details:
        description = _fetch_description(ref)
        _polite_sleep()

    if not description:
        berufe = item.get("alleBerufe") or []
        description = item.get("hauptberuf") or (", ".join(berufe) if berufe else None)

    return {
        "title": title,
        "company": company,
        "location": location,
        "url": public_url,
        "description": description,
        "source": "bundesagentur",
    }


def _search(keyword: str, page: int = 1, size: int = 50) -> list[dict]:
    params = {
        "was": keyword,
        "wo": "Deutschland",
        "angebotsart": 1,
        "size": size,
        "page": page,
    }
    try:
        resp = requests.get(SEARCH_URL, headers=API_HEADERS, params=params, timeout=20)
        if resp.status_code != 200:
            logger.warning(
                "Bundesagentur search '%s' returned %d", keyword, resp.status_code
            )
            return []
        data = resp.json()
    except requests.RequestException as e:
        logger.warning("Bundesagentur request failed for '%s': %s", keyword, e)
        return []
    except ValueError as e:
        logger.warning("Bundesagentur returned invalid JSON for '%s': %s", keyword, e)
        return []

    return data.get("ergebnisliste", []) or []


def scrape_bundesagentur(
    keywords: Optional[list[str]] = None,
    fetch_details: bool = True,
) -> list[dict]:
    keywords = keywords or DEFAULT_KEYWORDS
    results: list[dict] = []
    seen_urls: set[str] = set()

    for kw in keywords:
        logger.info("Bundesagentur: searching '%s'", kw)
        items = _search(kw)
        _polite_sleep()

        for item in items:
            try:
                job = _parse_item(item, fetch_details=fetch_details)
            except Exception as e:
                logger.debug("Bundesagentur parse error: %s", e)
                continue
            if not job:
                continue
            if job["url"] in seen_urls:
                continue
            seen_urls.add(job["url"])
            results.append(job)

    logger.info("Bundesagentur: collected %d unique jobs", len(results))
    return results
