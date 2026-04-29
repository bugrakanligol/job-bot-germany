import json
import logging
import time
from typing import Optional

from anthropic import Anthropic

from . import database
from .config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, JOB_KEYWORDS, SCORING_CHUNK_SIZE

logger = logging.getLogger(__name__)

# Lowercase set for fast O(1) keyword membership checks
_POSITIVE_TITLE_KEYWORDS: frozenset[str] = frozenset(
    kw.lower() for kw in JOB_KEYWORDS
) | frozenset({
    "sourcing", "import", "export", "distribution", "fulfillment",
    "fashion", "textil", "retail", "buying", "merchandise",
    "transport", "shipping", "spedition", "inventory", "demand",
})

SYSTEM_PROMPT = """You are a recruitment specialist scoring job-candidate fit.

Given a CV profile and a numbered list of job listings, return ONLY a valid JSON array
with one entry per job (same order, 0-based index):

[
  {
    "job_index": <integer>,
    "score": <integer 0-100>,
    "reasoning": "<2-4 sentences>",
    "status": "<'shortlisted' | 'reviewed' | 'skipped'>"
  }
]

## Scoring Algorithm (apply to EACH job independently)

### Step 1 — Domain / Industry base score
- Strong domain match (supply chain, global sourcing, fashion merchandising, sustainable
  procurement, textile, retail operations, ESG/compliance in fashion) → base = 55
- Adjacent domain (logistics, procurement, project management in any industry, e-commerce ops) → base = 38
- Unrelated domain → base = 10

### Step 2 — Years of experience (+20 if sufficient)
If candidate meets or exceeds the requirement → +20, else +0.

### Step 3 — Skill matches (+10 each, max +30)
Up to 3 explicit matches between job requirements and CV skills/tools/certifications.

### Step 4 — Language / location deductions
- Job requires German B2+ and candidate is beginner → -15
- Job outside Germany, no remote option → -10

### Step 5 — Bonus (+5 each, max +10)
- Title closely matches candidate's current/most recent title → +5
- Job requires certifications candidate holds (ESPR, GRS, DPP) → +5

### Step 6 — Final score
Sum all values. Clamp to [0, 100].
status: score >= 75 → "shortlisted" | score >= 50 → "reviewed" | else → "skipped"

Return ONLY the JSON array. No prose, no markdown fences."""


def _passes_keyword_filter(job: dict) -> bool:
    title = (job.get("title") or "").lower()
    return any(kw in title for kw in _POSITIVE_TITLE_KEYWORDS)


def _build_user_content(cv_profile: dict, jobs: list[dict]) -> str:
    cv_summary = json.dumps(
        {k: v for k, v in cv_profile.items() if not k.startswith("_")},
        ensure_ascii=False,
        indent=2,
    )
    job_blocks = []
    for i, job in enumerate(jobs):
        desc = (job.get("description") or "N/A")[:800]
        job_blocks.append(
            f"[{i}] Title: {job.get('title', '')}\n"
            f"    Company: {job.get('company', '')}\n"
            f"    Location: {job.get('location', '')}\n"
            f"    Description: {desc}"
        )
    return f"CV PROFILE:\n{cv_summary}\n\nJOB LISTINGS ({len(jobs)} total):\n\n" + "\n\n".join(job_blocks)


def _parse_chunk_response(content: list, jobs: list[dict]) -> list[dict]:
    text = "".join(
        block.text for block in content if getattr(block, "type", "") == "text"
    ).strip()

    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].lstrip()

    results = json.loads(text)
    if not isinstance(results, list):
        raise ValueError("Expected JSON array from Claude")

    scored = []
    for item in results:
        idx = int(item.get("job_index", 0))
        if idx >= len(jobs):
            continue
        scored.append({
            "job": jobs[idx],
            "score": int(item.get("score", 0)),
            "reasoning": item.get("reasoning", ""),
            "status": item.get("status", "skipped"),
        })
    return scored


def _score_chunk(client: Anthropic, cv_profile: dict, jobs: list[dict]) -> list[dict]:
    msg = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=max(512, 256 * len(jobs)),
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_content(cv_profile, jobs)}],
    )
    return _parse_chunk_response(msg.content, jobs)


def _persist_results(results: list[dict]) -> int:
    count = 0
    for r in results:
        database.update_job_score(r["job"]["id"], r["score"], r["reasoning"], r["status"])
        logger.info(
            "Job %d '%s' → %d (%s)",
            r["job"]["id"], r["job"].get("title", ""), r["score"], r["status"],
        )
        count += 1
    return count


