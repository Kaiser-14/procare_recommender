# ProCare4Life Recommender

## Description
Personalized recommendation and interaction system, which supports users through notification techniques to adopt healthy habits, maintain a good daily routine and follow the prescribed actions by the professionals for maintaining and improving their health condition,

Recommendation takes the outcomes from all the data processing components of the solution and defines a number of notifications or recommendations for the patients, depending on a decision-making process on the data collected and the predicted health condition of the patient and its evolution.  These are triggered from the human activity recognition component, the cognitive games, or the multimodal fusion engine. They have been implemented mainly around the areas of Physical Activity Recommendations and Cognitive Skills Recommendations.

## Installation
### Clone the repository
```bash
git clone https://github.com/Kaiser-14/procare_recommender.git
cd /procare_recommender/
```

### Setup virtual environment (skip to install locally)
[Linux/Mac]
```bash
python -m venv venv
source /venv/bin/activate
```

[Windows]
```bash
\venv\Scripts\activate
```

### Install dependencies
```bash
pip install -r requirements.txt
```

## Setup
Recommender is prepared to be used in a Docker container. In case to try local version, you will need to deploy and change database instances information.

### Locally
```python
python app.py
```
### Docker
```bash
docker-compose -p procare up --build -d
```

## Usage

### Recommender Status
`GET /status`

    curl -i -X GET -H 'Content-Type: application/json' http://localhost:5005/status

#### Success Response

    HTTP/1.0 200 OK
    Content-Type: text/html; charset=utf-8
    Server: Werkzeug/2.0.3 Python/3.8.12
    Date: Fri, 12 Aug 2022 10:40:43 GMT

    Running
    
#### Example
* **Python**

    ```python
    requests.get('http://localhost:5005/status', headers={'Content-type': 'application/json'})
    ```
  
### Update patient database
`GET /recommender/update_patient_db`

    curl -i -X GET -H 'Content-Type: application/json' http://localhost:5005/recommender/update_patient_db

#### Success Response

    HTTP/1.0 200 OK
    Content-Type: text/html; charset=utf-8
    Server: Werkzeug/2.0.3 Python/3.8.12
    Date: Fri, 12 Aug 2022 10:40:43 GMT

    {
        "rec_patients": [
            {
                  "ccdr_reference": "38969583",
                  "par_day": 2
                },
                {
                  "ccdr_reference": "95230435",
                  "par_day": 2
            }
        ]
    }
    
#### Example
* **Python**

    ```python
    requests.get('http://localhost:5005/recommender/update_patient_db', headers={'Content-type': 'application/json'})


### Update patient par day
`POST /recommender/update_par_day`

    curl -i -X POST -H 'Content-Type: application/json' http://localhost:5005/recommender/update_par_day -d '{"ccdr_reference": "98284945", "par_day": 2}'

#### Body
    
    {
        "patient_identity_management_key": "98284945",
        "par_day": 2
    }

#### Success Response

    HTTP/1.0 200 OK
    Content-Type: text/html; charset=utf-8
    Server: Werkzeug/2.0.3 Python/3.8.12
    Date: Fri, 12 Aug 2022 10:40:43 GMT

    {
      "patient_identity_management_key": "98284945",
      "par_day": 7
    }
    
#### Example
* **Python**

    ```python
    data = {'patient_identity_management_key': '98284945', 'par_day': 2}  
    requests.post('http://localhost:5005/recommender/update_par_day', data=data, headers={'Content-type': 'application/json'})
  

### Reset total database par day
`GET /recommender/update_par_day_total`

    curl -i -X GET -H 'Content-Type: application/json' http://localhost:5005/recommender/update_par_day_total

#### Success Response

    HTTP/1.0 200 OK
    Content-Type: text/html; charset=utf-8
    Server: Werkzeug/2.0.3 Python/3.8.12
    Date: Fri, 12 Aug 2022 10:40:43 GMT

    {
      "total": 240
    }
    
#### Example
* **Python**

    ```python
    requests.get('http://localhost:5005/recommender/update_par_day_total', headers={'Content-type': 'application/json'})
  

### Par notification
`GET /notification/daily_par`

    curl -i -X GET -H 'Content-Type: application/json' http://localhost:5005/notification/daily_par

#### Success Response

    HTTP/1.0 200 OK
    Content-Type: text/html; charset=utf-8
    Server: Werkzeug/2.0.3 Python/3.8.12
    Date: Fri, 12 Aug 2022 10:40:43 GMT

    {
      "patients": 240
    }
    
#### Example
* **Python**

    ```python
    requests.get('http://localhost:5005/notification/daily_par', headers={'Content-type': 'application/json'})
  

### Game notifications
`GET /notification/game_notifications`

    curl -i -X GET -H 'Content-Type: application/json' http://localhost:5005/notification/game_notifications

#### Success Response

    HTTP/1.0 200 OK
    Content-Type: text/html; charset=utf-8
    Server: Werkzeug/2.0.3 Python/3.8.12
    Date: Fri, 12 Aug 2022 10:40:43 GMT

    {
      "patients": 240
    }
    
