from app.models.video_clip import VideoClip


def test_videoclip_tablename():
    assert VideoClip.__tablename__ == "videoclip"


def test_videoclip_has_expected_columns():
    cols = set(VideoClip.__table__.columns.keys())
    expected = {
        "id", "project_id", "segment_id", "sequence_order", "source_type",
        "prompt", "video_url", "status", "duration_ms",
        "trim_start_ms", "trim_end_ms", "timeline_start_ms", "timeline_end_ms",
        "init_image_path", "created_at",
    }
    missing = expected - cols
    assert not missing, f"missing columns: {missing}"


def test_videoclip_foreign_keys_target_lowercase_tables():
    fks = {fk.target_fullname for fk in VideoClip.__table__.foreign_keys}
    assert "project.id" in fks
    assert "scriptsegment.id" in fks
