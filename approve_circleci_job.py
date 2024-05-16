#!/usr/bin/env python3
import json
import os
import urllib.request
import time
import argparse


def request_url(url, token, method="GET"):
    request = urllib.request.Request(url, method=method)
    request.add_header("Circle-Token", token)
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(e, body)
        raise e


def fetch_all_items(fetch_func, token, *args):
    items = []
    next_page_token = ""

    while True:
        results = fetch_func(token, *args, next_page_token)
        items.extend(results["items"])

        if not results.get("next_page_token"):
            break
        next_page_token = results["next_page_token"]

    return items


def get_jobs(token, workflow_id, next_page_token=""):
    url = f"https://circleci.com/api/v2/workflow/{workflow_id}/job?page_token={next_page_token}"
    return request_url(url, token)


def get_workflow(token, workflow_id, next_page_token=""):
    url = f"https://circleci.com/api/v2/workflow/{workflow_id}/?page_token={next_page_token}"
    return request_url(url, token)


def get_pipeline_workflows(token, pipeline_id, next_page_token=""):
    url = f"https://circleci.com/api/v2/pipeline/{pipeline_id}/workflow?page_token={next_page_token}"
    return request_url(url, token)


def approve_job(token, workflow_id, approval_request_id):
    url = f"https://circleci.com/api/v2/workflow/{workflow_id}/approve/{approval_request_id}"
    return request_url(url, token, "POST")


def main(token, repo_owner, repo_name, workflow_id, workflow_name, job):
    print("Fetching workflow info...")
    current_workflow = get_workflow(token, workflow_id)
    print(
        f"Current workflow name {current_workflow['name']}, workflow_id: {workflow_id}. Requested workflow name: {workflow_name}"
    )
    print(
        f"Running in pipeline_id: {current_workflow['pipeline_id']}, pipeline number: {current_workflow['pipeline_number']}"
    )
    print("Fetching workflows...")
    latest_job = None
    latest_workflow = None
    for workflow in fetch_all_items(
        get_pipeline_workflows, token, current_workflow["pipeline_id"]
    ):
        target_workflow_name = (
            workflow_name if workflow_name else current_workflow["name"]
        )

        if workflow["name"] != target_workflow_name:
            continue
        for job_item in fetch_all_items(get_jobs, token, workflow["id"]):
            if job_item["name"] != job:
                continue
            print(
                f"Found job in workflow {workflow['id']}, started at {job_item['started_at']}"
            )
            if latest_job is None or job_item["started_at"] > latest_job["started_at"]:
                latest_job = job_item
                latest_workflow = workflow

    if latest_job:
        print(f"Latest job: {latest_job}")
        approval_request_id = latest_job.get("approval_request_id")
        if not approval_request_id:
            print("Job is not waiting for an approval")
            exit(1)
        else:
            max_retries = 12
            delay = 5
            print(
                f"Approving job {latest_job['name']} in a workflow: {latest_workflow['name']} ({latest_workflow['id']})"
            )
            for attempt in range(max_retries):
                try:
                    print(
                        f"Attempt {attempt + 1} of {max_retries} to approve job in workflow: {latest_workflow['id']}"
                    )
                    approve_result = approve_job(
                        token, latest_workflow["id"], approval_request_id
                    )
                    print("Approval successful:", approve_result)
                    break
                except Exception as e:
                    print(f"Attempt {attempt + 1} failed with error: {e}")
                    if attempt + 1 == max_retries:
                        print("All retry attempts failed. Exiting.")
                        raise
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
            return
    print(f"No jobs found with name {job}")
    exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CircleCI Job Approver")
    parser.add_argument(
        "--token",
        help="CircleCI API token",
        required=False,
        default=os.environ["CIRCLECI_API_TOKEN"],
    )
    parser.add_argument(
        "--repo_owner",
        required=False,
        help="Repository owner",
        default=os.getenv("CIRCLE_PROJECT_USERNAME"),
    )
    parser.add_argument(
        "--repo_name",
        required=False,
        help="Repository name",
        default=os.getenv("CIRCLE_PROJECT_REPONAME"),
    )
    parser.add_argument(
        "--workflow_id",
        required=False,
        help="Workflow ID",
        default=os.getenv("CIRCLE_WORKFLOW_ID"),
    )
    parser.add_argument("--workflow_name", required=False, help="Workflow name")
    parser.add_argument("--job", required=True, help="Job name")

    args = parser.parse_args()

    main(
        args.token,
        args.repo_owner,
        args.repo_name,
        args.workflow_id,
        args.workflow_name,
        args.job,
    )
