import os

testing_mode = os.environ['TESTING'] if "TESTING" in os.environ else "no"

platform = "local"  # local, test, production
test_flag = True
if platform == "production":
    test_flag = False

test_references = [
    "98284945", "83288302", "38622059", "74403633", "84731590", "62664183", "92516276", "80005710", "25403788",
    "99439121"
]

if os.getenv("FLASK_HOST") is not None:
    flask_host = os.getenv("FLASK_HOST")
else:
    flask_host = "0.0.0.0"

if os.getenv("FLASK_PORT") is not None:
    flask_port = os.getenv("FLASK_PORT")
else:
    if testing_mode == "yes":
        flask_port = "5006"
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
    if testing_mode == "yes":
        postgres_host = "localhost"
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

if os.getenv("PROCARE_URL") is not None:
    procare_url = os.getenv("PROCARE_URL")
else:
    if platform == "local":
        procare_url = "http://195.82.130.203"
    else:
        if platform == "test":
            procare_url = "http://172.18.0.1"
        else:  # "production"
            procare_url = "http://172.19.0.1"

if os.getenv("CCDR_URL") is not None:
    ccdr_url = os.getenv("CCDR_URL")
else:
    ccdr_url = procare_url + ":8086"

if os.getenv("ACTIONLIB_URL") is not None:
    actionlib_url = os.getenv("ACTIONLIB_URL")
else:
    actionlib_url = procare_url + ":8090"

if os.getenv("FUSIONLIB_URL") is not None:
    fusionlib_url = os.getenv("FUSIONLIB_URL")
else:
    fusionlib_url = procare_url + ":8091"

if os.getenv("IDM_URL") is not None:
    idm_url = os.getenv("IDM_URL")
else:
    idm_url = procare_url + ":8085"

if os.getenv("RMQ_URL") is not None:
    rmq_url = os.getenv("RMQ_URL")
else:
    rmq_url = procare_url + ":8092"

if os.getenv("BACKEND_URL") is not None:
    backend_url = os.getenv("BACKEND_URL")
else:
    backend_url = procare_url + ":8081"

if os.getenv("DROP_TABLES") is not None:
    drop_tables = os.getenv("DROP_TABLES")
else:
    drop_tables = "no"
