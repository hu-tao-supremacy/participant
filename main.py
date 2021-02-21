from concurrent import futures
import logging

import grpc
import hts.common.common_pb2 as common
import hts.participant.service_pb2 as participant_service
from sqlalchemy.ext.declarative import declarative_base
import hts.participant.service_pb2_grpc as participant_service_grpc

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import db_entity as t

engine = create_engine('postgresql://hu-tao-mains:hu-tao-mains@localhost/hts')
base = declarative_base()
DBSession = sessionmaker(bind=engine)
session = DBSession()
base.metadata.create_all(engine)


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
        new_feedback = t.Feedback(
            id=request.feedback.id, event_id=request.feedback.event_id, feedback=feedback)
        session.add(new_feedback)
        session.commit()
        return common.Result(is_ok=True, description="The feedback is recieved")

    def RemoveFeedback(self, request, context):
        feedback_id = request.feedback.id
        feedback = session.query(t.Feedback).get(feedback_id)
        if (feedback):
            session.delete(feedback)
            session.commit()
            return common.Result(is_ok=True, description="The feedback is deleted")
        return common.Result(is_ok=False, description="No feedback found")

    def SearchEventsByName(self, request, context):
        return

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
