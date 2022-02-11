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

# if config.drop_tables == "yes":
#     logger.debug("init drop = True")
#     init_db(db, app, drop=True)
# else:
#     logger.debug("init drop = False")
#     init_db(db, app, drop=False)


@app.route("/status/", methods=['GET'])
def status():
    return "Running"


@app.route("/notification/readStatus/", methods=['POST'])
def notification_read():
    content = request.get_json()
    ref = content.get("messageUniqueIdentifier")
    if ref:
        notification = Notifications.get_by_id(ref)
        if notification:
            notification.read = True
            notification.save()
            return {"status": "OK",
                    "statusCode": 0
                    }
        else:
            return {"status": "Reference not found",
                    "statusCode": 2
                    }
    else:
        return {"status": "Bad request",
                "statusCode": 1
                }


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


@app.route("/recommender/get_notifications_of_patient/", methods=['GET'])
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
@app.route("/recommender/scores_injection/", methods=['GET'])
def schedule_scores_injection():
    RecommenderPatients.scores_injection()
    return 'Scores injected'


@scheduler.scheduled_job('cron', id='update_and_par', day='*', hour='12', minute='13')
def update_and_par():
    logger.info("Running daily scheduled database update and PAR round")
    with app.app_context():
        update()
        RecommenderPatients.par_notifications_round()


scheduler.start()

if __name__ == '__main__':
    app.run(host=config.flask_host, port=config.flask_port)
