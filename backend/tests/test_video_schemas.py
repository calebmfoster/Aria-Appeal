import uuid
from app.schemas.video import VideoClipRead, VideoClipUpdate


def test_videoclipread_minimal():
    vc = VideoClipRead(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        segment_id=None,
        sequence_order=0,
        source_type="generated",
        status="pending",
        prompt=None,
        video_url=None,
        duration_ms=None,
        trim_start_ms=None,
        trim_end_ms=None,
        timeline_start_ms=None,
        timeline_end_ms=None,
    )
    assert vc.source_type == "generated"
    assert vc.status == "pending"


def test_videoclipupdate_is_partial():
    upd = VideoClipUpdate(prompt="new prompt")
    assert upd.prompt == "new prompt"
    assert upd.trim_start_ms is None
