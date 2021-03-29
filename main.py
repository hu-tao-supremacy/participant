from concurrent import futures
import logging
import os

import grpc
import hts.common.common_pb2 as common
import hts.participant.service_pb2 as participant_service
import hts.participant.service_pb2_grpc as participant_service_grpc

from db_model import Event, EventDuration, UserEvent, session, Tag, EventTag, FacilityRequest, Answer, Location, User
from db_model import session
from helper import getInt64Value, b64encode, getStringValue
from datetime import datetime
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.wrappers_pb2 import BoolValue
from sqlalchemy import func, or_
import random


class ParticipantService(participant_service_grpc.ParticipantServiceServicer):

    def IsEventAvailable(self, request, context):
        event_id = request.event_id
        date = request.date

        result = session.query(EventDuration).filter(
            EventDuration.event_id == event_id).order_by(EventDuration.start).first()

        if (result is None):
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Event not found")
            return proto_pb2.Response()

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

        result = session.query(UserEvent).filter(
            UserEvent.user_id == user_id, UserEvent.event_id == event_id)

        if (result.scalar()):
            context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            context.set_details("User already send request this event.")
            return proto_pb2.Response()

        new_user_event = UserEvent(
            user_id=user_id, event_id=event_id, rating=None, ticket=None, status="PENDING")
        session.add(new_user_event)
        session.commit()

        added_user_event = result.scalar()
        return common.UserEvent(id=added_user_event.id, user_id=added_user_event.user_id, event_id=added_user_event.event_id, rating=getInt64Value(added_user_event.rating), ticket=getStringValue(added_user_event.ticket), status=added_user_event.status)

    def CancelEvent(self, request, context):
        user_id = request.user_id
        event_id = request.event_id

        results = session.query(UserEvent).filter(
            UserEvent.user_id == user_id, UserEvent.event_id == event_id).scalar()

        if (results):
            event = session.query(Event).filter(Event.id == event_id).scalar()

            session.delete(results)
            session.commit()
            return common.Event(id=event.id, organization_id=event.organization_id, location_id=getInt64Value(event.location_id), description=event.description, name=event.name, cover_image_url=getStringValue(event.cover_image_url), cover_image_hash=getStringValue(event.cover_image_hash), poster_image_url=getStringValue(event.poster_image_url), poster_image_hash=getStringValue(event.poster_image_hash), profile_image_url=getStringValue(event.profile_image_url), profile_image_hash=getStringValue(event.profile_image_hash), attendee_limit=event.attendee_limit, contact=getStringValue(event.contact))

        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details("User have not joined this event.")
        return proto_pb2.Response()

    def SubmitAnswerForPostEventQuestion(self, request, context):
        answers = request.answers
        new_answers = []
        user_event_id = request.user_event_id

        user_event_answer = session.query(Answer).filter(
            Answer.user_event_id == user_event_id)
        for answer in answers:
            unique_answer = user_event_answer.filter(
                Answer.question_id == answer.question_id)
            if(unique_answer.first() is None):
                new_answers.append(answer)

        if (not new_answers):
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("User already gave feedback")
            return proto_pb2.Response()
        for answer in new_answers:
            question_id = answer.question_id
            question_answer = answer.value
            new_answer = Answer(user_event_id=user_event_id,
                                question_id=question_id, value=question_answer)
            session.add(new_answer)
            session.commit()

        data = map(lambda result: common.Answer(user_event_id=result.user_event_id,
                                                question_id=result.question_id, value=result.value), user_event_answer.all())
        return participant_service.SubmitAnswerForPostEventQuestionResponse(answers=data)

    def GetEventById(self, request, context):
        event = session.query(Event).filter(
            Event.id == request.event_id).scalar()

        if (event is not None):
            return common.Event(id=event.id, organization_id=event.organization_id, location_id=getInt64Value(event.location_id), description=event.description, name=event.name, cover_image_url=getStringValue(event.cover_image_url), cover_image_hash=getStringValue(event.cover_image_hash), poster_image_url=getStringValue(event.poster_image_url), poster_image_hash=getStringValue(event.poster_image_hash), profile_image_url=getStringValue(event.profile_image_url), profile_image_hash=getStringValue(event.profile_image_hash), attendee_limit=event.attendee_limit, contact=getStringValue(event.contact))
        return common.Event()

    def GetAllEvents(self, request, context):
        events = session.query(Event)

        data = map(lambda event: common.Event(id=event.id, organization_id=event.organization_id, location_id=getInt64Value(event.location_id), description=event.description, name=event.name, cover_image_url=getStringValue(event.cover_image_url), cover_image_hash=getStringValue(event.cover_image_hash), poster_image_url=getStringValue(
            event.poster_image_url), poster_image_hash=getStringValue(event.poster_image_hash), profile_image_url=getStringValue(event.profile_image_url), profile_image_hash=getStringValue(event.profile_image_hash), attendee_limit=event.attendee_limit, contact=getStringValue(event.contact)), events)
        return participant_service.EventsResponse(event=data)

    def GetSuggestedEvents(self, request, context):

        def getRandomNumber():
            return round(random.random() * 100)

        events = []

        for i in range(0, 10):
            event = session.query(Event).filter(
                Event.id == getRandomNumber()).scalar()
            if (event is not None):
                events.append(common.Event(id=event.id, organization_id=event.organization_id, location_id=getInt64Value(event.location_id), description=event.description, name=event.name, cover_image_url=getStringValue(event.cover_image_url), cover_image_hash=getStringValue(event.cover_image_hash), poster_image_url=getStringValue(
                    event.poster_image_url), poster_image_hash=getStringValue(event.poster_image_hash), profile_image_url=getStringValue(event.profile_image_url), profile_image_hash=getStringValue(event.profile_image_hash), attendee_limit=event.attendee_limit, contact=getStringValue(event.contact)))

        return participant_service.EventsResponse(event=events)

    def GetUpcomingEvents(self, request, context):
        start = request.start.seconds
        end = request.end.seconds
        text = [float(start), float(end)]
        if (text[0] == 0 or text[1] == 0):
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
                date_events.append(common.Event(id=event.id, organization_id=event.organization_id, location_id=getInt64Value(event.location_id), description=event.description, name=event.name, cover_image_url=getStringValue(event.cover_image_url), cover_image_hash=getStringValue(event.cover_image_hash), poster_image_url=getStringValue(
                    event.poster_image_url), poster_image_hash=getStringValue(event.poster_image_hash), profile_image_url=getStringValue(event.profile_image_url), profile_image_hash=getStringValue(event.profile_image_hash), attendee_limit=event.attendee_limit, contact=getStringValue(event.contact)))
        if (date_events):
            return participant_service.EventsResponse(event=date_events)
        return participant_service.EventsResponse()

    def GetEventsByStringOfName(self, request, context):
        text = request.text.lower()
        if(text == ""):
            return participant_service.EventsResponse(event=None)
        results = session.query(Event).filter(
            func.lower(Event.name).contains(text))

        events = map(lambda event: common.Event(id=event.id, organization_id=event.organization_id, location_id=getInt64Value(event.location_id), description=event.description, name=event.name, cover_image_url=getStringValue(event.cover_image_url), cover_image_hash=getStringValue(event.cover_image_hash), poster_image_url=getStringValue(
            event.poster_image_url), poster_image_hash=getStringValue(event.poster_image_hash), profile_image_url=getStringValue(event.profile_image_url), profile_image_hash=getStringValue(event.profile_image_hash), attendee_limit=event.attendee_limit, contact=getStringValue(event.contact)), results)

        return participant_service.EventsResponse(event=events)

    def GetEventsByTagId(self, request, context):
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
                tag_events.append(common.Event(id=event.id, organization_id=event.organization_id, location_id=getInt64Value(event.location_id), description=event.description, name=event.name, cover_image_url=getStringValue(event.cover_image_url), cover_image_hash=getStringValue(event.cover_image_hash), poster_image_url=getStringValue(
                    event.poster_image_url), poster_image_hash=getStringValue(event.poster_image_hash), profile_image_url=getStringValue(event.profile_image_url), profile_image_hash=getStringValue(event.profile_image_hash), attendee_limit=event.attendee_limit, contact=getStringValue(event.contact)))

        if (tag_events):
            return participant_service.EventsResponse(event=tag_events)
        return participant_service.EventsResponse()

    def GetEventsByFacilityId(self, request, context):
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
                facility_events.append(common.Event(id=event.id, organization_id=event.organization_id, location_id=getInt64Value(event.location_id), description=event.description, name=event.name, cover_image_url=getStringValue(event.cover_image_url), cover_image_hash=getStringValue(event.cover_image_hash), poster_image_url=getStringValue(
                    event.poster_image_url), poster_image_hash=getStringValue(event.poster_image_hash), profile_image_url=getStringValue(event.profile_image_url), profile_image_hash=getStringValue(event.profile_image_hash), attendee_limit=event.attendee_limit, contact=getStringValue(event.contact)))

        if (facility_events):
            return participant_service.EventsResponse(event=facility_events)
        return participant_service.EventsResponse()

    def GetEventsByOrganizationId(self, request, context):
        organization_id = request.id

        results = session.query(Event).filter(
            Event.organization_id == organization_id).all()

        events = map(lambda event: common.Event(id=event.id, organization_id=event.organization_id, location_id=getInt64Value(event.location_id), description=event.description, name=event.name, cover_image_url=getStringValue(event.cover_image_url), cover_image_hash=getStringValue(event.cover_image_hash), poster_image_url=getStringValue(
            event.poster_image_url), poster_image_hash=getStringValue(event.poster_image_hash), profile_image_url=getStringValue(event.profile_image_url), profile_image_hash=getStringValue(event.profile_image_hash), attendee_limit=event.attendee_limit, contact=getStringValue(event.contact)), results)

        return participant_service.EventsResponse(event=events)

    def GetEventsByDate(self, request, context):
        timestamp = request.seconds
        text = float(timestamp)
        if (text == 0):
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
                date_events.append(common.Event(id=event.id, organization_id=event.organization_id, location_id=getInt64Value(event.location_id), description=event.description, name=event.name, cover_image_url=getStringValue(event.cover_image_url), cover_image_hash=getStringValue(event.cover_image_hash), poster_image_url=getStringValue(
                    event.poster_image_url), poster_image_hash=getStringValue(event.poster_image_hash), profile_image_url=getStringValue(event.profile_image_url), profile_image_hash=getStringValue(event.profile_image_hash), attendee_limit=event.attendee_limit, contact=getStringValue(event.contact)))
        if (date_events):
            return participant_service.EventsResponse(event=date_events)
        return participant_service.EventsResponse()

    def GetLocationById(self, request, context):
        id = request.id

        location = session.query(Location).filter(Location.id == id).scalar()

        if(location):
            return common.Location(id=location.id, name=location.name, google_map_url=location.google_map_url, description=getStringValue(location.description), travel_information_image_url=getStringValue(location.travel_information_image_url), travel_information_image_hash=getStringValue(location.travel_information_image_hash))
        else:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("No location found with given location_id")
            return proto_pb2.Response()

    def GetTagsFromEventId(self, request, context):
        event_id = request.id
        tags_id = []
        tags_of_event = []

        tags = session.query(EventTag).filter(
            EventTag.event_id == event_id).all()
        for tag in tags:
            tags_id.append(tag.id)

        for tag_id in tags_id:
            tag = session.query(Tag).filter(Tag.id == tag_id).scalar()
            if (tag is not None):
                tags_of_event.append(common.Tag(id=tag.id, name=tag.name))
        if (tags_of_event):
            return participant_service.GetTagsFromEventIdResonse(tags=tags_of_event)
        return participant_service.GetTagsFromEventIdResonse()

    def GetRatingFromEventId(self, request, context):
        event_id = request.id
        ratings = []

        user_events_by_event_id = session.query(UserEvent).filter(
            UserEvent.event_id == event_id).all()

        if (user_events_by_event_id):
            for user_event in user_events_by_event_id:
                temp = user_event.rating
                if (temp is not None):
                    ratings.append(temp)
            return participant_service.GetRatingFromEventIdResponse(result=ratings)
        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details("No rating found for event")
        return proto_pb2.Response()

    def GetApprovedUserFromEventId(self, request, context):
        event_id = request.id
        users_id = []
        approved_user = []

        user_events_by_event_id = session.query(UserEvent).filter(
            UserEvent.event_id == event_id, UserEvent.status == "APPROVED").all()

        if (user_events_by_event_id):
            for user_event in user_events_by_event_id:
                user_id = user_event.user_id
                users_id.append(user_id)
            users = session.query(User).filter(
                or_(User.id == v for v in users_id)).all()
            if users:
                for user in users:
                    approved_user.append(common.User(id=user.id, first_name=user.first_name, last_name=user.last_name, email=user.email, nickname=getStringValue(user.nickname), chula_id=getStringValue(
                        user.chula_id), address=getStringValue(user.address), profile_picture_url=getStringValue(user.profile_picture_url), is_chula_student=user.is_chula_student, gender=user.gender))
                return participant_service.GetApprovedUserFromEventIdResponse(users=approved_user)
        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details("No approved user found for event")
        return proto_pb2.Response()

    def GenerateQR(self, request, context):
        result = session.query(UserEvent).filter(
            UserEvent.id == request.user_event_id)
        if (result.scalar()):
            user_event = {"use_event_id": request.user_event_id, "user_id": request.user_id,
                          "event_id": request.event_id}
            string_user_event = b64encode(str(user_event))
            return participant_service.GenerateQRResponse(data=string_user_event)
        else:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("UserEvent not found")
            return proto_pb2.Response()

    def Ping(self, request, context):
        boolvalue = BoolValue()
        boolvalue.value = True
        return boolvalue


session.close()

port = os.environ.get("GRPC_PORT")

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    participant_service_grpc.add_ParticipantServiceServicer_to_server(
        ParticipantService(), server)
    server.add_insecure_port('[::]:'+port)
    server.start()
    server.wait_for_termination()


serve()
