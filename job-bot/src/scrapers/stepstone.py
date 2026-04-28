import logging
import random
import time
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from ..config import HTTP_HEADERS

logger = logging.getLogger(__name__)

BASE_URL = "https://www.stepstone.de"
DEFAULT_KEYWORDS = [
    "supply-chain",
    "logistik",
    "operations-manager",
    "procurement",
    "warehouse-manager",
]


def _polite_sleep() -> None:
    time.sleep(random.uniform(2.0, 3.0))


def _text_or_none(node) -> Optional[str]:
    if not node:
        return None
    text = node.get_text(separator=" ", strip=True)
    return text or None


def _parse_card(card) -> Optional[dict]:
    link = card.find("a", href=True)
    if not link:
        return None

    href = link["href"]
    url = href if href.startswith("http") else urljoin(BASE_URL, href)

    title = _text_or_none(card.find(["h2", "h3"])) or _text_or_none(link)
    if not title:
        return None

    company = _text_or_none(
        card.find(attrs={"data-at": "job-item-company-name"})
    ) or _text_or_none(card.find(class_=lambda c: c and "company" in c.lower()))

    location = _text_or_none(
        card.find(attrs={"data-at": "job-item-location"})
    ) or _text_or_none(card.find(class_=lambda c: c and "location" in c.lower()))

    description = _text_or_none(
        card.find(attrs={"data-at": "jobcard-content"})
    ) or _text_or_none(card.find("p"))

    return {
        "title": title,
        "company": company,
        "location": location,
        "url": url,
        "description": description,
        "source": "stepstone",
    }


def _fetch(url: str) -> Optional[str]:
    try:
        resp = requests.get(url, headers=HTTP_HEADERS, timeout=20)
        if resp.status_code != 200:
            logger.warning("StepStone %s returned %d", url, resp.status_code)
            return None
        return resp.text
    except requests.RequestException as e:
        logger.warning("StepStone request failed for %s: %s", url, e)
        return None


def scrape_stepstone(keywords: Optional[list[str]] = None) -> list[dict]:
    keywords = keywords or DEFAULT_KEYWORDS
    results: list[dict] = []
    seen_urls: set[str] = set()

    for kw in keywords:
        url = f"{BASE_URL}/jobs/{kw}/?where=Deutschland&sort=2"
        logger.info("StepStone: searching '%s'", kw)
        html = _fetch(url)
        _polite_sleep()
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.find_all("article") or soup.select("[data-at='job-item']")
        if not cards:
            cards = soup.select("div.job-element, li.job-element")

        for card in cards:
            try:
                job = _parse_card(card)
            except Exception as e:
                logger.debug("StepStone card parse error: %s", e)
                continue
            if not job:
                continue
            if job["url"] in seen_urls:
                continue
            seen_urls.add(job["url"])
            results.append(job)

    logger.info("StepStone: collected %d unique jobs", len(results))
    return results