def _score_sync(cv_profile: dict, jobs: list[dict]) -> int:
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    chunks = [jobs[i:i + SCORING_CHUNK_SIZE] for i in range(0, len(jobs), SCORING_CHUNK_SIZE)]
    scored = 0

    for idx, chunk in enumerate(chunks):
        logger.info("Chunk %d/%d — %d jobs…", idx + 1, len(chunks), len(chunk))
        try:
            results = _score_chunk(client, cv_profile, chunk)
            scored += _persist_results(results)
        except Exception as e:
            logger.error("Chunk %d failed (%s); retrying individually…", idx + 1, e)
            for job in chunk:
                try:
                    results = _score_chunk(client, cv_profile, [job])
                    scored += _persist_results(results)
                except Exception as e2:
                    logger.error("Job %d failed: %s", job.get("id"), e2)

    return scored


def _score_batch(cv_profile: dict, jobs: list[dict]) -> int:
    """Async Batch API — 50 % token discount. Polls until the batch ends."""
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    chunks = [jobs[i:i + SCORING_CHUNK_SIZE] for i in range(0, len(jobs), SCORING_CHUNK_SIZE)]

    requests = [
        {
            "custom_id": f"chunk-{i}",
            "params": {
                "model": ANTHROPIC_MODEL,
                "max_tokens": max(512, 256 * len(chunk)),
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": _build_user_content(cv_profile, chunk)}],
            },
        }
        for i, chunk in enumerate(chunks)
    ]

    logger.info("Submitting batch: %d requests (%d jobs)…", len(requests), len(jobs))
    batch = client.messages.batches.create(requests=requests)
    logger.info("Batch %s submitted. Polling for completion…", batch.id)

    while batch.processing_status != "ended":
        time.sleep(30)
        batch = client.messages.batches.retrieve(batch.id)
        logger.info("Batch status: %s", batch.processing_status)

    scored = 0
    for result in client.messages.batches.results(batch.id):
        if result.result.type != "succeeded":
            logger.error("Batch item %s: %s", result.custom_id, result.result.type)
            continue
        chunk_idx = int(result.custom_id.split("-")[1])
        chunk = chunks[chunk_idx]
        try:
            items = _parse_chunk_response(result.result.message.content, chunk)
            scored += _persist_results(items)
        except Exception as e:
            logger.error("Failed to parse batch item %s: %s", result.custom_id, e)

    return scored


def score_all_unscored(cv_profile: Optional[dict] = None, use_batch: bool = False) -> int:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")

    if cv_profile is None:
        cached = database.get_cv_profile()
        if not cached:
            raise RuntimeError("No CV profile found. Run 'parse-cv' first.")
        cv_profile = cached["parsed"]

    all_jobs = database.get_unscored_jobs()
    if not all_jobs:
        logger.info("No unscored jobs found.")
        return 0

    to_score = [j for j in all_jobs if _passes_keyword_filter(j)]
    to_skip = [j for j in all_jobs if not _passes_keyword_filter(j)]

    if to_skip:
        logger.info(
            "Keyword filter: auto-skipping %d/%d jobs (no API call).",
            len(to_skip), len(all_jobs),
        )
        for job in to_skip:
            database.update_job_score(job["id"], 0, "Filtered by keyword pre-check.", "skipped")

    if not to_score:
        logger.info("No jobs passed keyword filter.")
        return 0

    logger.info(
        "Scoring %d jobs — model=%s, chunk=%d, mode=%s",
        len(to_score), ANTHROPIC_MODEL, SCORING_CHUNK_SIZE,
        "batch" if use_batch else "sync",
    )

    if use_batch:
        return _score_batch(cv_profile, to_score)
    return _score_sync(cv_profile, to_score)


# Kept for backward compatibility (cover-letter flow does not use this, but just in case)
def score_job(job: dict, cv_profile: dict) -> Optional[dict]:
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        results = _score_chunk(client, cv_profile, [job])
        if not results:
            return None
        r = results[0]
        database.update_job_score(r["job"]["id"], r["score"], r["reasoning"], r["status"])
        return {"score": r["score"], "reasoning": r["reasoning"], "status": r["status"]}
    except Exception as e:
        logger.error("Failed to score job %d: %s", job.get("id", -1), e)
        return None
