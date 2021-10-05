# import dependencies
import json
from flask import Flask


# Import project dependencies
from helper import config
from helper.utils import init_db
from models.patients import RecommenderPatients

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://' + config.postgres_user + ':' + config.postgres_pass + '@' \
                                        + config.postgres_host + ':' + config.postgres_port + '/' + config.postgres_db
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

if config.drop_tables == "yes":
    db = init_db(app, drop=True)
else:
    db = init_db(app, drop=False)


@app.route("/status/", methods=['GET'])
def status():
    return "running"


@app.route("/update/", methods=['GET'])
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


if __name__ == '__main__':
    app.run(host=config.flask_host, port=config.flask_port)
