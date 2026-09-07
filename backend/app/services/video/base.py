from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class VideoGenRequest:
    prompt: str
    style_prompt: Optional[str] = None
    character_sheet: Optional[str] = None
    # First frame of the clip — used for tail-frame chaining (shot continuity).
    init_image_path: Optional[str] = None
    # Subject/style anchors that persist across the whole campaign. Unlike
    # init_image_path these do not dictate the opening frame, so they hold a
    # character consistent without forcing every shot to start where the last ended.
    reference_image_paths: List[str] = field(default_factory=list)
    negative_prompt: Optional[str] = None
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
