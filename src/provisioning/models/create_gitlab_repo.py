import os
import sys

import httpx


GITLAB_URL = os.getenv("GITLAB_URL", "https://gitlab.com").rstrip("/")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")


def create_repository(
    name: str,
    visibility: str = "private",
    namespace_num = None
) -> dict:
    """
    Creates an empty GitLab project.

    Args:
        name: Repository/project name.
        visibility: private, internal, or public.
        namespace_num: Optional GitLab group or namespace ID.

    Returns:
        The created project details.
    """
    if not GITLAB_TOKEN:
        raise RuntimeError(
            "GITLAB_TOKEN environment variable is not configured."
        )

    if visibility not in {"private", "internal", "public"}:
        raise ValueError(
            "Visibility must be private, internal, or public."
        )

    url = f"{GITLAB_URL}/api/v4/projects"

    payload = {
        "name": name,
        "visibility": visibility,
        "initialize_with_readme": False,
    }

    # If provided, create the project inside the specified group/namespace.
    if namespace_num is not None:
        payload["namespace_num"] = namespace_num

    headers = {
        "PRIVATE-TOKEN": GITLAB_TOKEN,
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            url,
            headers=headers,
            json=payload,
        )

    if response.status_code == 201:
        project = response.json()

        print("Repository created successfully.")
        print(f"Name: {project['name']}")
        print(f"URL: {project['web_url']}")
        print(f"Visibility: {project['visibility']}")
        print(f"Project ID: {project['id']}")

        return project

    if response.status_code == 409:
        raise RuntimeError(
            f"A project with this name/path may already exist: {name}"
        )

    raise RuntimeError(
        f"GitLab API error: HTTP {response.status_code}\n"
        f"Response: {response.text}"
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: python create_gitlab_repo.py "
            "<repository-name> [namespace-id]"
        )
        sys.exit(1)

    repository_name = sys.argv[1]

    namespace_num = (
        int(sys.argv[2])
        if len(sys.argv) >= 3
        else None
    )

    try:
        create_repository(
            name=repository_name,
            visibility="private",
            namespace_num=namespace_num,
        )
    except (RuntimeError, ValueError, httpx.HTTPError) as error:
        print(f"ERROR: {error}")
        sys.exit(1)
