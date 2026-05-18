# Import all the models, so that Base has them before being
# imported by Alembic
from app.db.base_class import Base  # noqa
from app.models.user import User  # noqa
from app.models.project import Project  # noqa
from app.models.voice_profile import VoiceProfile  # noqa
from app.models.script_segment import ScriptSegment  # noqa
