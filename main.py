from concurrent import futures
import logging
import os

import grpc
import hts.common.common_pb2 as common
import hts.participant.service_pb2 as participant_service
import hts.participant.service_pb2_grpc as participant_service_grpc

from db_model import Feedback, Event, EventDuration, UserEvent, session, Tag, EventTag, UserEventFeedback, FacilityRequest, Answer
from helper import getInt64Value, b64encode
from datetime import datetime
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.wrappers_pb2 import BoolValue
from sqlalchemy import func
import random


class ParticipantService(participant_service_grpc.ParticipantServiceServicer):

    def IsEventAvailable(self, request, context):
        event_id = request.event_id
        date = request.date

        result = session.query(EventDuration).filter(
            EventDuration.event_id == event_id).order_by(EventDuration.start).first()

        timestamp = Timestamp()
        timestamp.FromDatetime(result.start)
        boolvalue = BoolValue()

        if (timestamp.seconds > date.seconds):
            boolvalue.value = True
            return boolvalue

        boolvalue.value = False
        return boolvalue

    def JoinEvent(self, request, context):
        user_id = request.user_id
        event_id = request.event_id

        results = session.query(UserEvent).filter(
            UserEvent.user_id == user_id, UserEvent.event_id == event_id)

        if (results.scalar()):
            context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            context.set_details("User already joined this event.")
            return proto_pb2.Response()

        new_user_event = UserEvent(user_id=user_id, event_id=event_id)
        session.add(new_user_event)
        session.commit()
        event = session.query(Event).filter(Event.id == event_id).scalar()
        return common.Event(id=event.id, organization_id=event.organization_id, event_location_id=getInt64Value(event.event_location_id), description=event.description, name=event.name, cover_image_url=event.cover_image_url, cover_image_hash=event.cover_image_hash, poster_image_url=event.poster_image_url, poster_image_hash=event.poster_image_hash, contact=event.contact, profile_image_url=event.profile_image_url, profile_image_hash=event.profile_image_hash, attendee_limit=event.attendee_limit)

    def CancelEvent(self, request, context):
        user_id = request.user_id
        event_id = request.event_id

        results = session.query(UserEvent).filter(
            UserEvent.user_id == user_id, UserEvent.event_id == event_id).scalar()

        if (results):
            event = session.query(Event).filter(Event.id == event_id).scalar()

            session.delete(results)
            session.commit()
            return common.Event(id=event.id, organization_id=event.organization_id, event_location_id=getInt64Value(event.event_location_id), description=event.description, name=event.name, cover_image_url=event.cover_image_url, cover_image_hash=event.cover_image_hash, poster_image_url=event.poster_image_url, poster_image_hash=event.poster_image_hash, contact=event.contact, profile_image_url=event.profile_image_url, profile_image_hash=event.profile_image_hash, attendee_limit=event.attendee_limit)

        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details("User have not joined this event.")
        return proto_pb2.Response()

    def SubmitAnswerForPostEventQuestion(self, request, context):
        answers = request.answers
        user_event_id = request.user_event_id

        try:
            for answer in answers:
                question_id = answer.question_id
                question_answer = answer.value
                new_answer = Answer(user_event_id=user_event_id, question_id=question_id, value=question_answer)
                session.add(new_answer)
                session.commit()
        except:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("User already gave feedback")
            return proto_pb2.Response()
        

        results = session.query(Answer).filter(Answer.user_event_id == user_event_id).all()
        data = map(lambda result: common.Answer(user_event_id=result.user_event_id, question_id=result.question_id, value=result.value), results)
        return participant_service.SubmitAnswerForPostEventQuestionResponse(answers=data)

    def GetEventById(self, request, context):
        event = session.query(Event).filter(
            Event.id == request.event_id).scalar()

        if (event is not None):
            return common.Event(id=event.id, organization_id=event.organization_id, event_location_id=getInt64Value(event.event_location_id), description=event.description, name=event.name, cover_image_url=event.cover_image_url, cover_image_hash=event.cover_image_hash, poster_image_url=event.poster_image_url, poster_image_hash=event.poster_image_hash, contact=event.contact, profile_image_url=event.profile_image_url, profile_image_hash=event.profile_image_hash, attendee_limit=event.attendee_limit)
        return common.Event()

    def GetAllEvents(self, request, context):
        events = session.query(Event)

        data = map(lambda event: common.Event(id=event.id, organization_id=event.organization_id, event_location_id=getInt64Value(event.event_location_id), description=event.description, name=event.name, cover_image_url=event.cover_image_url, cover_image_hash=event.cover_image_hash,
                                              poster_image_url=event.poster_image_url, poster_image_hash=event.poster_image_hash, contact=event.contact, profile_image_url=event.profile_image_url, profile_image_hash=event.profile_image_hash, attendee_limit=event.attendee_limit), events)
        return participant_service.EventsResponse(event=data)

    def GetSuggestedEvents(self, request, context):

        def getRandomNumber():
            return round(random.random() * 100)

        events = []

        for i in range(0, 10):
            event = session.query(Event).filter(
                Event.id == getRandomNumber()).scalar()
            if (event is not None):
                events.append(common.Event(id=event.id, organization_id=event.organization_id, event_location_id=getInt64Value(event.event_location_id), description=event.description, name=event.name, cover_image_url=event.cover_image_url, cover_image_hash=event.cover_image_hash,
                                           poster_image_url=event.poster_image_url, poster_image_hash=event.poster_image_hash, contact=event.contact, profile_image_url=event.profile_image_url, profile_image_hash=event.profile_image_hash, attendee_limit=event.attendee_limit))

        return participant_service.EventsResponse(event=events)

    def GetUpcomingEvents(self, request, context):
        start = request.start.seconds
        end = request.end.seconds

        try:
            text = [float(start), float(end)]
        except:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Wrong timestamp format.")
            return proto_pb2.Response()

        start_date = datetime.fromtimestamp(text[0])
        end_date = datetime.fromtimestamp(text[1])

        event_durations = session.query(EventDuration).filter(
            EventDuration.start >= start_date, EventDuration.start < end_date).all()

        events_id = []
        date_events = []

        for event_duration in event_durations:
            events_id.append(event_duration.event_id)
        for event_id in events_id:
            event = session.query(Event).filter(
                Event.id == event_id).scalar()
            if (event is not None):
                date_events.append(common.Event(id=event.id, organization_id=event.organization_id, event_location_id=getInt64Value(event.event_location_id), description=event.description, name=event.name, cover_image_url=event.cover_image_url, cover_image_hash=event.cover_image_hash,
                                                poster_image_url=event.poster_image_url, poster_image_hash=event.poster_image_hash, contact=event.contact, profile_image_url=event.profile_image_url, profile_image_hash=event.profile_image_hash, attendee_limit=event.attendee_limit))
        if (date_events):
            return participant_service.EventsResponse(event=date_events)
        return participant_service.EventsResponse()

    def GetEventsByStringOfName(self, request, context):
        text = request.text.lower()
        if(text == ""):
            return participant_service.EventsResponse(event=None)
        results = session.query(Event).filter(
            func.lower(Event.name).contains(text))

        events = map(lambda event: common.Event(id=event.id, organization_id=event.organization_id, event_location_id=getInt64Value(event.event_location_id), description=event.description, name=event.name, cover_image_url=event.cover_image_url, cover_image_hash=event.cover_image_hash,
                                                poster_image_url=event.poster_image_url, poster_image_hash=event.poster_image_hash, contact=event.contact, profile_image_url=event.profile_image_url, profile_image_hash=event.profile_image_hash, attendee_limit=event.attendee_limit), results)

        return participant_service.EventsResponse(event=events)

    def GetEventsByTagId(self, request, context):
        tag_id = request.tag_id
        events_id = []
        tag_events = []

        events = session.query(EventTag).filter(
            EventTag.tag_id == tag_id).all()

        for event in events:
            events_id.append(event.id)

        for event_id in events_id:
            event = session.query(Event).filter(
                Event.id == event_id).scalar()
            if (event is not None):
                tag_events.append(common.Event(id=event.id, organization_id=event.organization_id, event_location_id=getInt64Value(event.event_location_id), description=event.description, name=event.name, cover_image_url=event.cover_image_url, cover_image_hash=event.cover_image_hash,
                                               poster_image_url=event.poster_image_url, poster_image_hash=event.poster_image_hash, contact=event.contact, profile_image_url=event.profile_image_url, profile_image_hash=event.profile_image_hash, attendee_limit=event.attendee_limit))

        if (tag_events):
            return participant_service.EventsResponse(event=tag_events)
        return participant_service.EventsResponse()

    def GetEventsByFacilityId(self, request, context):
        facility_id = request.facility_id
        events_id = []
        facility_events = []

        facility_requests = session.query(FacilityRequest).filter(
            FacilityRequest.facility_id == facility_id).all()

        for facility_request in facility_requests:
            events_id.append(facility_request.event_id)

        for event_id in events_id:
            event = session.query(Event).filter(
                Event.id == event_id).scalar()
            if (event is not None):
                facility_events.append(common.Event(id=event.id, organization_id=event.organization_id, event_location_id=getInt64Value(event.event_location_id), description=event.description, name=event.name, cover_image_url=event.cover_image_url, cover_image_hash=event.cover_image_hash,
                                                    poster_image_url=event.poster_image_url, poster_image_hash=event.poster_image_hash, contact=event.contact, profile_image_url=event.profile_image_url, profile_image_hash=event.profile_image_hash, attendee_limit=event.attendee_limit))

        if (facility_events):
            return participant_service.EventsResponse(event=facility_events)
        return participant_service.EventsResponse()

    def GetEventsByOrganizationId(self, request, context):
        organization_id = request.organization_id

        results = session.query(Event).filter(
            Event.organization_id == organization_id).all()

        events = map(lambda event: common.Event(id=event.id, organization_id=event.organization_id, event_location_id=getInt64Value(event.event_location_id), description=event.description, name=event.name, cover_image_url=event.cover_image_url, cover_image_hash=event.cover_image_hash,
                                                poster_image_url=event.poster_image_url, poster_image_hash=event.poster_image_hash, contact=event.contact, profile_image_url=event.profile_image_url, profile_image_hash=event.profile_image_hash, attendee_limit=event.attendee_limit), results)

        return participant_service.EventsResponse(event=events)

    def GetEventsByDate(self, request, context):
        timestamp = request.seconds
        try:
            text = float(timestamp)
        except:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Wrong timestamp format.")
            return proto_pb2.Response()

        date = datetime.fromtimestamp(text)
        start_date = datetime(date.year, date.month, date.day, 0, 0, 0)
        end_date = datetime(date.year, date.month, date.day + 1, 0, 0, 0)

        event_durations = session.query(EventDuration).filter(
            EventDuration.start >= start_date, EventDuration.start < end_date).all()

        events_id = []
        date_events = []

        for event_duration in event_durations:
            events_id.append(event_duration.event_id)
        for event_id in events_id:
            event = session.query(Event).filter(
                Event.id == event_id).scalar()
            if (event is not None):
                date_events.append(common.Event(id=event.id, organization_id=event.organization_id, event_location_id=getInt64Value(event.event_location_id), description=event.description, name=event.name, cover_image_url=event.cover_image_url, cover_image_hash=event.cover_image_hash,
                                                poster_image_url=event.poster_image_url, poster_image_hash=event.poster_image_hash, contact=event.contact, profile_image_url=event.profile_image_url, profile_image_hash=event.profile_image_hash, attendee_limit=event.attendee_limit))
        if (date_events):
            return participant_service.EventsResponse(event=date_events)
        return participant_service.EventsResponse()

    def GenerateQR(self, request, context):
        user_event = {"use_event_id": request.user_event_id, "user_id": request.user_id,
                      "event_id": request.event_id}
        string_user_event = b64encode(str(user_event))
        return participant_service.GenerateQRResponse(data=string_user_event)

    def Ping(self, request, context):
        boolvalue = BoolValue()
        boolvalue.value = True
        return boolvalue


port = os.environ.get("GRPC_PORT")


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    participant_service_grpc.add_ParticipantServiceServicer_to_server(
        ParticipantService(), server)
    server.add_insecure_port('[::]:'+port)
    server.start()
    server.wait_for_termination()


serve()
