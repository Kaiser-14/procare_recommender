import os

if os.getenv("FLASK_HOST") is not None:
    flask_host = os.getenv("FLASK_HOST")
else:
    flask_host = "0.0.0.0"

if os.getenv("FLASK_PORT") is not None:
    flask_port = os.getenv("FLASK_PORT")
else:
    flask_port = "5005"

if os.getenv("POSTGRES_USER") is not None:
    postgres_user = os.getenv("POSTGRES_USER")
else:
    postgres_user = "postgres"

if os.getenv("POSTGRES_PASS") is not None:
    postgres_pass = os.getenv("POSTGRES_PASS")
else:
    postgres_pass = "procare"

if os.getenv("POSTGRES_HOST") is not None:
    postgres_host = os.getenv("POSTGRES_HOST")
else:
    postgres_host = "db"

if os.getenv("POSTGRES_PORT") is not None:
    postgres_port = os.getenv("POSTGRES_PORT")
else:
    postgres_port = "5432"

if os.getenv("POSTGRES_DB") is not None:
    postgres_db = os.getenv("POSTGRES_DB")
else:
    postgres_db = "procare"

if os.getenv("CCDR_URL") is not None:
    ccdr_url = os.getenv("CCDR_URL")
else:
    ccdr_url = "http://195.82.130.203:8086"