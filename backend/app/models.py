"""Import every module's ORM models here so Alembic sees the full metadata.

Each feature module adds its own line, e.g. ``from app.modules.contracts.models import *``.
"""

from app.modules.audit.models import *  # noqa: F403
from app.modules.auth.models import *  # noqa: F403
from app.modules.contracts.models import *  # noqa: F403
from app.modules.documents.models import *  # noqa: F403
from app.modules.parties.models import *  # noqa: F403
from app.modules.properties.models import *  # noqa: F403
from app.modules.users.models import *  # noqa: F403
