from concurrent import futures
import logging

import grpc
import hts.common.common_pb2 as common
import hts.participant.service_pb2 as participant_service
import hts.participant.service_pb2_grpc as participant_service_grpc

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import db_entity as t

engine = create_engine('sqlite:///main.db')
DBSession = sessionmaker(bind=engine)
session = DBSession()


class ParticipantService(participant_service_grpc.ParticipantServiceServicer):

    def IsEventAvailable(self, request, context):
        return

    def JoinEvent(self, request, context):
        return

    def CancelEvent(self, request, context):
        return

    def CreateFeedback(self, request, context):
        return

    def RemoveFeedback(self, request, context):
        return

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
