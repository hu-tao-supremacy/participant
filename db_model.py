from sqlalchemy import create_engine, Column, ForeignKey, Integer, String, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
engine = create_engine('postgresql://hu-tao-mains:hu-tao-mains@localhost/hts')


class Event(Base):
    __tablename__ = 'event'
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organization.id"))
    event_location_id = Column(Integer, ForeignKey(
        "event_location.id"), nullable=True)
    description = Column(String)
    name = Column(String)
    cover_image = Column(String, nullable=True)
    cover_image_hash = Column(String, nullable=True)
    poster_image = Column(String, nullable=True)
    poster_image_hash = Column(String, nullable=True)
    contact = Column(String)


class Feedback(Base):
    __tablename__ = 'feedback'
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("event.id"))
    feedback = Column(String)


class EventDuration(Base):
    __tablename__ = 'event_duration'
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer)
    start = Column(TIMESTAMP)
    end = Column(TIMESTAMP)


Base.metadata.create_all(engine)

DBSession = sessionmaker(bind=engine)
session = DBSession()
