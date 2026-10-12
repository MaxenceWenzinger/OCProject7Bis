from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector as PgVector
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.event import Event

class Vector(Base):
    __tablename__ = "vectors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_uid: Mapped[int] = mapped_column(ForeignKey("events.uid"), nullable=False)
    vector: Mapped[PgVector] = mapped_column(PgVector(1536), nullable=False)

    event: Mapped["Event"] = relationship(back_populates="vectors")