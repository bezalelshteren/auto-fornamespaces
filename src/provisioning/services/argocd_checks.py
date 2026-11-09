from dataclasses import dataclass
from pathlib import Path
import logging
import yaml

from ..models.provision_request import SiteConfig


logger = logging.getLogger("provisioning")


@dataclass
class ProvisionDecision:
    """
    Contains the decisions made before generating Argo CD objects.
    """

    create_app_project: bool
    create_application: bool
    create_application_set: bool


def app_project_exists(
    git_repo_path: Path,
    tenant: str,
    lifecycle: str,
) -> bool:
    app_project_file = (
        git_repo_path
        / "argocd_projects"
        / tenant
        / f"{lifecycle}.yaml"
    )

    exists = app_project_file.exists()

    print(f"[DEBUG] Checking AppProject: {app_project_file}")
    print(f"[DEBUG] File exists: {exists}")

    return exists

def should_create_application(
    site: SiteConfig,
) -> bool:
    """
    Determines whether a standalone Application
    should be created for this Site.
    """

    return (
        site.argocd.enabled
        and site.argocd.type == "application"
    )


def should_create_application_set(
    site: SiteConfig,
) -> bool:
    """
    Determines whether an ApplicationSet
    should be created for this Site.
    """

    return (
        site.argocd.enabled
        and site.argocd.type == "application_set"
    )
def run_checks(
    site: SiteConfig,
) -> ProvisionDecision:
    """
    Determines which Argo CD objects are required.

    AppProject existence is checked later,
    after the repository has been updated from master.
    """
    return ProvisionDecision(
        create_app_project=False,
        create_application=should_create_application(site),
        create_application_set=should_create_application_set(site),
    )

def add_source_repo_to_app_project(
    app_project_path: Path,
    source_repo: str,
) -> bool:
    """
    Adds a repository to spec.sourceRepos in an existing AppProject.

    Returns:
        True if the repository was added.
        False if the repository already exists.
    """
    if not app_project_path.is_file():
        raise FileNotFoundError(
            f"AppProject file not found: {app_project_path}"
        )

    with app_project_path.open("r", encoding="utf-8") as file:
        app_project = yaml.safe_load(file)

    if not isinstance(app_project, dict):
        raise ValueError(
            f"Invalid AppProject YAML: {app_project_path}"
        )

    spec = app_project.get("spec")

    if not isinstance(spec, dict):
        raise ValueError(
            f"AppProject has no valid spec section: {app_project_path}"
        )

    source_repos = spec.get("sourceRepos", [])

    if not isinstance(source_repos, list):
        raise ValueError(
            f"spec.sourceRepos must be a list: {app_project_path}"
        )

    print(f"[DEBUG] AppProject file: {app_project_path}")
    print(f"[DEBUG] sourceRepos before: {source_repos}")
    print(f"[DEBUG] Repository to add: {source_repo}")

    if source_repo in source_repos:
        print("[DEBUG] Repository already exists. No changes made.")
        return False

    source_repos.append(source_repo)
    spec["sourceRepos"] = source_repos

    print(f"[DEBUG] sourceRepos after: {spec['sourceRepos']}")

    with app_project_path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(
            app_project,
            file,
            allow_unicode=True,
            sort_keys=False,
        )

    # Read the file again to verify that both repositories were saved.
    with app_project_path.open("r", encoding="utf-8") as file:
        saved_app_project = yaml.safe_load(file)

    saved_repos = saved_app_project["spec"]["sourceRepos"]

    print(f"[DEBUG] sourceRepos saved to disk: {saved_repos}")

    if source_repo not in saved_repos:
        raise RuntimeError(
            f"Repository was not saved to AppProject: {source_repo}"
        )

    return True



def add_new_namespace_to_monitoring_export(
    monitoring_export_path: Path,
    source_repo: str,
) -> bool:
    """
    Adds a repository to spec.sourceRepos in an existing AppProject.

    Returns:
        True if the repository was added.
        False if the repository already exists.
    """
    if not monitoring_export_path.is_file():
        raise FileNotFoundError(
            f"AppProject file not found: {monitoring_export_path}"
        )

    with monitoring_export_path.open("r", encoding="utf-8") as file:
        app_project = yaml.safe_load(file)

    if not isinstance(app_project, dict):
        raise ValueError(
            f"Invalid AppProject YAML: {monitoring_export_path}"
        )

    spec = app_project.get("spec")

    if not isinstance(spec, dict):
        raise ValueError(
            f"AppProject has no valid spec section: {monitoring_export_path}"
        )

    source_repos = spec.get("sourceRepos", [])

    if not isinstance(source_repos, list):
        raise ValueError(
            f"spec.sourceRepos must be a list: {monitoring_export_path}"
        )

    print(f"[DEBUG] AppProject file: {monitoring_export_path}")
    print(f"[DEBUG] sourceRepos before: {source_repos}")
    print(f"[DEBUG] Repository to add: {source_repo}")

    if source_repo in source_repos:
        print("[DEBUG] Repository already exists. No changes made.")
        return False

    source_repos.append(source_repo)
    spec["sourceRepos"] = source_repos

    print(f"[DEBUG] sourceRepos after: {spec['sourceRepos']}")

    with monitoring_export_path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(
            app_project,
            file,
            allow_unicode=True,
            sort_keys=False,
        )

    # Read the file again to verify that both repositories were saved.
    with monitoring_export_path.open("r", encoding="utf-8") as file:
        saved_app_project = yaml.safe_load(file)

    saved_repos = saved_app_project["spec"]["sourceRepos"]

    print(f"[DEBUG] sourceRepos saved to disk: {saved_repos}")

    if source_repo not in saved_repos:
        raise RuntimeError(
            f"Repository was not saved to AppProject: {source_repo}"
        )
    return True
