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
    print(f"A significant different was detected after the change - consider investigation or change roll-back")
else: 
    print(f"No Quality impact detected after the change")

exit

import urllib.parse, csv
#
multiplier = {
    "S": 1000,
    "M": 60 * 1000,
    "H": 60 * 60 * 1000,
    "D": 60 * 60 * 24 * 1000,
    "W": 60 * 60 * 24 * 1000 * 7,
}

# entityToHealthMetrics
healthMetrics = {
    "APPLICATION": {
        "metric": "builtin:apps.web.action.percentageOfUserActionsAffectedByErrors",
        "maxDelta": 5,
    },
    "SERVICE": {"metric": "builtin:service.errors.total.rate", "maxDelta": 5},
    "PROCESS_GROUP": {"metric": "", "maxDelta": 5},
    "HOST": {"metric": "", "maxDelta": 5},
}

performanceMetrics = {
    "APPLICATION": {"metric": "builtin:apps.other.apdex.osAndGeo", "maxDelta": 5},
    "SERVICE": {"metric": "builtin:service.response.time", "maxDelta": 5},
    "PROCESS_GROUP": {"metric": "", "maxDelta": 5},
    "HOST": {"metric": "", "maxDelta": 5},
}


def parseChangeDetails(file):
    """[summary]

    Args:
        file ([type]): [description]

    Raises:
        Exception: [description]

    Returns:
        [type]: [description]
    """
    with open(file) as csvfile:
        changes = csv.DictReader(csvfile)
        # ensure the change fields all exist or throw
        requiredFields = [
            "ChangeID",
            "StartDate",
            "EndDate",
            "AffectedEntities",
            "TestPeriod",
        ]
        if len(set(requiredFields).intersection(changes.fieldnames)) != len(
            requiredFields
        ):
            raise Exception(
                f"Input file had incorrect fields - must have all and only: {requiredFields}"
            )
        return list(changes)


def createDynatraceEvent(entity, eventData):
    """[summary]

    Args:
        entity ([type]): [description]
        eventData ([type]): [description]
    """
    print(eventData)
    body = {
        "eventType": "CUSTOM_INFO",
        "start": eventData["starttime"],
        "end": eventData["endtime"],
        "timeoutMinutes": 0,
        "attachRules": {
            "entityIds": [entity],
        },
        "title": eventData["name"],
        "description": eventData["name"],
        "source": "Hot-Session-Python-Quality-Gate",
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Token {token}",
    }
    # print(headers)
    url = f"{env}/api/v1/events"
    r = requests.post(url, json=body, headers=headers)
    print(f"uri: {url}, response: {r}, resBody: {r.text}")


def createDynatraceProblem(entity, eventData):
    """[summary]

    Args:
        entity ([type]): [description]
        eventData ([type]): [description]
    """
    print(eventData)
    body = {
        "eventType": "PERFORMANCE_EVENT",
        "start": eventData["starttime"],
        "end": eventData["endtime"],
        "timeoutMinutes": 0,
        "attachRules": {
            "entityIds": [entity],
        },
        "title": eventData["name"],
        "description": eventData["name"],
        "source": "Hot-Session-Python-Quality-Gate",
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Token {token}",
    }
    url = f"{env}/api/v1/events"
    r = requests.post(url, json=body, headers=headers)
    print(f"uri: {url}, response: {r}, resBody: {r.text}")


def fetchEntityDetails(entity, start=None, end=None):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Token {token}",
    }
    url = f"{env}/api/v2/entities/{entity}"
    if start and end:
        url += f"?to={end}&from={start}"
    elif start:
        url += f"?from={start}"
    elif end:
        url += f"?to={end}"

    r = requests.get(url, headers=headers)
    print(f"uri: {url}, response: {r}, resBody: {r.text}")


