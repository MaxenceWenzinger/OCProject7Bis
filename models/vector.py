from typing import TYPE_CHECKING

import pgvector
import pgvector.sqlalchemy
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.event import Event

class Vector(Base):
    __tablename__ = "vectors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_uid: Mapped[int] = mapped_column(ForeignKey("events.uid"), nullable=False)
    vector: Mapped[pgvector.Vector] = mapped_column(pgvector.sqlalchemy.VECTOR(dim=1024), nullable=False)
    sparse: Mapped[pgvector.SparseVector] = mapped_column(pgvector.sqlalchemy.SPARSEVEC(dim=250002), nullable=False)

    event: Mapped["Event"] = relationship(back_populates="vectors")