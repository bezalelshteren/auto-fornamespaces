from pathlib import Path
import logging

from jinja2 import Environment, FileSystemLoader

from ...models.git_services import GitActions
from ...config.settings import TEMPLATES_DIR
from ...models.provision_request import ProvisionRequest, SiteConfig
from ...services.argocd_checks import (
    ProvisionDecision,
    add_source_repo_to_app_project,
    app_project_exists,
)
from ...services.naming import build_names


logger = logging.getLogger("provisioning")


def generate_argocd(
    git: GitActions,
    request: ProvisionRequest,
    site: SiteConfig,
    decision: ProvisionDecision,
    app_project_output_dir: Path,
    applications_output_dir: Path,
) -> None:
    lifecycle = site.namespace.lifecycle

    logger.info(
        "Starting Argo CD generation: tenant=%s, application=%s, "
        "lifecycle=%s, site=%s",
        request.tenant,
        request.application,
        lifecycle,
        site.name,
    )

    # אין צורך להמשיך אם Argo CD אינו מופעל.
    if not site.argocd.enabled:
        logger.info(
            "Argo CD is disabled for site=%s. Skipping generation.",
            site.name,
        )
        return

    if not lifecycle:
        raise ValueError(
            f"Lifecycle is required for Argo CD generation: site={site.name}"
        )

    # בניית השמות שיועברו לתבניות Jinja.
    names = build_names(request, site)

    templates_dir = TEMPLATES_DIR / "argocd-objects"

    environment = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=False,
        keep_trailing_newline=True,
    )

    context = {
        "request": request,
        "site": site,
        "names": names,
        "cluster": site.name,
    }


    if not git.clone_or_update(target_revision="master"):
        logger.error(
            "Failed to clone or update Argo CD repository: site=%s",
            site.name,
        )
        raise RuntimeError(
            f"Failed to clone or update Argo CD repository for site={site.name}"
        )

    app_project_path = app_project_output_dir / f"{lifecycle}.yaml"

    project_exists = app_project_exists(
        git_repo_path=app_project_output_dir.parent.parent,
        tenant=request.tenant,
        lifecycle=lifecycle,
    )

    create_app_project = not project_exists
    update_existing_app_project = project_exists

    logger.info(
        "AppProject decision after Git pull: "
        "site=%s, path=%s, exists=%s, create=%s, update=%s",
        site.name,
        app_project_path,
        project_exists,
        create_app_project,
        update_existing_app_project,
    )

    templates: dict[str, tuple[Path, str]] = {}

    if create_app_project:
        if lifecycle in {"prd", "prod"}:
            templates["app-project_prod.yaml.j2"] = (
                app_project_output_dir,
                f"{lifecycle}.yaml",
            )
        elif lifecycle in {"dev", "stg"}:
            templates["app-project_nonprod.yaml.j2"] = (
                app_project_output_dir,
                f"{lifecycle}.yaml",
            )
        else:
            raise ValueError(
                f"Unsupported lifecycle '{lifecycle}' for site={site.name}"
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

    logger.info(
        "Argo CD generation decision: site=%s, create_app_project=%s, "
        "create_application=%s, create_application_set=%s, "
        "update_existing_app_project=%s",
        site.name,
        create_app_project,
        decision.create_application,
        decision.create_application_set,
        update_existing_app_project,
    )

    # אין שינויים אם אין תבניות ליצירה ואין צורך לעדכן AppProject.
    if not templates and not update_existing_app_project:
        logger.info(
            "No Argo CD changes required for site=%s.",
            site.name,
        )
        return

    branch = (
        f"feat/argocd_objects/"
        f"{request.application}-{lifecycle}-{request.tenant}-{site.name}"
    )

    if not git.checkout_branch(branch):
        logger.error(
            "Failed to checkout Argo CD branch: branch=%s, site=%s",
            branch,
            site.name,
        )
        raise RuntimeError(
            f"Failed to checkout Argo CD branch '{branch}' for site={site.name}"
        )

    if update_existing_app_project:
        if site.argocd.git_repo_url is None:
            raise ValueError(
                f"git_repo_url is required for enabled Argo CD: site={site.name}"
            )

        source_repo = str(site.argocd.git_repo_url)

        logger.info(
            "Updating existing AppProject: site=%s, path=%s, source_repo=%s",
            site.name,
            app_project_path,
            source_repo,
        )

        added = add_source_repo_to_app_project(
            app_project_path=app_project_path,
            source_repo=source_repo,
        )

        if added:
            logger.info(
                "Source repository added to AppProject: site=%s, repo=%s",
                site.name,
                source_repo,
            )
        else:
            logger.info(
                "Source repository already exists in AppProject: "
                "site=%s, repo=%s",
                site.name,
                source_repo,
            )

    for output_dir, _ in templates.values():
        output_dir.mkdir(parents=True, exist_ok=True)

    for template_name, (output_dir, output_filename) in templates.items():
        template = environment.get_template(template_name)
        rendered_content = template.render(**context)

        output_file = output_dir / output_filename

        output_file.write_text(
            rendered_content,
            encoding="utf-8",
        )

        logger.info(
            "Generated Argo CD file: site=%s, template=%s, path=%s",
            site.name,
            template_name,
            output_file,
        )

    commit_message = (
        f"feat: provision Argo CD resources for "
        f"{request.application} ({lifecycle}, {site.name})"
    )

    pushed = git.git_add_commit_push(
        commit_message=commit_message,
    )

    if not pushed:
        logger.warning(
            "Argo CD Git operation returned False: "
            "site=%s, branch=%s. Check whether there are changes to commit.",
            site.name,
            branch,
        )
        return

    logger.info(
        "Argo CD files committed and pushed successfully: "
        "site=%s, branch=%s",
        site.name,
        branch,
    )
