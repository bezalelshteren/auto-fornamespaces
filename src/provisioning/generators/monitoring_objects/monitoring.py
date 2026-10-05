from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from ...config.settings import MONITORING_TEMPLATES_DIR
from ...models.git_services import GitActions
from ...models.provision_request import ProvisionRequest
from ...services.naming import build_names


def generate_monitoring_ingest(
    git: GitActions,
    request: ProvisionRequest,
    monitoring_output_dir: Path,
) -> None:
    """
    Generates Kubernetes monitoring stack YAML objects.

    The monitoring object is generated from a Jinja2 template
    according to the ProvisionRequest.
    """

    # Namespace provisioning is disabled
    if not request.monitoring.enabled or request.namespace_config.customer_yahalom:
        return

    # Build all names required by the templates
    names = build_names(request)


    template_dir = (
        MONITORING_TEMPLATES_DIR
        / "monitoring_stack_inges"
    )

    output_dir = monitoring_output_dir

    environment = Environment(
        loader=FileSystemLoader(template_dir)
    )

    # Data available inside the Jinja2 template
    context = {
        "request": request,
        "names": names,
    }

    # Make sure the Git repository exists and is up to date
    if not git.clone_or_update("master"):
        raise RuntimeError(
            f"Failed to clone/update Git repository:"
            f"{git.git_repo_to_do_actions}"
        )

    # Create / checkout feature branch
    branch_name = f"feat/monitoring_objects/{request.application}"

    if not git.checkout_branch(branch_name):
        raise RuntimeError(
            f"Failed to checkout branch: {branch_name}"
        )

    # Only now create directories inside the Git repository
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )
    template = environment.get_template(
        ".values-ingest.yaml.j2"
    )
    context = {
        "namespace_name": request.application,
        "namespace_ip": request.monitoring.ip,
        "namespace_ip_pmm": request.monitoring.ip_pmm,
        "namespace_ecs_id": request.monitoring.ecs_id,
        "namespace_ecs_token": request.monitoring.ecs_token,
    }

    # Render the template
    rendered = template.render(**context)

    # Output filename
    output_name = (
        ".values-ingest.yaml"
    )

    output_file = output_dir / output_name

    print(
        f"[generate_monitoring] git repo path : "
        f"{git.git_repo_to_do_actions.resolve()}"
    )

    print(
        f"[generate_monitoring] writing to     : "
        f"{output_file.resolve()}"
    )

    print(
        f"[generate_monitoring] is under repo? : "
        f"{git.git_repo_to_do_actions.resolve() in output_file.resolve().parents}"
    )

    # Write rendered YAML
    output_file.write_text(
        rendered,
        encoding="utf-8",
    )
    # Load high.conf as a Jinja2 template
    high_conf_template = environment.get_template("high.conf")
    context = {
        "chart": names["chart_monitoring"],
        "version": names["chart_monitoring_ingest_version"],
    }

    # Render the template with the same context
    high_conf_rendered = high_conf_template.render(**context)

    # Destination file
    high_conf_destination = output_dir / "high.conf"

    # Write the rendered file
    high_conf_destination.write_text(
        high_conf_rendered,
        encoding="utf-8",
    )

    print(
        f"[generate_monitoring] copied high.conf: "
        f"{high_conf_destination.resolve()}"
    )

    # Never push directly to master
    if (
        git.get_current_branch() != "master"
        and git.get_current_branch() != "main"
    ):
        git.git_add_commit_push(
            "added monitoring object for "
            f"tenant: {request.tenant}, "
            f"lifecycle: {request.lifecycle}, "
            f"application: {request.application}"
        )



def generate_monitoring_export(
    git: GitActions,
    request: ProvisionRequest,
    monitoring_output_dir: Path,
) -> None:
    """
    Generates Kubernetes monitoring stack YAML objects.

    The monitoring object is generated from a Jinja2 template
    according to the ProvisionRequest.
    """

    # Namespace provisioning is disabled
    if not request.monitoring.enabled or request.namespace_config.customer_yahalom:
        return

    # Build all names required by the templates
    names = build_names(request)

    template_dir = (
        MONITORING_TEMPLATES_DIR
        / "monitoring_stack_export"
    )
    output_dir = monitoring_output_dir

    environment = Environment(
        loader=FileSystemLoader(template_dir)
    )


    # Make sure the Git repository exists and is up to date
    if not git.clone_or_update("master"):
        raise RuntimeError(
            f"Failed to clone/update Git repository:"
            f"{git.git_repo_to_do_actions}"
        )

    # Create / checkout feature branch
    branch_name = f"feat/monitoring_objects/{request.application}-{request.lifecycle}-{request.tenant}"

    if not git.checkout_branch(branch_name):
        raise RuntimeError(
            f"Failed to checkout branch: {branch_name}"
        )

    # Only now create directories inside the Git repository
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )
    template = environment.get_template(
        ".values-export.yaml.j2"
    )
    context = {
        "namespace_name": names["namespace"],
        "namespace_ip": request.monitoring.ip,
        "namespace_ip_pmm": request.monitoring.ip_pmm,
        "namespace_ecs_id": request.monitoring.ecs_id,
        "namespace_ecs_token": request.monitoring.ecs_token,
    }

    # Render the template
    rendered = template.render(**context)

    # Output filename
    output_name = (
        ".values-export.yaml"
    )

    output_file = output_dir / output_name

    print(
        f"[generate_monitoring] git repo path : "
        f"{git.git_repo_to_do_actions.resolve()}"
    )

    print(
        f"[generate_monitoring] writing to     : "
        f"{output_file.resolve()}"
    )

    print(
        f"[generate_monitoring] is under repo? : "
        f"{git.git_repo_to_do_actions.resolve() in output_file.resolve().parents}"
    )

    # Write rendered YAML
    output_file.write_text(
        rendered,
        encoding="utf-8",
    )
    # Load high.conf as a Jinja2 template
    high_conf_template = environment.get_template("high.conf")
    context = {
        "chart": names["chart_monitoring"],
        "version": names["chart_monitoring_ingest_version"],
    }

    # Render the template with the same context
    high_conf_rendered = high_conf_template.render(**context)

    # Destination file
    high_conf_destination = output_dir / "high.conf"

    # Write the rendered file
    high_conf_destination.write_text(
        high_conf_rendered,
        encoding="utf-8",
    )

    print(
        f"[generate_monitoring] copied high.conf: "
        f"{high_conf_destination.resolve()}"
    )

    # Never push directly to master
    if (
            git.get_current_branch() != "master"
            and git.get_current_branch() != "main"
    ):
        git.git_add_commit_push(
            "added monitoring object for "
            f"tenant: {request.tenant}, "
            f"lifecycle: {request.lifecycle}, "
            f"application: {request.application}"
        )
