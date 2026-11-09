from pathlib import Path
import logging

from jinja2 import Environment, FileSystemLoader

from ...config.settings import (
    ARGOCD_INFRA_REPOSITORY,
    ARGOCD_INFRA_REPOSITORIES,
    ARGOCD_TEMPLATES_DIR,
    BASE_DIR,
)
from ...models.git_services import GitActions
from ...models.provision_request import ProvisionRequest


logger = logging.getLogger("provisioning")

INFRA_REPOSITORY_NAME = "infra1"

INFRA_REPOSITORY_ROOT = "blackops"
INFRA_TENANTS_ROOT = "argocd-tenants"

INFRA_DEFAULT_BRANCH = "master"



ENVIRONMENT_DIRECTORIES = {
    "project": "argocd-project",
    "programs": "argocd-programs",
}


def _get_environment_git_repo(environment: str) -> str:
    """Return the Git repository URL configured for an environment."""
    config = ARGOCD_INFRA_REPOSITORIES.get(environment)

    if not config:
        raise ValueError(
            f"Missing Git repository configuration for environment: {environment}"
        )

    git_repo = config.get("git_repo")

    if not git_repo:
        raise ValueError(
            f"Missing git_repo URL for environment: {environment}"
        )

    logger.info(
        "[argocd_infra] Source repository | environment=%s | git_repo=%s",
        environment,
        git_repo,
    )

    return git_repo


# ============================================================
# Jinja templates
# ============================================================

APP_PROJECT_TEMPLATES = {
    "namespace": "app-project-infra-namespace.yaml.j2",
    "monitoring": "app-project-infra-monitoring.yaml.j2",
}


APPLICATION_SET_TEMPLATES = {
    "namespace": "application-infra-namespace.yaml.j2",
    "monitoring": "application-infra-monitoring.yaml.j2",
}



