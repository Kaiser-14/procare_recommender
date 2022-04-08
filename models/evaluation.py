import requests

import numpy as np
from datetime import datetime, timedelta

from helper.utils import logger
from helper import config


# Mobile recommendations

# Game recommendations

def game_evaluation(patient_reference):
	"""
	Evaluate data for specific patient based on weekly game data.

	:param patient_reference: Reference to identify patient.
	:return: A list of messages containing a list of notifications for game.
	"""

	messages = []

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
			"started": [],  # Games started
			"restarted": [],  # Games restarted
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

	# Loop over general list, being one item per day. Assign data based on parameters obtained.
	for day, summarization_day in enumerate(summarization_list.json()):
		# Days not played are returned as None in session_info
		if summarization_day["session_info"]:
			game_summarization["days_played"] += 1

			# Loop through every session of the day and save the games played
			for session in summarization_day["session_info"]:
				# print(session)
				game_summarization["games"]["global"].append(session["id"][-1:])
				game_summarization["games"]["specific"][str(day+1)].append(session["id"][-1:])
				game_summarization["games"]["type"][session["id"][-1:]] += 1

				game_summarization["stats"]["categories"]["global"].append(session["category"])
				if session["category"]:
					game_summarization["stats"]["categories"]["specific"][str(day+1)].append(session["category"])
					game_summarization["stats"]["categories"]["type"][session["id"][-1:]].append(session["category"])

				game_summarization["stats"]["level"]["global"].append(session["level"])
				if session["level"]:
					game_summarization["stats"]["level"]["specific"][str(day+1)].append(session["level"])
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

			game_summarization["stats"]["started"].append(
				summarization_day["session_interaction_results"]["nclicks_game_start"])
			game_summarization["stats"]["restarted"].append(
				summarization_day["session_interaction_results"]["nclicks_game_restart"])

		else:
			game_summarization["stats"]["started"].append(0)
			game_summarization["stats"]["restarted"].append(0)

	# Recommendation 1:
	# Use frequently cognitive game app
	if game_summarization["days_played"] < 3:
		messages.append("Use the cognitive game app more frequently.")

	# Recommendation 2:
	# Start a different game. Check the games played and compare with the whole list of 6 games
	unique, counts = np.unique(game_summarization["games"]["global"], return_counts=True)
	list_diff = np.setdiff1d(["1", "2", "3", "4", "5", "6"], list(unique))
	if len(list_diff) > 0:
		messages.append("Start a different game.")

	# Recommendation 3:
	# Customize the app
	for key in game_summarization["personalization"]:
		uniques = np.unique(game_summarization["personalization"][key])

		if not len(uniques) > 1:
			messages.append("You can customize the app in the settings (language, style and text size).")

	# Recommendation 4:
	# Change game category
	game_categories = []
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
		messages.append("Change game categories for games {}.".format(game_categories))

	# Recommendation 5:
	# Change game level
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
		messages.append("Increase the level for game {}.".format(game_levels_pos))
	if game_levels_neg:
		game_levels_neg = ",".join([str(item) for item in game_levels_neg])
		messages.append(
			"Remember that you can decrease the level for games. Test it on game {}.".format(game_levels_neg))

	# Recommendation 6:
	# Read carefully game information
	global_mean = []
	score_mean = []
	time_mean = []
	interaction_mean = []
	for game in range(6):
		if game_summarization["metrics"]["type"]["global"][str(game + 1)]:
			global_mean.append(np.mean(game_summarization["metrics"]["type"]["global"][str(game+1)]))
			score_mean.append(np.mean(game_summarization["metrics"]["type"]["score"][str(game+1)]))
			time_mean.append(np.mean(game_summarization["metrics"]["type"]["time"][str(game+1)]))
			interaction_mean.append(np.mean(game_summarization["metrics"]["type"]["interaction"][str(game+1)]))
		else:
			global_mean.append(None)
			score_mean.append(None)
			time_mean.append(None)
			interaction_mean.append(None)

	# Get games with values less than 0.5
	for param in [global_mean, score_mean, time_mean, interaction_mean]:
		values = [value for value in param if value if value < 0.5]

		if values:
			messages.append("Read game information carefully before playing.")
			break

	# Recommendation 7:
	# Complete the games
	if len(game_summarization["games"]["global"]) < sum(game_summarization["stats"]["started"]) / 2:
		messages.append("Complete the games.")

	# Recommendation 8
	# Play slowly
	# If by average, any click value is lower than 5 seconds
	avg_clicks_values_lower = [value for value in game_summarization["stats"]["time_between_clicks"] if value < 5]

	# Check if len of appended values are more than 30% of the games completed and send notification if metrics are low
	games_notification = []
	if len(avg_clicks_values_lower) / len(game_summarization["stats"]["time_between_clicks"]) < 0.3:
		for idx, game_mean in enumerate(global_mean):
			if game_mean and game_mean < 0.5:
				games_notification.append(idx + 1)
	if games_notification:
		games_notification = ",".join([str(item) for item in games_notification])
		messages.append("Play games {} more slowly and accurately.".format(str(games_notification)))

	# Recommendation 9:
	# Extract mean global metric and send notification based on results
	if game_summarization["metrics"]["total"]["global"]:
		mean_score_global = np.nanmean(np.array(game_summarization["metrics"]["total"]["global"], dtype=np.float64))
		if mean_score_global > 0.8:
			messages.append("You are doing great!")
		elif 0.5 < mean_score_global < 0.8:
			messages.append("Keep it up. You're doing it right.")
		else:
			messages.append("Keep trying to improve your results.")

	return messages
