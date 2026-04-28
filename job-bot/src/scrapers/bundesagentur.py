import logging
import random
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

API_BASE = "https://api.arbeitsagentur.de/jobsuche/pc/v4"
SEARCH_URL = f"{API_BASE}/jobs"
DETAIL_URL = f"{API_BASE}/jobdetails"
PUBLIC_DETAIL_URL = "https://www.arbeitsagentur.de/jobsuche/jobdetail"

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


def _polite_sleep() -> None:
    time.sleep(random.uniform(1.0, 2.0))


def _safe_get_location(item: dict) -> Optional[str]:
    aort = item.get("arbeitsort") or {}
    parts = [aort.get("ort"), aort.get("region"), aort.get("land")]
    parts = [p for p in parts if p]
    return ", ".join(parts) if parts else None


def _fetch_detail(hash_id: str) -> Optional[dict]:
    url = f"{DETAIL_URL}/{hash_id}"
    try:
        resp = requests.get(url, headers=API_HEADERS, timeout=20)
        if resp.status_code != 200:
            logger.debug("Bundesagentur detail %s -> %d", hash_id, resp.status_code)
            return None
        return resp.json()
    except requests.RequestException as e:
        logger.debug("Bundesagentur detail fetch failed for %s: %s", hash_id, e)
        return None
    except ValueError:
        return None


def _build_description(detail: Optional[dict], item: dict) -> Optional[str]:
    if detail:
        for key in ("stellenbeschreibung", "beschreibung", "stellenangebotsBeschreibung"):
            val = detail.get(key)
            if val and isinstance(val, str) and val.strip():
                return val.strip()

    return item.get("beruf") or item.get("titel")


def _parse_item(item: dict, fetch_details: bool = True) -> Optional[dict]:
    hash_id = item.get("hashId") or item.get("refnr")
    title = item.get("titel") or item.get("beruf")
    if not hash_id or not title:
        return None

    company = item.get("arbeitgeber")
    location = _safe_get_location(item)
    public_url = f"{PUBLIC_DETAIL_URL}/{hash_id}"

    detail = _fetch_detail(hash_id) if fetch_details else None
    if fetch_details:
        _polite_sleep()

    description = _build_description(detail, item)

    return {
        "title": title,
        "company": company,
        "location": location,
        "url": public_url,
        "description": description,
        "source": "bundesagentur",
    }


def _search(keyword: str, page: int = 0, size: int = 50) -> list[dict]:
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

    return data.get("stellenangebote", []) or []


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
