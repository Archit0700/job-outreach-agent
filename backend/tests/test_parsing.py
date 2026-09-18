"""Resume parsing tests."""
import pytest

from app.services.resume.parser import (
    claim_exists_in_resume,
    extract_text,
    heuristic_skills,
    parse_resume_to_profile,
)
from app.services.llm.mock_provider import MockLLMProvider


SAMPLE = """
Archit Chhikara
Computer Science Undergraduate

Skills: Python, SQL, Machine Learning, LLMs, RAG, Hugging Face, ChromaDB, Java, C++

Experience:
Research Internship — University of Southampton
Worked on robustness and reasoning evaluation for LLMs

Internship — RAG chatbot
Built a RAG-based PDF question-answering system using Hugging Face, ChromaDB and Gemini

Projects:
Company Placement Recommendation project using Python and SQL
"""


def test_heuristic_skills():
    skills = heuristic_skills(SAMPLE)
    assert "Python" in skills
    assert "SQL" in skills
    assert "RAG" in skills


def test_claim_exists():
    assert claim_exists_in_resume("Python", SAMPLE)
    assert claim_exists_in_resume("RAG chatbot internship", SAMPLE)
    assert not claim_exists_in_resume("Kubernetes production cluster", SAMPLE)


def test_extract_txt():
    text = extract_text("resume.txt", SAMPLE.encode())
    assert "Archit" in text


@pytest.mark.asyncio
async def test_parse_profile_mock():
    result = await parse_resume_to_profile(SAMPLE, llm=MockLLMProvider())
    assert "candidate" in result
    assert result["candidate"]["name"]
    assert result["skills_evidence"]
    assert any(s["skill"] == "Python" for s in result["skills_evidence"])
