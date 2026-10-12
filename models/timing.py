import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.event import Event

class Timing(Base):
    __tablename__ = "timings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_uid: Mapped[int] = mapped_column(ForeignKey("events.uid"), nullable=False)
    begin: Mapped[datetime.datetime] = mapped_column(nullable=False)
    end: Mapped[datetime.datetime] = mapped_column(nullable=False)

    event: Mapped["Event"] = relationship(back_populates="timings")