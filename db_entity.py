from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Event(Base):
    __tablename__ = 'event'
    id = Column(Integer, primary_key=True)


class Feedback(Base):
    __tablename__ = 'feedback'
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("event.id"))
    feedback = Column(String(250))
