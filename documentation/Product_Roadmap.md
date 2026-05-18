# Aria Appeal — Product Roadmap

**Created**: 2026-03-27
**Last Updated**: 2026-03-27

This document defines the gap between the current PoC and a polished, demo-ready product. Organized into priority tiers with the goal of making each tier independently demoable.

---

## Current State (Working)

- User registration and login
- Voice profile upload with quality validation (LUFS, speech clarity)
- Voice preview playback
- Campaign creation with LLM script generation
- Studio editor with script segments, waveform visualization, and inspector panel
- TTS generation with both preset voices and zero-shot voice cloning
- Per-segment regeneration with voice swap
- Global voice change + Regenerate All
- Auto re-export after regeneration
- Moore brand applied throughout

## Current State (Broken or Missing)

- No campaign list on dashboard (dead end after leaving studio)
- Export button doesn't download anything
- Script edits are local-only (lost on refresh)
- No dirty/unsaved indicator
- No project name anywhere
- No forgot password
- No delete confirmations
- Waveform has no time display, zoom, or volume
- No keyboard shortcuts
- PyTorch is CPU-only despite RTX 4080 Super being available

---

## Tier 1 — Must-Have for Demo (1-2 sessions)

These are blockers. Without them, a demo falls apart.

### 1.1 Campaign List on Dashboard
- Fetch and display all user campaigns as cards
- Show: title (or cause), creation date, status badge (draft/generating/complete), segment count
- Click to open studio
- Kebab menu: rename, delete (with confirmation)

### 1.2 Download Button
- Replace "Export" with "Download" semantics
- When master audio is ready, trigger browser file download (`.wav`)
- Show download progress or at minimum a spinner → download link
- If master audio doesn't exist yet, generate it first, then download

### 1.3 Auto-Save Script Edits to Backend
- Debounced save (500ms after last keystroke) for text, voice_profile_id, and emotion changes
- API endpoint to PATCH individual segment fields
- Save status indicator in inspector: "Saved" / "Saving..." / "Unsaved changes"
- On page load, always fetch fresh from backend (current behavior, now safe because edits persist)

### 1.4 Dirty Indicator on Modified Segments
- Track whether segment text/voice/emotion has changed since last audio generation
- Orange dot or "stale" badge on segments where text ≠ what was last generated
- "Regenerate" button visually highlighted (pulse or color change) when segment is dirty
- After regeneration completes, clear the dirty flag

### 1.5 GPU Acceleration
- One command: `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126`
- Existing code auto-detects CUDA and switches to bfloat16
- Expected speedup: 10-30s/segment → 1-3s/segment

### 1.6 Project Name
- Add `title` field to campaign creation modal (auto-generated from cause if left blank)
- Display project name in studio header (editable inline)
- Show on campaign cards in dashboard

---

## Tier 2 — Makes the Demo Impressive (1-2 sessions)

These turn a functional demo into a "wow" moment.

### 2.1 Prompt-Based Segment Editing
- Add a prompt input box to InspectorPanel: "Describe how to change this segment"
- Examples: "make it more urgent", "add a personal story", "shorten to two sentences"
- Send current segment text + prompt to LLM → receive rewritten text
- Auto-populate the text field with the result (user can review before regenerating)
- Optional: "Accept & Regenerate" button that saves + regenerates in one click

### 2.2 Custom Script Option
- Toggle on campaign creation: "Generate with AI" vs "Paste your own script"
- If pasting: single textarea, backend splits into segments by sentence/paragraph
- Same studio experience after creation

### 2.3 Emotion Directive UX
- Keep as free-form textarea (NOT presets/dropdown)
- Rich placeholder text showing the power of the field:
  ```
  e.g. "Sadly, slowly at first. Then building with a note of resolve
  and hope from the 4th sentence onward"
  ```
- Tooltip or help text explaining that emotion directives shape the voice performance
- Per-segment emotion (already supported) — make it visually prominent
- Consider a global emotion field in campaign creation that pre-fills all segments

### 2.4 Keyboard Shortcuts
- Space = play/pause
- ← / → = skip to previous/next segment
- Ctrl+S = force save (with visual confirmation)
- Escape = deselect segment
- Display shortcut hints on hover or in a help tooltip

### 2.5 Waveform Time Display
- Current time / total duration readout below or above waveform
- Format: `0:12 / 1:47`

