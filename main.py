from concurrent import futures
import logging

import grpc
import hts.common.common_pb2 as common
import hts.participant.service_pb2 as participant_service
import hts.participant.service_pb2_grpc as participant_service_grpc

from db_modal import Feedback, Event, session


class ParticipantService(participant_service_grpc.ParticipantServiceServicer):

    def IsEventAvailable(self, request, context):
        return

    def JoinEvent(self, request, context):
        return

    def CancelEvent(self, request, context):
        return

    def CreateFeedback(self, request, context):
        feedback = request.feedback.feedback
        if feedback == "":
            return common.Result(is_ok=False, description="The feedback is empty")
        new_feedback = Feedback(
            id=request.feedback.id, event_id=request.feedback.event_id, feedback=feedback)
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
        if(text == ""):
            return common.Result(is_ok=False, description="Empty String")
        results = session.query(Event).filter(Event.name.contains(text))

        # TODO: - Change to real data
        data = map(lambda result: common.Event(id=result.id, organization_id=1, event_location_id=None, description="a", name=result.name,
                                               cover_image=None, cover_image_hash=None, poster_image=None, poster_image_hash=None, contact="231"), results)

        return participant_service.SearchEventsByNameRespond(events=data)

    def GenerateQR(self, request, context):
        return


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    participant_service_grpc.add_ParticipantServiceServicer_to_server(
        ParticipantService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()


serve()
