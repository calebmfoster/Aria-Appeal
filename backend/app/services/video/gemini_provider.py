import os
import time
import uuid
from typing import List, Optional

import asyncer

from app.services.video.base import VideoProvider, VideoGenRequest, VideoGenResult
from app.services.video import ffmpeg_utils

# Matches the ffmpeg normalization target (1920x1080) so Veo renders at the
# resolution we actually keep — no upscaling, no wasted render.
TARGET_RESOLUTION = "1080p"


def _load_image(path: str):
    """Read an image file into a genai Image, or None if it isn't there."""
    from google.genai import types

    if not path or not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        data = f.read()
    mime = "image/png" if path.lower().endswith(".png") else "image/jpeg"
    return types.Image(image_bytes=data, mime_type=mime)


class GeminiVeoProvider(VideoProvider):
    """Generates a clip via Google Veo (Gemini API).

    Visuals only: we ask Veo not to generate audio, because the narration comes
    from the TTS pipeline and normalization strips any clip audio anyway.
    """

    name = "gemini"

    def __init__(self, api_key: str, model: str, out_dir: str,
                 poll_interval_s: float = 8.0, timeout_s: float = 300.0,
                 person_generation: str = "allow_adult"):
        self.api_key = api_key
        self.model = model
        self.out_dir = out_dir
        self.poll_interval_s = poll_interval_s
        self.timeout_s = timeout_s
        # Appeals are about people; the default would otherwise block subjects.
        self.person_generation = person_generation

    def _make_client(self):
        from google import genai
        return genai.Client(api_key=self.api_key)

    @staticmethod
    def _compose_prompt(req: VideoGenRequest) -> str:
        parts = [req.prompt or ""]
        if req.style_prompt:
            parts.append(f"Style: {req.style_prompt}")
        if req.character_sheet:
            parts.append(f"Consistent subjects: {req.character_sheet}")
        return "\n".join(p for p in parts if p)

    def _build_reference_images(self, req: VideoGenRequest) -> List:
        from google.genai import types

        refs = []
        for path in req.reference_image_paths or []:
            image = _load_image(path)
            if image is None:
                continue  # a missing anchor shouldn't sink the whole generation
            refs.append(types.VideoGenerationReferenceImage(
                image=image,
                reference_type=types.VideoGenerationReferenceType.ASSET,
            ))
        return refs

    def _generate_sync(self, req: VideoGenRequest) -> VideoGenResult:
        from google.genai import types

        if not self.api_key:
            raise RuntimeError(
                "Gemini API key is not configured. Set it in the launcher Settings "
                "panel or the GEMINI_API_KEY environment variable."
            )
        client = self._make_client()

        config = types.GenerateVideosConfig(
            number_of_videos=1,
            aspect_ratio=req.aspect_ratio,
            duration_seconds=int(req.duration_s),
            resolution=TARGET_RESOLUTION,
            generate_audio=False,
            person_generation=self.person_generation,
            negative_prompt=req.negative_prompt,
            reference_images=self._build_reference_images(req),
        )
        op = client.models.generate_videos(
            model=self.model,
            prompt=self._compose_prompt(req),
            image=_load_image(req.init_image_path or ""),
            config=config,
        )

        # Deadline off a monotonic clock rather than summing sleeps, so a zero
        # poll interval can't spin forever.
        deadline = time.monotonic() + self.timeout_s
        while not op.done:
            if time.monotonic() > deadline:
                raise TimeoutError(f"Veo generation timed out after {self.timeout_s}s")
            time.sleep(self.poll_interval_s)
            op = client.operations.get(op)

        if getattr(op, "error", None):
            raise RuntimeError(f"Veo generation failed: {op.error}")

        video = op.response.generated_videos[0].video
        data = client.files.download(file=video)
        os.makedirs(self.out_dir, exist_ok=True)
        out_path = os.path.join(self.out_dir, f"veo_{uuid.uuid4().hex}.mp4")
        with open(out_path, "wb") as f:
            f.write(data)

        return VideoGenResult(video_path=out_path, duration_ms=ffmpeg_utils.probe_duration_ms(out_path))

    async def generate(self, req: VideoGenRequest) -> VideoGenResult:
        return await asyncer.asyncify(self._generate_sync)(req)
