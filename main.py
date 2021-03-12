from concurrent import futures
import logging
import os

import grpc
import hts.common.common_pb2 as common
import hts.participant.service_pb2 as participant_service
import hts.participant.service_pb2_grpc as participant_service_grpc

from db_model import Feedback, Event, EventDuration, UserEvent, session, Tag, EventTag
import datetime
import random
from google.protobuf import wrappers_pb2 as wrapper


class ParticipantService(participant_service_grpc.ParticipantServiceServicer):

    def IsEventAvailable(self, request, context):
        event_id = request.id
        now = datetime.datetime.now()

        result = session.query(EventDuration).filter(
            EventDuration.id == event_id).scalar()

        if(result.start > now):
            return common.Result(is_ok=True, description="The event haven't start yet")
        return common.Result(is_ok=False, description="The event has already started")

    def JoinEvent(self, request, context):
        user_id = request.user.id
        event_id = request.event.id

        results = session.query(UserEvent).filter(
            UserEvent.user_id == user_id, UserEvent.event_id == event_id)

        if (results.scalar()):
            return common.Result(is_ok=False, description="User has already joined")

        new_user_event = UserEvent(user_id=user_id, event_id=event_id)
        session.add(new_user_event)
        session.commit()
        return common.Result(is_ok=True, description="User successfully join the event")

    def CancelEvent(self, request, context):
        user_id = request.user.id
        event_id = request.event.id

        results = session.query(UserEvent).filter(
            UserEvent.user_id == user_id, UserEvent.event_id == event_id).scalar()

        if (results):
            session.delete(results)
            session.commit()
            return common.Result(is_ok=True, description="Successfully cancel")

        return common.Result(is_ok=False, description="Cannot find event to cancel")

    def CreateFeedback(self, request, context):
        feedback = request.feedback.feedback
        if feedback == "":
            return common.Result(is_ok=False, description="The feedback is empty")
        new_feedback = Feedback(
            event_id=request.feedback.event_id, feedback=feedback)
        session.add(new_feedback)
        session.commit()
        return common.Result(is_ok=True, description="The feedback is recieved")

    def HasSubmitFeedback(self, request, context):
        return

    def RemoveFeedback(self, request, context):
        feedback_id = request.id
        feedback = session.query(Feedback).get(feedback_id)
        if (feedback):
            session.delete(feedback)
            session.commit()
            return common.Result(is_ok=True, description="The feedback is deleted")
        return common.Result(is_ok=False, description="No feedback found")

    def GetFeedbackFromEvent(self, request, context):
        return

    def GetUserFeedbackFromEvent(self, request, context):
        return

    def SearchEventsByName(self, request, context):
        text = request.text
        if(text == ""):
            return participant_service.EventsResponse(event=None)
        results = session.query(Event).filter(Event.name.contains(text))

        events = map(lambda result: common.Event(id=result.id, organization_id=result.organization_id, event_location_id=None, description=result.description, name=result.name,
                                                 cover_image=result.cover_image, cover_image_hash=result.cover_image_hash, poster_image=result.poster_image, poster_image_hash=result.poster_image_hash, contact=result.contact), results)

        return participant_service.EventsResponse(event=events)

    def SearchEventsByTag(self, request, context):
        text = request.text
        result = session.query(Tag).filter(Tag.name.ilike(text)).scalar()
        if (result is None):
            return participant_service.EventsResponse()
        tag_id = result.id

        events_id = []
        tag_events = []

        if (result is not None):
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

    def GenerateQR(self, request, context):
        user_event = {"id": request.id, "user_id": request.user_id,
                      "event_id": request.event_id}
        string_user_event = str(user_event)

        return participant_service.GenerateQRResponse(data=string_user_event)

    def GetEvent(self, request, context):
        event = session.query(Event).filter(
            Event.id == request.event_id).scalar()
        if (event is not None):
            data = common.Event(id=event.id, organization_id=event.organization_id, event_location_id=None, description=event.description, name=event.name,
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
                events.append(common.Event(id=event.id, organization_id=event.organization_id, event_location_id=None, description=event.description, name=event.name,
                                           cover_image=event.cover_image, cover_image_hash=event.cover_image_hash, poster_image=event.poster_image, poster_image_hash=event.poster_image_hash, contact=event.contact))

        return participant_service.EventsResponse(event=events)

    def GetAllEvents(self, request, context):
        events = session.query(Event)

        def getInt64Value(value):
            temp = wrapper.Int64Value()
            temp.value = value
            return temp

        data = map(lambda result: common.Event(id=result.id, organization_id=result.organization_id, event_location_id=getInt64Value(result.event_location_id), description=result.description, name=result.name,
                                               cover_image=result.cover_image, cover_image_hash=result.cover_image_hash, poster_image=result.poster_image, poster_image_hash=result.poster_image_hash, contact=result.contact), events)
        return participant_service.EventsResponse(event=data)


port = os.environ.get("GRPC_PORT")


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    participant_service_grpc.add_ParticipantServiceServicer_to_server(
        ParticipantService(), server)
    server.add_insecure_port('[::]:'+port)
    server.start()
    server.wait_for_termination()


serve()
