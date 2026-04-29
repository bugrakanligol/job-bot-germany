import logging
from typing import Optional

from . import database
from .config import JOB_KEYWORDS
from .scrapers.bundesagentur import scrape_bundesagentur
from .scrapers.indeed import scrape_indeed
from .scrapers.stepstone import scrape_stepstone

logger = logging.getLogger(__name__)


def scrape_all(
    keywords: Optional[list[str]] = None,
    sources: Optional[list[str]] = None,
) -> dict:
    database.init_db()
    keywords = keywords or JOB_KEYWORDS
    sources = [s.lower() for s in sources] if sources else ["bundesagentur", "indeed", "stepstone"]

    all_jobs: list[dict] = []

    if "bundesagentur" in sources:
        logger.info("Scraping Bundesagentur…")
        all_jobs.extend(scrape_bundesagentur(keywords=keywords))

    if "indeed" in sources:
        logger.info("Scraping Indeed…")
        all_jobs.extend(scrape_indeed(keywords=keywords))

    if "stepstone" in sources:
        logger.info("Scraping StepStone…")
        all_jobs.extend(scrape_stepstone(keywords=keywords))

    saved = 0
    skipped = 0
    for job in all_jobs:
        job_id = database.save_job(
            title=job["title"],
            company=job.get("company"),
            location=job.get("location"),
            description=job.get("description"),
            url=job["url"],
            source=job["source"],
        )
        if job_id:
            saved += 1
        else:
            skipped += 1

    logger.info(
        "Scraping complete: %d new jobs saved, %d duplicates skipped.", saved, skipped
    )
    return {"total": len(all_jobs), "saved": saved, "skipped": skipped}
