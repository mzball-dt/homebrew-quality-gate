# Process CSV
import json, requests, os
import urllib.parse, csv

env = "https://lzq49041.live.dynatrace.com"
token = os.getenv("hotsessiontoken")

# Conversion for time periods
multiplier = {
    "S": 1000,
    "M": 60 * 1000,
    "H": 60 * 60 * 1000,
    "D": 60 * 60 * 24 * 1000,
    "W": 60 * 60 * 24 * 1000 * 7,
}

# Metric's we'll use to check the impact/quality after the change
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
    """Parses the contents of a csv file into the expected fields

    Args:
        file (string): the path to a csv file with the required headers

    Raises:
        Exception: If the csvfile does not contain the headers required

    Returns:
        list(dict): a list of dicts that represents each line of the input csv file
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
    """Create a Dynatrace Event on the entity using information in eventData

    Args:
        entity (string): A Dynatrace Entity Type <ENTITY-TYPE>-<IDENTIFIER>
        eventData (dict): 
            name: string
            starttime: number
            endtime: number

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
    # print(f"uri: {url}, response: {r}, resBody: {r.text}")


def createDynatraceProblem(entity, eventData):
    """ Create 

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
        letter,val = change["TestPeriod"][-1:],int(change["TestPeriod"][:-1])
        QualityGateLength = val * multiplier[letter]
        entityType = change["AffectedEntities"].split('-')[0]

        referencePeriodStart = int(change["StartDate"]) - QualityGateLength
        referencePeriodEnd = int(change["StartDate"])
        QualityCheckingStart = int(change["EndDate"])
        QualityCheckingEnd = int(change["EndDate"]) + QualityGateLength

        headers = { "Content-Type": "application/json", "Authorization": f"Api-Token {token}" }
        reference_period_query = f"{env}/api/v2/metrics/query" \
                + f"?metricSelector={urllib.parse.quote_plus(healthMetrics[entityType]['metric'])}" \
                + "&entitySelector=" + urllib.parse.quote_plus(f'type("{entityType}"),entityId("{change["AffectedEntities"]}")') \
                + f'&from={referencePeriodStart}' \
                + f'&to={referencePeriodEnd}' \
                + f'&resolution=Inf'
        reference_result = requests.get(reference_period_query, headers=headers)
        print(f"uri: {reference_period_query}, response: {reference_result}, resBody: {reference_result.text}")

        quality_checking_query = f"{env}/api/v2/metrics/query" \
                + f"?metricSelector={urllib.parse.quote_plus(healthMetrics[entityType]['metric'])}" \
                + "&entitySelector=" + urllib.parse.quote_plus(f'type("{entityType}"),entityId("{change["AffectedEntities"]}")') \
                + f'&from={QualityCheckingStart}' \
                + f'&to={QualityCheckingEnd}' \
                + f'&resolution=Inf'
        quality_checking_result = requests.get(quality_checking_query, headers=headers)
        print(f"uri: {quality_checking_query}, response: {quality_checking_result}, resBody: {quality_checking_result.text}")

        # Use the 
        # If there was more than a 5% increase in response time
        if (pre_median-post_median < -0.05*pre_median):
            print(f"A significant difference was detected after the change - consider investigation or change roll-back")
        else: 
            print(f"No Quality impact detected after the change")

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
