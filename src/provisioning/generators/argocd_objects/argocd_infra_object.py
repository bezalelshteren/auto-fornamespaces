from pathlib import Path
import re
import logging

from jinja2 import Environment, FileSystemLoader

from ...config.settings import (
    ARGOCD_INFRA_REPOSITORY,
    ARGOCD_TEMPLATES_DIR,
    BASE_DIR,
)
from ...models.git_services import GitActions
from ...models.provision_request import ProvisionRequest

logger = logging.getLogger("provisioning")


LIFECYCLE_ENV = {
    "dev": "dev1",
    "stg": "stg1",
    "prd": "prd1",
}

APP_PROJECT_TEMPLATES = {
    "namespace": "app-project-infra-namespace.yaml.j2",
    "monitoring": "app-project-infra-monitoring.yaml.j2",
}

APPLICATION_TEMPLATE = "application.yaml.j2"

APPLICATION_SET_TEMPLATES = {
    "namespace": "application-infra-namespace.yaml.j2",
    "monitoring": "application-infra-monitoring.yaml.j2",
}


def generate_argocd_infra(request: ProvisionRequest) -> dict:
    logger.info(
        "[argocd_infra] START | tenant=%s | application=%s | sites=%s",
        request.tenant,
        request.application,
        len(request.sites),
    )

    jobs = {}

    try:
        # Collect all required ArgoCD infrastructure objects.
        # The key is the destination site inside the single infra repository.
        for site in request.sites:
            lifecycle = str(site.namespace.lifecycle or "").lower()

            logger.info(
                "[argocd_infra] Site=%s | lifecycle=%s | namespace=%s | "
                "monitoring=%s | ingest=%s | export=%s",
                site.name,
                lifecycle,
                site.namespace.enabled,
                site.monitoring.enabled,
                site.monitoring.ingest,
                site.monitoring.export,
            )

            if site.namespace.enabled:
                if lifecycle not in LIFECYCLE_ENV:
                    raise ValueError(f"Invalid lifecycle: {lifecycle}")

                environment = LIFECYCLE_ENV[lifecycle]
                jobs.setdefault(environment, []).append(
                    (site, "namespace", lifecycle)
                )

                logger.info(
                    "[argocd_infra] Namespace job added | site=%s | env=%s",
                    site.name,
                    environment,
                )

            if site.monitoring.enabled and (
                site.monitoring.ingest or site.monitoring.export
            ):
                if lifecycle not in LIFECYCLE_ENV:
                    raise ValueError(
                        f"Invalid lifecycle for monitoring: {lifecycle}"
                    )

                jobs.setdefault("monitoring1", []).append(
                    (site, "monitoring", lifecycle)
                )

                logger.info(
                    "[argocd_infra] Monitoring job added | site=%s | env=monitoring1",
                    site.name,
                )

        logger.info(
            "[argocd_infra] Jobs collected: %s",
            {
                env: [
                    (site.name, component, lifecycle)
                    for site, component, lifecycle in env_jobs
                ]
                for env, env_jobs in jobs.items()
            },
        )

        results = []

        # Each environment is written to its own directory, but all directories
        # are committed to the same infra Git repository.
        for environment, environment_jobs in jobs.items():
            logger.info(
                "[argocd_infra] Processing site=%s | jobs=%s | repository=infra",
                environment,
                len(environment_jobs),
            )

            result = _process_environment(
                request,
                environment,
                environment_jobs,
            )

            results.append(result)

            logger.info(
                "[argocd_infra] Site result: %s",
                result,
            )

        logger.info(
            "[argocd_infra] SUCCESS | tenant=%s | application=%s",
            request.tenant,
            request.application,
        )

        return {
            "status": "success",
            "tenant": request.tenant,
            "application": request.application,
            "repository": "infra",
            "sites": results,
        }

    except Exception:
        logger.exception(
            "[argocd_infra] FAILED | tenant=%s | application=%s",
            request.tenant,
            request.application,
        )
        raise


