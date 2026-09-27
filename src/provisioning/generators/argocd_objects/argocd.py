from pathlib import Path
from ...models.git_services import GitActions
from jinja2 import Environment, FileSystemLoader

from ...config.settings import TEMPLATES_DIR
from ...config.settings import GIT_REPO_FOR_ARGOCD_OBJECTS
from ...models.provision_request import ProvisionRequest
from ...services.argocd_checks import ProvisionDecision
from ...services.naming import build_names


def generate_argocd(
    git: GitActions,
    request: ProvisionRequest,
    decision: ProvisionDecision,
    app_project_output_dir: Path,
    applications_output_dir: Path,
) -> None:
    """
    Generates the Argo CD YAML objects according to the
    decisions produced by argocd_checks.py.
    """

    if not request.argocd.enabled:
        return

    names = build_names(request)

    environment = Environment(
        loader=FileSystemLoader(
            TEMPLATES_DIR / "argocd-objects"
        )
    )

    context = {
        "request": request,
        "names": names,
    }

    templates: dict[str, tuple[Path, str]] = {}


    if request.lifecycle == "prd":

        if decision.create_app_project:
            templates["app-project_prod.yaml.j2"] = (
                app_project_output_dir,
                f"{request.lifecycle}.yaml",
            )

    elif request.lifecycle in {"dev", "stg"}:

        if decision.create_app_project:
            templates["app-project_nonprod.yaml.j2"] = (
                app_project_output_dir,
                f"{request.lifecycle}.yaml",
            )


    if decision.create_application:
        templates["application.yaml.j2"] = (
            applications_output_dir,
            f"{request.application}.yaml",
        )


    if decision.create_application_set:
        templates["application-set.yaml.j2"] = (
            applications_output_dir,
            "applicationSet.yaml",
        )

    if decision.create_app_project:
        app_project_output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
    if decision.create_application or decision.create_application_set:
        applications_output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    if decision.create_app_project or decision.create_application_set or decision.create_application:
        git.clone_or_update()
        git.checkout_branch(f"feat/argocd_objects/{request.application}")

        for template_name, (output_dir, output_name) in templates.items():
            template = environment.get_template(
                template_name
            )

            rendered = template.render(
                **context
            )

            output_file = output_dir / output_name

            print(f"[generate_argocd] git repo path : {git.git_repo_for_argo}")
            print(f"[generate_argocd] writing to     : {output_file.resolve()}")
            print(
                f"[generate_argocd] is under repo? : {git.git_repo_for_argo.resolve() in output_file.resolve().parents}")

            output_file.write_text(
                rendered,
                encoding="utf-8",
            )
        if not git.get_current_branch() == "master":
            git.git_add_commit_push(f"added argocd objects for tenant: {request.tenant}, lifecycle: {request.lifecycle}, application: {request.application}" )