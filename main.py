from concurrent import futures
import logging
import os

import grpc
import hts.common.common_pb2 as common
import hts.participant.service_pb2 as participant_service
import hts.participant.service_pb2_grpc as participant_service_grpc

from db_model import (
    Event,
    EventDuration,
    UserEvent,
    DBSession,
    Tag,
    EventTag,
    FacilityRequest,
    Answer,
    Location,
    User,
    QuestionGroup,
    Question,
)
from helper import (
    getInt32Value,
    b64encode,
    getStringValue,
    getRandomNumber,
    throwError,
    getEventsByIds,
)
from datetime import datetime
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.wrappers_pb2 import BoolValue
from sqlalchemy import func, or_


class ParticipantService(participant_service_grpc.ParticipantServiceServicer):
    def IsEventAvailable(self, request, context):
        session = DBSession()
        try:
            event_id = request.event_id
            date = request.date

            query_event_duration = (
                session.query(EventDuration)
                .filter(EventDuration.event_id == event_id)
                .order_by(EventDuration.start)
                .first()
            )

            if query_event_duration is None:
                throwError("Event not found.", grpc.StatusCode.NOT_FOUND, context)

            timestamp = Timestamp()
            timestamp.FromDatetime(query_event_duration.start)
            boolvalue = BoolValue()

            if timestamp.seconds > date.seconds:
                boolvalue.value = True
                return boolvalue

            boolvalue.value = False
            return boolvalue
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def JoinEvent(self, request, context):
        session = DBSession()
        try:
            user_id = request.user_id
            event_id = request.event_id

            query_user_event = session.query(UserEvent).filter(
                UserEvent.user_id == user_id, UserEvent.event_id == event_id
            )

            if query_user_event.scalar():
                throwError(
                    "User already send request to this event.",
                    grpc.StatusCode.ALREADY_EXISTS,
                    context,
                )

            new_user_event = UserEvent(
                user_id=user_id,
                event_id=event_id,
                rating=None,
                ticket=None,
                status="PENDING",
                is_internal=False
            )
            session.add(new_user_event)
            session.commit()

            added_user_event = query_user_event.scalar()

            if added_user_event:
                return common.UserEvent(
                    id=added_user_event.id,
                    user_id=added_user_event.user_id,
                    event_id=added_user_event.event_id,
                    rating=getInt32Value(added_user_event.rating),
                    ticket=getStringValue(added_user_event.ticket),
                    status=added_user_event.status,
                    is_internal=added_user_event.is_internal,
                )
            throwError(
                "Database didn't update User Event.", grpc.StatusCode.INTERNAL, context
            )
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def CancelEvent(self, request, context):
        session = DBSession()
        try:
            user_id = request.user_id
            event_id = request.event_id

            query_user_event = (
                session.query(UserEvent)
                .filter(UserEvent.user_id == user_id, UserEvent.event_id == event_id)
                .scalar()
            )

            if query_user_event:
                event = session.query(Event).filter(Event.id == event_id).scalar()

                session.delete(query_user_event)
                session.commit()

                return common.Event(
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
                )

            throwError(
                "User have not yet request to join this event.",
                grpc.StatusCode.NOT_FOUND,
                context,
            )
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def SubmitAnswersForEventQuestion(self, request, context):
        session = DBSession()
        try:
            answers = request.answers
            question_ids = list(map(lambda answer: answer.question_id, answers))

            if request.type == 1:
                question_type = "PRE_EVENT"
            elif request.type == 2:
                question_type = "POST_EVENT"
            else:
                throwError(
                    "Please select type; 1 = POST, 2 = PRE.",
                    grpc.StatusCode.INVALID_ARGUMENT,
                    context,
                )

            user_event_id = request.user_event_id
            user_event = (
                session.query(UserEvent).filter(UserEvent.id == user_event_id).scalar()
            )
            if user_event is None:
                throwError("Did not find any user_event for ID " + str(user_event_id) + ".", grpc.StatusCode.NOT_FOUND, context)

            query = (
                session.query(Answer, Question, QuestionGroup)
                .filter(
                    Answer.question_id == Question.id,
                    Question.question_group_id == QuestionGroup.id,
                )
                .filter(Answer.user_event_id == user_event_id)
                .all()
            )

            if query:
                throwError(
                    "User already submit the answers for this event.",
                    grpc.StatusCode.ALREADY_EXISTS,
                    context,
                )

            query_question = session.query(QuestionGroup, Question).filter(
                Question.question_group_id == QuestionGroup.id,
                QuestionGroup.event_id == user_event.event_id,
                QuestionGroup.type == question_type,
            )

            query_question_id = list(
                map(lambda question: question.Question.id, query_question)
            )

            print("expect: " + str(query_question_id) + " got " + str(question_ids))
            if not (set(query_question_id) == set(question_ids)):
                throwError(
                    "expect: " + str(query_question_id) + " got " + str(question_ids),
                    grpc.StatusCode.INVALID_ARGUMENT,
                    context,
                )

            for answer in answers:
                question_id = answer.question_id
                question_answer = answer.value
                new_answer = Answer(
                    user_event_id=user_event_id,
                    question_id=question_id,
                    value=question_answer,
                )
                session.add(new_answer)
                session.commit()

            query_answers = session.query(Answer).filter(
                Answer.user_event_id == user_event_id
            )

            data = map(
                lambda result: common.Answer(
                    id=result.id,
                    user_event_id=result.user_event_id,
                    question_id=result.question_id,
                    value=result.value,
                ),
                query_answers.all(),
            )

            return participant_service.SubmitAnswerForEventQuestionResponse(
                answers=data
            )
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def GetEventById(self, request, context):
        session = DBSession()
        try:
            query_event = (
                session.query(Event).filter(Event.id == request.event_id).scalar()
            )

            if query_event is not None:
                return common.Event(
                    id=query_event.id,
                    organization_id=query_event.organization_id,
                    location_id=getInt32Value(query_event.location_id),
                    description=query_event.description,
                    name=query_event.name,
                    cover_image_url=getStringValue(query_event.cover_image_url),
                    cover_image_hash=getStringValue(query_event.cover_image_hash),
                    poster_image_url=getStringValue(query_event.poster_image_url),
                    poster_image_hash=getStringValue(query_event.poster_image_hash),
                    profile_image_url=getStringValue(query_event.profile_image_url),
                    profile_image_hash=getStringValue(query_event.profile_image_hash),
                    attendee_limit=query_event.attendee_limit,
                    contact=getStringValue(query_event.contact),
                )

            throwError("Event not found.", grpc.StatusCode.NOT_FOUND, context)
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def GetAllEvents(self, request, context):
        session = DBSession()
        try:
            query_events = session.query(Event).all()

            data = map(
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
            return participant_service.EventsResponse(event=data)
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def GetTagById(self, request, context):
        session = DBSession()
        try:
            query_tag = session.query(Tag).filter(Tag.id == request.id).scalar()

            if query_tag:
                return common.Tag(id=query_tag.id, name=query_tag.name)
            throwError("Tag not found", grpc.StatusCode.NOT_FOUND, context)
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def GetAllTags(self, request, context):
        session = DBSession()
        try:
            query_tags = session.query(Tag).all()

            data = map(lambda tag: common.Tag(id=tag.id, name=tag.name), query_tags)
            return participant_service.TagsResponse(tags=data)
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def GetSuggestedEvents(self, request, context):
        session = DBSession()
        try:
            events = []

            for i in range(0, 10):
                query_event = (
                    session.query(Event).filter(Event.id == getRandomNumber()).scalar()
                )
                if query_event is not None:
                    events.append(
                        common.Event(
                            id=query_event.id,
                            organization_id=query_event.organization_id,
                            location_id=getInt32Value(query_event.location_id),
                            description=query_event.description,
                            name=query_event.name,
                            cover_image_url=getStringValue(query_event.cover_image_url),
                            cover_image_hash=getStringValue(
                                query_event.cover_image_hash
                            ),
                            poster_image_url=getStringValue(
                                query_event.poster_image_url
                            ),
                            poster_image_hash=getStringValue(
                                query_event.poster_image_hash
                            ),
                            profile_image_url=getStringValue(
                                query_event.profile_image_url
                            ),
                            profile_image_hash=getStringValue(
                                query_event.profile_image_hash
                            ),
                            attendee_limit=query_event.attendee_limit,
                            contact=getStringValue(query_event.contact),
                        )
                    )

            return participant_service.EventsResponse(event=events)
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def GetUpcomingEvents(self, request, context):
        session = DBSession()
        try:
            start = request.start.seconds
            end = request.end.seconds
            text = [float(start), float(end)]

            start_date = datetime.fromtimestamp(text[0])
            end_date = datetime.fromtimestamp(text[1])

            query_event_durations = (
                session.query(EventDuration)
                .filter(
                    EventDuration.start >= start_date, EventDuration.start < end_date
                )
                .all()
            )

            date_events = []
            events_id = map(
                lambda event_duration: (event_duration.event_id), query_event_durations
            )

            date_events = getEventsByIds(events_id=events_id, session=session)

            return participant_service.EventsResponse(event=date_events)
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def GetEventsByStringOfName(self, request, context):
        session = DBSession()
        try:
            text = request.text.lower()
            if text == "":
                return participant_service.EventsResponse(event=None)
            results = session.query(Event).filter(func.lower(Event.name).contains(text))

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
                results,
            )

            return participant_service.EventsResponse(event=events)
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def GetEventsByTagIds(self, request, context):
        session = DBSession()
        try:
            tag_id = request.tag_ids

            query_event_tags = (
                session.query(EventTag).filter(EventTag.tag_id.in_(tag_id)).all()
            )

            events_id = map(lambda event: event.id, query_event_tags)

            tag_events = getEventsByIds(events_id=events_id, session=session)

            return participant_service.EventsResponse(event=tag_events)
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def GetEventsByFacilityId(self, request, context):
        session = DBSession()
        try:
            facility_id = request.id

            query_facility_requests = (
                session.query(FacilityRequest)
                .filter(FacilityRequest.facility_id == facility_id)
                .all()
            )

            events_id = map(
                lambda facility_request: facility_request.event_id,
                query_facility_requests,
            )
            facility_events = getEventsByIds(events_id=events_id, session=session)

            return participant_service.EventsResponse(event=facility_events)
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def GetEventsByOrganizationId(self, request, context):
        session = DBSession()
        try:
            organization_id = request.id

            query_events = (
                session.query(Event)
                .filter(Event.organization_id == organization_id)
                .all()
            )

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

            return participant_service.EventsResponse(event=events)
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def GetEventsByDate(self, request, context):
        session = DBSession()
        try:
            timestamp = request.seconds
            text = float(timestamp)

            date = datetime.fromtimestamp(text)
            start_date = datetime(date.year, date.month, date.day, 0, 0, 0)
            end_date = datetime(date.year, date.month, date.day + 1, 0, 0, 0)

            query_event_durations = (
                session.query(EventDuration)
                .filter(
                    EventDuration.start >= start_date, EventDuration.start < end_date
                )
                .all()
            )

            events_id = map(
                lambda event_duration: event_duration.event_id, query_event_durations
            )
            date_events = getEventsByIds(events_id=events_id, session=session)

            return participant_service.EventsResponse(event=date_events)
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def GetLocationById(self, request, context):
        session = DBSession()
        try:
            id = request.id

            query_location = session.query(Location).filter(Location.id == id).scalar()

            if query_location:
                return common.Location(
                    id=query_location.id,
                    name=query_location.name,
                    google_map_url=query_location.google_map_url,
                    description=getStringValue(query_location.description),
                    travel_information_image_url=getStringValue(
                        query_location.travel_information_image_url
                    ),
                    travel_information_image_hash=getStringValue(
                        query_location.travel_information_image_hash
                    ),
                )
            throwError(
                "No location found with given location_id",
                grpc.StatusCode.NOT_FOUND,
                context,
            )
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def GetTagsByEventId(self, request, context):
        session = DBSession()
        try:
            event_id = request.id
            tags_id = []
            tags_of_event = []

            tags = session.query(EventTag).filter(EventTag.event_id == event_id).all()
            for tag in tags:
                tags_id.append(tag.id)

            for tag_id in tags_id:
                tag = session.query(Tag).filter(Tag.id == tag_id).scalar()
                if tag is not None:
                    tags_of_event.append(common.Tag(id=tag.id, name=tag.name))
            return participant_service.TagsResponse(tags=tags_of_event)
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def GetRatingByEventId(self, request, context):
        session = DBSession()
        try:
            event_id = request.id
            ratings = []

            query_user_events = (
                session.query(UserEvent).filter(UserEvent.event_id == event_id).all()
            )

            if query_user_events:
                for user_event in query_user_events:
                    temp = user_event.rating
                    if temp is not None:
                        ratings.append(temp)
                return participant_service.GetRatingByEventIdResponse(result=ratings)
            throwError("No rating found for event.", grpc.StatusCode.NOT_FOUND, context)
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def GetUsersByEventId(self, request, context):
        session = DBSession()
        try:
            event_id = request.event_id
            status = request.status
            status_type = None
            chosen_users = None

            if status == 1:
                status_type = "PENDING"
            elif status == 2:
                status_type = "APPROVED"
            elif status == 3:
                status_type = "REJECTED"

            query_user_events = (
                session.query(UserEvent, User)
                .filter(UserEvent.user_id == User.id)
                .filter(UserEvent.event_id == event_id, UserEvent.status == status_type)
                .all()
            )

            if query_user_events:
                chosen_users = map(
                    lambda user_event: common.User(
                        id=user_event.User.id,
                        first_name=user_event.User.first_name,
                        last_name=user_event.User.last_name,
                        email=user_event.User.email,
                        nickname=getStringValue(user_event.User.nickname),
                        chula_id=getStringValue(user_event.User.chula_id),
                        address=getStringValue(user_event.User.address),
                        profile_picture_url=getStringValue(
                            user_event.User.profile_picture_url
                        ),
                        is_chula_student=user_event.User.is_chula_student,
                        gender=user_event.User.gender,
                        did_setup=user_event.User.did_setup,
                        district=getStringValue(user_event.User.district),
                        zip_code=getStringValue(user_event.User.zip_code),
                        phone_number=getStringValue(user_event.User.phone_number),
                        province=getStringValue(user_event.User.province),
                        academic_year=getInt32Value(user_event.User.academic_year),
                    ),
                    query_user_events,
                )

            return participant_service.GetUsersByEventIdResponse(users=chosen_users)
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def GetEventDurationsByEventId(self, request, context):
        session = DBSession()
        try:
            event_id = request.id
            event_durations = []

            query_event_durations = (
                session.query(EventDuration)
                .filter(EventDuration.event_id == event_id)
                .all()
            )

            if query_event_durations:
                for event_duration in query_event_durations:
                    start_timestamp = Timestamp()
                    finish_timestamp = Timestamp()
                    start_timestamp.FromDatetime(event_duration.start)
                    finish_timestamp.FromDatetime(event_duration.finish)
                    event_durations.append(
                        common.EventDuration(
                            id=event_duration.id,
                            event_id=event_duration.event_id,
                            start=start_timestamp,
                            finish=finish_timestamp,
                        )
                    )
            return participant_service.GetEventDurationsByEventIdResponse(
                event_durations=event_durations
            )
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def GetQuestionGroupsByEventId(self, request, context):
        session = DBSession()
        try:
            event_id = request.id
            question_groups = []

            query_question_groups = (
                session.query(QuestionGroup)
                .filter(QuestionGroup.event_id == event_id)
                .all()
            )

            if query_question_groups is None:
                return participant_service.GetQuestionGroupsByEventIdResponse(
                    question_groups=[]
                )

            for question_group_query in query_question_groups:
                question_groups.append(
                    common.QuestionGroup(
                        id=question_group_query.id,
                        event_id=question_group_query.event_id,
                        type=question_group_query.type,
                        seq=question_group_query.seq,
                        title=question_group_query.title,
                    )
                )
            return participant_service.GetQuestionGroupsByEventIdResponse(
                question_groups=question_groups
            )

        except:
            session.rollback()
            raise
        finally:
            session.close()

    def GetQuestionsByQuestionGroupId(self, request, context):
        session = DBSession()
        try:
            question_group_id = request.id
            questions = []

            query_questions = (
                session.query(Question)
                .filter(Question.question_group_id == question_group_id)
                .all()
            )

            if query_questions is None:
                return participant_service.GetQuestionsByQuestionGroupIdResponse(
                    questions=[]
                )

            for question_query in query_questions:
                questions.append(
                    common.Question(
                        id=question_query.id,
                        question_group_id=question_query.question_group_id,
                        seq=question_query.seq,
                        answer_type=question_query.answer_type,
                        is_optional=question_query.is_optional,
                        title=question_query.title,
                        subtitle=question_query.subtitle,
                    )
                )
            return participant_service.GetQuestionsByQuestionGroupIdResponse(
                questions=questions
            )

        except:
            session.rollback()
            raise
        finally:
            session.close()

    def GetAnswersByQuestionId(self, request, context):
        session = DBSession()
        try:
            question_id = request.id
            answers = []

            query_answers = (
                session.query(Answer).filter(Answer.question_id == question_id).all()
            )

            if query_answers:
                answers = map(
                    lambda answer: common.Answer(
                        id=answer.id,
                        user_event_id=answer.user_event_id,
                        question_id=answer.question_id,
                        value=answer.value,
                    ),
                    query_answers,
                )

            return participant_service.AnswersResponse(answers=answers)
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def GetAnswersByUserEventId(self, request, context):
        session = DBSession()
        try:
            user_event_id = request.id
            answers = []

            query_answers = (
                session.query(Answer)
                .filter(Answer.user_event_id == user_event_id)
                .all()
            )

            if query_answers:
                answers = map(
                    lambda answer: common.Answer(
                        id=answer.id,
                        user_event_id=answer.user_event_id,
                        question_id=answer.question_id,
                        value=answer.value,
                    ),
                    query_answers,
                )

            return participant_service.AnswersResponse(answers=answers)
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def GetUserAnswerByQuestionId(self, request, context):
        session = DBSession()
        try:
            user_id = request.user_id
            question_id = request.question_id
            selected_user_event_id = []

            query_user_events = (
                session.query(UserEvent).filter(UserEvent.user_id == user_id).all()
            )

            selected_user_event_id = map(
                lambda query_user_event: query_user_event.id, query_user_events
            )

            query_answer = (
                session.query(Answer)
                .filter(
                    Answer.question_id == question_id,
                    Answer.user_event_id.in_(selected_user_event_id),
                )
                .scalar()
            )

            if query_answer:
                return common.Answer(
                    id=query_answer.id,
                    user_event_id=query_answer.user_event_id,
                    question_id=query_answer.question_id,
                    value=query_answer.value,
                )
            throwError("No Answers found for User.", grpc.StatusCode.NOT_FOUND, context)

        except:
            session.rollback()
            raise
        finally:
            session.close()

    def GetUserEventByUserAndEventId(self, request, context):
        session = DBSession()
        try:
            user_id = request.user_id
            event_id = request.event_id

            query_user_event = session.query(UserEvent).filter(
                UserEvent.user_id == user_id, UserEvent.event_id == event_id
            )
            if query_user_event.scalar():
                user_event = query_user_event.scalar()
                return common.UserEvent(
                    id=user_event.id,
                    user_id=user_event.user_id,
                    event_id=user_event.event_id,
                    rating=getInt32Value(user_event.rating),
                    ticket=getStringValue(user_event.ticket),
                    status=user_event.status,
                    is_internal=user_event.is_internal,
                )
            throwError("User Event not found", grpc.StatusCode.NOT_FOUND, context)
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def GetEventsByUserId(self, request, context):
        session = DBSession()
        try:
            user_id = request.user_id

            query_user_events = (
                session.query(UserEvent, Event)
                .filter(UserEvent.event_id == Event.id)
                .filter(UserEvent.user_id == user_id)
                .all()
            )

            events = map(
                lambda event: common.Event(
                    id=event.Event.id,
                    organization_id=event.Event.organization_id,
                    location_id=getInt32Value(event.Event.location_id),
                    description=event.Event.description,
                    name=event.Event.name,
                    cover_image_url=getStringValue(event.Event.cover_image_url),
                    cover_image_hash=getStringValue(event.Event.cover_image_hash),
                    poster_image_url=getStringValue(event.Event.poster_image_url),
                    poster_image_hash=getStringValue(event.Event.poster_image_hash),
                    profile_image_url=getStringValue(event.Event.profile_image_url),
                    profile_image_hash=getStringValue(event.Event.profile_image_hash),
                    attendee_limit=event.Event.attendee_limit,
                    contact=getStringValue(event.Event.contact),
                ),
                query_user_events,
            )

            return participant_service.EventsResponse(event=events)

        except:
            session.rollback()
            raise
        finally:
            session.close()

    def GetUserEventsByEventId(self, request, context):
        session = DBSession()
        try:
            event_id = request.id

            query_user_event = (
                session.query(UserEvent).filter(UserEvent.event_id == event_id).all()
            )

            chosen_user_events = map(
                lambda user_event: common.UserEvent(
                    id=user_event.id,
                    user_id=user_event.user_id,
                    event_id=user_event.event_id,
                    rating=getInt32Value(user_event.rating),
                    ticket=getStringValue(user_event.ticket),
                    status=user_event.status,
                    is_internal=user_event.is_internal,
                ),
                query_user_event,
            )
            return participant_service.GetUserEventsByEventIdResponse(
                user_events=chosen_user_events
            )
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def GenerateQR(self, request, context):
        session = DBSession()
        try:
            query_result = session.query(UserEvent).filter(
                UserEvent.id == request.user_event_id
            )
            if query_result.scalar():
                user_event = {
                    "use_event_id": request.user_event_id,
                    "user_id": request.user_id,
                    "event_id": request.event_id,
                }
                string_user_event = b64encode(str(user_event))
                return participant_service.GenerateQRResponse(data=string_user_event)

            throwError("UserEvent not found.", grpc.StatusCode.NOT_FOUND, context)

        except:
            session.rollback()
            raise
        finally:
            session.close()

    def Ping(self, request, context):
        session = DBSession()
        try:
            boolvalue = BoolValue()
            boolvalue.value = True
            return boolvalue
        except:
            session.rollback()
            raise
        finally:
            session.close()


port = os.environ.get("GRPC_PORT")


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    participant_service_grpc.add_ParticipantServiceServicer_to_server(
        ParticipantService(), server
    )
    server.add_insecure_port("[::]:" + port)
    server.start()
    server.wait_for_termination()


serve()
