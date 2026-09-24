from dataclasses import dataclass
from pathlib import Path

from ..models.provision_request import ProvisionRequest


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
) -> bool:
    """
    Checks whether an AppProject for the tenant
    already exists in the Git repository.

    Expected file:

        argocd/app-projects/<tenant>.yaml

    Example:

        argocd/app-projects/customer-a.yaml
    """

    app_project_file = (
        git_repo_path
        / "argocd"
        / "app-projects"
        / f"{tenant}.yaml"
    )

    return app_project_file.exists()


def should_create_application(
    request: ProvisionRequest,
) -> bool:
    """
    Determines whether a standalone Application
    should be created.
    """

    return (
        request.argocd.enabled
        and request.argocd.application
    )


def should_create_application_set(
    request: ProvisionRequest,
) -> bool:
    """
    Determines whether an ApplicationSet
    should be created.
    """

    return (
        request.argocd.enabled
        and request.argocd.application_set
    )


def run_checks(
    request: ProvisionRequest,
    git_repo_path: Path,
) -> ProvisionDecision:
    """
    Runs all provisioning checks and returns
    a ProvisionDecision.

    This function does not generate files.
    It only decides what should be generated.
    """

    project_exists = app_project_exists(
        git_repo_path=git_repo_path,
        tenant=request.tenant,
    )

    return ProvisionDecision(
        create_app_project=not project_exists,
        create_application=should_create_application(
            request
        ),
        create_application_set=should_create_application_set(
            request
        ),
    )