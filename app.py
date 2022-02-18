# import dependencies
import json
import os
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler

# Import project dependencies
from helper import config
from helper.utils import init_db
from models.patients import RecommenderPatients, Notifications, db
from helper.utils import logger

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://' + config.postgres_user + ':' + config.postgres_pass + '@' \
										+ config.postgres_host + ':' + config.postgres_port + '/' + config.postgres_db
logger.debug(app.config['SQLALCHEMY_DATABASE_URI'])

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# if config.drop_tables == "yes":
#     logger.debug("init drop = True")
#     init_db(db, app, drop=True)
# else:
#     logger.debug("init drop = False")
#     init_db(db, app, drop=False)


@app.route("/status", methods=['GET'])
def status():
	return "Running"

# Recommender calls

# @app.route("/recommender/update_patient_db/", methods=['GET'])
# def update():
#     response = {
#         "rec_patients": [],
#         "total": None
#     }
#     patients, total = RecommenderPatients.update_db()
#     if total:
#         response["total"] = total
#     if patients:
#         for patient in patients:
#             response["rec_patients"].append(patient.get_dict())
#     return json.dumps(response, indent=3)


@app.route("/recommender/get_notifications_of_patient", methods=['GET'])
def get_notifications_of_patient():
	notifications = []
	ref = request.args["ref"]
	if ref:
		patient = RecommenderPatients.get_by_ccdr_ref(ref)
		if patient:
			for notification in patient.get_notifications():
				notifications.append(notification.get_dict())
			return str(notifications)
		else:
			return "Reference not found", 404
	else:
		return "Reference needed", 400


scheduler = BackgroundScheduler()
# with app.app_context():
#     logger.info("First database update")
#     update()


@scheduler.scheduled_job('cron', id='scores_injection', day='*', hour='12', minute='12')
@app.route("/recommender/scores_injection", methods=['GET'])
def schedule_scores_injection():
	RecommenderPatients.scores_injection()
	return 'Scores injected'


@app.route("/recommender/create_recommendation", methods=['POST'])
def create_recommendation():
	data = request.get_json()

	patient = data.get('identity_management_key')
	date = [data.get('start_date')[0], data.get('end_date')[0]]

	par_notification = RecommenderPatients.recommendation(patient, date)

	return 'Notification sent for patient {}: {}'.format(patient, par_notification)


# TODO: Enable when deploying
# @scheduler.scheduled_job('cron', id='update_and_par', day='*', hour='12', minute='13')
@app.route("/notification/daily_par", methods=['GET'])
def daily_par():
	logger.info("Running daily PAR round")

	RecommenderPatients.par_notifications_round()
	return "Finished."


# Notifications calls

# Send notifications to a user
@app.route("/notification/send_notifications_patient", methods=['POST'])
def notification_send():
	# TODO: This notification should be sent by own recommender? I mean, the recommender based on scores, should define
	# the message body which corresponds to par notifications. ID patient is retrieved from get_patients, but
	# msg unique identifier and receiver device type? Should it be PAR notification? But which device type?
	# We could remove form here de par notifications part as it will be part of the POST
	content = request.get_json()

	# Get par notifications
	script_dir = os.path.dirname(__file__)  # <-- absolute dir the script is in
	rel_path = "./par/par_notifications.json"
	abs_file_path = os.path.join(script_dir, rel_path)

	with open(abs_file_path) as json_file:
		par_notifications = json.load(json_file)

	# TODO: Properly select par notification
	msg = list(par_notifications.values())[1]

	destination = 'patient'

	logger.info('Notification: {}'.format(msg))
	Notifications.send(msg, destination)

	return 'Notification sent:\n{}'.format(msg)


# Send notifications to a medical professional by patient
# TODO: Should it be the same as the internal? Remember, device type receiver always must be web
@app.route("/notification/send_notifications_professional", methods=['POST'])
def notification_send_professional():
	msg = request.get_json()

	destination = 'professional'

	logger.info('Notification: {}'.format(msg))
	Notifications.send(msg, destination)

	return 'OK'


# Send to the backend the unique identifier of the notification message when the user reads the notification
@app.route("/notification/readStatus", methods=['POST'])
def notification_read():
	content = request.get_json()
	ref = content.get("messageUniqueIdentifier")
	if ref:
		notification = Notifications.get_by_id(ref)
		if notification:
			notification.read = True
			notification.save()
			return {
				"status": "OK",
				"statusCode": 0
			}
		else:
			return {
				"status": "Reference not found",
				"statusCode": 2
			}
	else:
		return {
			"status": "Bad request",
			"statusCode": 1
		}


# HTTP request about IPAQ analysis
# TODO: To be tested once deployed
@app.route("/notification/activity_level", methods=['POST'])
def notification_par():
	data = request.get_json()
	patient = data.get("identity_management_key")

	response = RecommenderPatients.par_notification(patient)

	return 'Patient: {}. PA notification: {}.'.format(patient, response.status_code)


# This method is used to receive all the notification that have been sent to the patients in a specific organization,
# as well as the read status of these notifications.
@app.route("/notification/getNotifications", methods=['POST'])
def get_notifications():
	data = request.get_json()

	organization = data.get('organization_code')
	date_start = data.get('date_start')
	date_end = data.get('date_end')
	date = [date_start, date_end]

	# TODO: We need token auth per patient and define function
	# request = None
	notifications = Notifications.retrieve_notifications(organization, date)

	if organization:
		return request
	else:
		return {
			"status": "ERR",
			"statusCode": 1000
		}

	# return 'Not yet implemented'


scheduler.start()

if __name__ == '__main__':
	app.run(host=config.flask_host, port=config.flask_port)
