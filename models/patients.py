import requests
from uuid import uuid4
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin
from datetime import datetime, timedelta

from helper.utils import logger, par_notifications
from helper import config

db = SQLAlchemy()


class RecommenderPatients(db.Model, UserMixin):
    __tablename__ = 'RecommenderPatients'

    ccdr_reference = db.Column(db.String, primary_key=True)
    par_day = db.Column(db.Integer, nullable=False)
    notification = relationship("Notifications", backref="RecommenderPatient")

    def __init__(self, ccdr_reference, par_day=1):
        self.ccdr_reference = ccdr_reference
        self.par_day = par_day

    def get_dict(self):
        return {
            "ccdr_reference": self.ccdr_reference,
            "par_day": self.par_day
        }

    def save(self):
        if self.ccdr_reference:
            db.session.add(self)
            logger.debug(self.ccdr_reference)
        db.session.commit()

    def par_notification(self):
        notification = Notifications(par_notifications[str(self.par_day)])
        self.notification.append(notification)
        if self.par_day in [1, 7, 14, 21, 28, 35]:
            category = self.par_analysis()
            analysis_notification = Notifications("Activity category: " + str(category))
            self.notification.append(analysis_notification)
            analysis_notification.send()
        self.par_day = (self.par_day + 1) % 41
        db.session.commit()
        notification.send()

    def get_notifications(self):
        return self.notification

    @staticmethod
    def get_by_ccdr_ref(ref):
        return RecommenderPatients.query.filter_by(ccdr_reference=ref).first()

    def par_analysis(self):
        logger.info("Evaluating activity for patient " + str(self.ccdr_reference))
        post = {
            "identity_management_key": self.ccdr_reference
        }
        today = datetime.today()
        week_ago = today - timedelta(weeks=1)
        response = requests.post(config.ccdr_url + "/api/v1/web/questionnaire/getPatientQuestionnairesResponses",
                                 json=post).json()

        valid_quests = []
        for quest in response.json():
            survey_id = quest["survey_id"].split(".")[0]
            if survey_id == "7":
                # test = "Mon Jun 28 09:07:16 UTC 2021".replace(" UTC ", " ")
                survey_datetime = datetime.strptime(quest["date"].replace(" UTC ", " "), '%a %b %d %H:%M:%S %Y')
                if today > survey_datetime > week_ago:
                    valid_quests.append(quest)
                    logger.debug(quest)

        if valid_quests:
            final_quest = valid_quests[0]
            vigorous_days, vigorous_hours, vigorous_minutes, moderate_days, moderate_hours, moderate_minutes, \
            walk_days, walk_hours, walk_minutes, sitting_hours, sitting_minutes = (None,) * 11
            for answer in final_quest["answers"]:
                question_id = answer["question_id"]
                if question_id is 0:
                    vigorous_days = int(answer["text_input_value"])
                if question_id is 1:
                    vigorous_hours = int(answer["text_input_value"])
                if question_id is 2:
                    vigorous_minutes = int(answer["text_input_value"])
                if question_id is 3:
                    moderate_days = int(answer["text_input_value"])
                if question_id is 4:
                    moderate_hours = int(answer["text_input_value"])
                if question_id is 5:
                    moderate_minutes = int(answer["text_input_value"])
                if question_id is 6:
                    walk_days = int(answer["text_input_value"])
                if question_id is 7:
                    walk_hours = int(answer["text_input_value"])
                if question_id is 8:
                    walk_minutes = int(answer["text_input_value"])
                if question_id is 9:
                    sitting_hours = int(answer["text_input_value"])
                if question_id is 10:
                    sitting_minutes = int(answer["text_input_value"])

            variables = vigorous_days, vigorous_hours, vigorous_minutes, moderate_days, moderate_hours, \
                        moderate_minutes, walk_days, walk_hours, walk_minutes, sitting_hours, sitting_minutes

            if None not in variables:
                vigorous_met_value = 8.0
                moderate_met_value = 4.0
                walk_met_value = 3.3
                vigorous_time = vigorous_minutes + (60 * vigorous_hours)
                moderate_time = moderate_minutes + (60 * moderate_hours)
                walk_time = walk_minutes + (60 * walk_hours)
                vigorous_met = vigorous_met_value * vigorous_days * vigorous_time
                moderate_met = moderate_met_value * moderate_days * moderate_time
                walk_met = walk_met_value * walk_days * walk_time
                total_met_value = vigorous_met + moderate_met + walk_met

                if vigorous_days >= 3 and vigorous_time >= 20:
                    category = 1  # Minimally active
                    if vigorous_met >= 1500:
                        category = 2  # HEPA Active
                    else:
                        if walk_days + moderate_days + vigorous_days >= 7 and total_met_value >= 3000:
                            category = 2  # HEPA Active
                else:
                    if moderate_days + walk_days >= 5:
                        if moderate_time + walk_time >= 30:
                            category = 1  # Minimally active
                        else:
                            if walk_days + moderate_days + vigorous_days >= 5 and total_met_value >= 600:
                                category = 1  # Minimally active
                            else:
                                category = 0  # Inactive
                    else:
                        category = 0  # Inactive
                return category

    @staticmethod
    def get_all():
        list_of_services = RecommenderPatients.query.all()
        total = len(list_of_services)
        return list_of_services, total

    @staticmethod
    def par_notifications_round():
        patients, total = RecommenderPatients.get_all()
        for patient in patients:
            patient.par_notification()

    @staticmethod
    def update_db():
        try:
            response = requests.get(config.ccdr_url + "/api/v1/mobile/patient").json()
            for patient in response:
                ccdr_ref = patient["identity_management_key"]
                rec_patient = RecommenderPatients.get_by_ccdr_ref(ccdr_ref)
                if not rec_patient:
                    rec_patient = RecommenderPatients(ccdr_ref)
                rec_patient.save()
            return RecommenderPatients.get_all()

        except requests.exceptions.RequestException as e:
            logger.error("Getting all patients from CCDR error", exc_info=True)
            return str(e), 0


class Notifications(db.Model, UserMixin):
    __tablename__ = 'Notifications'

    id = db.Column(db.String, primary_key=True)
    read = db.Column(db.Boolean, nullable=False)
    msg = db.Column(db.String, nullable=False)
    patient = db.Column(db.String, db.ForeignKey('RecommenderPatients.ccdr_reference'))

    def __init__(self, msg):
        self.id = str(uuid4())
        self.msg = msg
        self.read = False

    def send(self):
        notification = {
            "receiverUniqueIdentifier": self.patient,
            "messageBody": self.msg,
            "messageUniqueIdentifier": self.id,
            "senderUniqueIdentifier": "Recommender"
        }
        logger.debug(notification)
        # TODO post notification

    def get_dict(self):
        return {
            "id": self.id,
            "msg": self.msg,
            "read": self.read
        }

    def save(self):
        if self.id and self.msg and self.read and self.patient:
            db.session.add(self)
            logger.debug("Notification " + str(self.id) + " saved")
        else:
            logger.error("Incomplete notification couldn't be saved")
        db.session.commit()

    @staticmethod
    def get_by_id(_id):
        return Notifications.query.filter_by(id=_id).first()
