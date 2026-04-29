import json
import logging
from typing import Optional

from anthropic import Anthropic

from . import database
from .config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert career coach writing a tailored cover letter in German.

Write a professional, concise cover letter (3-4 paragraphs, ~250-350 words) for the candidate applying to the given job.

Guidelines:
- Address the company directly (use "Sehr geehrte Damen und Herren," if no contact name is known)
- Opening: express enthusiasm for the specific role and company
- Body: highlight 2-3 concrete skills/experiences from the CV that match the job requirements
- Closing: confident call to action, request for interview
- Tone: professional but warm; not robotic
- Language: German (use English only for technical terms already in the job description)
- Do NOT include date, address blocks, or signature lines — only the letter body text

Return ONLY the letter body text, no JSON, no extra formatting."""


def generate_cover_letter(job: dict, cv_profile: dict) -> str:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")

    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    cv_summary = json.dumps(
        {k: v for k, v in cv_profile.items() if not k.startswith("_")},
        ensure_ascii=False,
        indent=2,
    )

    job_text = (
        f"Title: {job.get('title', '')}\n"
        f"Company: {job.get('company', '')}\n"
        f"Location: {job.get('location', '')}\n"
        f"Description:\n{job.get('description', '') or 'N/A'}"
    )

    msg = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"CV PROFILE:\n{cv_summary}\n\n"
                    f"JOB LISTING:\n{job_text}\n\n"
                    "Write the cover letter body in German."
                ),
            }
        ],
    )

    letter = "".join(
        block.text for block in msg.content if getattr(block, "type", "") == "text"
    ).strip()

    return letter


def generate_and_save(job_id: int, cv_profile: Optional[dict] = None) -> str:
    if cv_profile is None:
        cached = database.get_cv_profile()
        if not cached:
            raise RuntimeError("No CV profile found. Run 'parse-cv' first.")
        cv_profile = cached["parsed"]

    jobs = database.get_all_jobs()
    job = next((j for j in jobs if j["id"] == job_id), None)
    if not job:
        raise ValueError(f"Job ID {job_id} not found in database.")

    logger.info("Generating cover letter for job %d '%s'…", job_id, job.get("title", ""))
    letter = generate_cover_letter(job, cv_profile)

    with database.get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM applications WHERE job_id = ?", (job_id,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE applications SET cover_letter = ? WHERE job_id = ?",
                (letter, job_id),
            )
        else:
            conn.execute(
                "INSERT INTO applications (job_id, cover_letter) VALUES (?, ?)",
                (job_id, letter),
            )

    logger.info("Cover letter saved for job %d.", job_id)
    return letter


def get_cover_letter(job_id: int) -> Optional[str]:
    with database.get_conn() as conn:
        row = conn.execute(
            "SELECT cover_letter FROM applications WHERE job_id = ?", (job_id,)
        ).fetchone()
        return row["cover_letter"] if row else None
