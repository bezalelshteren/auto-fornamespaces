from ..models.git_services import GitActions
from ..config.settings import ARGO_DIR_TARGET, GIT_REPO_FOR_ARGOCD_OBJECTS,NAMESPACE_REPOSITORIES ,GIT_REPO_FOR_MONITORING_INGEST,MONITORING_DIR_TARGET_INGEST, GIT_REPO_FOR_MONITORING_EXPORT, MONITORING_DIR_TARGET_EXPORT
from ..generators.argocd_objects.argocd import generate_argocd
from ..models.provision_request import ProvisionRequest
from ..services.argocd_checks import run_checks
from ..generators.namespace_objects.namespace import generate_namespace
from ..generators.monitoring_objects.monitoring import (generate_monitoring_ingest,generate_monitoring_export)

def provision_argo(
    request: ProvisionRequest
) -> dict:
    """
    Provision Argo CD objects for every target site.

    All sites use the same Git repository.
    Each site has its own directory inside the repository.
    """

    git_argo = GitActions(
        git_repo_to_clone=GIT_REPO_FOR_ARGOCD_OBJECTS,
        git_repo_to_do_actions=ARGO_DIR_TARGET,
    )

    results = []

    for site in request.target_sites:

        print(f"[provision_argo] site={site}")

        # Each site has its own directory inside the same repository
        site_dir = ARGO_DIR_TARGET

        app_project_output_dir = (
            site_dir
            / "argocd_projects"
            / site
            / request.tenant
            / request.lifecycle
        )

        applications_output_dir = (
            site_dir
            / "argocd_programs"
            / site
            / request.tenant
            / request.lifecycle
        )

        decision = run_checks(
            request=request,
            git_repo_path=ARGO_DIR_TARGET,
        )

        generate_argocd(
            git=git_argo,
            request=request,
            decision=decision,
            applications_output_dir=applications_output_dir,
            app_project_output_dir=app_project_output_dir,
            site=site,
        )

        results.append({
            "site": site,
            "output_directory": {
                "applications": str(
                    applications_output_dir
                ),
                "app_project": str(
                    app_project_output_dir
                ),
            },
            "decision": {
                "create_app_project": (
                    decision.create_app_project
                ),
                "create_application": (
                    decision.create_application
                ),
                "create_application_set": (
                    decision.create_application_set
                ),
            },
        })

    return {
        "status": "generated",
        "tenant": request.tenant,
        "lifecycle": request.lifecycle,
        "application": request.application,
        "sites": results,
    }



def provision_namespace(request: ProvisionRequest) -> None:

    if not request.namespace_config.enabled:
        return

    target_sites = request.target_sites

    for environment in target_sites:

        if environment not in NAMESPACE_REPOSITORIES:
            raise ValueError(
                f"Unknown namespace environment: {environment}"
            )

        repository = NAMESPACE_REPOSITORIES[environment]

        git_repo = repository["git_repo"]
        local_path = repository["local_path"]

        print(
            f"[provision_namespace] "
            f"environment={environment}"
        )

        print(
            f"[provision_namespace] "
            f"repo={git_repo}"
        )

        print(
            f"[provision_namespace] "
            f"local_path={local_path}"
        )

        git_namespace = GitActions(
            git_repo_to_clone=git_repo,
            git_repo_to_do_actions=local_path,
        )

        namespace_output_dir = (
            local_path
            / request.tenant
            / "managed-namespaces"
            / request.application
        )

        namespace_yahalom_output_dir = (
            local_path
            / "managed-namespaces"
            / request.tenant
            / request.lifecycle
        )

        generate_namespace(
            git=git_namespace,
            request=request,
            namespace_output_dir=namespace_output_dir,
            namespace_output_dir_for_yahalom=namespace_yahalom_output_dir,
            cluster=environment,
        )


def provision_monitoring_ingest(request: ProvisionRequest) -> None:
    if not request.monitoring.enabled:
        return

    git_monitoring = GitActions(
        git_repo_to_clone=GIT_REPO_FOR_MONITORING_INGEST,
        git_repo_to_do_actions=MONITORING_DIR_TARGET_INGEST,
    )


    monitoring_output_dir = (
        MONITORING_DIR_TARGET_INGEST
        / request.tenant
        / "monitoring"
        / request.application
    )


    generate_monitoring_ingest(
        git=git_monitoring,
        request=request,
        monitoring_output_dir=monitoring_output_dir,
    )

def provision_monitoring_export(request: ProvisionRequest) -> None:
    if not request.monitoring.enabled:
        return

    git_monitoring = GitActions(
        git_repo_to_clone=GIT_REPO_FOR_MONITORING_EXPORT,
        git_repo_to_do_actions=MONITORING_DIR_TARGET_EXPORT,
    )


    monitoring_output_dir = (
        MONITORING_DIR_TARGET_EXPORT
        / request.tenant
        / "monitoring"
        / request.application
    )


    generate_monitoring_export(
        git=git_monitoring,
        request=request,
        monitoring_output_dir=monitoring_output_dir,
    )