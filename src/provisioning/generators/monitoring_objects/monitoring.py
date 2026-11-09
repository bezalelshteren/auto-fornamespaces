from pathlib import Path
import logging
from functools import wraps

from jinja2 import Environment, FileSystemLoader

from ...config.settings import MONITORING_TEMPLATES_DIR
from ...models.git_services import GitActions
from ...models.provision_request import ProvisionRequest, SiteConfig
from ...services.naming import build_names


logger = logging.getLogger("provisioning")


def log_monitoring_execution(func):
    """Log function start, successful completion, and full exception traceback."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info("========== START %s ==========", func.__name__)
        try:
            result = func(*args, **kwargs)
            logger.info("========== SUCCESS %s ==========", func.__name__)
            return result
        except Exception:
            logger.exception(
                "========== FAILED %s: unhandled exception ==========",
                func.__name__,
            )
            raise

    return wrapper


@log_monitoring_execution
def generate_monitoring_ingest(
    git: GitActions,
    request: ProvisionRequest,
    site: SiteConfig,
    monitoring_output_dir: Path,
) -> str | None:
    """
    Generates monitoring ingest configuration and Grafana dashboard
    for a specific site in the same repository and branch.
    """

    logger.info("Ingest request: tenant=%s team=%s application=%s site=%s output_dir=%s", request.tenant, request.team, request.application, site.name, monitoring_output_dir)
    monitoring = site.monitoring

    # Skip if ingest is disabled for this site.
    if not monitoring.enabled or not monitoring.ingest:
        logger.info(
            "Monitoring ingest skipped: site=%s, reason=disabled",
            site.name,
        )
        return None

    # Preserve the existing customer-specific exclusion.
    if request.customer_yahalom:
        logger.info(
            "Monitoring ingest skipped: site=%s, reason=customer_yahalom",
            site.name,
        )
        return None

    logger.debug("Building resource names for monitoring ingest")
    names = build_names(request, site)

    # Monitoring ingest templates.
    template_dir = MONITORING_TEMPLATES_DIR / "monitoring_stack_inges"

    logger.info("Ingest template directory: path=%s exists=%s", template_dir, template_dir.is_dir())
    environment = Environment(
        loader=FileSystemLoader(template_dir)
    )

    # Clone or update the repository.
    logger.info("Updating ingest repository: repo=%s revision=master", git.git_repo_to_do_actions)
    if not git.clone_or_update("master"):
        raise RuntimeError(
            "Failed to clone/update monitoring ingest repository: "
            f"{git.git_repo_to_do_actions}"
        )

    # Create a dedicated feature branch.
    branch_name = (
        f"feat/monitoring_objects/"
        f"{request.application}-{site.name}-ingest"
    )

    logger.info("Checking out ingest branch: branch=%s", branch_name)
    if not git.checkout_branch(branch_name):
        raise RuntimeError(
            f"Failed to checkout branch: {branch_name}"
        )

    logger.info("Creating/checking output directory: path=%s", monitoring_output_dir)
    monitoring_output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Shared context for monitoring ingest templates.
    context = {
        "tenant": request.tenant,
        "team": request.team,
        "application": request.application,
        "site": site.name,
        "namespace_name": names["namespace"],
        "namespace_ip": monitoring.ip,
        "namespace_webhook_url": monitoring.webhook_url,
        "namespace_ecs_id": monitoring.ecs_id,
        "namespace_ecs_token": monitoring.ecs_token,
    }

    # --------------------------------------------------
    # 1. Generate monitoring ingest values.
    # --------------------------------------------------

    logger.info("Loading template: %s", template_dir / ".values-ingest.yaml.j2")
    template = environment.get_template(".values-ingest.yaml.j2")

    logger.debug("Rendering ingest template with context keys=%s", list(context.keys()))
    rendered = template.render(**context)

    output_file = monitoring_output_dir / ".values-ingest.yaml"

    logger.info("Writing ingest values file: path=%s", output_file)
    output_file.write_text(
        rendered,
        encoding="utf-8",
    )

    logger.info(
        "Generated monitoring ingest values: site=%s, file=%s",
        site.name,
        output_file,
    )

    # --------------------------------------------------
    # 2. Generate monitoring ingest high_conf.yaml.
    # --------------------------------------------------

    logger.info("Loading high_conf template: %s", template_dir / "high_conf.yaml")
    high_conf_template = environment.get_template("high_conf.yaml")

    high_conf_rendered = high_conf_template.render(
        chart=names["chart_monitoring"],
        version=names["chart_monitoring_ingest_version"],
    )

    high_conf_destination = monitoring_output_dir / "high_conf.yaml"

    high_conf_destination.write_text(
        high_conf_rendered,
        encoding="utf-8",
    )

    logger.info(
        "Generated monitoring ingest high_conf.yaml: site=%s, file=%s",
        site.name,
        high_conf_destination,
    )

    # --------------------------------------------------
    # 3. Generate Grafana dashboard in the same repository.
    # --------------------------------------------------

    # TODO: Replace these paths with the actual dashboard
    # template directory and output directory in your repository.
    logger.info("Starting Grafana dashboard generation")
    dashboard_template_dir = (
        MONITORING_TEMPLATES_DIR / "grafana-objects"
    )

    dashboard_output_dir = (
        monitoring_output_dir / "grafana_dashboard"
    )

    logger.info("Grafana template directory: path=%s exists=%s", dashboard_template_dir, dashboard_template_dir.is_dir())
    dashboard_environment = Environment(
        loader=FileSystemLoader(dashboard_template_dir)
    )

    logger.info("Loading Grafana template: %s", dashboard_template_dir / "dashboard.yaml.j2")
    dashboard_template = dashboard_environment.get_template(
        "grafana-deshbord.yaml.j2"
    )

    dashboard_context = {
        **context,
        "dashboard_title": (
            f"{request.application} - {site.name}"
        ),
        "dashboard_uid": (
            f"{request.application}-{site.name}"
        ),
    }

    logger.debug("Rendering Grafana template with context keys=%s", list(dashboard_context.keys()))
    dashboard_rendered = dashboard_template.render(
        **dashboard_context
    )

    logger.info("Creating Grafana output directory: path=%s", dashboard_output_dir)
    dashboard_output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    dashboard_destination = (
        dashboard_output_dir / "dashboard.yaml"
    )

    logger.info("Writing Grafana dashboard: path=%s", dashboard_destination)
    dashboard_destination.write_text(
        dashboard_rendered,
        encoding="utf-8",
    )

    logger.info(
        "Generated Grafana dashboard: site=%s, file=%s",
        site.name,
        dashboard_destination,
    )

    # --------------------------------------------------
    # 4. Validate the branch before pushing.
    # --------------------------------------------------

    logger.info("Checking current Git branch before push")
    current_branch = git.get_current_branch()

    if current_branch in {None, "HEAD", "master", "main"}:
        raise RuntimeError(
            f"Refusing to push from invalid branch: {current_branch}"
        )

    # --------------------------------------------------
    # 5. Commit and push ingest + dashboard together.
    # --------------------------------------------------

    logger.info("Committing and pushing ingest + Grafana dashboard changes")
    mr_url = git.git_add_commit_push(
        "Added monitoring ingest and Grafana dashboard for "
        f"tenant={request.tenant}, "
        f"application={request.application}, "
        f"site={site.name}"
    )

    if not mr_url:
        raise RuntimeError(
            "Failed to push monitoring ingest and Grafana dashboard: "
            f"application={request.application}, site={site.name}"
        )

    return mr_url





@log_monitoring_execution
def generate_monitoring_export(
    git: GitActions,
    request: ProvisionRequest,
    site: SiteConfig,
    monitoring_output_dir: Path,
) -> str | None:
    """
    Generates monitoring export configuration for a specific site.
    """

    logger.info("Export request: tenant=%s team=%s application=%s site=%s output_dir=%s", request.tenant, request.team, request.application, site.name, monitoring_output_dir)
    monitoring = site.monitoring

    # Skip if export is disabled for this site.
    if not monitoring.enabled or not monitoring.export:
        logger.info(
            "Monitoring export skipped: site=%s, reason=disabled",
            site.name,
        )
        return None

    # Preserve the existing customer-specific exclusion.
    if request.customer_yahalom:
        logger.info(
            "Monitoring export skipped: site=%s, reason=customer_yahalom",
            site.name,
        )
        return None

    logger.debug("Building resource names for monitoring export")
    names = build_names(request, site)

    template_dir = (
        MONITORING_TEMPLATES_DIR / "monitoring_stack_export"
    )

    logger.info("Export template directory: path=%s exists=%s", template_dir, template_dir.is_dir())
    environment = Environment(
        loader=FileSystemLoader(template_dir)
    )

    logger.info("Updating export repository: repo=%s revision=master", git.git_repo_to_do_actions)
    if not git.clone_or_update("master"):
        raise RuntimeError(
            "Failed to clone/update monitoring export repository: "
            f"{git.git_repo_to_do_actions}"
        )

    if monitoring_output_dir.exists():
        if any(monitoring_output_dir.rglob("*.values.yaml")):
            logger.info(
                f"Monitoring export exist adding {request.application} to monitoring export: site=%s, file=%s", )

    branch_name = (
        f"feat/monitoring_objects/"
        f"{request.application}-{site.name}-export"
    )

    logger.info("Checking out export branch: branch=%s", branch_name)
    if not git.checkout_branch(branch_name):
        raise RuntimeError(
            f"Failed to checkout branch: {branch_name}"
        )

    monitoring_output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Render the export values file.
    logger.info("Loading export template: %s", template_dir / ".values-export.yaml.j2")
    template = environment.get_template(".values-export.yaml.j2")

    context = {
        "namespace_name": names["namespace"],
        "namespace_ip": monitoring.ip,
        "namespace_webhook_url": monitoring.webhook_url,
        "namespace_ecs_id": monitoring.ecs_id,
        "namespace_ecs_token": monitoring.ecs_token,
    }

    logger.debug("Rendering export template with context keys=%s", list(context.keys()))
    rendered = template.render(**context)

    output_file = monitoring_output_dir / ".values-export.yaml"

    logger.info("Writing export values file: path=%s", output_file)
    output_file.write_text(
        rendered,
        encoding="utf-8",
    )

    logger.info(
        "Generated monitoring export values: site=%s, file=%s",
        site.name,
        output_file,
    )

    # Render high_conf.yaml.
    logger.info("Loading export high_conf template: %s", template_dir / "high_conf.yaml")
    high_conf_template = environment.get_template("high_conf.yaml")

    high_conf_rendered = high_conf_template.render(
        chart=names["chart_monitoring"],
        version=names["chart_monitoring_ingest_version"],
    )

    high_conf_destination = monitoring_output_dir / "high_conf.yaml"

    high_conf_destination.write_text(
        high_conf_rendered,
        encoding="utf-8",
    )

    logger.info(
        "Generated monitoring export high_conf.yaml: site=%s, file=%s",
        site.name,
        high_conf_destination,
    )

    logger.info("Checking current Git branch before export push")
    current_branch = git.get_current_branch()

    if current_branch in {None, "HEAD", "master", "main"}:
        raise RuntimeError(
            f"Refusing to push from invalid branch: {current_branch}"
        )

    logger.info("Committing and pushing monitoring export changes")
    mr_url = git.git_add_commit_push(
        "Added monitoring export for "
        f"tenant={request.tenant}, "
        f"application={request.application}, "
        f"site={site.name}"
    )

    if not mr_url:
        raise RuntimeError(
            f"Failed to push monitoring export changes: "
            f"application={request.application}, site={site.name}"
        )

    return mr_url