def generate_argocd_infra(request: ProvisionRequest) -> dict:
    """
    Generate ArgoCD infrastructure objects in one Git repository.

    All environments are generated in one checkout,
    one feature branch and one Git push.
    """

    logger.info(
        "[argocd_infra] START | tenant=%s | application=%s | sites=%s",
        request.tenant,
        request.application,
        len(request.sites),
    )

    try:
        # ----------------------------------------------------
        # 1. Collect generation jobs
        # ----------------------------------------------------

        jobs = _collect_jobs(request)

        if not jobs:
            logger.info("[argocd_infra] No enabled jobs found.")

            return {
                "status": "unchanged",
                "tenant": request.tenant,
                "application": request.application,
                "repository": INFRA_REPOSITORY_NAME,
                "sites": [],
            }

        logger.info(
            "[argocd_infra] Jobs collected: %s",
            {
                environment: [
                    (site.name, component, lifecycle)
                    for site, component, lifecycle in environment_jobs
                ]
                for environment, environment_jobs in jobs.items()
            },
        )

        # ----------------------------------------------------
        # 2. Load repository configuration
        # ----------------------------------------------------

        config = ARGOCD_INFRA_REPOSITORY

        if not config or not config.get("git_repo"):
            raise ValueError(
                "Missing Git repository configuration for infra1"
            )

        repo_path = Path(
            config.get("local_path") or INFRA_REPOSITORY_NAME
        )

        if not repo_path.is_absolute():
            repo_path = BASE_DIR / "git-repos" / repo_path

        repo_path = repo_path.resolve()

        logger.info(
            "[argocd_infra] Repository configuration | remote=%s | "
            "local_path=%s | default_branch=%s",
            config["git_repo"],
            repo_path,
            INFRA_DEFAULT_BRANCH,
        )

        # ----------------------------------------------------
        # 3. Clone/update repository ONCE
        # ----------------------------------------------------

        git = GitActions(config["git_repo"], repo_path)

        logger.info(
            "[argocd_infra] Git clone/update started | path=%s",
            repo_path,
        )

        if not git.clone_or_update(
            target_revision=INFRA_DEFAULT_BRANCH
        ):
            raise RuntimeError(
                f"Git clone/update failed: {INFRA_REPOSITORY_NAME}"
            )

        if not git.directory_exists():
            raise RuntimeError(
                f"Invalid Git repository directory: {repo_path}"
            )

        logger.info(
            "[argocd_infra] Repository ready | path=%s | branch=%s",
            repo_path,
            git.get_current_branch(),
        )


        # branch = _build_branch_name(request)
        branch_name = "feat/argocd-infra/" + request.tenant
        branch = git.checkout_branch(branch_name)

        logger.info(
            "[argocd_infra] Checking out feature branch=%s",
            branch,
        )

        # if not git.checkout_branch(branch):
        #     raise RuntimeError(
        #         f"Cannot checkout feature branch: {branch}"
        #     )

        current_branch = git.get_current_branch()

        logger.info(
            "[argocd_infra] Current branch=%s",
            current_branch,
        )

        if current_branch in {
            INFRA_DEFAULT_BRANCH,
            "master",
            None,
            "HEAD",
        }:
            raise RuntimeError(
                f"Refusing to generate/push on protected branch: "
                f"{current_branch}"
            )


        jinja = Environment(
            loader=FileSystemLoader(str(ARGOCD_TEMPLATES_DIR)),
            autoescape=False,
            keep_trailing_newline=True,
        )

        logger.info(
            "[argocd_infra] Jinja initialized | templates=%s",
            ARGOCD_TEMPLATES_DIR,
        )

        # ----------------------------------------------------
        # 6. Plan all objects for all environments
        # ----------------------------------------------------

        planned, existing = _plan_objects(
            request=request,
            jobs=jobs,
            repo_path=repo_path,
        )

        logger.info(
            "[argocd_infra] Planning completed | planned=%s | existing=%s",
            len(planned),
            len(existing),
        )

        if not planned:
            logger.info(
                "[argocd_infra] Nothing new to generate."
            )

            return {
                "status": "unchanged",
                "tenant": request.tenant,
                "application": request.application,
                "repository": INFRA_REPOSITORY_NAME,
                "repository_path": str(repo_path),
                "branch": current_branch,
                "generated": [],
                "already_exists": existing,
            }

        # ----------------------------------------------------
        # 7. Render and write all files
        # ----------------------------------------------------

        generated = _render_and_write(
            planned=planned,
            jinja=jinja,
        )

        if not generated:
            logger.info(
                "[argocd_infra] No new files generated."
            )

            return {
                "status": "unchanged",
                "tenant": request.tenant,
                "application": request.application,
                "repository": INFRA_REPOSITORY_NAME,
                "repository_path": str(repo_path),
                "branch": current_branch,
                "generated": [],
                "already_exists": existing,
            }

        # ----------------------------------------------------
        # 8. Git commit and push ONCE
        # ----------------------------------------------------

        commit_message = (
            f"feat: add ArgoCD infra objects for "
            f"{request.tenant}/{request.application}"
        )

        logger.info(
            "[argocd_infra] Git commit/push started | "
            "branch=%s | files=%s | message=%s",
            branch,
            len(generated),
            commit_message,
        )

        if not git.git_add_commit_push(
            commit_message=commit_message
        ):
            raise RuntimeError(
                "Git add/commit/push failed for infra1"
            )

        logger.info(
            "[argocd_infra] SUCCESS | repository=%s | "
            "path=%s | branch=%s | generated=%s",
            INFRA_REPOSITORY_NAME,
            repo_path,
            branch,
            generated,
        )

        return {
            "status": "pushed",
            "tenant": request.tenant,
            "application": request.application,
            "repository": INFRA_REPOSITORY_NAME,
            "repository_path": str(repo_path),
            "branch": branch,
            "generated": generated,
            "already_exists": existing,
        }

    except Exception:
        logger.exception(
            "[argocd_infra] FAILED | tenant=%s | application=%s",
            request.tenant,
            request.application,
        )
        raise


# ============================================================
# Collect jobs
# ============================================================

def _collect_jobs(request: ProvisionRequest) -> dict:
    """
    Collect all required jobs.

    Namespace:
        The target cluster is taken directly from site.name.
        Lifecycle is metadata and does not determine the cluster.

    Monitoring:
        All monitoring objects -> monitoring1
    """

    jobs = {}

    for site in request.sites:

        lifecycle = str(
            site.namespace.lifecycle or ""
        ).lower()

        logger.info(
            "[argocd_infra] Site=%s | lifecycle=%s | "
            "namespace_enabled=%s | monitoring_enabled=%s | "
            "ingest=%s | export=%s",
            site.name,
            lifecycle,
            site.namespace.enabled,
            site.monitoring.enabled,
            site.monitoring.ingest,
            site.monitoring.export,
        )

        if not lifecycle:
            raise ValueError(
                f"Missing lifecycle for site: {site.name}"
            )

        # ----------------------------------------------------
        # Namespace
        # ----------------------------------------------------

        if site.namespace.enabled:

            # The cluster name is the environment/repository key.
            # Do not infer the cluster from lifecycle: multiple clusters
            # may use the same lifecycle (for example, MOBILE + dev).
            environment = site.name

            jobs.setdefault(environment, []).append(
                (site, "namespace", lifecycle)
            )

            logger.info(
                "[argocd_infra] Namespace job added | "
                "site=%s | environment=%s",
                site.name,
                environment,
            )

        # ----------------------------------------------------
        # Monitoring
        # ----------------------------------------------------

        if site.monitoring.enabled and (
            site.monitoring.ingest
            or site.monitoring.export
        ):

            jobs.setdefault("monitoring1", []).append(
                (site, "monitoring", lifecycle)
            )

            logger.info(
                "[argocd_infra] Monitoring job added | "
                "site=%s | environment=monitoring1",
                site.name,
            )

    return jobs


