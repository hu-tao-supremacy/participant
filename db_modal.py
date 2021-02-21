from sqlalchemy import create_engine, Column, ForeignKey, Integer, String
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


Base.metadata.create_all(engine)

DBSession = sessionmaker(bind=engine)
session = DBSession()
