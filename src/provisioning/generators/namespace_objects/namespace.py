from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ...config.settings import NAMESPACE_TEMPLATES_DIR
from ...models.git_services import GitActions
from ...models.provision_request import ProvisionRequest
from ...services.naming import build_names


def generate_namespace(
    git: GitActions,
    request: ProvisionRequest,
    namespace_output_dir: Path,
    namespace_output_dir_for_yahalom: Path,
    cluster: str
) -> None:
    """
    Generates Kubernetes Namespace YAML objects.

    The namespace object is generated from a Jinja2 template
    according to the ProvisionRequest.
    """

    # Namespace provisioning is disabled
    if not request.namespace_config.enabled:
        return

    # Build all names required by the templates
    names = build_names(request)


    if request.namespace_config.customer_yahalom:
        template_dir = (
            NAMESPACE_TEMPLATES_DIR
            / "namespace-for-yahalom"
        )

        output_dir = namespace_output_dir_for_yahalom

    else:
        template_dir = (
            NAMESPACE_TEMPLATES_DIR
            / "namespace-for-all-customers"
        )

        output_dir = namespace_output_dir

    environment = Environment(
        loader=FileSystemLoader(template_dir)
    )


    # Data available inside the Jinja2 template
    if request.namespace_config.customer_yahalom:
        context = {
            "cluster": cluster,
            "request": request,
            "names": names,
            "namespace": {
                "name": names["namespace"],
                "ldap_group": request.ldap_group,
                "scc": request.scc,
            },
        }
    else:
        context = {
            "cluster": cluster,
            "request": request,
            "names": names,
            "namespace": {
                "name": names["namespace"],
                "ldap_group": request.ldap_group,
            },
        }

    # Make sure the Git repository exists and is up to date
    if not git.clone_or_update(target_revision="master"):
        raise RuntimeError(
            f"Failed to clone/update Git repository: "
            f"{git.git_repo_to_do_actions}"
        )

    # Create / checkout feature branch
    branch_name = f"feat/namespace_objects/{request.application}-{request.lifecycle}-{request.tenant}"
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
        ".values.yaml.j2"
    )

    # Render the template
    rendered = template.render(**context)

    # Output filename
    output_name = (
        ".values.yaml"
    )

    output_file = output_dir / output_name

    print(
        f"[generate_namespace] git repo path : "
        f"{git.git_repo_to_do_actions.resolve()}"
    )

    print(
        f"[generate_namespace] writing to     : "
        f"{output_file.resolve()}"
    )

    print(
        f"[generate_namespace] is under repo? : "
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
        "chart": "monitoring-stack",
        "version": "1.0.0",
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
        f"[generate_namespace] copied high.conf: "
        f"{high_conf_destination.resolve()}"
    )

    # Never push directly to master
    if (
        git.get_current_branch() != "master"
        and git.get_current_branch() != "main"
    ):
        git.git_add_commit_push(
            "added namespace object for "
            f"tenant: {request.tenant}, "
            f"lifecycle: {request.lifecycle}, "
            f"application: {request.application}"
        )