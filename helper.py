from google.protobuf import wrappers_pb2 as wrapper
from google.protobuf.timestamp_pb2 import Timestamp
import base64
import random
import grpc
from db_model import Event
import hts.common.common_pb2 as common
from sqlalchemy.orm import class_mapper


def getInt32Value(value):
    if value is None:
        return None
    temp = wrapper.Int32Value()
    temp.value = value
    return temp


def getTimeStamp(data):
    if data is None:
        return None
    timestamp = Timestamp()
    timestamp.FromDatetime(data)
    return timestamp


def b64encode(data):
    encodedBytes = base64.b64encode(data.encode("utf-8"))
    return str(encodedBytes, "utf-8")


def getStringValue(value):
    if value is None:
        return None
    temp = wrapper.StringValue()
    temp.value = value
    return temp


def getRandomNumber():
    return round(random.random() * 100)


def throwError(details: str, statusCode: grpc.StatusCode, context):
    context.set_code(statusCode)
    context.set_details(details)
    return proto_pb2.Response()


def getEventsByIds(events_id: [str], session):
    events = []

    query_events = session.query(Event).filter(Event.id.in_(events_id)).all()
    if query_events is not None:
        events = map(
            lambda event: common.Event(
                id=event.id,
                organization_id=event.organization_id,
                location_id=getInt32Value(event.location_id),
                description=event.description,
                name=event.name,
                cover_image_url=getStringValue(event.cover_image_url),
                cover_image_hash=getStringValue(event.cover_image_hash),
                poster_image_url=getStringValue(event.poster_image_url),
                poster_image_hash=getStringValue(event.poster_image_hash),
                profile_image_url=getStringValue(event.profile_image_url),
                profile_image_hash=getStringValue(event.profile_image_hash),
                attendee_limit=event.attendee_limit,
                contact=getStringValue(event.contact),
            ),
            query_events,
        )

    return events