from concurrent import futures
import logging
import os

import grpc
import hts.common.common_pb2 as common
import hts.participant.service_pb2 as participant_service
import hts.participant.service_pb2_grpc as participant_service_grpc

from db_model import Feedback, Event, EventDuration, UserEvent, session
import datetime


class ParticipantService(participant_service_grpc.ParticipantServiceServicer):

    def IsEventAvailable(self, request, context):
        event_id = request.event.id
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

    def RemoveFeedback(self, request, context):
        feedback_id = request.feedback.id
        feedback = session.query(Feedback).get(feedback_id)
        if (feedback):
            session.delete(feedback)
            session.commit()
            return common.Result(is_ok=True, description="The feedback is deleted")
        return common.Result(is_ok=False, description="No feedback found")

    def SearchEventsByName(self, request, context):
        text = request.name
        print(text)
        if(text == ""):
            print("asdf")
            return participant_service.SearchEventsByNameRespond(events=None)
        results = session.query(Event).filter(Event.name.contains(text))

        data = map(lambda result: common.Event(id=result.id, organization_id=result.organization_id, event_location_id=result.event_location_id, description=result.description, name=result.name,
                                               cover_image=result.cover_image, cover_image_hash=result.cover_image_hash, poster_image=result.poster_image, poster_image_hash=result.poster_image_hash, contact=result.contact), results)

        return participant_service.SearchEventsByNameRespond(events=data)

    def GenerateQR(self, request, context):
        param = request.user_event
        user_event = {"id": param.id, "user_id": param.user_id,
                      "event_id": param.event_id}
        string_user_event = str(user_event)

        return participant_service.GenerateQRRespond(data=string_user_event)


port = os.environ.get("GRPC_PORT")


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    participant_service_grpc.add_ParticipantServiceServicer_to_server(
        ParticipantService(), server)
    server.add_insecure_port('[::]:'+port)
    server.start()
    server.wait_for_termination()


serve()
