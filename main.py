from concurrent import futures
import logging
import os

import grpc
import hts.common.common_pb2 as common
import hts.participant.service_pb2 as participant_service
import hts.participant.service_pb2_grpc as participant_service_grpc

from db_model import Feedback, Event, EventDuration, UserEvent, session, Tag, EventTag, UserEventFeedback, FacilityRequest
from helper import getInt64Value, b64encode
from datetime import datetime
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.wrappers_pb2 import BoolValue
from sqlalchemy import func
import random


class ParticipantService(participant_service_grpc.ParticipantServiceServicer):

    def IsEventAvailable(self, request, context):
        event_id = request.event.id
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
        user_id = request.user.id
        event_id = request.event.id

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

        return common.Event(id=event.id, organization_id=event.organization_id, event_location_id=getInt64Value(event.event_location_id), description=event.description, name=event.name,
                            cover_image=event.cover_image, cover_image_hash=event.cover_image_hash, poster_image=event.poster_image, poster_image_hash=event.poster_image_hash, contact=event.contact)

    def CancelEvent(self, request, context):
        user_id = request.user.id
        event_id = request.event.id

        results = session.query(UserEvent).filter(
            UserEvent.user_id == user_id, UserEvent.event_id == event_id).scalar()

        if (results):
            event = session.query(Event).filter(Event.id == event_id).scalar()

            session.delete(results)
            session.commit()
            return common.Event(id=event.id, organization_id=event.organization_id, event_location_id=getInt64Value(event.event_location_id), description=event.description, name=event.name,
                                cover_image=event.cover_image, cover_image_hash=event.cover_image_hash, poster_image=event.poster_image, poster_image_hash=event.poster_image_hash, contact=event.contact)

        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details("User have not joined this event.")
        return proto_pb2.Response()

    def CreateFeedback(self, request, context):
        # TODO: - Only 1 user 1 feedback
        user_id = request.user.id
        feedback = request.feedback.feedback

        if feedback == "":
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("No feedback given.")
            return proto_pb2.Response()

        new_feedback = Feedback(
            event_id=request.feedback.event_id, feedback=feedback)
        session.add(new_feedback)
        session.commit()

        new_user_event_feedback = UserEventFeedback(
            user_id=user_id, event_feedback_id=new_feedback.id)
        session.add(new_user_event_feedback)
        session.commit()

        return common.EventFeedback(id=new_feedback.id, event_id=new_feedback.event_id, feedback=new_feedback.feedback)

    def RemoveFeedback(self, request, context):
        feedback_id = request.id
        feedback = session.query(Feedback).get(feedback_id)

        if (feedback):
            session.delete(feedback)
            session.commit()
            return common.EventFeedback(id=feedback.id, event_id=feedback.event_id, feedback=feedback.feedback)

        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details("Cannot find specify feedback.")
        return proto_pb2.Response()

    def GetFeedbacksFromEvent(self, request, context):
        event_id = request.id

        feedbacks = session.query(Feedback).filter(
            Feedback.event_id == event_id).all()

        data = map(lambda result: common.EventFeedback(
            id=result.id, event_id=result.event_id, feedback=result.feedback), feedbacks)

        return participant_service.GetFeedbacksFromEventResponse(event_feedback=data)

    def GetUserFeedbackFromEvent(self, request, context):
        user_id = request.user.id
        event_id = request.event.id

        user_event_feedbacks = session.query(UserEventFeedback).filter(
            UserEventFeedback.user_id == user_id).all()
        for user_event_feedback in user_event_feedbacks:
            feedback_id = user_event_feedback.event_feedback_id

            feedback = session.query(Feedback).filter(
                Feedback.id == feedback_id, Feedback.event_id == event_id).scalar()
            if feedback is not None:
                return common.EventFeedback(id=feedback.id, event_id=feedback.event_id, feedback=feedback.feedback)
        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details("Cannot find feedback.")
        return proto_pb2.Response()

    def GetEventsByStringOfName(self, request, context):
        text = request.text.lower()
        if(text == ""):
            return participant_service.EventsResponse(event=None)
        results = session.query(Event).filter(
            func.lower(Event.name).contains(text))

        events = map(lambda result: common.Event(id=result.id, organization_id=result.organization_id, event_location_id=None, description=result.description, name=result.name,
                                                 cover_image=result.cover_image, cover_image_hash=result.cover_image_hash, poster_image=result.poster_image, poster_image_hash=result.poster_image_hash, contact=result.contact), results)

        return participant_service.EventsResponse(event=events)

    def GetEventsByTag(self, request, context):
        tag_id = request.id
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
                tag_events.append(common.Event(id=event.id, organization_id=event.organization_id, event_location_id=None, description=event.description, name=event.name,
                                               cover_image=event.cover_image, cover_image_hash=event.cover_image_hash, poster_image=event.poster_image, poster_image_hash=event.poster_image_hash, contact=event.contact))

        if (tag_events):
            return participant_service.EventsResponse(event=tag_events)
        return participant_service.EventsResponse()

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
                date_events.append(common.Event(id=event.id, organization_id=event.organization_id, event_location_id=None, description=event.description, name=event.name,
                                                cover_image=event.cover_image, cover_image_hash=event.cover_image_hash, poster_image=event.poster_image, poster_image_hash=event.poster_image_hash, contact=event.contact))
        if (date_events):
            return participant_service.EventsResponse(event=date_events)
        return participant_service.EventsResponse()

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
                date_events.append(common.Event(id=event.id, organization_id=event.organization_id, event_location_id=None, description=event.description, name=event.name,
                                                cover_image=event.cover_image, cover_image_hash=event.cover_image_hash, poster_image=event.poster_image, poster_image_hash=event.poster_image_hash, contact=event.contact))
        if (date_events):
            return participant_service.EventsResponse(event=date_events)
        return participant_service.EventsResponse()

    def GetEventsByFacility(self, request, context):
        facility_id = request.id
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
                facility_events.append(common.Event(id=event.id, organization_id=event.organization_id, event_location_id=None, description=event.description, name=event.name,
                                                    cover_image=event.cover_image, cover_image_hash=event.cover_image_hash, poster_image=event.poster_image, poster_image_hash=event.poster_image_hash, contact=event.contact))

        if (facility_events):
            return participant_service.EventsResponse(event=facility_events)
        return participant_service.EventsResponse()

    def GetEventsByOrganization(self, request, context):
        organization_id = request.id

        results = session.query(Event).filter(
            Event.organization_id == organization_id).all()

        events = map(lambda result: common.Event(id=result.id, organization_id=result.organization_id, event_location_id=None, description=result.description, name=result.name,
                                                 cover_image=result.cover_image, cover_image_hash=result.cover_image_hash, poster_image=result.poster_image, poster_image_hash=result.poster_image_hash, contact=result.contact), results)

        return participant_service.EventsResponse(event=events)

    def GenerateQR(self, request, context):
        user_event = {"id": request.id, "user_id": request.user_id,
                      "event_id": request.event_id}
        string_user_event = b64encode(str(user_event))

        return participant_service.GenerateQRResponse(data=string_user_event)

    def GetEvent(self, request, context):
        event = session.query(Event).filter(
            Event.id == request.event_id).scalar()

        if (event is not None):
            data = common.Event(id=event.id, organization_id=event.organization_id, event_location_id=getInt64Value(event.event_location_id), description=event.description, name=event.name,
                                cover_image=event.cover_image, cover_image_hash=event.cover_image_hash, poster_image=event.poster_image, poster_image_hash=event.poster_image_hash, contact=event.contact)
            return data
        return common.Event()

    def GetSuggestedEvents(self, request, context):

        def getRandomNumber():
            return round(random.random() * 100)

        events = []

        for i in range(0, 10):
            event = session.query(Event).filter(
                Event.id == getRandomNumber()).scalar()
            if (event is not None):
                events.append(common.Event(id=event.id, organization_id=event.organization_id, event_location_id=getInt64Value(event.event_location_id), description=event.description, name=event.name,
                                           cover_image=event.cover_image, cover_image_hash=event.cover_image_hash, poster_image=event.poster_image, poster_image_hash=event.poster_image_hash, contact=event.contact))

        return participant_service.EventsResponse(event=events)

    def GetAllEvents(self, request, context):
        events = session.query(Event)

        data = map(lambda result: common.Event(id=result.id, organization_id=result.organization_id, event_location_id=getInt64Value(result.event_location_id), description=result.description, name=result.name,
                                               cover_image=result.cover_image, cover_image_hash=result.cover_image_hash, poster_image=result.poster_image, poster_image_hash=result.poster_image_hash, contact=result.contact), events)
        return participant_service.EventsResponse(event=data)

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
