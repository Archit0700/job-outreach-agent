"""No-fabrication tailoring tests."""
import pytest

from app.services.tailoring.tailor import deterministic_tailor, tailor_resume, validate_no_fabrication

RESUME = """
Archit
Skills: Python, SQL, Java
Project: RAG chatbot with Hugging Face
Internship: LLM evaluation at Southampton
"""

PROFILE = {
    "candidate": {
        "name": "Archit",
        "skills": ["Python", "SQL", "Java"],
        "projects": ["RAG chatbot with Hugging Face"],
        "internships": ["LLM evaluation at Southampton"],
        "education": [{"degree": "Computer Science"}],
    },
    "skills_evidence": [{"skill": "Python", "evidence": ["RAG chatbot"]}],
}


def test_deterministic_reorder():
    result = deterministic_tailor(
        PROFILE, RESUME, "Python Backend Engineer", "Need Python and SQL. Kubernetes required."
    )
    assert result["diff"]["added_claims"] == []
    assert result["content"]["skills_order"][0] in {"Python", "SQL"}
    issues = validate_no_fabrication(result, RESUME)
    assert issues == []


def test_fabrication_detected():
    bad = {
        "plain_text": "Increased revenue by 400% with Kubernetes",
        "diff": {"added_claims": ["Kubernetes expert"]},
        "claims_used": ["Kubernetes expert"],
    }
    issues = validate_no_fabrication(bad, RESUME)
    assert issues


@pytest.mark.asyncio
async def test_tailor_async():
    result = await tailor_resume(
        PROFILE, RESUME, "AI Engineer", "Python RAG LLMs", use_llm=False
    )
    assert result["fabrication_issues"] == []
    assert "Python" in result["content"]["skills_order"]
