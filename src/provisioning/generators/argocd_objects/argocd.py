from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from provisioning.config.settings import TEMPLATES_DIR
from provisioning.models.provision_request import ProvisionRequest
from provisioning.services.naming import build_names


def generate_argocd(request: ProvisionRequest, output_dir: Path) -> None:

    if not request.argocd.enabled:
        return

    names = build_names(request)

    environment = Environment(
        loader=FileSystemLoader(
            TEMPLATES_DIR / "argocd"
        )
    )

    context = {
        "request": request,
        "names": names,
    }

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    templates = {
        "app-project.yaml.j2": "app-project.yaml",
        "application.yaml.j2": "application.yaml",
        "application-set.yaml.j2": "application-set.yaml",
    }

    for template_name, output_name in templates.items():

        template = environment.get_template(template_name)

        rendered = template.render(**context)

        output_file = output_dir / output_name

        output_file.write_text(
            rendered,
            encoding="utf-8",
        )