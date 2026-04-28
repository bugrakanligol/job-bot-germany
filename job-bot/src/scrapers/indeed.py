import logging
import random
import time
from typing import Optional
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

from ..config import HTTP_HEADERS

logger = logging.getLogger(__name__)

BASE_URL = "https://de.indeed.com"
DEFAULT_KEYWORDS = [
    "Supply Chain Manager",
    "Logistik",
    "Operations Manager",
    "Procurement",
    "Warehouse",
]


def _polite_sleep() -> None:
    time.sleep(random.uniform(2.0, 3.0))


def _text_or_none(node) -> Optional[str]:
    if not node:
        return None
    text = node.get_text(separator=" ", strip=True)
    return text or None


def _parse_card(card) -> Optional[dict]:
    title_el = card.select_one("h2.jobTitle a") or card.find("a", href=True)
    if not title_el:
        return None

    href = title_el.get("href", "")
    if not href:
        return None
    url = href if href.startswith("http") else urljoin(BASE_URL, href)

    title_text = (
        _text_or_none(card.select_one("h2.jobTitle span"))
        or _text_or_none(title_el)
    )
    if not title_text:
        return None

    company = _text_or_none(
        card.select_one("[data-testid='company-name']")
    ) or _text_or_none(card.select_one("span.companyName"))

    location = _text_or_none(
        card.select_one("[data-testid='text-location']")
    ) or _text_or_none(card.select_one("div.companyLocation"))

    description = _text_or_none(
        card.select_one("div.job-snippet")
    ) or _text_or_none(card.select_one("[role='presentation']"))

    return {
        "title": title_text,
        "company": company,
        "location": location,
        "url": url.split("&")[0] if "?" in url else url,
        "description": description,
        "source": "indeed",
    }


def _fetch(url: str) -> Optional[str]:
    try:
        resp = requests.get(url, headers=HTTP_HEADERS, timeout=20)
        if resp.status_code != 200:
            logger.warning("Indeed %s returned %d", url, resp.status_code)
            return None
        return resp.text
    except requests.RequestException as e:
        logger.warning("Indeed request failed for %s: %s", url, e)
        return None


def scrape_indeed(keywords: Optional[list[str]] = None) -> list[dict]:
    keywords = keywords or DEFAULT_KEYWORDS
    results: list[dict] = []
    seen_urls: set[str] = set()

    for kw in keywords:
        q = quote_plus(kw)
        url = f"{BASE_URL}/jobs?q={q}&l=Deutschland&sort=date&fromage=7"
        logger.info("Indeed: searching '%s'", kw)
        html = _fetch(url)
        _polite_sleep()
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div.job_seen_beacon") or soup.select("a.tapItem")
        if not cards:
            cards = soup.select("li[data-testid='jobListItem']")

        for card in cards:
            try:
                job = _parse_card(card)
            except Exception as e:
                logger.debug("Indeed card parse error: %s", e)
                continue
            if not job:
                continue
            if job["url"] in seen_urls:
                continue
            seen_urls.add(job["url"])
            results.append(job)

    logger.info("Indeed: collected %d unique jobs", len(results))
    return results
