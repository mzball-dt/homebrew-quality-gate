# Process CSV
import json, requests, os

env = "https://lzq49041.live.dynatrace.com"
token = os.getenv("hotsessiontoken")
ChangeFinishTime = 1606711764531
entity = 'SERVICE-2140EC6FA1E12D6F'
metric = 'builtin:service.response.time'

# Get the entity and key components that relate to it.
pre_change_query = f'{env}/api/v2/metrics/query?metricSelector={metric}:percentile(50)' \
                        + f'&entitySelector=type("{entity.split("-")[0]}"),entityId("{entity}")'\
                        + f'&from={ChangeFinishTime-60 * 60 * 24 * 1000}' \
                        + f'&to={ChangeFinishTime}' \
                        + f'&resolution=Inf'
pre_Change = requests.get(pre_change_query, headers={"Content-Type": "application/json","Authorization": f"Api-Token {token}"})
pre_median = json.loads(pre_Change.text)['result'][0]['data'][0]['values'][0]

post_change_query = f'{env}/api/v2/metrics/query?metricSelector={metric}:percentile(50)' \
                        + f'&entitySelector=type("{entity.split("-")[0]}"),entityId("{entity}")' \
                        + f'&from={ChangeFinishTime}' \
                        + f'&to={ChangeFinishTime+60 * 60 * 24 * 1000}' \
                        + f'&resolution=Inf'
post_Change = requests.get(post_change_query, headers={"Content-Type": "application/json","Authorization": f"Api-Token {token}"})
post_median = json.loads(post_Change.text)['result'][0]['data'][0]['values'][0]

# If there was more than a 5% increase in response time
if (pre_median-post_median < -0.05*pre_median): 
    print(f"A significant difference was detected after the change - consider investigation or change roll-back")
else: 
    print(f"No Quality impact detected after the change")