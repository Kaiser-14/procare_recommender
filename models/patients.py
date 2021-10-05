import requests
from flask_sqlalchemy import SQLAlchemy

from helper.utils import logger
from helper import config

db = SQLAlchemy()


class RecommenderPatients(db.Model):
    __tablename__ = 'RecommenderPatients'

    id = db.Column(db.Integer, primary_key=True)
    ccdr_reference = db.Column(db.String, nullable=False)
    par_day = db.Column(db.Integer, nullable=False)

    def __init__(self, _id=None, ccdr_reference=None, par_day=0):
        self.id = _id
        self.ccdr_reference = ccdr_reference
        self.par_day = par_day

    def get_dict(self):
        return {
            "id": self.id,
            "ccdr_reference": self.ccdr_reference,
            "par_day": self.par_day
        }

    def save(self):
        if not self.id:
            db.session.add(self)
        db.session.commit()

    @staticmethod
    def get_by_ccdr_ref(ref):
        return RecommenderPatients.query.filter_by(ccdr_reference=ref).first()

    @staticmethod
    def get_all():
        list_of_services = RecommenderPatients.query.all()
        total = len(list_of_services)
        return list_of_services, total

    @staticmethod
    def update_db():
        try:
            response = requests.get(config.ccdr_url + "/api/v1/mobile/patient").json()
            for patient in response:
                ccdr_ref = patient["identity_management_key"]
                rec_patient = RecommenderPatients.get_by_ccdr_ref(ccdr_ref)
                if not rec_patient:
                    rec_patient = RecommenderPatients(ccdr_reference=ccdr_ref)
                rec_patient.save()
            return RecommenderPatients.get_all()

        except requests.exceptions.RequestException as e:
            logger.error("Getting all patients from CCDR error", exc_info=True)
            return str(e), 0
