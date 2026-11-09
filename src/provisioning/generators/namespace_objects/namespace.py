from pathlib import Path
import logging

from jinja2 import Environment, FileSystemLoader

from ...config.settings import NAMESPACE_TEMPLATES_DIR
from ...models.git_services import GitActions
from ...models.provision_request import ProvisionRequest, SiteConfig
from ...services.naming import build_names


logger = logging.getLogger("provisioning")


def generate_namespace(
    git: GitActions,
    request: ProvisionRequest,
    site: SiteConfig,
    namespace_output_dir: Path,
    namespace_output_dir_for_yahalom: Path,
) -> None:
    """
    Generates Kubernetes Namespace YAML objects for a specific site.
    """

    namespace_config = site.namespace

    # Skip namespace generation if disabled for this site.
    if not namespace_config.enabled:
        logger.info(
            "Namespace generation skipped: site=%s, reason=disabled",
            site.name,
        )
        return

    # Build names using the request and the current site.
    names = build_names(request, site)

    # Customer type is defined at the request level.
    is_yahalom = request.customer_yahalom

    # Select the appropriate template directory and output path.
    if is_yahalom:
        template_dir = (
            NAMESPACE_TEMPLATES_DIR / "namespace-for-yahalom"
        )
        output_dir = namespace_output_dir_for_yahalom
    else:
        template_dir = (
            NAMESPACE_TEMPLATES_DIR / "namespace-for-all-customers"
        )
        output_dir = namespace_output_dir

    logger.info(
        "Namespace template selected: tenant=%s, application=%s, "
        "site=%s, customer_yahalom=%s, template_dir=%s",
        request.tenant,
        request.application,
        site.name,
        is_yahalom,
        template_dir,
    )

    environment = Environment(
        loader=FileSystemLoader(template_dir),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Build the data available to the Jinja2 template.
    namespace_context = {
        "name": names["namespace"],
        "ldap_group": request.ldap_group,
    }

    # Add SCC for Yahalom customers.
    if is_yahalom:
        scc = getattr(request, "scc", None)

        namespace_context["scc"] = scc

        if scc is None:
            logger.warning(
                "Yahalom customer has no SCC value: tenant=%s, site=%s",
                request.tenant,
                site.name,
            )

    # Add compute configuration only when custom=True
    # and a compute configuration was provided.
    if request.custom and request.compute is not None:
        namespace_context["compute"] = (
            request.compute.model_dump(exclude_none=True)
        )

        logger.info(
            "Custom compute configuration added: site=%s",
            site.name,
        )
    else:
        logger.info(
            "Custom compute configuration skipped: site=%s, custom=%s",
            site.name,
            request.custom,
        )

    context = {
        "cluster": site.name,
        "request": request,
        "site": site,
        "names": names,
        "namespace": namespace_context,
    }

    # Clone or update the repository.
    if not git.clone_or_update(target_revision="master"):
        raise RuntimeError(
            "Failed to clone/update Git repository: "
            f"{git.git_repo_to_do_actions}"
        )

    # Validate lifecycle for this site.
    lifecycle = namespace_config.lifecycle

    if not lifecycle:
        raise ValueError(
            "Lifecycle is required when namespace provisioning "
            f"is enabled for site '{site.name}'"
        )

    # Create or checkout a feature branch for this site.
    branch_name = (
        f"feat/namespace_objects/"
        f"{request.application}-{lifecycle}-"
        f"{request.tenant}-{site.name}"
    )

    if not git.checkout_branch(branch_name):
        raise RuntimeError(
            f"Failed to checkout branch: {branch_name}"
        )

    # Create the output directory inside the repository.
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Render the namespace values file using the selected template.
    template = environment.get_template(".values.yaml.j2")
    rendered = template.render(**context)

    output_file = output_dir / ".values.yaml"

    output_file.write_text(
        rendered,
        encoding="utf-8",
    )

    logger.info(
        "Generated namespace values: site=%s, file=%s",
        site.name,
        output_file,
    )

    # Render high_conf.yaml.
    high_conf_template = environment.get_template("high_conf.yaml")

    if is_yahalom:
        high_conf_rendered = high_conf_template.render(
            chart="namespace-yahalom",
            version="1.0.0",
        )
    else:
        high_conf_rendered = high_conf_template.render(
            chart="namespace-standard",
            version="1.0.0",
        )

    # Write the rendered content to high_conf.yaml.
    high_conf_destination = output_dir / "high_conf.yaml"

    high_conf_destination.write_text(
        high_conf_rendered,
        encoding="utf-8",
    )

    logger.info(
        "Generated high_conf.yaml: site=%s, file=%s",
        site.name,
        high_conf_destination,
    )

    # Commit and push the generated namespace files.
    commit_message = (
        f"Provision namespace for application={request.application}, "
        f"tenant={request.tenant}, site={site.name}"
    )

    logger.info(
        "Committing namespace changes: site=%s, branch=%s",
        site.name,
        branch_name,
    )

    pushed = git.git_add_commit_push(
        commit_message=commit_message,
    )

    if not pushed:
        raise RuntimeError(
            "Namespace changes were not pushed. "
            f"site={site.name}, branch={branch_name}. "
            "Check Git logs to identify the reason."
        )

    logger.info(
        "Namespace changes pushed successfully: site=%s, branch=%s",
        site.name,
        branch_name,
    )
