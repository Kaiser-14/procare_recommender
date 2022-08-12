from datetime import datetime, timedelta
from random import sample

import numpy as np
import requests

from helper import config
from helper.utils import game_notifications, multimodal_notifications


# Mobile recommendations

def multimodal_evaluation(patient_reference, country_code, scores, deviations):
	"""
	This method is used to evaluate the multimodal recommendation system.

	:param patient_reference: Patient identification
	:param country_code: Patient country code
	:param scores: Data list of scores for two consecutive weeks
	:param deviations: Data list of deviations for two consecutive weeks
	:return: messages_scores: A list of messages containing deviations notifications.
	messages_deviations: A list of messages containing deviations notifications
	"""

	messages_scores = []
	messages_deviations = []

	# Scores. Extract difference between weeks
	scores_result = {key: scores[1][key] - scores[0].get(key, 0) for key in scores[1].keys()}

	# Cognitive State Score (CSS)
	if scores[1]["css"] == 0:
		# Check if the patient has not played cognitive games in the last two weeks
		body = {
			"identity_management_key": patient_reference,
			"role": "patient",
			"startDate": (datetime.now() - timedelta(days=14)).strftime("%d-%m-%Y"),
			"endDate": (datetime.now() - timedelta(days=1)).strftime("%d-%m-%Y")
		}

		summarization_list = requests.post(config.ccdr_url + "/api/v1/game/getSummarizationList", json=body)
		cognitive_played = [True for session in summarization_list.json() if not session["session_info"]]
		cognitive_played = True if any(cognitive_played) else False

		if cognitive_played:  # Patient did not perform well
			messages_scores.append(multimodal_notifications['CSS_11'][country_code])
		else:  # Patient might not be playing any games in the last two weeks
			messages_scores.append(multimodal_notifications['CSS_12'][country_code])
	if scores_result["css"] < 0:
		msg1 = multimodal_notifications['CSS_21'][country_code]  # Patient is not playing well
		msg2 = multimodal_notifications['CSS_22'][country_code]  # Suggest to decrease the level
		# Select a random message between ms1 and msg2
		messages_scores.append(sample([msg1, msg2], 1)[0])
	else:
		msg1 = multimodal_notifications['CSS_31'][country_code]  # Patient is doing great
		msg2 = multimodal_notifications['CSS_32'][country_code]  # Suggest to increase level
		# Select a random message between ms1 and msg2
		messages_scores.append(sample([msg1, msg2], 1)[0])

	# Medication Intake Score (MIS)
	if scores[1]["mis"] == 0:
		# Check prescribed medicine
		body = {
			"identity_management_key": patient_reference,
		}

		prescription_list = requests.post(config.ccdr_url + "/api/v1/mobile/prescription/list/", json=body)

		if prescription_list:
			messages_scores.append(multimodal_notifications['MIS_11'][country_code])  # Patient did not register medicine
	if scores_result["mis"] < 0:
		messages_scores.append(multimodal_notifications['MIS_21'][country_code])  # Register the medicine
	else:
		messages_scores.append(multimodal_notifications['MIS_31'][country_code])  # Continue daily medicine intake

	# Motor Functions Score (MFS)
	if scores[1]["mfs"] == 1:
		messages_scores.append(multimodal_notifications['MFS_11'][country_code])  # No symptoms detected
	if scores_result["mfs"] < 0:
		messages_scores.append(multimodal_notifications['MFS_21'][country_code])  # Contact doctor to get feedback
	else:
		messages_scores.append(multimodal_notifications['MFS_31'][country_code])  # Improving motor functions

	# Physical Activity Score (PAS)
	if scores[1]["pas"] == 0:
		messages_scores.append(multimodal_notifications['PAS_11'][country_code])  # No activity detected
	if scores_result["pas"] < 0:
		messages_scores.append(multimodal_notifications['PAS_21'][country_code])  # Encourage to be physically active
	else:
		messages_scores.append(multimodal_notifications['PAS_31'][country_code])  # Physical activity are improving

	# Sleep Score (SS)
	if scores[1]["ss"] == 0:
		messages_scores.append(multimodal_notifications['SS_11'][country_code])  # No sleep detected, wear the wristband
	if scores_result["ss"] < 0:
		messages_scores.append(multimodal_notifications['SS_21'][country_code])  # Encourage to sleep
	else:
		messages_scores.append(multimodal_notifications['SS_31'][country_code])  # Sleep score is improving

	# Deviations
	# Alarm by type of alert (key) if probability is greater than 0.5
	alert_list = []
	[alert_list.append(key) for key, value in deviations[1].items() if value > 0.5]

	category_dict = {
		"amf": "Abnormalities in Motor Functions", "dca": "Decline in Cognitive Abilities",
		"dpa": "Decline in Physical Activities", "sd": "Sleep Disorders", "ovd": "Overall Deviation"}

	today = datetime.today()
	start_date = today - timedelta(days=14)
	end_date = today - timedelta(days=1)

	# Extract username and email from patient_reference
	body = {
		"identity_management_key": patient_reference
	}
	patient_information = requests.post(config.idm_url + "/findUserByIdentityKey", json=body).json()
	username = patient_information["username"]

	for category in alert_list:
		messages_deviations.append(multimodal_notifications["D_1"][country_code].format(
			username, patient_reference, start_date.strftime("%d/%m/%Y"), end_date.strftime("%d/%m/%Y"),
			"{:.3f}".format(deviations[1][category]), category_dict[category]))

	# Sample three random messages from the list of scores messages
	# messages_scores = sample(messages_scores, 3)

	return messages_scores, messages_deviations


