# Process CSV
import json, requests, os
import urllib.parse, csv

env = os.getenv("hotsession_environment") 
env = "https://lzq49041.live.dynatrace.com" # remove this for final
token = os.getenv("hotsession_token")

# Conversion for time periods into milliseconds
timewindow_to_ms_lookup = {
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
        "maxPercentDiff": 5,
    },
    "SERVICE": {"metric": "builtin:service.errors.total.rate", "maxPercentDiff": 5},
    "PROCESS_GROUP": {"metric": "", "maxPercentDiff": 5},
    "HOST": {"metric": "", "maxPercentDiff": 5},
}

performanceMetrics = {
    "APPLICATION": {"metric": "builtin:apps.other.apdex.osAndGeo", "maxPercentDiff": -5},
    "SERVICE": {"metric": "builtin:service.response.time", "maxPercentDiff": 5},
    "PROCESS_GROUP": {"metric": "", "maxPercentDiff": 5},
    "HOST": {"metric": "", "maxPercentDiff": 5},
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
        "description": eventData["description"],
        "source": "Hot-Session-Python-Quality-Gate",
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Token {token}",
    }
    url = f"{env}/api/v1/events"
    r = requests.post(url, json=body, headers=headers)
    print(f"uri: {url}, response: {r}, resBody: {r.text}")

if __name__ == "__main__":
    # Grab the change details from the target file
    changes = parseChangeDetails("./singlechangeExample.csv")
    
    # Loop through each of the changes that have been provided via the csv file
    for change in changes:
        """
        A Change looks like this: 
        |<-------Reference Period--------->|<---Change Window--->|<-------Quality Checking Period-------->|

        We will create a Problem if during the quality checking period, the performance or 
            health drops below what was recorded in the the Reference Period
        Both the reference period and the quality checking periods will be the same length

        For each change we will: 
            1. Determine the length of the windows we're using
            2. Determine the type of entity that the change is affecting
            3. Determine the reference and quality windows based on when the change started and finished
            4. Query the health of the affected entity using the calculated windows
            5. Raise a problem if there was a problematic difference
        """
        print(f"Processing Change: {change['ChangeID']}")

        # How long will the gating windows be? - Transform '22H' (example) into a letter and value
        letter,val = change["TestPeriod"][-1:], int(change["TestPeriod"][:-1])
        window_length = val * timewindow_to_ms_lookup[letter]
        
        # Get the entityType from the change entity
        entityType = change["AffectedEntities"].split('-')[0]

        # Calculate the Reference and QualityGate windows
        referencePeriodStart = int(change["StartDate"]) - window_length
        referencePeriodEnd = int(change["StartDate"])
        QualityGateStart = int(change["EndDate"])
        QualityGateEnd = int(change["EndDate"]) + window_length

        # Make a headers object for our queries
        headers = { "Content-Type": "application/json", "Authorization": f"Api-Token {token}" }

        # Query Dynatrace for the Metric median during the Reference and QualityGate windows
        reference_period_query = f"{env}/api/v2/metrics/query" \
                + f"?metricSelector={urllib.parse.quote_plus(healthMetrics[entityType]['metric'] + ':avg')}" \
                + "&entitySelector=" + urllib.parse.quote_plus(f'type("{entityType}"),entityId("{change["AffectedEntities"]}")') \
                + f'&from={referencePeriodStart}' \
                + f'&to={referencePeriodEnd}' \
                + f'&resolution=Inf'
        reference_response = requests.get(reference_period_query, headers=headers)
        reference_value = json.loads(reference_response.text)['result'][0]['data'][0]['values'][0]
        print(f"uri: {reference_period_query}, response: {reference_response}, resBody: {reference_response.text}")

        quality_checking_query = f"{env}/api/v2/metrics/query" \
                + f"?metricSelector={urllib.parse.quote_plus(healthMetrics[entityType]['metric'] + ':avg')}" \
                + "&entitySelector=" + urllib.parse.quote_plus(f'type("{entityType}"),entityId("{change["AffectedEntities"]}")') \
                + f'&from={QualityGateStart}' \
                + f'&to={QualityGateEnd}' \
                + f'&resolution=Inf'
        quality_checking_response = requests.get(quality_checking_query, headers=headers)
        quality_checking_value = json.loads(quality_checking_response.text)['result'][0]['data'][0]['values'][0]
        print(f"uri: {quality_checking_query}, response: {quality_checking_response}, resBody: {quality_checking_response.text}")

        # Determine if the Quality Gate should be triggered
        valueDifference = reference_value-quality_checking_value
        maxDifferenceFromReferencePeriod = healthMetrics[entityType]['maxPercentDiff']/100*reference_value
        
        # If the value diff is larger than the allowable amount
        print(f"Comparing Reference: {reference_value} with Quality Gate Period: {quality_checking_value}")
        if (valueDifference > maxDifferenceFromReferencePeriod):
            print(f"A significant difference was detected after the change - raising a performance problem against the affected entities")
            createDynatraceProblem(change["AffectedEntities"], {
                "name": f"Broken Quality Gate for Change: '{change['ChangeID']}'",
                "description": f"The performance of {entityType} for {healthMetrics[entityType]['metric']} dropped by {difference}.\n \
                    The acceptable difference for a {entityType} entity is less than {healthMetrics[entityType]['delta']}%",
                "startime": QualityGateStart,
                "endtime": QualityGateEnd,
            })
        else: 
            print(f"No Quality impact detected after the change")
