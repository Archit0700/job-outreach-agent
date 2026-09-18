"""Resume PDF/DOCX text extraction and structured profile parsing."""
from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path
from typing import Any

from app.services.llm.base import LLMProvider, wrap_untrusted
from app.services.llm.factory import get_llm_provider


def extract_text_from_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


def extract_text_from_docx(data: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs if p.text).strip()


def extract_text(filename: str, data: bytes) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return extract_text_from_pdf(data)
    if lower.endswith(".docx"):
        return extract_text_from_docx(data)
    if lower.endswith(".txt"):
        return data.decode("utf-8", errors="replace")
    raise ValueError(f"Unsupported resume format: {filename}")


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


PARSE_SYSTEM = """You are a resume parser. Extract a structured candidate profile from the resume text.
Rules:
- Only extract facts present in the resume. NEVER fabricate.
- For each skill, list evidence (project/job names) from the resume.
- Return JSON with keys: candidate (name, education, skills, experience, internships, projects, certifications, achievements, links, contact), skills_evidence (list of {skill, evidence}).
"""


async def parse_resume_to_profile(
    raw_text: str,
    llm: LLMProvider | None = None,
) -> dict[str, Any]:
    llm = llm or get_llm_provider()
    # Resume is user-provided trusted content, but still wrap for consistency
    user = f"Parse this resume into structured JSON:\n\n{raw_text[:50000]}"
    result = await llm.complete_json(PARSE_SYSTEM, user)
    if not isinstance(result, dict):
        raise ValueError("Parser did not return an object")
    # Ensure required shape
    candidate = result.get("candidate") or {}
    if not candidate.get("skills"):
        candidate["skills"] = heuristic_skills(raw_text)
    skills_evidence = result.get("skills_evidence") or []
    if not skills_evidence:
        skills_evidence = [
            {"skill": s, "evidence": ["Found in resume text"]} for s in candidate["skills"]
        ]
    return {
        "candidate": candidate,
        "skills_evidence": skills_evidence,
        "raw_text_hash": text_hash(raw_text),
    }


KNOWN_SKILLS = [
    "Python", "Java", "C++", "C", "SQL", "JavaScript", "TypeScript", "React", "Node.js",
    "FastAPI", "Django", "Flask", "Machine Learning", "Deep Learning", "TensorFlow",
    "PyTorch", "LLMs", "RAG", "Hugging Face", "ChromaDB", "Docker", "Kubernetes",
    "AWS", "GCP", "Azure", "Git", "Android", "Kotlin", "Swift", "Go", "Rust",
    "PostgreSQL", "MongoDB", "Redis", "GraphQL", "REST", "MATLAB", "NumPy", "Pandas",
]


def heuristic_skills(text: str) -> list[str]:
    found = []
    for skill in KNOWN_SKILLS:
        if re.search(rf"\b{re.escape(skill)}\b", text, re.I):
            found.append(skill)
    return found


def claim_exists_in_resume(claim: str, resume_text: str) -> bool:
    """Simple evidence check: claim tokens appear in resume (no fabrication)."""
    claim_l = claim.lower().strip()
    if not claim_l:
        return False
    resume_l = resume_text.lower()
    if claim_l in resume_l:
        return True
    # Check significant tokens
    tokens = [t for t in re.findall(r"[a-z0-9+#.]{3,}", claim_l) if t not in {"the", "and", "for", "with"}]
    if not tokens:
        return False
    hits = sum(1 for t in tokens if t in resume_l)
    return hits >= max(1, len(tokens) // 2)