# Game recommendations

def game_evaluation(patient_reference, country_code):
	"""
	Evaluate data for specific patient based on weekly game data.

	:param country_code: Country code of the patient
	:param patient_reference: Reference to identify patient.
	:return: A list of messages containing a notifications for game.
	"""

	messages = []
	messages_tier2 = []
	messages_tier3 = []

	body = {
		"identity_management_key": patient_reference,
		"role": "patient",
		"startDate": (datetime.now() - timedelta(days=6)).strftime("%d-%m-%Y"),
		"endDate": datetime.now().strftime("%d-%m-%Y")
	}

	summarization_list = requests.post(config.ccdr_url + "/api/v1/game/getSummarizationList", json=body)

	game_summarization = {
		"days_played": 0,
		"games": {
			"global": [],  # Games completed
			"specific": {  # Games played per day
				"1": [], "2": [], "3": [], "4": [], "5": [], "6": [], "7": [],
			},
			"type": {  # Games played per type of game
				"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0
			},
		},
		"stats": {
			"started": {  # Games started
				"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0
			},
			"restarted": {  # Games restarted
				"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0
			},
			"categories": {
				"global": [],  # Total list of categories
				"specific": {  # List of categories per day
					"1": [], "2": [], "3": [], "4": [], "5": [], "6": [], "7": [],
				},
				"type": {  # Categories played per game
					"1": [], "5": [], "6": [],
				}
			},
			"level": {
				"global": [],  # Total list of levels
				"specific": {  # List of levels per day
					"1": [], "2": [], "3": [], "4": [], "5": [], "6": [], "7": []
				},
				"type": {  # Level played per game
					"1": [], "5": [], "6": [],
				}
			},
			"time_between_clicks": [],  # List of times per game
		},
		"personalization": {  # Total list
			"language": [], "style": [], "textsize": [],
		},
		"metrics": {
			"total": {  # Total metrics per session
				"global": [], "score": [], "time": [], "interaction": []
			},
			"type": {  # Metrics per game
				"global": {"1": [], "2": [], "3": [], "4": [], "5": [], "6": []},
				"score": {"1": [], "2": [], "3": [], "4": [], "5": [], "6": []},
				"time": {"1": [], "2": [], "3": [], "4": [], "5": [], "6": []},
				"interaction": {"1": [], "2": [], "3": [], "4": [], "5": [], "6": []},
			}
		}
	}

	date = None
	day = 0

	# Loop over general list, being one item per day. Assign data based on parameters obtained.
	for summarization_day in summarization_list.json():
		# Filter duplicate dates
		if date != summarization_day["date"]:
			day += 1
			date = summarization_day["date"]
			if summarization_day["session_info"]:
				game_summarization["days_played"] += 1

		# Days not played are returned as None in session_info
		if summarization_day["session_info"]:
			# Loop through every session of the day and save the games played
			for session in summarization_day["session_info"]:
				game_summarization["games"]["global"].append(session["id"][-1:])
				game_summarization["games"]["specific"][str(day)].append(session["id"][-1:])
				game_summarization["games"]["type"][session["id"][-1:]] += 1

				game_summarization["stats"]["categories"]["global"].append(session["category"])
				if session["category"]:
					game_summarization["stats"]["categories"]["specific"][str(day)].append(session["category"])
					game_summarization["stats"]["categories"]["type"][session["id"][-1:]].append(session["category"])

				game_summarization["stats"]["level"]["global"].append(session["level"])
				if session["level"]:
					game_summarization["stats"]["level"]["specific"][str(day)].append(session["level"])
					game_summarization["stats"]["level"]["type"][session["id"][-1:]].append(session["level"])

				game_summarization["personalization"]["language"].append(session["app_language"])
				game_summarization["personalization"]["style"].append(session["app_style"])
				game_summarization["personalization"]["textsize"].append(session["app_textsize"])

				game_summarization["metrics"]["total"]["global"].append(session["metric_global"])
				game_summarization["metrics"]["total"]["score"].append(session["metric_score"])
				game_summarization["metrics"]["total"]["time"].append(session["metric_time"])
				game_summarization["metrics"]["total"]["interaction"].append(session["metric_interaction"])

				game_summarization["metrics"]["type"]["global"][session["id"][-1:]].append(session["metric_global"])
				game_summarization["metrics"]["type"]["score"][session["id"][-1:]].append(session["metric_score"])
				game_summarization["metrics"]["type"]["time"][session["id"][-1:]].append(session["metric_time"])
				game_summarization["metrics"]["type"]["interaction"][session["id"][-1:]].append(
					session["metric_interaction"])

				game_summarization["stats"]["time_between_clicks"].append(session["avg_time_between_clicks"])

			game_summarization["stats"]["started"][str(day)] += summarization_day["session_interaction_results"][
				"nclicks_game_start"]
			game_summarization["stats"]["restarted"][str(day)] += summarization_day["session_interaction_results"][
				"nclicks_game_restart"]

	# Summarize mean stats
	global_mean = []
	score_mean = []
	time_mean = []
	interaction_mean = []
	for game in range(6):
		if game_summarization["metrics"]["type"]["global"][str(game + 1)]:
			global_mean.append(np.mean(game_summarization["metrics"]["type"]["global"][str(game + 1)]))
			score_mean.append(np.mean(game_summarization["metrics"]["type"]["score"][str(game + 1)]))
			time_mean.append(np.mean(game_summarization["metrics"]["type"]["time"][str(game + 1)]))
			interaction_mean.append(np.mean(game_summarization["metrics"]["type"]["interaction"][str(game + 1)]))
		else:
			global_mean.append(None)
			score_mean.append(None)
			time_mean.append(None)
			interaction_mean.append(None)

	# Recommendation 1.1
	# Use frequently cognitive game app
	if game_summarization["days_played"] < 3 and not game_summarization["days_played"] == 0:
		messages.append(game_notifications['R11'][country_code])

	# Recommendation 1.2
	# Play slowly
	# If by average, any click value is lower than 5 seconds
	avg_clicks_values_lower = [value for value in game_summarization["stats"]["time_between_clicks"] if value < 5]

	# Check if len of appended values are more than 30% of the games completed and send notification if metrics are low
	games_notification = []
	if game_summarization["days_played"] > 0:
		if len(avg_clicks_values_lower) / len(game_summarization["stats"]["time_between_clicks"]) < 0.3:
			for idx, game_mean in enumerate(global_mean):
				if game_mean and game_mean < 0.5:
					games_notification.append(idx + 1)
		if games_notification:
			games_notification = ",".join([str(item) for item in games_notification])
			messages.append(game_notifications['R12'][country_code].format(str(games_notification)))

	# Recommendation 1.3
	# Complete the games
	if game_summarization["days_played"] > 0:
		if len(game_summarization["games"]["global"]) < sum(game_summarization["stats"]["started"].values()) / 2:
			messages.append(game_notifications['R13'][country_code])

	# Recommendation 1.4
	# Start a different game. Check the games played and compare with the whole list of 6 games
	if game_summarization["days_played"] > 0:
		unique, counts = np.unique(game_summarization["games"]["global"], return_counts=True)
		list_diff = np.setdiff1d(["1", "2", "3", "4", "5", "6"], list(unique))
		if len(list_diff) > 0:
			messages.append(game_notifications['R14'][country_code])

	# Recommendation 2.1
	# Change game category
	game_categories = []
	if game_summarization["days_played"] > 0:
		for game in ["1", "5", "6"]:
			unique, counts = np.unique(game_summarization["stats"]["categories"]["type"][game], return_counts=True)
			if game == "1":
				if 0 < len(unique) < 4:
					game_categories.append(game)
			else:
				if 0 < len(unique) < 3:
					game_categories.append(game)

		if game_categories:
			game_categories = ",".join([str(item) for item in game_categories])
			messages_tier2.append(game_notifications['R21'][country_code].format(game_categories))

	# Recommendation 2.2 / 2.3
	# Change game level
	if game_summarization["days_played"] > 0:
		game_levels_pos = []
		game_levels_neg = []
		for game in ["1", "5", "6"]:
			unique, counts = np.unique(game_summarization["stats"]["level"]["type"][game], return_counts=True)
			if 0 < len(unique) == 1:
				if game_summarization["metrics"]["type"]["global"][game]:
					if np.mean(game_summarization["metrics"]["type"]["global"][game]) > 0.5:
						game_levels_pos.append(game)
					else:
						game_levels_neg.append(game)

		if game_levels_pos:
			game_levels_pos = ",".join([str(item) for item in game_levels_pos])
			messages_tier2.append(game_notifications['R22'][country_code].format(game_levels_pos))
		if game_levels_neg:
			game_levels_neg = ",".join([str(item) for item in game_levels_neg])
			messages_tier2.append(game_notifications['R23'][country_code].format(game_levels_neg))

	# Recommendation 2.4
	# Read carefully game information
	# Get games with values less than 0.5
	if game_summarization["days_played"] > 0:
		for param in [global_mean, score_mean, time_mean, interaction_mean]:
			values = [value for value in param if value if value < 0.5]

			if values:
				messages_tier2.append(game_notifications['R24'][country_code])
				break

	# Recommendation 3.1
	# Customize the app
	if game_summarization["days_played"] > 0:
		for key in game_summarization["personalization"]:
			uniques = np.unique(game_summarization["personalization"][key])

			if not len(uniques) > 1:
				messages_tier3.append(game_notifications['R31'][country_code])

	# Recommendation 3.2 / 3.3 / 3.4
	# Extract mean global metric and send notification based on results
	if game_summarization["metrics"]["total"]["global"]:
		mean_score_global = np.nanmean(np.array(game_summarization["metrics"]["total"]["global"], dtype=np.float64))
		if mean_score_global > 0.8:
			messages_tier3.append(game_notifications['R32'][country_code])
		elif 0.5 < mean_score_global < 0.8:
			messages_tier3.append(game_notifications['R33'][country_code])
		else:
			messages_tier3.append(game_notifications['R34'][country_code])

	# Select randomly a message if there are more than two notifications, sorting by priority
	if len(messages) < 2:
		if messages_tier2:
			try:
				msg_sample = sample(messages_tier2, 2 - len(messages))
				messages.extend(msg_sample)
			except ValueError:
				messages.extend(messages_tier2)
		if len(messages) < 2 and messages_tier3:
			try:
				msg_sample = sample(messages_tier3, 2 - len(messages))
				messages.extend(msg_sample)
			except ValueError:
				messages.extend(messages_tier3)

	return messages
