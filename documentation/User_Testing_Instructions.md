# Phase IX User Testing Instructions

Please follow these steps to verify the Deep Voice Cloning features implemented in Phase IX.

## Prerequisites

- Supabase DB connection must be active
- Alembic migration `a1b2c3d4e5f6` must be applied (`python -m alembic upgrade head`)
- A WAV audio sample (15-45 seconds of clear speech) for testing voice cloning

## 1. Start the Application

**A. Start the FastAPI Backend**
1. Open a terminal in `d:\Repo\Aria Appeal\backend`.
2. Activate your virtual environment: `.\.venv\Scripts\Activate.ps1`.
3. Start the FastAPI server: `uvicorn app.main:app --reload`.

**B. Start the Next.js Frontend**
1. Open a terminal in `d:\Repo\Aria Appeal\frontend`.
2. Run `npm run dev`.
3. Open `http://localhost:3000` in your browser.

## 2. Test Voice Profile Upload with Cloning

1. Navigate to the Dashboard and find the Voice Profile section.
2. Click "Add New Voice Profile."
3. Enter a profile name (e.g., "My Voice").
4. *(Optional)* In the "Reference Transcript" textarea, type the exact words spoken in your audio sample.
5. Upload a `.wav` file (15-45 seconds of clear speech).
6. **Verification (Validation)**: The audio quality panel should show:
   - Loudness (LUFS) value — must be above -38 LUFS
   - Speech Clarity — must be above 15%
   - Green "Audio Quality: Passed" indicator
7. Click "Save Voice Profile."
8. **Verification (Success)**: Toast message: "Voice profile created with cloned voice!"
9. **Verification (List)**: The new profile appears in "Your Voice Profiles" with a purple "Cloned" badge.

## 3. Test Cloned Voice in Studio Editor

1. Open an existing project in the Studio editor, or create a new campaign.
2. Select any sentence segment in the Left-Hand script column.
3. In the Right-Hand Inspector panel, open the Voice Profile dropdown.
4. Select your newly created cloned voice profile (it should be listed by name).
5. Optionally add an emotion/direction (e.g., "Speak warmly and slowly").
6. Click "Regenerate Segment."
7. **Verification**:
   - The backend logs should show `Generating CLONED voice audio` (not `preset voice`).
   - The success toast should appear.
   - The waveform visualizer should display and play the generated audio.
   - The audio should sound like the uploaded reference voice (not a default Qwen preset).

## 4. Regression: Verify Preset Speakers Still Work

1. Select a different sentence segment.
2. In the Voice Profile dropdown, select "Default/Auto" or leave it unset.
3. Click "Regenerate Segment."
4. **Verification**: Audio generates successfully using the default Aiden preset voice.

## 5. Verify Global Voice Application

1. Click into the blank gray area (deselect all segments) to show Global Inspector.
2. Set the "Global Voice Profile" dropdown to your cloned voice.
3. Click "Regenerate All Segments."
4. **Verification**: All segments should regenerate using the cloned voice.

## 6. Known Limitations

- **FFmpeg not installed**: Only WAV format is supported for uploads and exports.
- **Cloning quality**: Depends heavily on the quality of the uploaded reference audio. Quiet rooms and consistent microphone distance produce the best results.
- **Reference transcript**: Providing the transcript of what was spoken in the reference audio improves cloning accuracy but is optional.
