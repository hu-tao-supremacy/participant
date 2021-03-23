from sqlalchemy import create_engine, Column, ForeignKey, Integer, String, TIMESTAMP, Boolean, Enum, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

Base = declarative_base()

user = os.environ.get("POSTGRES_USER")
password = os.environ.get("POSTGRES_PASSWORD")
host = os.environ.get("POSTGRES_HOST")
db = os.environ.get("POSTGRES_DB")

engine = create_engine('postgresql://'+user+':'+password+'@'+host+'/'+db)


class Event(Base):
    __tablename__ = 'event'
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organization.id"))
    event_location_id = Column(BigInteger, ForeignKey(
        "event_location.id"), nullable=True)
    description = Column(String)
    name = Column(String)
    cover_image_url = Column(String, nullable=True)
    cover_image_hash = Column(String, nullable=True)
    poster_image_url = Column(String, nullable=True)
    poster_image_hash = Column(String, nullable=True)
    contact = Column(String)
    profile_image_url = Column(String, nullable=True)
    profile_image_hash = Column(String, nullable=True)
    attendee_limit = Column(Integer)

class Feedback(Base):
    __tablename__ = 'event_feedback'
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("event.id"))
    feedback = Column(String)


class EventDuration(Base):
    __tablename__ = 'event_duration'
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('event.id'))
    start = Column(TIMESTAMP)
    end = Column(TIMESTAMP)


class UserEvent(Base):
    __tablename__ = 'user_event'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    event_id = Column(Integer, ForeignKey("event.id"))


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String)
    nickname = Column(String, nullable=True)
    chula_id = Column(String, nullable=True)
    is_chula_student = Column(Boolean)
    gender = Column(
        Enum("M", "F", "NS", name="gender_enum", create_type=False))


class Tag(Base):
    __tablename__ = "tag"
    id = Column(Integer, primary_key=True)
    name = Column(String)


class EventTag(Base):
    __tablename__ = "event_tag"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('event.id'))
    tag_id = Column(Integer, ForeignKey('tag.id'))


class UserEventFeedback(Base):
    __tablename__ = "user_event_feedback"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    event_feedback_id = Column(Integer, ForeignKey('event_feedback.id'))


class Facility(Base):
    __tablename__ = "facility"
    id = Column(Integer, primary_key=True)
    name = Column(String)


class FacilityRequest(Base):
    __tablename__ = "facility_request"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('event.id'))
    facility_id = Column(Integer, ForeignKey('facility.id'))

class Answer(Base):
    __tablename__ = "answer"
    id = Column(Integer, primary_key=True)
    user_event_id = Column(Integer, ForeignKey('user_event.id'))
    question_id = Column(Integer, ForeignKey('question.id'))
    value = Column(String)

class Question(Base):
    __tablename__ = "question"
    id = Column(Integer, primary_key=True)

Base.metadata.create_all(engine)

DBSession = sessionmaker(bind=engine)
session = DBSession()
