from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional
import uuid
from sqlalchemy import String, ForeignKey
from app.db.base_class import Base
from pgvector.sqlalchemy import Vector

if TYPE_CHECKING:
    from .user import User

class VoiceProfile(Base):
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"))
    name: Mapped[str] = mapped_column(String, index=True)
    embedding: Mapped[Vector] = mapped_column(Vector(1024))
    base_model: Mapped[str] = mapped_column(String, default="Qwen3-TTS-12Hz-1.7B-Base")
    reference_audio_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reference_text: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    owner: Mapped["User"] = relationship("User", back_populates="voice_profiles")
