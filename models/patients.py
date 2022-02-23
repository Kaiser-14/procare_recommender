import json

import requests
from uuid import uuid4
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin
from datetime import datetime, timedelta

from helper.utils import logger, par_notifications
from helper import config

db = SQLAlchemy()

# Flags
test_flag = True
debug_requests = True


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
		if self.par_day in [10, 15, 25, 30, 35, 40]:
			category, sitting_minutes = self.par_analysis()
			category = RecommenderPatients.get_color_category(category)
			analysis_notification = Notifications(
				"activity_level_color: ,\ninactivity_minutes: ".format(category, str(sitting_minutes)))
			self.notification.append(analysis_notification)
			analysis_notification.send()
		self.par_day = (self.par_day + 1) % 41
		db.session.commit()
		notification.send()

	def get_notifications(self):
		return self.notification

	# @staticmethod
	def get_by_ccdr_ref(ref):
		return RecommenderPatients.query.filter_by(ccdr_reference=ref).first()

	@staticmethod
	def recommendation(patient, date):
		category, variables = RecommenderPatients.par_analysis(patient)
		scores, deviations = RecommenderPatients.scores_injection_patient(patient, date)

		notification_key = "1"
		par_notification = par_notifications[str(notification_key)]

		msg = {
			"identity_management_key": patient,
			"message_body": par_notification,
			"message_unique_identifier": '1234',  # TODO: Change to UUID: str(uuid4())
			"sender_unique_identifier": "recommendLib",
			"receiver_device_type": 'game',  # TODO: Change to corresponding service: web mobile or game
		}
		Notifications.send(msg, destination='patient')

		return par_notification

	# @staticmethod
	def par_analysis(self):
		logger.info("Evaluating activity for patient " + self.ccdr_reference)
		body = {
			"identity_management_key": self.ccdr_reference
		}

		# Initialize variables
		category = None
		variables = None

		today = datetime.today()
		week_ago = today - timedelta(weeks=1)
		response = requests.post(
			config.ccdr_url + "/api/v1/web/questionnaire/getPatientQuestionnairesResponses", json=body).json()

		valid_quests = []
		if response:
			for quest in response.json():
				survey_id = quest["survey_id"].split(".")[0]
				if survey_id == "7":
					# test = "Mon Jun 28 09:07:16 UTC 2021".replace(" UTC ", " ")
					survey_datetime = datetime.strptime(quest["date"].replace(" UTC ", " "), '%a %b %d %H:%M:%S %Y')
					if today > survey_datetime > week_ago:
						valid_quests.append(quest)
						logger.debug(quest)
		else:
			logger.debug('No questionnaire for patient {}'.format(self.ccdr_reference))

		if valid_quests:
			final_quest = valid_quests[0]
			vigorous_days, vigorous_hours, vigorous_minutes, moderate_days, moderate_hours, moderate_minutes, \
				walk_days, walk_hours, walk_minutes, sitting_hours, sitting_minutes = (None,) * 11
			for answer in final_quest["answers"]:
				question_id = answer["question_id"]
				if question_id == 0:
					vigorous_days = int(answer["text_input_value"])
				if question_id == 1:
					vigorous_hours = int(answer["text_input_value"])
				if question_id == 2:
					vigorous_minutes = int(answer["text_input_value"])
				if question_id == 3:
					moderate_days = int(answer["text_input_value"])
				if question_id == 4:
					moderate_hours = int(answer["text_input_value"])
				if question_id == 5:
					moderate_minutes = int(answer["text_input_value"])
				if question_id == 6:
					walk_days = int(answer["text_input_value"])
				if question_id == 7:
					walk_hours = int(answer["text_input_value"])
				if question_id == 8:
					walk_minutes = int(answer["text_input_value"])
				if question_id == 9:
					sitting_hours = int(answer["text_input_value"])
				if question_id == 10:
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
				# return category+1, variables
		return category+1, variables

	@staticmethod
	def get_patients_db():
		list_of_services = RecommenderPatients.query.all()
		total = len(list_of_services)
		return list_of_services, total

	# Get all patient unique identifiers from the identity management API
	@staticmethod
	def get_patients():
		headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
		if not test_flag:
			idm_response = requests.get(
				config.idm_url + "/getAllPacientKeys", headers=headers)
		else:
			idm_response = ["98284945", "98284945"]

		number_of_patients = len(idm_response)
		return idm_response, number_of_patients

	@staticmethod
	def par_notifications_round():
		patient_references, patients_total = RecommenderPatients.get_patients_db()
		# reference_patients, patients_total = RecommenderPatients.get_patients()
		patient_count = 0

		for patient in patient_references:
			patient_count = patient_count + 1
			logger.info('Par notification: Patient {}/{}'.format(patient_count, patients_total))
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
			return RecommenderPatients.get_patients_db()

		except requests.exceptions.RequestException as e:
			logger.error("Getting all patients from CCDR error", exc_info=True)
			return str(e), 0

	@staticmethod
	def scores_injection():
		# patients, total = RecommenderPatients.get_patients_db()
		patients, patients_total = RecommenderPatients.get_patients()

		if not test_flag:
			start_dates = [
				"01-11-2021", "08-11-2021", "15-11-2021", "22-11-2021", "29-11-2021",
				"06-12-2021", "13-12-2021", "20-12-2021", "27-12-2021", "03-01-2022",
				"10-01-2022", "17-01-2022", "24-01-2022", "31-01-2022", "07-02-2022"
			]
			end_dates = [
				"07-11-2021", "14-11-2021", "21-11-2021", "28-11-2021", "05-12-2021",
				"12-12-2021", "19-12-2021", "26-12-2021", "02-01-2022", "09-01-2022",
				"16-01-2022", "23-01-2022", "30-01-2022", "06-02-2022", "13-02-2022"
			]
		else:
			start_dates = ["25-08-2021", "25-08-2021"]
			end_dates = ["25-08-2021", "25-08-2021"]

		patient_count = 0
		for patient in patients:
			period_count = 0
			patient_count = patient_count + 1
			logger.info("Processing patient " + patient + "....\n")
			for start_date, end_date in zip(start_dates, end_dates):
				period_count = period_count + 1
				date = [start_date, end_date]
				actionlib_response, fusionlib_response = RecommenderPatients.calculate_scores(patient, date)

				logger.info("Completed data injection " + str(period_count) + "/" + str(
					len(start_dates)) + " for " + patient + " between " + start_date + " and " + end_date +
					" ActionLib: " + str(actionlib_response.status_code) + " FusionLib: " + str(
					fusionlib_response.status_code))

				logger.debug("ActionLib Response:\nStatus: {}\nContent: {}\n".format(
					str(actionlib_response.status_code), str(actionlib_response.content)))
				logger.debug("FusionLib Response:\nStatus: {}\nContent: {}\n".format(
					str(actionlib_response.status_code), str(actionlib_response.content)))
				logger.info("--------------")

			logger.info("\nInjection completed. Patient: {}/{}\n".format(str(patient_count), str(patients_total)))
			logger.info("--------------")

		logger.info("Data injection completed")

	@staticmethod
	def scores_injection_patient(patient, date):
		logger.info("Processing patient " + patient + "....\n")

		actionlib_response, fusionlib_response = RecommenderPatients.calculate_scores(patient, date)

		scores = actionlib_response.json()['scores']
		deviations = fusionlib_response.json()['deviations']

		logger.info('Scores: {}\nDeviations: {}\n'.format(scores, deviations))

		return scores, deviations

	# Run both ActionLib (HBR) scores and FusionLib (MMF) deviation for specific patient and date
	@staticmethod
	def calculate_scores(patient, date):
		# today = datetime.today()
		# week_ago = today - timedelta(weeks=1)
		body = {
			"identity_management_key": str(uuid4()),
			"organization": "000",
			"role": "system",
			"scenario": "data_injection",
			"patient_identity_management_key": patient,
			"measurements_start_date": date[0],
			"measurements_end_date": date[1],
		}

		# logger("Request: {}\n".format(str(body)))

		headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
		actionlib_response = requests.post(
			config.actionlib_url + "/calculate_scores", data=json.dumps(body), headers=headers)
		fusionlib_response = requests.post(
			config.fusionlib_url + "/calculate_deviations", data=json.dumps(body), headers=headers)

		if actionlib_response.status_code != 200:
			logger.error(actionlib_response.text)
		if fusionlib_response.status_code != 200:
			logger.error(fusionlib_response.text)

		return actionlib_response, fusionlib_response

	@staticmethod
	def get_color_category(category):
		if category == 1:
			return "red"
		elif category == 2:
			return "orange"
		elif category == 3:
			return "green"
		else:
			return None


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
		body = {
			"identity_management_key": self.patient,
			"message_body": self.msg,
			"message_unique_identifier": self.id,
			"sender_unique_identifier": "recommendLib",
			"receiver_device_type": 'game',  # TODO: Change to mobile
		}

		logger.debug(body)

		headers = {'Content-type': 'application/json', 'Accept': 'application/json'}

		notification_response = requests.post(
			config.rmq_url + "/notification/sendNotifications",
			data=json.dumps(body), headers=headers
		)

		# TODO: Control to send notifications to professionals (always receiver via web)
		# notification_response = requests.post(
		# 	config.rmq_url + "/notification/sendNotificationToMedicalProfessionalByPatient",
		# 	data=json.dumps(body), headers=headers
		# )

		destination = "patient"
		Notifications.check_response(destination, notification_response, body)

	# Previous version
	# @staticmethod
	# def send(body, destination):
	# 	logger.debug(body)
	#
	# 	headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
	# 	if destination == 'patient':
	# 		notification_response = requests.post(
	# 			config.rmq_url + "/notification/sendNotifications",
	# 			data=json.dumps(body), headers=headers
	# 		)
	# 	elif destination == 'professional':
	# 		# The receiving device should always be web notification
	# 		body["receiver_device_type"] = "web"
	# 		notification_response = requests.post(
	# 			config.rmq_url + "/notification/sendNotificationToMedicalProfessionalByPatient",
	# 			data=json.dumps(body), headers=headers
	# 		)
	# 	else:
	# 		notification_response = None
	# 	Notifications.check_response(destination, notification_response, body)

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

	@staticmethod
	def check_response(destination, response, body):
		if response:
			if response.status_code == 200:
				logger.debug('Notification sent to {} via {}'.format(
					body['identity_management_key'], body['receiver_device_type']))
			elif response.status_code == 1000:
				logger.error('NOTIFICATION ERROR: Request returned general error.')
			elif response.status_code == 1007:
				logger.error('NOTIFICATION ERROR: There is no patient with the patient_identity_management_key {}'.format(
					body['identity_management_key']))
			elif response.status_code == 1060 and destination == 'patient':
				logger.error('NOTIFICATION ERROR: receiver_device_type ({}) does not match the user role'.format(
					body['receiver_device_type']))
			elif response.status_code == 1048:
				logger.error('NOTIFICATION ERROR: notification_queue_key not found')
			else:
				logger.error('NOTIFICATION ERROR.')
		else:
			logger.debug('No response.')

	@staticmethod
	def retrieve_notifications(patient, organization, date):

		# TODO: Login to retrieve notifications.

		headers = {
			"Content-type": "application/json",
			"Accept": "application/json",
			"Authorization": "Bearer MYREALLYLONGTOKENIGOT"}
		# client_type = "web"
		# notification_response = requests.get(
		# 	config.backend_url + client_type + "/getNotificationQueueKey",
		# 	data=json.dumps(body), headers=headers
		# )

		pass

	@staticmethod
	def check_notification(ref):
		# TODO: Define function
		pass
