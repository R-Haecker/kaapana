import requests
import json
import os
from kaapanapy.logger import get_logger
from kaapanapy.helper import get_project_user_access_token

logger = get_logger(__name__)
SERVICES_NAMESPACE = os.getenv("SERVICES_NAMESPACE")

file_path = "/app/config/initial_projects.json"
aii_service = f"http://aii-service.{SERVICES_NAMESPACE}.svc:8080"

if __name__ == "__main__":
    with open(file_path, "r") as file:
        initial_project = json.load(file)

    access_token = get_project_user_access_token()
    auth_header = {"x-forwarded-access-token": access_token}

    for project in initial_project:
        logger.info(f"Request creation of {project=}")
        response = requests.post(
            f"{aii_service}/projects", data=json.dumps(project), headers=auth_header
        )
        response.raise_for_status()
