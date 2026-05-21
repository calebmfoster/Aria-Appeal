# Aria Appeal

AI-powered donor-focused audio studio for non-profit fundraising. Generates campaign scripts via LLM, synthesizes speech via Qwen3-TTS, and provides a Descript-style studio editor for iterative audio editing with zero-shot voice cloning.

## Tech Stack

- **Frontend**: Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS, Zustand, wavesurfer.js
- **Backend**: FastAPI (Python 3.12), SQLAlchemy (async), Pydantic
- **Database**: PostgreSQL + pgvector (hosted on Supabase)
- **TTS**: Qwen3-TTS (1.7B-Base for cloning, CustomVoice for presets)
- **Auth**: NextAuth.js (frontend) + JWT/bcrypt (backend)

## Project Structure

```
backend/
  app/
    api/routes/      # FastAPI route handlers
    models/          # SQLAlchemy ORM models
    schemas/         # Pydantic request/response schemas
    services/        # Business logic (tts_engine, voice_cloner, llm, audio_editor, mastering)
    core/            # Config, security, system settings
    db/              # Database session + base classes
  alembic/           # Database migrations
  static/audio/      # Generated audio files
  static/voice_uploads/  # Reference audio for voice cloning
frontend/
  app/               # Next.js App Router pages
  components/        # React components (studio/, dashboard/, ui/)
  store/             # Zustand state (studioStore.ts)
  types/             # TypeScript interfaces
  lib/               # API config, utilities
documentation/       # Project charter, progress, issues, session prompts
```

## Dev Commands

```bash
# Backend
cd backend
.\.venv\Scripts\Activate.ps1          # Windows venv
uvicorn app.main:app --reload         # Start FastAPI (localhost:8000)
python -m alembic upgrade head        # Run migrations

# Frontend
cd frontend
npm run dev                           # Start Next.js (localhost:3000)
npm run build                         # Production build
npm run lint                          # ESLint
```

## Environment

- Backend `.env` must have `DATABASE_URL` (asyncpg connection string to Supabase)
- Frontend `.env.local` should set `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`
- Docker is NOT installed on this system — use local dev commands
- `ffmpeg`/`ffprobe` are NOT available — audio processing uses `soundfile` for WAV

## Code Conventions

- Backend uses async/await throughout (async SQLAlchemy sessions, asyncer for sync→async bridging)
- Background tasks use FastAPI `BackgroundTasks` (not Celery/Redis)
- Audio files are served from `/static/audio/` via FastAPI static mount
- Voice profile IDs are UUIDs; the TTS engine resolves them to either preset speaker names or reference audio paths
- All API routes are mounted under `/api/v1/`

## Key Architecture Decisions

- **TTS dual-path**: Profiles with `reference_audio_path` use zero-shot cloning (Base model); others use preset speakers (CustomVoice model)
- **Embeddings**: 1024-dim acoustic embeddings stored via pgvector; extracted by Qwen3-TTS tokenizer with spectral fallback
- **State management**: Zustand with discrete slices for script, playback, selection, and generation tracking
- **Audio editing**: pydub-based splicing with 25ms logarithmic crossfades at stitch points

## Current Phase

Phase X (Session 10) complete as of 2026-05-21. TTS working end-to-end on GPU (RTX 4080 Super, PyTorch 2.11.0+cu126, bfloat16). Studio is fully featured: inline editing, segment CRUD + drag-to-reorder, waveform controls, voice picker tabs, apiFetch migration. Dashboard polished: voice cloning legal disclaimer, voice profile usage indicator + inline rename, campaign progress bars + duration display.

See `documentation/Product_Roadmap.md` for the full prioritized feature/polish backlog (Tiers 1-4).

See `documentation/Project_Progress.md` for full history and `documentation/Next_Session_Prompt.md` for next steps.

## Session Workflow

1. Read `documentation/Next_Session_Prompt.md` for context on what to work on
2. After completing work, update `documentation/Project_Progress.md` and `documentation/Next_Session_Prompt.md`
3. Always update `documentation/Open_Issues.md` with any new discoveries
