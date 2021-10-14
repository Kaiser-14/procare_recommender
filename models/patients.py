import requests
from uuid import uuid4
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin

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
        self.par_day = self.par_day + 1
        db.session.commit()
        notification.send()

    def get_notifications(self):
        return self.notification

    @staticmethod
    def get_by_ccdr_ref(ref):
        return RecommenderPatients.query.filter_by(ccdr_reference=ref).first()

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
            logger.debug("Notification "+str(self.id)+" saved")
        else:
            logger.error("Incomplete notification couldn't be saved")
        db.session.commit()

    @staticmethod
    def get_by_id(_id):
        return Notifications.query.filter_by(id=_id).first()
