import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, Column, ForeignKey, Numeric, String, Table, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.models import AuditColumnsMixin, uuid_pk
from app.modules.users.models import User

# Who manages which property. It is a Property Manager's data scope (docs/roles-and-permissions.md).
property_assignments = Table(
    "property_assignments",
    Base.metadata,
    Column("property_id", Uuid, ForeignKey("properties.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True),
)


class Property(AuditColumnsMixin, Base):
    """A real estate asset that contracts relate to (SRS 4.6, 7.1 Property)."""

    __tablename__ = "properties"
    __table_args__ = (
        CheckConstraint(
            "property_type IN ('residential', 'retail', 'office', 'industrial', 'land', 'mixed_use', 'other')",
            name="property_type",
        ),
        CheckConstraint("area_sqm IS NULL OR area_sqm > 0", name="area_positive"),
        CheckConstraint("code = upper(code)", name="code_uppercase"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    # Stored upper-cased, so "wm-g14" and "WM-G14" are the same property.
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    property_type: Mapped[str] = mapped_column(String(30))
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(100))
    area_sqm: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    notes: Mapped[str | None] = mapped_column(Text)

    managers: Mapped[list[User]] = relationship(
        secondary=property_assignments, lazy="selectin", order_by=User.full_name
    )
