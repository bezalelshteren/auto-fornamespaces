from pathlib import Path
from ...models.git_services import GitActions
from jinja2 import Environment, FileSystemLoader
from ...config.settings import TEMPLATES_DIR
from ...models.provision_request import ProvisionRequest
from ...services.argocd_checks import ProvisionDecision
from ...services.naming import build_names
from ...services.argocd_checks import app_project_exists


def generate_argocd(
    git: GitActions,
    request: ProvisionRequest,
    decision: ProvisionDecision,
    app_project_output_dir: Path,
    applications_output_dir: Path,
    site: str
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
        "cluster": site,
    }

    templates: dict[str, tuple[Path, str]] = {}
    if not git.clone_or_update(target_revision="master"):
        raise RuntimeError(
            f"Failed to clone/update Git repository: "
            f"{git.git_repo_to_do_actions}"
        )

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

    if decision.create_app_project or decision.create_application_set or decision.create_application:


        # Create / checkout feature branch
        branch_name = f"feat/argocd_objects/{request.application}-{request.lifecycle}-{request.tenant}"
        if not git.checkout_branch(branch_name):
            raise RuntimeError(
                f"Failed to checkout branch: {branch_name}"
            )

        # Only now it is safe to create folders inside the repo
        if decision.create_app_project:
            app_project_output_dir.mkdir(
                parents=True,
                exist_ok=True,
            )
        elif not decision.create_app_project:
            if  app_project_exists(
                git_repo_path=git.git_repo_to_do_actions,
                tenant=request.tenant,
                lifecycle=request.lifecycle
            ):
                print(
                    f"[generate_argocd] Argo CD project already exists for tenant: {request.tenant}, lifecycle: {request.lifecycle}. adding jost the new repo"
                )


        if decision.create_application or decision.create_application_set:
            applications_output_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

        for template_name, (output_dir, output_name) in templates.items():
            template = environment.get_template(
                template_name
            )

            rendered = template.render(
                **context
            )

            output_file = output_dir / output_name

            print(f"[generate_argocd] git repo path : {git.git_repo_to_do_actions}")
            print(f"[generate_argocd] writing to     : {output_file.resolve()}")
            print(
                f"[generate_argocd] is under repo? : {git.git_repo_to_do_actions.resolve() in output_file.resolve().parents}")

            output_file.write_text(
                rendered,
                encoding="utf-8",
            )
        if not git.get_current_branch() == "master" and not git.get_current_branch() == "main":
            git.git_add_commit_push(f"added argocd objects for tenant: {request.tenant}, lifecycle: {request.lifecycle}, application: {request.application}" )