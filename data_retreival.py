import requests
import pandas as pd

# GET Incidents data using REST API and save it in incidents_data variable.

url = 'https://api.pagerduty.com/incidents'
headers = {
    'Accept': 'application/json',
    'Authorization': 'Token token=u+Bi6nF2sMs6fvdTgxhg',
    'Content-Type': 'application/json'
}
params = {
    'date_range': 'all',
    'limit': 100,  # Adjust the limit as needed
    'total': True,
    'offset': 0,
    'include[]':'body'
}

response = requests.get(url, headers=headers, params=params)

incidents_data = []

if response.status_code == 200:
    data = response.json()
    total_incidents = data.get('total', 0)

    while params['offset'] < total_incidents:
        incidents = data.get('incidents', [])

        for incident in incidents:

            incident_id = incident.get('id')
            summary = incident.get('summary')
            incident_number = incident.get('incident_number')
            title = incident.get('title')
            created_at = incident.get('created_at')
            updated_at = incident.get('updated_at')
            status = incident.get('status')
            service_data = incident.get('service', {})
            service_name = service_data.get('summary', 'Service Data Unavailable')
            body_details = {}
            body = incident.get('body')
            if body:
                body_details = body.get('details', {})

            incident_info = {
                'incident_number': incident_number,
                'incident_id': incident_id,
                'title': title,
                'summary': summary,
                'details': body_details, 
                'status': status,
                'service': service_name,
                'created_at': created_at,
                'updated_at': updated_at,
            }

            incidents_data.append(incident_info)

        params['offset'] += len(incidents)
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
        else:
            print("Error:", response.status_code)
            print(response.text)
            break
else:
    print("Error:", response.status_code)
    print(response.text)

# Convert incidents_data into a DataFrame
df = pd.DataFrame(incidents_data)

# Display the info of DataFrame
df.info()

# Store DataFrame as CSV
df.to_csv('data/incidents_data.csv', index=False)
