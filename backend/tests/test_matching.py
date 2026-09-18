"""Matching + why-this-job tests."""
import pytest

from app.services.matching.matcher import heuristic_match, match_job

PROFILE = {
    "candidate": {
        "name": "Archit",
        "skills": ["Python", "SQL", "RAG", "LLMs", "Machine Learning"],
        "education": [{"degree": "Computer Science"}],
        "projects": ["RAG chatbot"],
        "experience": [],
        "internships": ["University of Southampton LLM evaluation"],
    },
    "skills_evidence": [
        {"skill": "Python", "evidence": ["RAG chatbot"]},
        {"skill": "RAG", "evidence": ["RAG chatbot"]},
    ],
}


def test_heuristic_match_scores():
    result = heuristic_match(
        PROFILE,
        "ML Engineer Intern",
        "Looking for Python, RAG, LLMs, and Kubernetes experience. Entry level.",
    )
    assert result["overall_score"] > 50
    assert "Python" in result["strong_matches"]
    assert "RAG" in result["strong_matches"]
    assert any("Kubernetes" in g or g == "Kubernetes" for g in result["potential_gaps"])
    assert result["why_this_job"]["matches"]
    assert result["why_this_job"]["gaps"]


@pytest.mark.asyncio
async def test_match_job_no_invention():
    result = await match_job(
        PROFILE,
        "Software Engineer",
        "Requires Python and SQL. Kubernetes is a plus.",
        use_llm=False,
    )
    # Should not list Kubernetes as strong match
    assert all("kubernetes" not in s.lower() for s in result["strong_matches"])
