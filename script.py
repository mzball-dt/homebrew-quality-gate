# Process CSV
import csv,requests,os

env = 'https://lzq49041.live.dynatrace.com'
token = os.getenv('hostsessiontoken')

# 
multiplier = {
    'S': 1000,
    'M': 60*1000,
    'H': 60*60*1000,
    'D': 60*60*24*1000,
    'W': 60*60*24*1000*7,
}

# entityToHealthMetrics
healthMetrics = {
    'APPLICATION': '',
    'SERVICE': '',
    'PROCESS_GROUP': '',
    'HOST': '',
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
        if len(set(requiredFields).intersection(changes.fieldnames)) != len(requiredFields):
            raise Exception(
                f"Input file had incorrect fields - must have all and only: {requiredFields}"
            )
        return list(changes)


def createDynatraceEvent(entity,eventData):
    """[summary]

    Args:
        entity ([type]): [description]
        eventData ([type]): [description]
    """    
    print(eventData)
    body = {
        "eventType": "CUSTOM_INFO",
        "start": eventData['starttime'],
        "end": eventData['endtime'],
        "timeoutMinutes": 0,
        "attachRules": {
            "entityIds": [
                entity
            ],
        },
        "title": eventData['name'],
        "description": eventData['name'],
        "source": "Hot-Session-Python-Quality-Gate"
    }
    headers = { 
        'Content-Type' : 'application/json', 
        'Authorization' : f"Api-Token {token}"
    }
    url = f"{env}/api/v1/events"
    r = requests.post(url, json=body, headers=headers)
    print(f"uri: {url}, response: {r}, resBody: {r.text}")


def createDynatraceProblem(entity,eventData):
    """[summary]

    Args:
        entity ([type]): [description]
        eventData ([type]): [description]
    """    
    print(eventData)
    body = {
        "eventType": "PERFORMANCE_EVENT",
        "start": eventData['starttime'],
        "end": eventData['endtime'],
        "timeoutMinutes": 0,
        "attachRules": {
            "entityIds": [
                entity
            ],
        },
        "title": eventData['name'],
        "description": eventData['name'],
        "source": "Hot-Session-Python-Quality-Gate"
    }
    headers = { 
        'Content-Type' : 'application/json', 
        'Authorization' : f"Api-Token {token}"
    }
    url = f"{env}/api/v1/events"
    r = requests.post(url, json=body, headers=headers)
    print(f"uri: {url}, response: {r}, resBody: {r.text}")


def createDynatraceDashboard(dashboardDetails):
    """[summary]

    Args:
        dashboardDetails ([type]): [description]
    """    
    body = {
            "metadata": {
                "configurationVersions": [3],
                "clusterVersion": "1.206.95.20201116-094826"
            },
            "dashboardMetadata": {
                "name": "QualityGate Overview",
                "shared": True,
                "sharingDetails": {
                    "linkShared": True,
                    "published": True
                },
                "dashboardFilter": {
                    "timeframe": ""
                },
                "tags": [dashboardDetails["ChangeID"], "QualityGateReport"]
            },
            "tiles": [{
                "name": "Markdown",
                "tileType": "MARKDOWN",
                "configured": True,
                "bounds": {
                    "top": 38,
                    "left": 0,
                    "width": 1102,
                    "height": 152
                },
                "tileFilter": {},
                "markdown": "## This is a Markdown tile\n\nIt supports **rich text** and [links](https://dynatrace.com)"
            }, {
                "name": "Custom chart",
                "tileType": "CUSTOM_CHARTING",
                "configured": True,
                "bounds": {
                    "top": 228,
                    "left": 0,
                    "width": 532,
                    "height": 152
                },
                "tileFilter": {
                    "timeframe": "2020-11-30 20:00 to 2020-11-30 22:00"
                },
                "filterConfig": {
                    "type": "MIXED",
                    "customName": "Lock time",
                    "defaultName": "Custom chart",
                    "chartConfig": {
                        "legendShown": True,
                        "type": "TIMESERIES",
                        "series": [{
                            "metric": "builtin:service.lockTime",
                            "aggregation": "NONE",
                            "type": "LINE",
                            "entityType": "SERVICE",
                            "dimensions": [{
                                "id": "0",
                                "name": "dt.entity.service",
                                "values": [],
                                "entityDimension": True
                            }],
                            "sortAscending": False,
                            "sortColumn": True,
                            "aggregationRate": "TOTAL"
                        }],
                        "resultMetadata": {}
                    },
                    "filtersPerEntityType": {
                        "SERVICE": {
                            "SPECIFIC_ENTITIES": ["SERVICE-0759B154091378CA"]
                        }
                    }
                }
            }, {
                "name": "Problems",
                "tileType": "OPEN_PROBLEMS",
                "configured": True,
                "bounds": {
                    "top": 418,
                    "left": 0,
                    "width": 152,
                    "height": 152
                },
                "tileFilter": {
                    "timeframe": "2020-11-30 20:00 to 2020-11-30 22:00"
                }
            }, {
                "name": "Problems",
                "tileType": "OPEN_PROBLEMS",
                "configured": True,
                "bounds": {
                    "top": 418,
                    "left": 570,
                    "width": 152,
                    "height": 152
                },
                "tileFilter": {
                    "timeframe": "2020-11-30 20:00 to 2020-11-30 22:00"
                }
            }, {
                "name": "Custom chart",
                "tileType": "CUSTOM_CHARTING",
                "configured": True,
                "bounds": {
                    "top": 228,
                    "left": 570,
                    "width": 532,
                    "height": 152
                },
                "tileFilter": {
                    "timeframe": "2020-11-30 20:00 to 2020-11-30 22:00"
                },
                "filterConfig": {
                    "type": "MIXED",
                    "customName": "Lock time",
                    "defaultName": "Custom chart",
                    "chartConfig": {
                        "legendShown": True,
                        "type": "TIMESERIES",
                        "series": [{
                            "metric": "builtin:service.lockTime",
                            "aggregation": "NONE",
                            "type": "LINE",
                            "entityType": "SERVICE",
                            "dimensions": [{
                                "id": "0",
                                "name": "dt.entity.service",
                                "values": [],
                                "entityDimension": True
                            }],
                            "sortAscending": False,
                            "sortColumn": True,
                            "aggregationRate": "TOTAL"
                        }],
                        "resultMetadata": {}
                    },
                    "filtersPerEntityType": {
                        "SERVICE": {
                            "SPECIFIC_ENTITIES": ["SERVICE-0759B154091378CA"]
                        }
                    }
                }
            }, {
                "name": "Quality Gate Reference Period",
                "tileType": "HEADER",
                "configured": True,
                "bounds": {
                    "top": 190,
                    "left": 570,
                    "width": 304,
                    "height": 38
                },
                "tileFilter": {}
            }, {
                "name": "Quality Gate Monitored Period",
                "tileType": "HEADER",
                "configured": True,
                "bounds": {
                    "top": 190,
                    "left": 0,
                    "width": 304,
                    "height": 38
                },
                "tileFilter": {}
            }]
        }
    headers = { 
        'Content-Type' : 'application/json', 
        'Authorization' : f"Api-Token {token}"
    }
    url = f"{env}/api/config/v1/dashboards"
    r = requests.post(url, json=body, headers=headers)
    print(f"uri: {url}, response: {r}, resBody: {r.text}")


if __name__ == "__main__":
    # Grab the change details from the target file
    changes = parseChangeDetails("./singlechangeExample.csv")

    # Add events to the service for the qg period and change start/end times
    for change in changes:

        # process the qg period
        letter = change['TestPeriod'][-1:]
        val = int(change['TestPeriod'][:-1])
        QualityGateLength = val*multiplier[letter]

        # mark the change period
        createDynatraceEvent(change['AffectedEntities'], {
            'name': f"{change['ChangeID']} - Change Period",
            'starttime': int(change['StartDate']),
            'endtime': int(change['EndDate']),
        })

        # mark the quality gate reference period
        createDynatraceEvent(change['AffectedEntities'], {
            'name': f"{change['ChangeID']} - Quality Gate Reference Period",
            'starttime': int(change['StartDate'])-QualityGateLength,
            'endtime': int(change['StartDate']),
        })

        # Mark the quality gate watching period
        createDynatraceEvent(change['AffectedEntities'], {
            'name': f"{change['ChangeID']} - Quality Gate Period",
            'starttime': int(change['EndDate']),
            'endtime': int(change['EndDate'])+QualityGateLength,
        })

    # Get the entity and key components that relate to it.
    # This is the bit that works with the new API
    # if the current drops against the extant or a static then problem

    # Stretch goals
    # Create Dashboard