def _process_environment(request, environment, jobs):
    logger.info(
        "[argocd_infra] START site=%s | repository=infra",
        environment,
    )

    stage = "load_repository_config"
    try:
        config = ARGOCD_INFRA_REPOSITORY

        logger.info(
            "[argocd_infra] Infra repository config | config=%s",
            {
                "local_path": config.get("local_path") if config else None,
                "git_repo_configured": bool(config and config.get("git_repo")),
            },
        )

        if not config or not config.get("git_repo"):
            raise ValueError("Missing Git repository configuration for infra")

        stage = "resolve_repository_path"
        repo_path = Path(config["local_path"])

        if not repo_path.is_absolute():
            repo_path = BASE_DIR / "git-repos" / repo_path

        logger.info(
            "[argocd_infra] Infra repository path=%s",
            repo_path,
        )

        stage = "initialize_git_actions"
        git = GitActions(config["git_repo"], repo_path)

        logger.info("[argocd_infra] Git clone/update started | repository=infra | path=%s", repo_path)
        stage = "git_clone_or_update"

        if not git.clone_or_update(target_revision="master"):
            raise RuntimeError("Git clone/update failed: infra")

        logger.info("[argocd_infra] Git clone/update completed | repository=infra")

        stage = "validate_git_directory"
        if not git.directory_exists():
            raise RuntimeError(f"Invalid Git repository: {repo_path}")

        stage = "initialize_jinja"
        jinja = Environment(
            loader=FileSystemLoader(str(ARGOCD_TEMPLATES_DIR)),
            autoescape=False,
            keep_trailing_newline=True,
        )

        logger.info(
            "[argocd_infra] Jinja initialized | templates=%s",
            ARGOCD_TEMPLATES_DIR,
        )

        planned = []
        existing = []
        handled_projects = set()

        from ...services.naming import build_names

        for site, component, lifecycle in jobs:
            stage = f"build_objects:{site.name}:{component}:{lifecycle}"
            logger.info(
                "[argocd_infra] Building objects | destination_site=%s | source_site=%s | component=%s | lifecycle=%s",
                environment,
                site.name,
                component,
                lifecycle,
            )

            logger.info("[argocd_infra] Calling build_names | source_site=%s", site.name)
            names = build_names(request, site)

            logger.info(
                "[argocd_infra] Names generated | site=%s | names=%s",
                site.name,
                names,
            )

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
            }

            # All objects are stored under the Black Ops tenant in the
            # single infra repository, separated by destination site.
            site_root = repo_path / "blackops" / environment

            project_file = (
                site_root / "argocd-objects"
                / request.tenant / f"{lifecycle}.yaml"
            )

            app_dir = (
                site_root / "argocd-programs" / site.name
                / request.tenant / lifecycle
            )

            application_file = app_dir / f"{request.application}.yaml"
            appset_file = app_dir / "applicationSet.yaml"

            logger.info(
                "[argocd_infra] Target paths | project=%s | application=%s | appset=%s",
                project_file,
                application_file,
                appset_file,
            )

            # AppProject - once per lifecycle in this destination site.
            project_key = (environment, lifecycle)
            if project_key not in handled_projects:
                if not project_file.exists():
                    template = APP_PROJECT_TEMPLATES[component]

                    logger.info(
                        "[argocd_infra] AppProject missing | template=%s | path=%s",
                        template,
                        project_file,
                    )

                    planned.append((
                        template,
                        project_file,
                        context,
                    ))
                else:
                    logger.info(
                        "[argocd_infra] AppProject already exists: %s",
                        project_file,
                    )
                    existing.append(str(project_file))

                handled_projects.add(project_key)

            # Application
            if not application_file.exists():
                logger.info(
                    "[argocd_infra] Application missing | template=%s | path=%s",
                    APPLICATION_TEMPLATE,
                    application_file,
                )

                planned.append((
                    APPLICATION_TEMPLATE,
                    application_file,
                    context,
                ))
            else:
                logger.info(
                    "[argocd_infra] Application already exists: %s",
                    application_file,
                )
                existing.append(str(application_file))

            # ApplicationSet
            if not appset_file.exists():
                template = APPLICATION_SET_TEMPLATES[component]

                logger.info(
                    "[argocd_infra] ApplicationSet missing | template=%s | path=%s",
                    template,
                    appset_file,
                )

                planned.append((
                    template,
                    appset_file,
                    context,
                ))
            else:
                logger.info(
                    "[argocd_infra] ApplicationSet already exists: %s",
                    appset_file,
                )

                existing.append(str(appset_file))

        logger.info(
            "[argocd_infra] Planning completed | site=%s | planned=%s | existing=%s",
            environment,
            len(planned),
            len(existing),
        )

        if not planned:
            logger.info(
                "[argocd_infra] Nothing to generate | site=%s",
                environment,
            )

            return {
                "site": environment,
                "status": "unchanged",
                "generated": [],
                "already_exists": existing,
            }

        branch = re.sub(
            r"[^A-Za-z0-9._/-]+",
            "-",
            f"feat/argocd_infra/{environment}-{request.tenant}-{request.application}",
        ).strip("-")

        logger.info(
            "[argocd_infra] Checkout branch=%s | repository=infra",
            branch,
        )

        stage = "git_checkout_branch"
        checkout_result = git.checkout_branch(branch)
        logger.info(
            "[argocd_infra] Checkout result | branch=%s | result=%s",
            branch, checkout_result,
        )
        if not checkout_result:
            raise RuntimeError(f"Cannot checkout branch: {branch}")

        current_branch = git.get_current_branch()

        logger.info(
            "[argocd_infra] Current branch=%s",
            current_branch,
        )

        if current_branch in {"main", "master", None, "HEAD"}:
            raise RuntimeError(f"Refusing to push to branch: {current_branch}")

        generated = []

        for template_name, output_file, context in planned:
            stage = f"render_template:{template_name}:{output_file}"
            logger.info(
                "[argocd_infra] Rendering template=%s | output=%s",
                template_name,
                output_file,
            )

            if output_file.exists():
                logger.warning(
                    "[argocd_infra] File already exists, skipping: %s",
                    output_file,
                )
                existing.append(str(output_file))
                continue

            output_file.parent.mkdir(parents=True, exist_ok=True)

            logger.info("[argocd_infra] Loading Jinja template: %s", template_name)
            template = jinja.get_template(template_name)
            logger.info("[argocd_infra] Rendering Jinja template: %s", template_name)
            rendered = template.render(**context)
            logger.info(
                "[argocd_infra] Template rendered | template=%s | bytes=%s",
                template_name, len(rendered.encode("utf-8")),
            )

            stage = f"write_file:{output_file}"
            try:
                with output_file.open("x", encoding="utf-8") as file:
                    file.write(rendered)

                generated.append(str(output_file))

                logger.info(
                    "[argocd_infra] File generated successfully: %s",
                    output_file,
                )

            except FileExistsError:
                logger.warning(
                    "[argocd_infra] File appeared during generation: %s",
                    output_file,
                )
                existing.append(str(output_file))

        if not generated:
            logger.info(
                "[argocd_infra] No new files generated | site=%s",
                environment,
            )

            return {
                "site": environment,
                "status": "unchanged",
                "generated": [],
                "already_exists": existing,
            }

        message = (
            f"feat: add ArgoCD infra objects for "
            f"{request.tenant}/{request.application} ({environment})"
        )

        logger.info(
            "[argocd_infra] Git commit/push started | branch=%s | files=%s | message=%s",
            branch,
            len(generated),
            message,
        )

        stage = "git_add_commit_push"
        push_result = git.git_add_commit_push(commit_message=message)
        logger.info(
            "[argocd_infra] Git add/commit/push result | site=%s | result=%s",
            environment, push_result,
        )
        if not push_result:
            raise RuntimeError(f"Git commit/push failed: {environment}")

        logger.info(
            "[argocd_infra] Git commit/push completed | site=%s | branch=%s",
            environment,
            branch,
        )

        return {
            "site": environment,
            "status": "pushed",
            "branch": branch,
            "generated": generated,
            "already_exists": existing,
        }

    except Exception:
        logger.exception(
            "[argocd_infra] FAILED site=%s | repository=infra | stage=%s",
            environment, stage,
        )
        raise
