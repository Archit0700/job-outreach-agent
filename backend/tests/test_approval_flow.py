"""Full approval gating API flow."""
import pytest


@pytest.mark.asyncio
async def test_cannot_send_without_approval(client, auth_headers):
    # Login + resume
    files = {
        "file": (
            "resume.txt",
            b"Archit\nComputer Science\nSkills: Python, SQL, RAG, LLMs\nProject: RAG chatbot with ChromaDB",
            "text/plain",
        )
    }
    up = await client.post("/api/resumes/upload", headers=auth_headers, files=files)
    assert up.status_code == 200, up.text

    companies = (await client.get("/api/companies", headers=auth_headers)).json()
    company_id = companies[0]["id"]

    # Add verified contact so email path is possible
    contact = await client.post(
        "/api/contacts",
        headers=auth_headers,
        json={
            "company_id": company_id,
            "name": "Campus Recruiter",
            "email": "campus.recruiter@example.com",
            "role": "University Recruiter",
            "source": "user_provided",
        },
    )
    assert contact.status_code == 200, contact.text

    # We need a job — use discover (network) or create via adding greenhouse board company
    # Insert job using a tiny helper endpoint isn't available; use discover on Stripe if network works,
    # else create company with manual job through DB by calling prepare after inventing via companies seed.
    # For offline: post discover then if empty, skip prepare and craft message via reject path.
    disc = await client.post("/api/jobs/discover", headers=auth_headers, json={})
    assert disc.status_code == 200

    jobs = (await client.get("/api/jobs", headers=auth_headers)).json()
    if not jobs:
        pytest.skip("No jobs discovered offline — discovery adapters returned empty")

    job_id = jobs[0]["id"]
    prep = await client.post(
        "/api/outreach/prepare",
        headers=auth_headers,
        json={"job_id": job_id, "use_llm": False},
    )
    assert prep.status_code == 200, prep.text
    msg = prep.json()

    # Attempt send without approve
    send = await client.post(f"/api/outreach/{msg['id']}/send", headers=auth_headers)
    assert send.status_code == 400
    assert "approved" in send.json()["detail"].lower()


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
