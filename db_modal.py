from sqlalchemy import create_engine, Column, ForeignKey, Integer, String, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
engine = create_engine('postgresql://hu-tao-mains:hu-tao-mains@localhost/hts')


class Event(Base):
    __tablename__ = 'event'
    id = Column(Integer, primary_key=True)
    name = Column(String)


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
