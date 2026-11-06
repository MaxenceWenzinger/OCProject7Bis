from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.timing import Timing
    from models.vector import Vector

class Event(Base):
    __tablename__ = "events"

    uid: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    canonicalurl: Mapped[str] = mapped_column(nullable=True)
    title_fr: Mapped[str] = mapped_column(nullable=False)
    description_fr: Mapped[str] = mapped_column(nullable=False)
    longdescription_fr: Mapped[str] = mapped_column(nullable=True)
    keywords_fr: Mapped[str] = mapped_column(nullable=True)
    conditions_fr: Mapped[str] = mapped_column(nullable=True)
    location_name: Mapped[str] = mapped_column(nullable=True)
    location_address: Mapped[str] = mapped_column(nullable=True)
    location_city: Mapped[str] = mapped_column(nullable=True)
    location_department: Mapped[str] = mapped_column(nullable=True)
    location_region: Mapped[str] = mapped_column(nullable=True)
    location_coordinates: Mapped[str] = mapped_column(nullable=True)
    age_min: Mapped[int] = mapped_column(nullable=True)
    age_max: Mapped[int] = mapped_column(nullable=True)
    accessibility: Mapped[str] = mapped_column(nullable=True)
    attendancemode: Mapped[int] = mapped_column(nullable=True)

    timings: Mapped[list["Timing"]] = relationship(back_populates="event")
    vectors: Mapped[list["Vector"]] = relationship(back_populates="event")