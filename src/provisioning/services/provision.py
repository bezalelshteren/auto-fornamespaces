from ..models.git_services import GitActions

from ..config.settings import (
    ARGO_DIR_TARGET,
    GIT_REPO_FOR_ARGOCD_OBJECTS,
    NAMESPACE_REPOSITORIES,
    GIT_REPO_FOR_MONITORING_INGEST,
    MONITORING_DIR_TARGET_INGEST,
)

from ..generators.argocd_objects.argocd import generate_argocd
from ..models.provision_request import ProvisionRequest, SiteConfig

from ..services.argocd_checks import run_checks

from ..generators.namespace_objects.namespace import generate_namespace

from ..generators.monitoring_objects.monitoring import (
    generate_monitoring_ingest,
    generate_monitoring_export,
)


def provision_argo(
    request: ProvisionRequest,
    site: SiteConfig,
) -> dict:
    """
    Provision Argo CD objects for one site.

    Shared configuration comes from request.
    Site-specific configuration comes from site.
    """

    if not site.argocd.enabled:
        return {
            "site": site.name,
            "status": "skipped",
            "reason": "ArgoCD is disabled",
        }

    print(
        f"[provision_argo] "
        f"application={request.application}, "
        f"site={site.name}"
    )

    git_argo = GitActions(
        git_repo_to_clone=GIT_REPO_FOR_ARGOCD_OBJECTS,
        git_repo_to_do_actions=ARGO_DIR_TARGET,
    )

    site_dir = ARGO_DIR_TARGET

    app_project_output_dir = (
        site_dir
        / "argocd_projects"
        / request.tenant
    )

    applications_output_dir = (
        site_dir
        / "argocd_programs"
        / site.name
        / request.tenant
    )

    decision = run_checks(
        site=site,
    )

    generate_argocd(
        git=git_argo,
        request=request,
        site=site,
        decision=decision,
        applications_output_dir=applications_output_dir,
        app_project_output_dir=app_project_output_dir,
    )

    return {
        "site": site.name,
        "status": "generated",
        "output_directory": {
            "applications": str(applications_output_dir),
            "app_project": str(app_project_output_dir),
        },
        "decision": {
            "create_app_project": decision.create_app_project,
            "create_application": decision.create_application,
            "create_application_set": decision.create_application_set,
        },
    }


def provision_namespace(
    request: ProvisionRequest,
    site: SiteConfig,
) -> dict:
    """
    Provision a namespace for one site.
    """

    if not site.namespace.enabled:
        return {
            "site": site.name,
            "status": "skipped",
            "reason": "Namespace provisioning is disabled",
        }

    environment = site.name

    if environment not in NAMESPACE_REPOSITORIES:
        raise ValueError(
            f"Unknown namespace environment: {environment}"
        )

    repository = NAMESPACE_REPOSITORIES[environment]

    git_repo = repository["git_repo"]
    local_path = repository["local_path"]

    print(
        f"[provision_namespace] "
        f"tenant={request.tenant}, "
        f"application={request.application}, "
        f"site={environment}"
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
        / request.tenant
        / "managed-namespaces"
        / request.application
    )

    generate_namespace(
        git=git_namespace,
        request=request,
        namespace_output_dir=namespace_output_dir,
        namespace_output_dir_for_yahalom=namespace_yahalom_output_dir,
        site=site,    )

    return {
        "site": site.name,
        "status": "generated",
        "output_directory": str(namespace_output_dir),
    }


def provision_monitoring_ingest(
    request: ProvisionRequest,
    site: SiteConfig,
) -> dict:
    """
    Provision monitoring ingest for one site.
    """

    if not site.monitoring.enabled or not site.monitoring.ingest:
        return {
            "site": site.name,
            "status": "skipped",
            "reason": "Monitoring ingest is disabled",
        }
    if request.customer_yahalom:
        return {request.application :"custemer yahalom dont use monitoring stck per tenant its per cluster !!!!"}

    git_monitoring = GitActions(
        git_repo_to_clone=GIT_REPO_FOR_MONITORING_INGEST,
        git_repo_to_do_actions=MONITORING_DIR_TARGET_INGEST,
    )

    monitoring_output_dir = (
        MONITORING_DIR_TARGET_INGEST
        / request.tenant
        / "monitoring"
        / request.application
        / site.name
    )

    generate_monitoring_ingest(
        git=git_monitoring,
        request=request,
        site=site,
        monitoring_output_dir=monitoring_output_dir,
    )


    return {
        "site": site.name,
        "status": "generated",
        "output_directory": str(monitoring_output_dir),
    }


def provision_monitoring_export(
    request: ProvisionRequest,
    site: SiteConfig,
) -> dict:
    """
    Provision monitoring export for one site.
    """

    if not site.monitoring.enabled or not site.monitoring.export:
        return {
            "site": site.name,
            "status": "skipped",
            "reason": "Monitoring export is disabled",
        }
    environment = site.name

    if environment not in NAMESPACE_REPOSITORIES:
        raise ValueError(
            f"Unknown monitoring environment: {environment}"
        )

    repository = NAMESPACE_REPOSITORIES[environment]

    git_repo = repository["git_repo"]
    local_path = repository["local_path"]

    print(
        f"[provision_monitoring] "
        f"tenant={request.tenant}, "
        f"application={request.application}, "
        f"site={environment}"
    )

    git_monitoring = GitActions(
        git_repo_to_clone=git_repo,
        git_repo_to_do_actions=local_path,
    )

    monitoring_output_dir = (
        local_path
        / request.tenant
        / "monitoring"
        / request.application
        / site.name
    )

    generate_monitoring_export(
        git=git_monitoring,
        request=request,
        site=site,
        monitoring_output_dir=monitoring_output_dir,
    )

    return {
        "site": site.name,
        "status": "generated",
        "output_directory": str(monitoring_output_dir),
    }
