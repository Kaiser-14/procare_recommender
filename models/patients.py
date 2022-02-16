import json
import uuid

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

	@staticmethod
	def par_notification(patient, par_day=0):
		# notification = Notifications(par_notifications[str(self.par_day)])
		# self.notification.append(notification)

		notification_response = {}

		# Round notifications
		if par_day in [1, 7, 14, 21, 28, 35]:
			category, variables = patient.par_analysis()
			# analysis_notification = Notifications("Activity category: " + str(category))
			# self.notification.append(analysis_notification)
			# TODO: What should we send?
			# analysis_notification.send()
			Notifications.send()
		# PA notification
		else:
			category, variables = RecommenderPatients.par_analysis(patient)

			body = {
				"activity_level": category,
				"patient_identity_management_key": patient,
				"sitting_minutes": variables['sitting_minutes'],
			}

			headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
			# if destination == 'patient':
			# TODO: post notification. Which IP and PORT?
			notification_response = requests.post(
				config.fusionlib_url + "/notification/sendNotifications",
				data=json.dumps(body), headers=headers
			)

		par_day = (par_day + 1) % 41
		# db.session.commit()
		# TODO: What should we send?
		# notification.send()
		return notification_response

	def get_notifications(self):
		return self.notification

	# @staticmethod
	# def get_by_ccdr_ref(ref):
	#     return RecommenderPatients.query.filter_by(ccdr_reference=ref).first()

	@staticmethod
	def recommendation(patient, date):
		# category, variables = RecommenderPatients.par_analysis(patient)
		scores, deviations = RecommenderPatients.scores_injection_patient(patient, date)

		notification_key = "1"
		par_notification = par_notifications[str(notification_key)]

		return par_notification

	@staticmethod
	def par_analysis(patient):
		# logger.info("Evaluating activity for patient " + str(self.ccdr_reference))
		logger.info("Evaluating activity for patient " + patient)
		post = {
			"identity_management_key": patient
		}

		today = datetime.today()
		week_ago = today - timedelta(weeks=1)
		response = requests.post(
			config.ccdr_url + "/api/v1/web/questionnaire/getPatientQuestionnairesResponses", json=post).json()

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
				return category+1, variables

	# TODO: Remove
	# @staticmethod
	# def get_all():
	#     list_of_services = RecommenderPatients.query.all()
	#     total = len(list_of_services)
	#     return list_of_services, total

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
		patients, patients_total = RecommenderPatients.get_patients()
		patient_count = 0
		for patient in patients:
			patient_count = patient_count + 1
			# patient.par_notification()
			print('Par notification: Patient {}/{}'.format(patient_count, patients_total))
			RecommenderPatients.par_notification(patient)

	# @staticmethod
	# def update_db():
	#     try:
	#         response = requests.get(config.ccdr_url + "/api/v1/mobile/patient").json()
	#         for patient in response:
	#             ccdr_ref = patient["identity_management_key"]
	#             rec_patient = RecommenderPatients.get_by_ccdr_ref(ccdr_ref)
	#             if not rec_patient:
	#                 rec_patient = RecommenderPatients(ccdr_ref)
	#             rec_patient.save()
	#         return RecommenderPatients.get_all()
	#
	#     except requests.exceptions.RequestException as e:
	#         logger.error("Getting all patients from CCDR error", exc_info=True)
	#         return str(e), 0

	@staticmethod
	def scores_injection():
		# patients, total = RecommenderPatients.get_all()
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
			print("Processing patient " + patient + "....\n")
			for start_date, end_date in zip(start_dates, end_dates):
				period_count = period_count + 1
				date = [start_date, end_date]
				actionlib_response, fusionlib_response = RecommenderPatients.calculate_scores(patient, date)

				print("Completed data injection " + str(period_count) + "/" + str(
					len(start_dates)) + " for " + patient + " between " + start_date + " and " + end_date +
					" ActionLib: " + str(actionlib_response.status_code) + " FusionLib: " + str(
					fusionlib_response.status_code))

				print("ActionLib Response:\nStatus: {}\nContent: {}\n".format(
					str(actionlib_response.status_code), str(actionlib_response.content)))
				print("FusionLib Response:\nStatus: {}\nContent: {}\n".format(
					str(actionlib_response.status_code), str(actionlib_response.content)))
				print("--------------")

			print("\nInjection completed. Patient: {}/{}\n".format(str(patient_count), str(patients_total)))
			print("--------------")

		print("Data injection completed")

	@staticmethod
	def scores_injection_patient(patient, date):
		print("Processing patient " + patient + "....\n")

		actionlib_response, fusionlib_response = RecommenderPatients.calculate_scores(patient, date)

		print(actionlib_response.json())
		scores = actionlib_response.json()['scores']
		deviations = fusionlib_response.json()['deviations']

		print('Scores: {}\nDeviations: {}'.format(scores, deviations))

		return scores, deviations

	# Run both ActionLib (HBR) scores and FusionLib (MMF) deviation for specific patient and date
	@staticmethod
	def calculate_scores(patient, date):
		# today = datetime.today()
		# week_ago = today - timedelta(weeks=1)
		body = {
			"identity_management_key": str(uuid.uuid4()),
			"organization": "000",
			"role": "system",
			"scenario": "data_injection",
			"patient_identity_management_key": patient,
			"measurements_start_date": date[0],
			"measurements_end_date": date[1],
		}

		print("Request: {}\n".format(str(body)))

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

	@staticmethod
	def send(content, destination):
		notification = {
			"identity_management_key": content["identity_management_key"],  # "97902929",  # Patient
			# "receiverUniqueIdentifier": self.patient,
			"messageBody": content["messageBody"],  # self.msg,
			"messageUniqueIdentifier": content["message_unique_identifier"],  # "1234",  # self.id,
			"senderUniqueIdentifier": "recommendLib",
			"receiver_device_type": content["receiver_device_type"],  # web mobile or game
		}
		# notification = {
		#     "identity_management_key": content['identity_management_key'],  # Patient
		#     # "receiverUniqueIdentifier": self.patient,
		#     "messageBody": content['msg'],  # self.msg,
		#     "messageUniqueIdentifier": "1234",  # self.id,
		#     "senderUniqueIdentifier": "Recommender",
		#     "receiver_device_type": "web",  # web, mobile or game
		# }

		logger.debug(notification)

		headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
		if destination == 'patient':
			# TODO: post notification. Which IP and PORT?
			# http: // < IP >: 8092 / notification / sendNotifications
			notification_response = requests.post(
				config.fusionlib_url + "/notification/sendNotifications",
				data=json.dumps(notification), headers=headers
			)

			# Notifications.check_notifications_responses(notification, notification_response, destination)

			if notification_response:
				if notification_response.status_code == 200:
					print('Notification sent to {} via {}'.format(notification['identity_management_key'],
											notification['receiver_device_type']))
				elif notification_response.status_code == 1000:
					print('NOTIFICATION ERROR: Request returned general error.')
				elif notification_response.status_code == 1007:
					print('NOTIFICATION ERROR: There is no patient with the patient_identity_management_key {}'.format(
											notification['identity_management_key']))
				elif notification_response.status_code == 1060:
					print('NOTIFICATION ERROR: receiver_device_type ({}) does not match the user role'.format(
											notification['receiver_device_type']))
				elif notification_response.status_code == 1048:
					print('NOTIFICATION ERROR: notification_queue_key not found')
				else:
					print('NOTIFICATION ERROR.')
			else:
				print('No response.')
		elif destination == 'professional':
			# TODO: post notification. Which IP and PORT?
			# http: // < IP >: 8092 / notification / sendNotifications
			notification_response = requests.post(
				config.fusionlib_url + "/notification/sendNotificationToMedicalProfessionalByPatient",
				data=json.dumps(notification), headers=headers
			)

			if notification_response:
				if notification_response.status_code == 200:
					print('Notification sent to {} via {}'.format(notification['identity_management_key'],
											notification['receiver_device_type']))
				elif notification_response.status_code == 1000:
					print('NOTIFICATION ERROR: Request returned general error.')
				elif notification_response.status_code == 1007:
					print('NOTIFICATION ERROR: There is no patient with the patient_identity_management_key {}'.format(
											notification['identity_management_key']))
				elif notification_response.status_code == 1048:
					print('NOTIFICATION ERROR: notification_queue_key not found')
				else:
					print('NOTIFICATION ERROR.')
			else:
				print('No response.')

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
