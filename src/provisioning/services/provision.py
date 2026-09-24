from pathlib import Path
from ..config.settings import GENERATED_DIR, GIT_REPO_PATH
from ..generators.argocd_objects.argocd import generate_argocd
from ..models.provision_request import ProvisionRequest
from ..services.argocd_checks import run_checks


def provision(
    request: ProvisionRequest,
) -> dict:
    """
    Main provisioning workflow.

    1. Determine the Git repository location.
    2. Run provisioning checks.
    3. Generate Argo CD objects according to the decisions.
    """

    # Temporary local Git repository path.
    #
    # Later this should point to the cloned Git repository
    # or another Git integration layer.


    decision = run_checks(
        request=request,
        git_repo_path=GIT_REPO_PATH
    )

    app_project_output_dir = (
        GENERATED_DIR
        / "argocd_projects"
        / request.tenant
        / request.lifecycle
    )
    applications_output_dir = (
        GENERATED_DIR
        / "argocd_programs"
        / request.tenant
        / request.lifecycle
    )

    generate_argocd(
        request=request,
        decision=decision,
        applications_output_dir=applications_output_dir,
        app_project_output_dir=app_project_output_dir
    )

    return {
        "status": "generated",

        "tenant": request.tenant,

        "lifecycle": request.lifecycle,

        "application": request.application,

        "output_directory": (
            applications_output_dir,app_project_output_dir
        ),

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
    }

