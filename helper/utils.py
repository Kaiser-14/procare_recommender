import json
import logging
import os
import shutil
import time

import colorlog

from helper.config import testing_mode


def check_directory_expired_date(total_time=3600, app_logs_dir="app_logs"):
	try:

		# If not exists
		if not os.path.exists(app_logs_dir):
			print('Create New APP Logs Folder')
			os.makedirs(app_logs_dir)
		else:
			# if exists check the date
			prev_date = os.path.getmtime(app_logs_dir)
			current_date = time.time()

			# Date has expired
			if int(current_date - prev_date) >= total_time:
				print('Update APP Logs folder')
				try:
					# Delete directory and create it again
					shutil.rmtree(app_logs_dir)
					os.makedirs(app_logs_dir)
				except Exception as e:
					print(e)
	except Exception as e:
		print(e)


def init_logger(dunder_name, testing_logger) -> logging.Logger:

	log_format = (
		'%(asctime)s - '
		'%(name)s - '
		'%(funcName)s - '
		'%(levelname)s - '
		'%(message)s'
	)
	bold_seq = '\033[1m'
	colorlog_format = (
		f'{bold_seq} '
		'%(log_color)s '
		f'{log_format}'
	)
	colorlog.basicConfig(format=colorlog_format)
	logger = logging.getLogger(dunder_name)

	if testing_logger:
		logger.setLevel(logging.DEBUG)
	else:
		logger.setLevel(logging.INFO)

	# Logs directory
	parent_dir = os.getenv('GLOBAL_PARENT_DIR')
	if parent_dir is not None:
		app_logs_dir = os.path.join(parent_dir, "app_logs")
	else:
		app_logs_dir = os.path.join("", "app_logs")

	# Output full log
	check_directory_expired_date(app_logs_dir=app_logs_dir)
	log_path = os.path.join(app_logs_dir, "app.log")
	fh = logging.FileHandler(log_path)
	fh.setLevel(logging.DEBUG)
	formatter = logging.Formatter(log_format)
	fh.setFormatter(formatter)
	logger.addHandler(fh)

	# Output warning log
	log_path_w = os.path.join(app_logs_dir, "app.warning.log")
	fh = logging.FileHandler(log_path_w)
	fh.setLevel(logging.WARNING)
	formatter = logging.Formatter(log_format)
	fh.setFormatter(formatter)
	logger.addHandler(fh)

	# Output error log
	log_path_e = os.path.join(app_logs_dir, "app.error.log")
	fh = logging.FileHandler(log_path_e)
	fh.setLevel(logging.ERROR)
	formatter = logging.Formatter(log_format)
	fh.setFormatter(formatter)
	logger.addHandler(fh)
	return logger


def init_db(_db, app, drop=False):
	_db.init_app(app)
	with app.app_context():
		if drop:
			_db.drop_all()
		# Service.__table__.drop()
		_db.create_all()
	return _db


if testing_mode == "yes":
	logger = init_logger(__name__, testing_logger=True)
else:
	logger = init_logger(__name__, testing_logger=False)

# Par notifications
script_dir = os.path.dirname(__file__)  # <-- absolute dir the script is in

rel_path_par = "../par/par_notifications.json"
abs_file_path_par = os.path.join(script_dir, rel_path_par)

rel_path_ieq = "../par/ieq_notifications.json"
abs_file_path_ieq = os.path.join(script_dir, rel_path_ieq)

rel_path_ieq = "../par/ipaq_notifications.json"
abs_file_path_ipaq = os.path.join(script_dir, rel_path_ieq)

rel_path_ieq = "../par/game_notifications.json"
abs_file_path_game = os.path.join(script_dir, rel_path_ieq)

rel_path_ieq = "../par/motivational_notifications.json"
abs_file_path_motivational = os.path.join(script_dir, rel_path_ieq)

with open(abs_file_path_par, encoding='utf-8') as json_file:
	par_notifications = json.load(json_file)
with open(abs_file_path_ieq, encoding='utf-8') as json_file:
	ieq_notifications = json.load(json_file)
with open(abs_file_path_ipaq, encoding='utf-8') as json_file:
	ipaq_notifications = json.load(json_file)
with open(abs_file_path_game, encoding='utf-8') as json_file:
	game_notifications = json.load(json_file)
with open(abs_file_path_motivational, encoding='utf-8') as json_file:
	motivational_notifications = json.load(json_file)
