import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

from anthropic import Anthropic

from . import database
from .config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, CV_PATH

logger = logging.getLogger(__name__)


PROMPT = """You are a CV parsing assistant. Extract a structured profile from the CV text.

Return ONLY valid JSON with this exact schema (no prose, no markdown fences):

{
  "name": "",
  "email": "",
  "phone": "",
  "location": "",
  "summary": "",
  "skills": [],
  "languages": [{"language": "", "level": ""}],
  "experience": [{"title": "", "company": "", "duration": "", "description": ""}],
  "education": [{"degree": "", "institution": "", "year": ""}],
  "certifications": []
}

Rules:
- Use empty strings or empty arrays for missing fields, never null.
- "summary" should be 2-4 sentences capturing seniority, focus area, and core strengths.
- Translate German content faithfully; keep proper nouns as-is.
- "level" for languages: e.g. "native", "C1", "B2", "fluent".
"""


def _read_pdf(path: Path) -> str:
    text_parts: list[str] = []
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                if t.strip():
                    text_parts.append(t)
        if text_parts:
            return "\n".join(text_parts)
    except Exception as e:
        logger.warning("pdfplumber failed (%s); falling back to PyPDF2", e)

    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(str(path))
        for page in reader.pages:
            t = page.extract_text() or ""
            if t.strip():
                text_parts.append(t)
    except Exception as e:
        logger.error("PyPDF2 also failed: %s", e)
        raise

    return "\n".join(text_parts)


def _file_fingerprint(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _call_claude(raw_text: str) -> dict:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=4096,
        system=PROMPT,
        messages=[
            {"role": "user", "content": f"CV TEXT:\n\n{raw_text}"}
        ],
    )
    content = "".join(
        block.text for block in msg.content if getattr(block, "type", "") == "text"
    ).strip()

    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:].lstrip()

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error("Claude returned non-JSON content: %s", content[:300])
        raise ValueError(f"Failed to parse Claude JSON output: {e}") from e


def parse_cv(cv_path: Optional[Path] = None) -> dict:
    path = Path(cv_path) if cv_path else CV_PATH
    if not path.exists():
        raise FileNotFoundError(f"CV file not found: {path}")

    database.init_db()

    raw_text = _read_pdf(path)
    if not raw_text.strip():
        raise ValueError(f"Could not extract text from PDF: {path}")

    fingerprint = _file_fingerprint(path)
    cached = database.get_cv_profile()
    if cached:
        cached_parsed = cached["parsed"]
        if cached_parsed.get("_fingerprint") == fingerprint:
            logger.info("CV unchanged; returning cached profile")
            return cached_parsed

    parsed = _call_claude(raw_text)
    parsed["_fingerprint"] = fingerprint

    database.save_cv_profile(raw_text, json.dumps(parsed, ensure_ascii=False))
    return parsed
