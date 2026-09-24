from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ...config.settings import TEMPLATES_DIR
from ...models.provision_request import ProvisionRequest
from ...services.argocd_checks import ProvisionDecision
from ...services.naming import build_names


def generate_argocd(
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

    # ---------------------------------------------------------
    # AppProject
    # ---------------------------------------------------------

    if request.lifecycle == "prod":

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

    # ---------------------------------------------------------
    # Standalone Application
    # ---------------------------------------------------------

    if decision.create_application:
        templates["application.yaml.j2"] = (
            applications_output_dir,
            f"{request.application}.yaml",
        )

    # ---------------------------------------------------------
    # ApplicationSet
    # ---------------------------------------------------------

    if decision.create_application_set:
        templates["application-set.yaml.j2"] = (
            applications_output_dir,
            "applicationSet.yaml",
        )

    # ---------------------------------------------------------
    # Create output directories
    # ---------------------------------------------------------
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

    # ---------------------------------------------------------
    # Render templates and write files
    # ---------------------------------------------------------

    for template_name, (output_dir, output_name) in templates.items():

        template = environment.get_template(
            template_name
        )

        rendered = template.render(
            **context
        )

        output_file = output_dir / output_name

        output_file.write_text(
            rendered,
            encoding="utf-8",
        )
