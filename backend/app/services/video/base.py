from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class VideoGenRequest:
    prompt: str
    style_prompt: Optional[str] = None
    character_sheet: Optional[str] = None
    init_image_path: Optional[str] = None
    duration_s: float = 8.0
    aspect_ratio: str = "16:9"


@dataclass
class VideoGenResult:
    video_path: str
    duration_ms: Optional[int] = None


class VideoProvider(ABC):
    """Produces a raw video clip from a request. Normalization happens downstream."""

    name: str = "base"

    @abstractmethod
    async def generate(self, req: VideoGenRequest) -> VideoGenResult:
        ...
