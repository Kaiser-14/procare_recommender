# import dependencies
from flask import Flask
# from flask_sqlalchemy import SQLAlchemy
import requests

# Import project dependencies
from helper import config


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://' + config.postgres_user + ':' + config.postgres_pass + '@'\
                                        + config.postgres_host + ':' + config.postgres_port + '/' + config.postgres_db


@app.route("/get_patients/", methods=['GET'])
def index():
    return requests.get(config.ccdr_url+"/api/v1/mobile/patient")


if __name__ == '__main__':
    app.run(host=config.flask_host, port=config.flask_port)
