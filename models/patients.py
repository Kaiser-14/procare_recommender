import json
import time

import requests
from uuid import uuid4
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin
from datetime import datetime, timedelta, date

from helper.utils import logger, par_notifications
from helper import config

db = SQLAlchemy()


class RecommenderPatients(db.Model, UserMixin):
	__tablename__ = 'RecommenderPatients'

	ccdr_reference = db.Column(db.String, primary_key=True)
	par_day = db.Column(db.Integer, nullable=False)
	organization = db.Column(db.String, nullable=False)
	notification = relationship("Notifications", backref="RecommenderPatient")

	def __init__(self, ccdr_reference, organization, par_day=0):
		self.ccdr_reference = ccdr_reference
		self.par_day = par_day
		self.organization = organization

	def get_dict(self):
		return {
			"ccdr_reference": self.ccdr_reference,
			"par_day": self.par_day,
			"organization": self.organization,
		}

	def save(self):
		if self.ccdr_reference:
			db.session.add(self)
			logger.debug(self.ccdr_reference)
		db.session.commit()

	def par_notification(self, ipaq=False):
		if not ipaq:
			self.par_day = (self.par_day + 1) % 41
			if self.par_day == 0:
				self.par_day = 1
			message = par_notifications[str(self.par_day)]
			if message:
				notification = Notifications(self.ccdr_reference, message)
				self.notification.append(notification)

				notification.send(receiver="mobile")

		if self.par_day in [7, 14, 21, 28, 35] or ipaq:
			message = "Your weekly questionnaire is available. " \
				"If you have not answered, please, fill the form into the app."
			ipaq_notification = Notifications(self.ccdr_reference, message)
			self.notification.append(ipaq_notification)
			ipaq_notification.send(receiver="mobile")

		db.session.commit()

	def game_notification(self):
		body = {
			"identity_management_key": self.ccdr_reference,
			"organization": self.organization,
			"role": "patient",
			"date": "09-03-2022",
		}
		response = requests.post(
			config.ccdr_url + "/api/v1/game/getSummarization", json=body).json()

		game_score = response["session_info"][0]["metric_global"]
		game_clicks = response["session_info"][0]["nclicks_total"]

		message = None
		if game_score > 0.5:
			message = "Change the game."

		if message:
			notification = Notifications(self.ccdr_reference, message)
			self.notification.append(notification)
			notification.send(receiver="game")

	def get_notifications(self):
		return self.notification

	@staticmethod
	def get_by_ccdr_ref(ref):
		return RecommenderPatients.query.filter_by(ccdr_reference=ref).first()

	def recommendation(self):

		category, sitting_minutes = self.par_analysis()
		scores, deviations = self.scores_injection_patient()

		notification_key = "2"
		par_notification = par_notifications[str(notification_key)]

		notification = Notifications(self.ccdr_reference, par_notification)
		self.notification.append(notification)
		notification.send()
		db.session.commit()

		return par_notification

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
					category = 2  # Minimally active
					if vigorous_met >= 1500:
						category = 3  # HEPA Active
					else:
						if walk_days + moderate_days + vigorous_days >= 7 and total_met_value >= 3000:
							category = 3  # HEPA Active
				else:
					if moderate_days + walk_days >= 5:
						if moderate_time + walk_time >= 30:
							category = 2  # Minimally active
						else:
							if walk_days + moderate_days + vigorous_days >= 5 and total_met_value >= 600:
								category = 2  # Minimally active
							else:
								category = 1  # Inactive
					else:
						category = 1  # Inactive
				# return category+1, variables
		return category, variables

	@staticmethod
	def get_patients_db():
		if not config.test_flag:
			list_of_services = RecommenderPatients.query.all()
		else:
			list_of_services = [RecommenderPatients.query.filter_by(ccdr_reference="98284945").first()]
		total = len(list_of_services)
		return list_of_services, total

	@staticmethod
	def notifications_round(receiver):
		patient_references, patients_total = RecommenderPatients.get_patients_db()
		patient_count = 0

		for patient in patient_references:
			patient_count = patient_count + 1
			if receiver == "mobile":
				logger.info('Par notification: Patient {}/{}'.format(patient_count, patients_total))
				patient.par_notification()
			elif receiver == "game":
				patient.game_notification()

		return patient_count

	@staticmethod
	def update_db():
		try:
			response = requests.get(config.ccdr_url + "/api/v1/mobile/patient").json()
			for patient in response:
				ccdr_ref = patient["identity_management_key"]
				organization = patient["organization_code"]
				rec_patient = RecommenderPatients.get_by_ccdr_ref(ccdr_ref)
				if not rec_patient:
					rec_patient = RecommenderPatients(ccdr_ref, organization)
					rec_patient.save()
			return RecommenderPatients.get_patients_db()

		except requests.exceptions.RequestException as e:
			logger.error("Getting all patients from CCDR error", exc_info=True)
			return str(e), 0

	@staticmethod
	def scores_injection():
		patients, total = RecommenderPatients.get_patients_db()

		patient_count = 0
		for patient in patients:
			period_count = 0
			patient_count = patient_count + 1
			logger.info("Processing patient " + patient.ccdr_reference + "....\n")

			actionlib_response, fusionlib_response = patient.calculate_scores()

			logger.debug("ActionLib Response:\nStatus: {}\nContent: {}\n".format(
				str(actionlib_response.status_code), str(actionlib_response.content)))
			logger.debug("FusionLib Response:\nStatus: {}\nContent: {}\n".format(
				str(actionlib_response.status_code), str(actionlib_response.content)))
			logger.info("--------------")

		logger.info("Injection completed. Patient: {}/{}\n".format(str(patient_count), str(total)))
		logger.info("--------------")

		return patient_count

	def scores_injection_patient(self):
		logger.info("Processing patient " + self.ccdr_reference + "....\n")

		actionlib_response, fusionlib_response = self.calculate_scores()

		scores = actionlib_response.json()['scores']
		deviations = fusionlib_response.json()['deviations']

		logger.info("Scores: {}".format(scores))
		logger.info("Deviations: {}".format(deviations))

		return scores, deviations

	# Run both ActionLib (HBR) scores and FusionLib (MMF) deviation for specific patient and date
	def calculate_scores(self):
		# today = datetime.today()
		# week_ago = today - timedelta(weeks=1)

		actionlib_response = None
		fusionlib_response = None

		today = datetime.today()

		body = {
			"identity_management_key": str(uuid4()),
			"organization": self.organization,
			"role": "system",
			"scenario": "data_injection",
			"patient_identity_management_key": self.ccdr_reference,
			"measurements_start_date": (today - timedelta(days=7)).strftime("%d-%m-%Y"),
			"measurements_end_date": today.strftime("%d-%m-%Y"),
		}

		# FIXME: Uncomment once tested in server
		# In test server: RiskAssesment/ActionLib and Diagnostic/FusionLib
		# Generate scores into the platform
		headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
		# actionlib_response = requests.post(
		# 	config.actionlib_url + "/generate_scores", data=json.dumps(body), headers=headers)
		# fusionlib_response = requests.post(
		# 	config.fusionlib_url + "/generate_deviations", data=json.dumps(body), headers=headers)

		actionlib_response = requests.post(
			config.actionlib_url + "/calculate_scores", data=json.dumps(body), headers=headers)

		# If there is no response from actionLib, we can skip the fusionLib request and save time
		# FIXME: Control this situation. 200 for test on calculate_scores / 204 for generateScores
		if actionlib_response.status_code != 200:
			logger.error(actionlib_response.text)
		else:
			fusionlib_response = requests.post(
				config.fusionlib_url + "/calculate_deviations", data=json.dumps(body), headers=headers)
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
	datetime_sent = db.Column(db.String, nullable=True)
	datetime_read = db.Column(db.String, nullable=True)
	patient = db.Column(db.String, db.ForeignKey('RecommenderPatients.ccdr_reference'))

	def __init__(self, ccdr_reference, msg):
		self.id = str(uuid4())
		self.msg = msg
		self.read = False
		self.datetime_sent = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
		self.datetime_read = None
		self.patient = ccdr_reference

	def send(self, receiver):
		body = {
			"identity_management_key": self.patient,
			"message_body": self.msg,
			"message_unique_identifier": self.id,
			"sender_unique_identifier": "recommendLib",
			"receiver_device_type": receiver,
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

		self.save_notification()

	def get_dict(self):
		return {
			"id": self.id,
			"msg": self.msg,
			"read": self.read,
			"datetime_sent": self.datetime_sent,
			"datetime_read": self.datetime_read,
			"patient": self.patient,
		}

	def save_notification(self):
		if self.id and self.msg and self.patient and self.datetime_sent:
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
	def check_notification_status(notification_id):
		notification = Notifications.get_by_id(notification_id)

		if notification:
			par = Notifications.check_par_notification(notification.msg)

			notification.read = True
			notification.datetime_read = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
			notification.save_notification()

			if not par:
				return {
					"status": "OK",
					"statusCode": 0
				}
			else:
				patient = RecommenderPatients.get_by_ccdr_ref(notification.patient)
				category, sitting_minutes = patient.par_analysis()
				category = RecommenderPatients.get_color_category(category)

				return {
					"activity_level_color": category,
					"inactivity_minutes": sitting_minutes
				}
		else:
			return {
				"status": "Reference not found",
				"statusCode": 2
			}

	@staticmethod
	def check_par_notification(msg):
		par = False
		if msg in par_notifications.values():
			par = True
		return par

	@staticmethod
	def check_timestamp(dates):
		for i, date in enumerate(dates):
			date = ''.join(filter(str.isdigit, date[:10]))
			date = datetime.strptime(date, "%d%m%Y")
			date = datetime.timestamp(date)
			dates[i] = date

		if dates[2] >= dates[0] >= dates[1]:
			return True
		else:
			return False

	@staticmethod
	def check_ipaq():
		patients, total = RecommenderPatients.get_patients_db()
		patient_count = 0

		today = date.today()
		yesterday = today - timedelta(days=1)

		for patient in patients:
			ipaq_response = requests.post(
				config.ccdr_url + "/api/v1/mobile/surveys/get_response/7.2?identity_management_key=" +
				patient.ccdr_reference).json()

			ipaq_datetime = datetime.strptime(
				ipaq_response[-1]["date"][4:].replace("UTC ", ""), '%b %d %H:%M:%S %Y').strftime("%d-%m-%Y")

			if not ipaq_response and ipaq_datetime in [yesterday, today]:
				notifications = patient.get_notifications()

				for notification in notifications:
					dates = [notification.datetime_sent, yesterday.strftime("%d-%m-%Y"), today.strftime("%d-%m-%Y")]

					if notification.msg.startswith("Your") and not notification.read and Notifications.check_timestamp(dates):
						logger.info("Sending reminder for IPAQ notification to patient {}".format(patient.ccdr_reference))
						patient.par_notification(True)
						patient_count = patient_count + 1
						break

		return patient_count