# ============================================================
# Plan objects
# ============================================================

def _plan_objects(
    request: ProvisionRequest,
    jobs: dict,
    repo_path: Path,
) -> tuple[list, list]:

    planned = []
    existing = []

    handled_projects = set()

    from ...services.naming import build_names

    for environment, environment_jobs in jobs.items():

        # Directory names are shared by all environments. The Git source
        # repository remains environment-specific.
        directory_config = ENVIRONMENT_DIRECTORIES
        source_repo = _get_environment_git_repo(environment)

        environment_root = (
            repo_path
            / INFRA_REPOSITORY_ROOT
            / INFRA_TENANTS_ROOT
            / environment
        )

        logger.info(
            "[argocd_infra] Environment destination | "
            "environment=%s | root=%s",
            environment,
            environment_root,
        )

        for site, component, lifecycle in environment_jobs:

            logger.info(
                "[argocd_infra] Building objects | "
                "environment=%s | site=%s | component=%s | lifecycle=%s",
                environment,
                site.name,
                component,
                lifecycle,
            )

            names = build_names(request, site)

            context = {
                "request": request,
                "site": site,
                "names": names,
                "cluster": site.name,
                "component": component,
                "environment": component,
                "lifecycle": lifecycle,
                "tenant": request.tenant,
                "team": request.team,
                "application": request.application,
                "namespace_name": names.get("namespace"),
                "argo_environment": environment,
                "source_repo": source_repo,
            }

            # ------------------------------------------------
            # AppProject path
            # ------------------------------------------------

            project_file = (
                environment_root
                / directory_config["project"]
                / request.tenant
                / f"{lifecycle}.yaml"
            )

            # ------------------------------------------------
            # ApplicationSet paths
            # ------------------------------------------------

            app_dir = (
                environment_root
                / directory_config["programs"]
                / site.name
                / request.tenant
            )

            application_file = (
                app_dir / f"{request.application}.yaml"
            )

            appset_file = (
                app_dir / "applicationSet.yaml"
            )

            logger.info(
                "[argocd_infra] Target paths | "
                "project=%s | application=%s | appset=%s",
                project_file,
                application_file,
                appset_file,
            )

            # ------------------------------------------------
            # AppProject - once per environment/tenant/lifecycle
            # ------------------------------------------------

            project_key = (
                environment,
                request.tenant,
                lifecycle,
            )

            if project_key not in handled_projects:

                if project_file.exists():

                    existing.append(str(project_file))

                    logger.info(
                        "[argocd_infra] AppProject exists; skipping: %s",
                        project_file,
                    )

                else:

                    planned.append(
                        (
                            APP_PROJECT_TEMPLATES[component],
                            project_file,
                            context,
                            environment,
                        )
                    )

                handled_projects.add(project_key)

            # ------------------------------------------------
            # ApplicationSet
            # ------------------------------------------------

            if appset_file.exists():

                existing.append(str(appset_file))

                logger.info(
                    "[argocd_infra] ApplicationSet exists; skipping: %s",
                    appset_file,
                )

            else:

                planned.append(
                    (
                        APPLICATION_SET_TEMPLATES[component],
                        appset_file,
                        context,
                        environment,
                    )
                )

    return planned, existing



def _render_and_write(
    planned: list,
    jinja: Environment,
) -> list:

    generated = []

    for (
        template_name,
        output_file,
        context,
        environment,
    ) in planned:

        logger.info(
            "[argocd_infra] Rendering | environment=%s | "
            "template=%s | output=%s",
            environment,
            template_name,
            output_file,
        )

        # Do not overwrite existing files.
        if output_file.exists():

            logger.info(
                "[argocd_infra] File already exists; skipping: %s",
                output_file,
            )

            continue

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        template = jinja.get_template(template_name)

        rendered = template.render(**context)

        try:

            # Exclusive creation prevents accidental overwrite.
            with output_file.open(
                "x",
                encoding="utf-8",
            ) as file:

                file.write(rendered)

            generated.append(str(output_file))

            logger.info(
                "[argocd_infra] File generated | "
                "path=%s | bytes=%s",
                output_file,
                len(rendered.encode("utf-8")),
            )

        except FileExistsError:

            logger.info(
                "[argocd_infra] File appeared during generation; "
                "skipping: %s",
                output_file,
            )

    return generated