### 2.6 Delete Confirmations
- Voice profile delete: "Delete [name]? This cannot be undone."
- Campaign delete: "Delete [title]? All audio and script data will be permanently removed."
- Use a modal or inline confirm pattern, not browser `confirm()`

---

## Tier 3 — Production Polish (Ongoing)

These make it feel like a real product, not a prototype.

### 3.1 Inline Text Editing
- Click segment text in ScriptEditor to edit directly (contentEditable or inline textarea)
- Changes sync to inspector panel and trigger auto-save
- Reduces the "edit in one place, see in another" friction

### 3.2 Segment Management
- Add new segment (insert above/below)
- Delete segment (with confirmation + audio cleanup)
- Split segment (cursor position → two segments)
- Merge adjacent segments
- Drag-to-reorder (update sequence_order, recalculate timestamps)

### 3.3 Waveform Controls
- Zoom in/out (slider or +/- buttons)
- Volume slider
- Skip forward/back 5 seconds
- Minimap for long audio files

### 3.4 Per-Segment Mini Waveforms
- Small waveform thumbnail on each ScriptEditor card
- Shows relative duration and audio shape at a glance
- Click to seek

### 3.5 Forgot Password Flow
- "Forgot password?" link on login page
- Backend endpoint to send reset email
- Reset page with token validation and new password form

### 3.6 Auto-Login After Registration
- After successful registration, call `signIn()` automatically
- Redirect straight to dashboard instead of login page

### 3.7 Session Timeout Handling
- Detect 401 responses globally (fetch wrapper or axios interceptor)
- Show re-login modal overlay instead of silent failure
- Preserve current page state so user can resume after re-auth

### 3.8 Security Hardening
- Extend NextAuth session type (eliminate `as any` casts)
- CSRF protection middleware on FastAPI
- JWT refresh token rotation
- Rate limiting feedback in UI

### 3.9 Polling Safeguards
- Max retry count on all polling loops (e.g., 60 retries = 5 minutes)
- After max retries, show error state with "Retry" button
- Clean up intervals on component unmount (already partially done)

### 3.10 Mobile Responsive
- Dashboard: stack cards vertically, full-width voice upload
- Studio: not expected to work on phone, but show a "Use desktop for the best experience" message
- Login/register: already mostly works, add brand context on mobile

---

## Tier 4 — Enterprise / Scale (Future)

### 4.1 Infrastructure
- Docker compose with CUDA runtime image
- BackgroundTasks → Celery + Redis
- Local file storage → S3/R2 + CDN
- Model serving via vLLM or Triton Inference Server
- CI/CD pipeline
- Structured logging + Sentry error monitoring

### 4.2 Multi-Tenancy
- Organization accounts with team members
- Role-based access (admin, editor, viewer)
- Shared voice library per organization
- Campaign collaboration (multiple editors)

### 4.3 Advanced Audio
- Background music/SFX library with mixing
- Audio mastering (compression, EQ, normalization)
- Export format picker (WAV/MP3/FLAC/AAC)
- Batch export (multiple campaigns)

### 4.4 Analytics
- Campaign generation metrics (time to create, iterations per campaign)
- Voice usage analytics
- Cost tracking (GPU compute time per campaign)

### 4.5 Integrations
- Webhook on campaign completion
- API access for programmatic campaign generation
- CRM integration (import donor segments, personalize scripts)

---

## Demo Prep Checklist

Before any live demo, ensure:

- [ ] GPU PyTorch installed and verified (`torch.cuda.is_available() == True`)
- [ ] Both TTS models pre-loaded (first generation after restart is slow due to model loading)
- [ ] At least one cloned voice profile uploaded and tested
- [ ] Cloudflare Tunnel configured and tested from another device
- [ ] A rehearsed flow: create campaign → show script → change voice → regenerate → download
- [ ] Backup: have a pre-generated campaign ready to open in case of live demo issues
- [ ] Clear browser cache / use incognito to avoid stale state

---

## Estimated Effort

| Tier | Sessions | What You Get |
|------|----------|-------------|
| Tier 1 | 1-2 | Functional demo that doesn't break |
| Tier 2 | 1-2 | Impressive demo that shows vision |
| Tier 3 | 3-5 | Product that feels real |
| Tier 4 | 10+ | Enterprise-ready platform |