def createDynatraceDashboard(dashboardDetails):
    """[summary]

    Args:
        dashboardDetails ([type]): [description]
    """
    body = {
        "metadata": {
            "configurationVersions": [3],
            "clusterVersion": "1.206.95.20201116-094826",
        },
        "dashboardMetadata": {
            "name": "QualityGate Overview",
            "shared": True,
            "sharingDetails": {"linkShared": True, "published": True},
            "dashboardFilter": {"timeframe": ""},
            "tags": [dashboardDetails["ChangeID"], "QualityGateReport"],
        },
        "tiles": [
            {
                "name": "Markdown",
                "tileType": "MARKDOWN",
                "configured": True,
                "bounds": {"top": 38, "left": 0, "width": 1102, "height": 152},
                "tileFilter": {},
                "markdown": "## This is a Markdown tile\n\nIt supports **rich text** and [links](https://dynatrace.com)",
            },
            {
                "name": "Custom chart",
                "tileType": "CUSTOM_CHARTING",
                "configured": True,
                "bounds": {"top": 228, "left": 0, "width": 532, "height": 152},
                "tileFilter": {"timeframe": "2020-11-30 20:00 to 2020-11-30 22:00"},
                "filterConfig": {
                    "type": "MIXED",
                    "customName": "Lock time",
                    "defaultName": "Custom chart",
                    "chartConfig": {
                        "legendShown": True,
                        "type": "TIMESERIES",
                        "series": [
                            {
                                "metric": "builtin:service.lockTime",
                                "aggregation": "NONE",
                                "type": "LINE",
                                "entityType": "SERVICE",
                                "dimensions": [
                                    {
                                        "id": "0",
                                        "name": "dt.entity.service",
                                        "values": [],
                                        "entityDimension": True,
                                    }
                                ],
                                "sortAscending": False,
                                "sortColumn": True,
                                "aggregationRate": "TOTAL",
                            }
                        ],
                        "resultMetadata": {},
                    },
                    "filtersPerEntityType": {
                        "SERVICE": {"SPECIFIC_ENTITIES": ["SERVICE-0759B154091378CA"]}
                    },
                },
            },
            {
                "name": "Problems",
                "tileType": "OPEN_PROBLEMS",
                "configured": True,
                "bounds": {"top": 418, "left": 0, "width": 152, "height": 152},
                "tileFilter": {"timeframe": "2020-11-30 20:00 to 2020-11-30 22:00"},
            },
            {
                "name": "Problems",
                "tileType": "OPEN_PROBLEMS",
                "configured": True,
                "bounds": {"top": 418, "left": 570, "width": 152, "height": 152},
                "tileFilter": {"timeframe": "2020-11-30 20:00 to 2020-11-30 22:00"},
            },
            {
                "name": "Custom chart",
                "tileType": "CUSTOM_CHARTING",
                "configured": True,
                "bounds": {"top": 228, "left": 570, "width": 532, "height": 152},
                "tileFilter": {"timeframe": "2020-11-30 20:00 to 2020-11-30 22:00"},
                "filterConfig": {
                    "type": "MIXED",
                    "customName": "Lock time",
                    "defaultName": "Custom chart",
                    "chartConfig": {
                        "legendShown": True,
                        "type": "TIMESERIES",
                        "series": [
                            {
                                "metric": "builtin:service.lockTime",
                                "aggregation": "NONE",
                                "type": "LINE",
                                "entityType": "SERVICE",
                                "dimensions": [
                                    {
                                        "id": "0",
                                        "name": "dt.entity.service",
                                        "values": [],
                                        "entityDimension": True,
                                    }
                                ],
                                "sortAscending": False,
                                "sortColumn": True,
                                "aggregationRate": "TOTAL",
                            }
                        ],
                        "resultMetadata": {},
                    },
                    "filtersPerEntityType": {
                        "SERVICE": {"SPECIFIC_ENTITIES": ["SERVICE-0759B154091378CA"]}
                    },
                },
            },
            {
                "name": "Quality Gate Reference Period",
                "tileType": "HEADER",
                "configured": True,
                "bounds": {"top": 190, "left": 570, "width": 304, "height": 38},
                "tileFilter": {},
            },
            {
                "name": "Quality Gate Monitored Period",
                "tileType": "HEADER",
                "configured": True,
                "bounds": {"top": 190, "left": 0, "width": 304, "height": 38},
                "tileFilter": {},
            },
        ],
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Token {token}",
    }
    url = f"{env}/api/config/v1/dashboards"
    r = requests.post(url, json=body, headers=headers)
    print(f"uri: {url}, response: {r}, resBody: {r.text}")


## NOTES
# It looks like for Services there's no process group tied to it in the v2 API?
# This makes it very hard to 'walk' the entity graph - even when I 'walk' to a SERVICE_INSTANCE

# Recieve Change data from Slack?
# - Needs web server
# - Parse json webhook out
# - cron'ing ability

# Stretch goals
# Create Dashboard

if __name__ == "__main__":
    # Grab the change details from the target file
    changes = parseChangeDetails("./singlechangeExample.csv")
    
    # Add events to the service for the qg period and change start/end times
    for change in changes:

        # process the qg period
        # make this a separate entry = no weird processing
        letter = change["TestPeriod"][-1:]  
        val = int(change["TestPeriod"][:-1])
        QualityGateLength = val * multiplier[letter]
        entityType = change["AffectedEntities"].split('-')[0]

        referencePeriodStart = int(change["StartDate"]) - QualityGateLength
        referencePeriodEnd = int(change["StartDate"])
        QualityCheckingStart = int(change["EndDate"])
        QualityCheckingEnd = int(change["EndDate"]) + QualityGateLength

        # Get the entity and key components that relate to it.
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Api-Token {token}",
        }
        url = f"{env}/api/v2/metrics/query"
        url += f"?metricSelector={urllib.parse.quote_plus(healthMetrics[entityType]['metric'])}"
        url += "&entitySelector=" + urllib.parse.quote_plus(f'type("{entityType}"),entityId("{change["AffectedEntities"]}")')
        # print(url)
        r = requests.get(url, headers=headers)
        # print(f"uri: {url}, response: {r}, resBody: {r.text}")

        # This is the bit that works with the new API
        # if the current drops against the extant or a static then problem

        

        """ Extra stuff we can ignore for simple demo
        # mark the change period
        createDynatraceEvent(
            change["AffectedEntities"],
            {
                "name": f"{change['ChangeID']} - Change Period",
                "starttime": int(change["StartDate"]),
                "endtime": int(change["EndDate"]),
            },
        )

        # mark the quality gate reference period
        createDynatraceEvent(
            change["AffectedEntities"],
            {
                "name": f"{change['ChangeID']} - Quality Gate Reference Period",
                "starttime": referencePeriodStart,
                "endtime": referencePeriodEnd,
            },
        )

        # Mark the quality gate watching period
        createDynatraceEvent(
            change["AffectedEntities"],
            {
                "name": f"{change['ChangeID']} - Quality Gate Period",
                "starttime": QualityCheckingStart,
                "endtime": QualityCheckingEnd,
            },
        )
        """
