# AI Job Outreach & Resume Tailoring Agent

Production-oriented MVP that turns a **master resume** into **matched jobs**, **evidence-backed tailored resumes**, **personalized outreach**, and **human-approved** sends — with hard guarantees against fabrication, guessed emails, and auto-send.

Spec: `/workspace/job-outreach-spec/SPEC.md` (authoritative).

## Quick start

```bash
cd job-outreach-agent
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:3000  
- API docs: http://localhost:8000/docs  
- Health: http://localhost:8000/health  

Demo login (no OAuth required): open the app → **Log in** → continue as Archit (`archit@example.com`).

### Without Docker (API unit tests / local API)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=sqlite+aiosqlite:///./dev.db
export LLM_PROVIDER=mock
export APP_SECRET_KEY=dev-secret
uvicorn app.main:app --reload --port 8000

# tests
pytest -q
```

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

## Architecture

| Service | Role |
|--------|------|
| `frontend/` | Next.js + React + TypeScript + Tailwind |
| `backend/` | FastAPI domain APIs + services |
| `postgres` (pgvector image) | Persistence + vector extension ready |
| `redis` + `worker` | **Celery + Redis** queue (chosen over ARQ/RQ for ecosystem maturity) |
| LLM layer | `mock` / OpenAI / Gemini / Anthropic with structured JSON |

### Pipeline

Master Resume → Profile → Job Discovery → Match (“Why this job?”) → Tailor (no fabrication) → Public contacts only → Email + QC → **Human approval** → Send → Track / optional follow-ups.

## What is fully implemented vs stubbed

### Implemented
- DB models for all SPEC §17 tables (+ audit_logs)
- Resume upload (PDF/DOCX/TXT), parse → candidate profile + skills evidence
- Preferences / settings with Archit defaults
- **Greenhouse** public board API adapter (real HTTP)
- **Lever** public postings API adapter (real HTTP when board exists)
- Heuristic + optional LLM semantic matching with evidence-backed gaps/matches
- Resume tailoring that **reorders/emphasizes only**; fabrication QC
- Contact model: **user-provided / verified only** — never guessed emails
- Official application URL fallback when no verified contact
- Outreach prepare → edit → approve → reject → save → send
- Approval gating, duplicate prevention, daily & per-company limits
- QC gate (placeholders, exaggeration, unverified recipients)
- Gmail + Microsoft Graph OAuth **wired**; **safe no-op send** if keys unset
- Dashboard metrics, job feed filters, outreach review UI, resume versions UI
- Celery tasks for discovery + follow-up dispatch
- Automated tests (parsing, matching, no-fabrication, duplicates, approval)

### Honest stubs / extension points
- Workday / Wellfound / LinkedIn adapters return `[]` (`stub_sources.py`) — no CAPTCHA/auth bypass
- Google **app** login OAuth start URL only (demo login is the local path)
- pgvector extension enabled in Postgres; embeddings column stored as JSON for SQLite test portability (wire `vector` type in Postgres-only deploy if desired)
- Follow-up **sending** uses the same no-op/provider path; only schedules when user opts in
- Alembic revision `001` documents schema; app also `create_all` on startup for MVP bootstrap

## Non-negotiables (enforced in code)

- Never fabricate qualifications / contacts / emails
- Never auto-send (`require_manual_approval` default true)
- Daily + per-company send limits; duplicate outreach blocked
- JD/web content wrapped as untrusted (prompt-injection safe)
- No CAPTCHA / auth / robots bypass for discovery

## Environment keys

See `.env.example` for every variable. Minimum for local demo:

```bash
APP_SECRET_KEY=...
LLM_PROVIDER=mock
POSTGRES_* / DATABASE_URL  # via compose
REDIS_URL                  # via compose
```

Optional:

| Key | Purpose |
|-----|---------|
| `OPENAI_API_KEY` / `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` | Real LLM |
| `GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET` | Gmail send |
| `MS_CLIENT_ID` / `MS_CLIENT_SECRET` | Outlook send |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | App Google login |

### Gmail OAuth setup
1. Google Cloud Console → enable **Gmail API**
2. OAuth client (Web) with redirect `http://localhost:8000/api/oauth/gmail/callback`
3. Scope used: `gmail.send` only
4. Connect from **Settings** in the UI

### Microsoft Graph setup
1. Azure App Registration → redirect `http://localhost:8000/api/oauth/microsoft/callback`
2. Delegated permission `Mail.Send`
3. Connect from **Settings**

## Target companies (seed)

SPEC §19 list (Google, Microsoft, Amazon, Adobe, Atlassian, Deloitte, PwC, EY, KPMG, ZS, Mu Sigma, Tredence, BlackRock) plus companies with known public Greenhouse boards for live discovery demos.

## Queue choice

**Celery + Redis** — documented in `backend/app/workers/celery_app.py`. Tasks: `jobs.discover`, `followups.dispatch`.

## Git

Repository is initialized locally. Push when you have credentials:

```bash
git remote add origin <your-repo-url>
git push -u origin main
```

## License

For personal / educational use aligned with responsible outreach practices in the spec.
