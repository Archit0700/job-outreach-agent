"""Deterministic mock LLM for tests and local runs without API keys."""
from __future__ import annotations

import json
import re
from typing import Any

from app.services.llm.base import LLMProvider


class MockLLMProvider(LLMProvider):
    name = "mock"

    async def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> str:
        lower = (system + user).lower()

        if "parse" in lower and "resume" in lower:
            return json.dumps(self._parse_resume(user))
        if "match" in lower or "score" in lower:
            return json.dumps(self._match(user))
        if "tailor" in lower:
            return json.dumps(self._tailor(user))
        if "email" in lower or "outreach" in lower:
            return json.dumps(self._email(user))
        if "qc" in lower or "verif" in lower or "quality" in lower:
            return json.dumps({"verified": True, "issues": []})
        if "personalization" in lower:
            return json.dumps(
                {
                    "role_alignment": "Relevant technical background",
                    "matching_experience": ["Python projects"],
                    "company_reason": "Strong engineering culture",
                    "technical_alignment": ["Python", "SQL"],
                }
            )
        return json.dumps({"ok": True, "message": "mock response"})

    def _parse_resume(self, user: str) -> dict[str, Any]:
        text = user
        skills = []
        for skill in [
            "Python", "Java", "C++", "SQL", "Machine Learning", "LLMs", "RAG",
            "Hugging Face", "ChromaDB", "TensorFlow", "JavaScript", "React",
            "FastAPI", "Docker", "Git", "Android", "Kotlin",
        ]:
            if re.search(rf"\b{re.escape(skill)}\b", text, re.I):
                skills.append(
                    {
                        "skill": skill,
                        "evidence": ["Mentioned in resume text"],
                    }
                )
        name_match = re.search(r"(?:name[:\s]+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text)
        name = name_match.group(1) if name_match else "Archit"
        return {
            "candidate": {
                "name": name,
                "education": [{"degree": "Computer Science", "institution": "University", "year": None}],
                "skills": [s["skill"] for s in skills] or ["Python", "SQL"],
                "experience": [],
                "internships": [],
                "projects": [],
                "certifications": [],
                "achievements": [],
                "links": {},
                "contact": {},
            },
            "skills_evidence": skills
            or [{"skill": "Python", "evidence": ["Default from mock parser"]}],
        }

    def _match(self, user: str) -> dict[str, Any]:
        # Simple heuristic overlap for mock
        profile_skills = set(re.findall(r"\b(Python|Java|SQL|RAG|LLM|React|Android|ML)\b", user, re.I))
        score = min(95.0, 40.0 + len(profile_skills) * 10)
        strong = sorted({s.title() if s.lower() != "sql" else "SQL" for s in profile_skills}) or ["Python"]
        return {
            "overall_score": score,
            "technical_skills": min(100.0, score + 5),
            "experience_score": max(50.0, score - 15),
            "education_score": 100.0,
            "projects_score": max(60.0, score - 5),
            "role_alignment": score,
            "strong_matches": strong,
            "potential_gaps": ["Production Kubernetes experience"],
            "why_this_job": {
                "matches": [{"item": s, "reason": "strong match"} for s in strong],
                "gaps": [{"item": "Kubernetes", "reason": "not evidenced in resume"}],
            },
        }

    def _tailor(self, user: str) -> dict[str, Any]:
        return {
            "content": {
                "summary": "Entry-level software engineer with evidence-backed skills from master resume.",
                "skills_order": ["Python", "SQL", "Machine Learning"],
                "emphasized_projects": [],
                "emphasized_experience": [],
                "bullets": [],
            },
            "plain_text": "TAILORED RESUME (mock)\nSkills prioritized from master resume only.\n",
            "diff": {
                "reordered_skills": True,
                "added_claims": [],
                "removed_sections": [],
                "rewritten_bullets": [],
            },
            "claims_used": [],
        }

    def _email(self, user: str) -> dict[str, Any]:
        company = "the company"
        role = "the role"
        m = re.search(r"company[:\s]+([^\n]+)", user, re.I)
        if m:
            company = m.group(1).strip()[:80]
        m = re.search(r"role[:\s]+([^\n]+)", user, re.I)
        if m:
            role = m.group(1).strip()[:80]
        body = (
            f"Hi,\n\nI'm Archit, a Computer Science undergraduate interested in the {role} "
            f"opportunity at {company}.\n\n"
            "My recent work has focused on software engineering and applied ML. "
            "I have evidence-backed experience with Python and related tools from my resume.\n\n"
            f"The {role} stood out because it aligns with my technical background. "
            "I've attached a tailored resume. If the team is considering entry-level candidates, "
            "I'd appreciate the opportunity to discuss how I could contribute.\n\n"
            "Best,\nArchit"
        )
        return {
            "subject": f"Interest in {role} at {company}",
            "body": body,
            "personalization": {
                "role_alignment": f"Interest in {role}",
                "matching_experience": ["Python experience from resume"],
                "company_reason": f"Interest in {company}",
                "technical_alignment": ["Python"],
            },
            "word_count": len(body.split()),
        }
