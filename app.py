# import dependencies
import json
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

if config.drop_tables == "yes":
	logger.debug("init drop = True")
	init_db(db, app, drop=True)
else:
	logger.debug("init drop = False")
	init_db(db, app, drop=False)


@app.route("/status", methods=['GET'])
def status():
	return "Running"


# Recommender calls
@app.route("/recommender/update_patient_db", methods=['GET'])
def update():
	response = {
		"rec_patients": [],
		"total": None
	}
	patients, total = RecommenderPatients.update_db()
	if total:
		response["total"] = total
	if patients:
		for patient in patients:
			response["rec_patients"].append(patient.get_dict())
	return json.dumps(response, indent=3)


scheduler = BackgroundScheduler()
with app.app_context():
	logger.info("First database update")
	update()


@scheduler.scheduled_job('cron', id='scores_injection', day='*', hour='12', minute='12')
@app.route("/recommender/scores_injection", methods=['GET'])
def schedule_scores_injection():
	RecommenderPatients.scores_injection()
	return 'Scores injected'


@app.route("/recommender/create_recommendation", methods=['POST'])
def create_recommendation():
	data = request.get_json()

	patient_reference = data.get('identity_management_key')
	date = [data.get('start_date')[0], data.get('end_date')[0]]

	patient = RecommenderPatients.get_by_ccdr_ref(patient_reference)
	par_notification = patient.recommendation(date)

	return 'Notification sent for patient {}: {}'.format(patient_reference, par_notification)


# Notifications calls

# Daily notification par
@scheduler.scheduled_job('cron', id='update_and_par', day='*', hour='12', minute='13')
@app.route("/notification/daily_par", methods=['GET'])
def daily_par():
	logger.info("Running daily PAR round")
	with app.app_context():
		update()
		RecommenderPatients.notifications_round(receiver="mobile")

	return "Finished."


@scheduler.scheduled_job('cron', id='game_notifications', day='*', hour='19', minute='15')
@app.route("/notification/game_notifications", methods=['GET'])
def game_notifications():
	logger.info("Running daily game round")
	with app.app_context():
		update()
		RecommenderPatients.notifications_round(receiver="game")

	return "Finished."


# Check weekly IPAQ questionnaire filled
@scheduler.scheduled_job('cron', id='weekly_check_ipaq', day='1', hour='18', minute='05')
@app.route("/notification/weekly_check_ipaq", methods=['GET'])
def weekly_check_ipaq():
	logger.info("Checking weekly IPAQ notifications")
	Notifications.check_ipaq()

	return "Finished weekly IPAQ checks"


# Send to the backend the unique identifier of the notification message when the user reads the notification
@app.route("/notification/readStatus", methods=['POST'])
def notification_read():
	content = request.get_json()
	notification_id = content.get("messageId")

	if notification_id:
		return Notifications.check_notification_status(notification_id)
	else:
		return {
			"status": "Bad request",
			"statusCode": 1
		}


# This method is used to receive all the notification that have been sent to a patient in a specific organization,
# as well as the read status of these notifications.
@app.route("/notification/getNotifications", methods=['POST'])
def get_notifications():
	data = request.get_json()

	patient_reference = data.get("patient_identity_management_key")
	organization = data.get("organization_code")
	date_start = data.get("date_start")
	date_end = data.get("date_end")

	notifications = []

	if patient_reference:
		patient = RecommenderPatients.get_by_ccdr_ref(patient_reference)
		if patient:
			for notification in patient.get_notifications():
				dates = [notification.datetime_sent, date_start, date_end]
				notification_range = Notifications.check_timestamp(dates)
				if notification_range:
					notification_dict = notification.get_dict()
					body = {
						"message": notification_dict["msg"],
						"date": notification_dict["datetime_sent"],
						"isReadStatus": notification_dict["read"],
						"user": patient_reference
					}
					notifications.append(body)
			return str(notifications), 200
		else:
			return "Patient not found", 404
	else:
		return {
			"status": "ERR",
			"statusCode": 1000
		}


scheduler.start()

if __name__ == '__main__':
	app.run(host=config.flask_host, port=config.flask_port)
