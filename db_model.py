from sqlalchemy import (
    create_engine,
    Column,
    ForeignKey,
    Integer,
    String,
    TIMESTAMP,
    Boolean,
    Enum,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

Base = declarative_base()

user = os.environ.get("POSTGRES_USER")
password = os.environ.get("POSTGRES_PASSWORD")
host = os.environ.get("POSTGRES_HOST")
db = os.environ.get("POSTGRES_DB")

engine = create_engine("postgresql://" + user + ":" + password + "@" + host + "/" + db)


class Event(Base):
    __tablename__ = "event"

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organization.id"))
    location_id = Column(Integer, nullable=True)
    description = Column(String)
    name = Column(String)
    cover_image_url = Column(String, nullable=True)
    cover_image_hash = Column(String, nullable=True)
    poster_image_url = Column(String, nullable=True)
    poster_image_hash = Column(String, nullable=True)
    profile_image_url = Column(String, nullable=True)
    profile_image_hash = Column(String, nullable=True)
    attendee_limit = Column(Integer)
    contact = Column(String, nullable=True)


class EventDuration(Base):
    __tablename__ = "event_duration"

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("event.id"))
    start = Column(TIMESTAMP)
    finish = Column(TIMESTAMP)


class UserEvent(Base):
    __tablename__ = "user_event"

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    event_id = Column(Integer, ForeignKey("event.id"))
    rating = Column(Integer, nullable=True)
    ticket = Column(String, nullable=True)
    status = Column(
        Enum("PENDING", "APPROVED", "REJECTED", name="status_enum", create_type=False)
    )


class User(Base):
    __tablename__ = "user"

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    id = Column(Integer, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String)
    nickname = Column(String, nullable=True)
    chula_id = Column(String, nullable=True)
    is_chula_student = Column(Boolean)
    gender = Column(Enum("M", "F", "NS", name="gender_enum", create_type=False))
    address = Column(String, nullable=True)
    profile_picture_url = Column(String, nullable=True)
    did_setup = Column(Boolean)
    district = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    province = Column(String, nullable=True)
    academic_year = Column(Integer, nullable=True)


class Tag(Base):
    __tablename__ = "tag"

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    id = Column(Integer, primary_key=True)
    name = Column(String)


class EventTag(Base):
    __tablename__ = "event_tag"

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("event.id"))
    tag_id = Column(Integer, ForeignKey("tag.id"))


class Facility(Base):
    __tablename__ = "facility"

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    id = Column(Integer, primary_key=True)
    name = Column(String)


class FacilityRequest(Base):
    __tablename__ = "facility_request"

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("event.id"))
    facility_id = Column(Integer, ForeignKey("facility.id"))


class Answer(Base):
    __tablename__ = "answer"

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    id = Column(Integer, primary_key=True)
    user_event_id = Column(Integer, ForeignKey("user_event.id"))
    question_id = Column(Integer, ForeignKey("question.id"))
    value = Column(String)


class Question(Base):
    __tablename__ = "question"

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    id = Column(Integer, primary_key=True)
    question_group_id = Column(Integer, ForeignKey("question_group.id"))
    seq = Column(Integer)
    answer_type = Column(
        Enum("SCALE", "TEXT", name="answer_type_enum", create_type=False)
    )
    is_optional = Column(Boolean)
    title = Column(String)
    subtitle = Column(String)


class Location(Base):
    __tablename__ = "location"

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    id = Column(Integer, primary_key=True)
    name = Column(String)
    google_map_url = Column(String)
    description = Column(String, nullable=True)
    travel_information_image_url = Column(String, nullable=True)
    travel_information_image_hash = Column(String, nullable=True)


class QuestionGroup(Base):
    __tablename__ = "question_group"

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("event.id"))
    type = Column(
        Enum(
            "PRE_EVENT",
            "POST_EVENT",
            name="question_group_type_enum",
            create_type=False,
        )
    )
    seq = Column(Integer)
    title = Column(String)


Base.metadata.create_all(engine)

DBSession = sessionmaker(bind=engine)
