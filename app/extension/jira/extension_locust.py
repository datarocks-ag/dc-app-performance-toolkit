import random
import re
from locustio.common_utils import init_logger, jira_measure, raise_if_login_failed, fetch_by_re
from locustio.jira.requests_params import Login, BrowseIssue, CreateIssue, SearchJql, ViewBoard, BrowseBoards, \
    BrowseProjects, AddComment, ViewDashboard, EditIssue, ViewProjectSummary, jira_datasets

logger = init_logger(app_type='jira')
jira_dataset = jira_datasets()

BASE_PATH='/rest/quantum/1.0/'

def search_estimated_resource(estimated_resources, resource_id):
    for keyval in estimated_resources:
        if resource_id == keyval['resourceId']:
            return keyval
    return None

def get_quick_estimation_order(estimation_orders):
    for keyval in estimation_orders:
        if keyval['estimationOrderType'] == 'USER_ESTIMATION_ORDER' and keyval['isUserAllowedToEstimate'] == True:
            return keyval
    return None

@jira_measure
def app_specific_action(locust):
    raise_if_login_failed(locust)
    params = BrowseIssue()
    issue_key =  random.choice(jira_dataset['issues'])[0]

    r = locust.get(f'/browse/{issue_key}', catch_response=True)
    content = r.content.decode('utf-8')
    issue_id = fetch_by_re(params.issue_id_pattern, content)


    r = locust.get(BASE_PATH + f'estimation-panel/estimated-issue/{issue_id}', catch_response=True)
    response_json= r.json()
    if response_json['isEstimationExisting'] == False:
        r = locust.put(BASE_PATH + f'estimation/', catch_response=True, json= {"issueId": issue_id})
        r = locust.get(BASE_PATH + f'estimation-panel/estimated-issue/{issue_id}', catch_response=True)
        response_json= r.json()

    assert response_json['isEstimationExisting'] == True
    
    estimation_id = response_json['estimationId']
    r = locust.get(BASE_PATH + f'estimation/{estimation_id}', catch_response=True)
    response_json= r.json()
    
    estimation_state = response_json['estimationState']

    if estimation_state == 'DISABLED':
        locust.patch(BASE_PATH + f'estimation/{estimation_id}', catch_response=True, json={"targetEstimationState": "QUICK_ESTIMATING"})
    elif estimation_state == 'ESTIMATION_DESIGN':
        locust.patch(BASE_PATH + f'estimation/{estimation_id}', catch_response=True, json={"targetEstimationState": "QUICK_ESTIMATING"})
    elif estimation_state == 'ESTIMATING':
        locust.patch(BASE_PATH + f'estimation/{estimation_id}', catch_response=True, json={"targetEstimationState": "REPLAN"})
        locust.patch(BASE_PATH + f'estimation/{estimation_id}', catch_response=True, json={"targetEstimationState": "QUICK_ESTIMATING"})
    elif estimation_state == 'FAILED':
        locust.patch(BASE_PATH + f'estimation/{estimation_id}', catch_response=True, json={"targetEstimationState": "REPLAN"})
        locust.patch(BASE_PATH + f'estimation/{estimation_id}', catch_response=True, json={"targetEstimationState": "QUICK_ESTIMATING"})
    elif estimation_state == 'ESTIMATED':
        locust.patch(BASE_PATH + f'estimation/{estimation_id}', catch_response=True, json={"targetEstimationState": "QUICK_ESTIMATING"})
    elif estimation_state == 'REPLAN':
        locust.patch(BASE_PATH + f'estimation/{estimation_id}', catch_response=True, json={"targetEstimationState": "QUICK_ESTIMATING"})

        
    r = locust.get(BASE_PATH + f'estimation/{estimation_id}', catch_response=True)
    response_json = r.json()

    assert response_json['estimationState'] == 'QUICK_ESTIMATING'

    r = locust.get(BASE_PATH + f'estimation-panel/active-resources/{issue_id}', catch_response=True)
    response_json = r.json()

    assert len(response_json)>0

    resource_id = response_json[0]['resourceId']

    r = locust.get(BASE_PATH + f'estimation/{estimation_id}/estimated-resource', catch_response=True)
    response_json = r.json()
    
    estimated_resource = search_estimated_resource(response_json, resource_id)

    if estimated_resource == None:
        locust.post(BASE_PATH + f'estimation/{estimation_id}/estimated_resource', catch_response=True, json={'resourceId': resource_id})
        r = locust.get(BASE_PATH + f'estimation/{estimation_id}/estimated-resource', catch_response=True)
        response_json = r.json()
        estimated_resource = search_estimated_resource(response_json, resource_id)

    assert estimated_resource != None

    estimated_resource_id = estimated_resource['estimatedResourceId']

    r = locust.post(BASE_PATH + f'estimation-panel/estimation/{estimation_id}/estimated-resource/{estimated_resource_id}/create-quick-estimation-order', catch_response=True)

    r = locust.get(BASE_PATH + f'estimation-panel/estimation/{estimation_id}/estimated-resource/{estimated_resource_id}/estimation-order', catch_response=True)
    response_json = r.json()

    quick_estimation_order = get_quick_estimation_order(response_json)

    assert quick_estimation_order != None

    estimation_order_id = quick_estimation_order['estimationOrderId']

    value_set = {'pointEstimateValueSet': {'value': '10'}}

    locust.post(BASE_PATH + f'estimation/{estimation_id}/estimated-resource/{estimated_resource_id}/estimation-order/{estimation_order_id}/estimate', catch_response=True, json=value_set)
