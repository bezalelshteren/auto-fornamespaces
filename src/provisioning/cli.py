import json

from .models.provision_request import ProvisionRequest
from .services.provision import (
    provision_monitoring_export,
    provision_monitoring_ingest,
    provision_namespace,
    provision_argo,
)


def ask(prompt: str, default: str | None = None) -> str:
    """
    Ask the user for a string value.

    If a default value is provided, pressing Enter
    will use the default.
    """
    if default is not None:
        value = input(f"{prompt} [{default}]: ").strip()
        return value or default

    return input(f"{prompt}: ").strip()


def ask_bool(prompt: str, default: bool = False) -> bool:
    """
    Ask the user for a boolean value.

    Accepts:
        y / yes / true / 1
        n / no / false / 0
    """

    default_text = "yes" if default else "no"

    while True:
        value = input(
            f"{prompt} [yes/no, default={default_text}]: "
        ).strip().lower()

        if not value:
            return default

        if value in ("yes", "y", "true", "1"):
            return True

        if value in ("no", "n", "false", "0"):
            return False

        print("Please enter yes or no.")


def ask_sites() -> list[str]:
    """
    Ask for target sites.

    Example:
        dev1,prd1
    """

    while True:
        value = input(
            "Target sites (example: dev1,prd1): "
        ).strip()

        sites = [
            site.strip()
            for site in value.split(",")
            if site.strip()
        ]

        if sites:
            return sites

        print("At least one target site is required.")


def build_request() -> dict:
    """
    Collect all required values from the user
    and build the complete ProvisionRequest dictionary.
    """

    print()
    print("====================================")
    print(" Provisioning Automation")
    print("====================================")
    print()

    # ==========================================================
    # Basic information
    # ==========================================================

    print("--- Basic configuration ---")

    cluster = ask("Cluster")
    tenant = ask("Tenant")
    team = ask("Team")
    application = ask("Application")
    lifecycle = ask("Lifecycle", "dev")
    ldap_group = ask("LDAP group")

    # ==========================================================
    # Target sites
    # ==========================================================

    print()
    print("--- Target sites ---")

    target_sites = ask_sites()

    # ==========================================================
    # Git configuration
    # ==========================================================

    print()
    print("--- Git configuration ---")

    repo_url = ask("Git repository URL")
    target_revision = ask("Git revision", "main")
    path = ask("Git path")

    # ==========================================================
    # Namespace configuration
    # ==========================================================

    print()
    print("--- Namespace configuration ---")

    namespace_enabled = ask_bool(
        "Enable namespace provisioning?",
        default=True,
    )

    customer_yahalom = ask_bool(
        "Customer Yahalom?",
        default=False,
    )

    namespace_config = {
        "enabled": namespace_enabled,
        "customer_yahalom": customer_yahalom,
    }

    # ==========================================================
    # ArgoCD configuration
    # ==========================================================

    print()
    print("--- ArgoCD configuration ---")

    argocd_enabled = ask_bool(
        "Enable ArgoCD?",
        default=True,
    )

    argocd_application = ask_bool(
        "Create ArgoCD Application?",
        default=True,
    )

    argocd_application_set = ask_bool(
        "Create ArgoCD ApplicationSet?",
        default=False,
    )

    argocd = {
        "enabled": argocd_enabled,
        "application": argocd_application,
        "application_set": argocd_application_set,
    }

    # ==========================================================
    # Monitoring configuration
    # ==========================================================

    print()
    print("--- Monitoring configuration ---")

    monitoring_enabled = ask_bool(
        "Enable monitoring?",
        default=True,
    )

    monitoring = {
        "enabled": monitoring_enabled,
    }

    if monitoring_enabled:
        monitoring["ip"] = ask("Monitoring IP")
        monitoring["ip_pmm"] = ask("PMM IP")
        monitoring["ecs_id"] = ask("ECS ID")
        monitoring["ecs_token"] = ask("ECS token")

    # ==========================================================
    # Build complete request
    # ==========================================================

    data = {
        "cluster": cluster,
        "tenant": tenant,
        "team": team,
        "application": application,
        "lifecycle": lifecycle,
        "ldap_group": ldap_group,
        "target_sites": target_sites,

        "git": {
            "repo_url": repo_url,
            "target_revision": target_revision,
            "path": path,
        },

        "namespace_config": namespace_config,

        "argocd": argocd,

        "monitoring": monitoring,
    }

    return data


def main():
    # ==========================================================
    # 1. Ask user for all data
    # ==========================================================

    data = build_request()

    # ==========================================================
    # 2. Show generated JSON
    # ==========================================================

    print()
    print("====================================")
    print(" Generated Provision Request")
    print("====================================")

    print(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        )
    )

    # ==========================================================
    # 3. Validate using Pydantic
    # ==========================================================

    print()
    print("Validating request...")

    try:
        request = ProvisionRequest(**data)

    except Exception as e:
        print()
        print("====================================")
        print(" INVALID PROVISION REQUEST")
        print("====================================")
        print()
        print(e)
        print()

        return

    print("Request is valid.")

    # ==========================================================
    # 4. Save JSON
    # ==========================================================

    json_path = "request.json"

    with open(
        json_path,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print(f"Request saved to: {json_path}")

    # ==========================================================
    # 5. Confirmation
    # ==========================================================

    print()

    confirm = ask_bool(
        "Run provisioning?",
        default=False,
    )

    if not confirm:
        print()
        print("Provisioning cancelled.")
        return

    # ==========================================================
    # 6. Run provisioning
    # ==========================================================

    print()
    print("====================================")
    print(" Starting provisioning")
    print("====================================")
    print()

    # Namespace
    if request.namespace_config.enabled:
        print("Running namespace provisioning...")
        provision_namespace(request)
        print("Namespace provisioning completed.")
    else:
        print("Namespace provisioning is disabled.")

    # ArgoCD
    if request.argocd.enabled:
        print("Running ArgoCD provisioning...")
        provision_argo(request)
        print("ArgoCD provisioning completed.")
    else:
        print("ArgoCD provisioning is disabled.")

    # Monitoring ingest
    if request.monitoring.enabled:
        print("Running monitoring ingest provisioning...")
        provision_monitoring_ingest(request)
        print("Monitoring ingest provisioning completed.")

        print("Running monitoring export provisioning...")
        provision_monitoring_export(request)
        print("Monitoring export provisioning completed.")
    else:
        print("Monitoring is disabled.")

    # ==========================================================
    # Done
    # ==========================================================

    print()
    print("====================================")
    print(" Provisioning completed successfully")
    print("====================================")


if __name__ == "__main__":
    main()

