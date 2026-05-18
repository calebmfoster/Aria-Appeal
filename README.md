# Aria Appeal

AI-powered donor-focused audio studio for non-profit fundraising. Generates campaign scripts via LLM, synthesizes speech via Qwen3-TTS, and provides a Descript-style studio editor for iterative audio editing with zero-shot voice cloning.

## Stack

- **Frontend** — Next.js 15 (App Router), React 19, TypeScript, Tailwind, Zustand, wavesurfer.js
- **Backend** — FastAPI (Python 3.12), async SQLAlchemy, Pydantic
- **Database** — PostgreSQL + pgvector (Supabase)
- **TTS** — Qwen3-TTS (1.7B-Base for zero-shot cloning, CustomVoice for preset speakers)
- **Auth** — NextAuth.js (frontend) + JWT/bcrypt (backend)

## Quickstart

### Backend
```powershell
cd backend
copy .env.example .env   # fill in DATABASE_URL and ANTHROPIC_API_KEY
copy config.json.example config.json
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend
```powershell
cd frontend
copy .env.example .env.local   # set NEXTAUTH_SECRET and confirm API URL
npm install
npm run dev
```

The app runs at `http://localhost:3000`, backed by `http://localhost:8000`.

## Project Layout

```
backend/         FastAPI app, models, services, alembic migrations
frontend/        Next.js app, components, Zustand store
documentation/   Charter, progress, open issues, next-session prompts
launcher.py      Tk-based dev launcher (Windows)
```

## More

- [`CLAUDE.md`](CLAUDE.md) — codebase conventions and key architecture decisions
- [`documentation/Product_Roadmap.md`](documentation/Product_Roadmap.md) — prioritized feature backlog
- [`documentation/Project_Progress.md`](documentation/Project_Progress.md) — phase history
- [`documentation/Open_Issues.md`](documentation/Open_Issues.md) — known issues and deferred work

## Notes

- `ffmpeg`/`ffprobe` are not used — audio I/O is WAV-only via `soundfile`.
- GPU is optional but recommended (PyTorch + CUDA 12.6). The TTS engine auto-detects CUDA and uses bfloat16 when available.