#### Example
* **Python**

    ```python
    requests.get('http://localhost:5005/notification/game_notifications', headers={'Content-type': 'application/json'})
  

### IPAQ reminder
`GET /notification/daily_check_ipaq`

    curl -i -X GET -H 'Content-Type: application/json' http://localhost:5005/notification/daily_check_ipaq

#### Success Response

    HTTP/1.0 200 OK
    Content-Type: text/html; charset=utf-8
    Server: Werkzeug/2.0.3 Python/3.8.12
    Date: Fri, 12 Aug 2022 10:40:43 GMT

    {
      "patients": 20
    }
    
#### Example
* **Python**

    ```python
    requests.get('http://localhost:5005/notification/daily_check_ipaq', headers={'Content-type': 'application/json'})
  

### Goals notifications
`GET /`

    curl -i -X GET -H 'Content-Type: application/json' http://localhost:5005/notification/weekly_goals

#### Success Response

    HTTP/1.0 200 OK
    Content-Type: text/html; charset=utf-8
    Server: Werkzeug/2.0.3 Python/3.8.12
    Date: Fri, 12 Aug 2022 10:40:43 GMT

    {
      "patients": 240
    }
    
#### Example
* **Python**

    ```python
    requests.get('http://localhost:5005/notification/weekly_goals', headers={'Content-type': 'application/json'})
  

### Multimodal notifications
`GET /notification/scores_injection`

    curl -i -X GET -H 'Content-Type: application/json' http://localhost:5005/notification/scores_injection

#### Success Response

    HTTP/1.0 200 OK
    Content-Type: text/html; charset=utf-8
    Server: Werkzeug/2.0.3 Python/3.8.12
    Date: Fri, 12 Aug 2022 10:40:43 GMT

    {
      "patients": 240
    }
    
#### Example
* **Python**

    ```python
    requests.get('http://localhost:5005/notification/scores_injection', headers={'Content-type': 'application/json'})
 
 
### Hydration notifications
`GET /notification/hydration`

    curl -i -X GET -H 'Content-Type: application/json' http://localhost:5005/notification/hydration

#### Success Response

    HTTP/1.0 200 OK
    Content-Type: text/html; charset=utf-8
    Server: Werkzeug/2.0.3 Python/3.8.12
    Date: Fri, 12 Aug 2022 10:40:43 GMT

    {
      "patients": 240
    }
    
#### Example
* **Python**

    ```python
    requests.get('http://localhost:5005/notification/hydration', headers={'Content-type': 'application/json'})
  
### Read status notifications
`POST /notification/readStatus`

    curl -i -X POST -H 'Content-Type: application/json' http://localhost:5005/notification/readStatus -d '{"messageId": "ea3066d8-7301-4d43-bf8b-83f60872e742"}'

#### Body

    {
      "messageId": "ea3066d8-7301-4d43-bf8b-83f60872e742"
    }

#### Success Response

    HTTP/1.0 200 OK
    Content-Type: text/html; charset=utf-8
    Server: Werkzeug/2.0.3 Python/3.8.12
    Date: Fri, 12 Aug 2022 10:40:43 GMT

    {
      "status": "OK",
      "statusCode": 0
    }
    
#### Error Response
* **Code:** 1010 CONFLICT <br />
**Content:** `Field can’t be null.`

#### Example
* **Python**

    ```python
    requests.post('http://localhost:5005/notification/readStatus', headers={'Content-type': 'application/json'})
  
### Get patient notifications
`POST /notification/getNotifications`

    curl -i -X POST -H 'Content-Type: application/json' http://localhost:5005/notification/getNotifications -d '{"patient_identity_management_key": "98284945", "organization_code":"007", "date_start":"22/04/2022", "date_end":"30/05/2022"}'

#### Body
    {
      "patient_identity_management_key": "98284945",
      "organization_code": "007",
      "date_start": "22/04/2022",
      "date_end": "30/05/2022"
    }

#### Success Response

    HTTP/1.0 200 OK
    Content-Type: text/html; charset=utf-8
    Server: Werkzeug/2.0.3 Python/3.8.12
    Date: Fri, 12 Aug 2022 10:40:43 GMT

    [
      {
        "message": "Benefits of regular and consequences of insufficient physical activity: Regular physical activity improves your heart and respiratory performance.",
        "date_sent": "25-04-2022 07:45:22",
        "date_read": null,
        "isReadStatus": false,
        "user": "98284945"
      },
      {
        "message": "Benefits of regular and consequences of insufficient physical activity: Insufficient physical activity is one of the indirect leading factors for death worldwide.",
        "date_sent": "25-04-2022 07:45:40",
        "date_read": null,
        "isReadStatus": false,
        "user": "98284945"
      }
    ]

#### Error Response
* **Code:** 1000 <br />
**Content:** `Error occurred.`
* **Code:** 1010 <br />
**Content:** `Field can’t be null.`
* **Code:** 1007 <br />
**Content:** `User doesn’t exist.`

#### Example
* **Python**

    ```python
    requests.post('http://localhost:5005/notification/getNotifications', headers={'Content-type': 'application/json'})

## License
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
