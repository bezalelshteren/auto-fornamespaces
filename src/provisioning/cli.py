import json
import logging
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .models.provision_request import ProvisionRequest
from .services.provision import (
    provision_monitoring_export,
    provision_monitoring_ingest,
    provision_namespace,
    provision_argo,
)


logger = logging.getLogger("provisioning.cli")


def ask(prompt: str, default: str | None = None) -> str:
    """Ask for a string, optionally using a default value."""
    if default is not None:
        value = input(f"{prompt} [{default}]: ").strip()
        return value or default

    return input(f"{prompt}: ").strip()


def ask_bool(prompt: str, default: bool = False) -> bool:
    """Ask for a boolean value."""
    default_text = "yes" if default else "no"

    while True:
        value = input(
            f"{prompt} [yes/no, default={default_text}]: "
        ).strip().lower()

        if not value:
            return default

        if value in {"yes", "y", "true", "1"}:
            return True

        if value in {"no", "n", "false", "0"}:
            return False

        print("Please enter yes or no.")


def ask_required(prompt: str) -> str:
    """Ask until a non-empty value is provided."""
    while True:
        value = ask(prompt)

        if value:
            return value

        print("This field is required.")


def ask_sites() -> list[dict[str, Any]]:
    """Collect independent configuration for each target site."""

    sites: list[dict[str, Any]] = []
    seen_sites: set[str] = set()

    print("\n--- Target sites ---")
    print("Enter site names one at a time.")
    print("Press Enter without a value when finished.")

    while True:
        name = ask("Site name")

        if not name:
            if sites:
                break

            print("At least one site is required.")
            continue

        if name in seen_sites:
            print(f"Site '{name}' was already added.")
            continue

        seen_sites.add(name)

        print(f"\n--- Configuration for site: {name} ---")

        # Namespace
        print("\nNamespace configuration")

        namespace_enabled = ask_bool(
            "Enable namespace provisioning?",
            default=True,
        )

        namespace: dict[str, Any] = {
            "enabled": namespace_enabled,
        }

        if namespace_enabled:
            namespace["customer_yahalom"] = ask_bool(
                "Is this a Yahalom customer?",
                default=False,
            )

            namespace["lifecycle"] = ask_required(
                "Lifecycle (dev/test/prod)",
            )

            namespace["ldap_group"] = ask_required(
                "LDAP group",
            )

        # Argo CD
        print("\nArgo CD configuration")

        argocd_enabled = ask_bool(
            "Enable Argo CD provisioning?",
            default=True,
        )

        argocd: dict[str, Any] = {
            "enabled": argocd_enabled,
        }

        if argocd_enabled:
            print("1. Application")
            print("2. ApplicationSet")

            while True:
                choice = ask("Resource type (1/2)", default="1")

                if choice == "1":
                    argocd["type"] = "application"
                    break

                if choice == "2":
                    argocd["type"] = "application_set"
                    break

                print("Please enter 1 or 2.")

            argocd["git_repo_url"] = ask_required(
                "Application Git repository URL",
            )

        # Monitoring
        print("\nMonitoring configuration")

        monitoring_enabled = ask_bool(
            "Enable monitoring?",
            default=True,
        )

        monitoring: dict[str, Any] = {
            "enabled": monitoring_enabled,
        }

        if monitoring_enabled:
            monitoring["ingest"] = ask_bool(
                "Enable monitoring ingest?",
                default=True,
            )

            monitoring["export"] = ask_bool(
                "Enable monitoring export?",
                default=True,
            )

            if monitoring["ingest"] or monitoring["export"]:
                monitoring["ip"] = ask(
                    "Monitoring IP",
                )

                monitoring["ip_pmm"] = ask(
                    "PMM IP",
                )

                monitoring["ecs_id"] = ask(
                    "ECS ID",
                )

                monitoring["ecs_token"] = ask(
                    "ECS token",
                )

        sites.append(
            {
                "name": name,
                "namespace": namespace,
                "argocd": argocd,
                "monitoring": monitoring,
            }
        )

        print(f"\nSite '{name}' added.")

        if not ask_bool("Add another site?", default=True):
            break

    return sites


def build_request_data() -> dict[str, Any]:
    """Collect the complete provisioning request."""

    print("\n====================================")
    print(" Provisioning Automation")
    print("====================================")

    print("\n--- General configuration ---")

    tenant = ask_required("Tenant")
    team = ask_required("Team")
    application = ask_required("Application")

    customer_yahalom = ask_bool(
        "Is this a Yahalom customer?",
        default=False,
    )

    sites = ask_sites()

    return {
        "tenant": tenant,
        "team": team,
        "application": application,
        "customer_yahalom": customer_yahalom,
        "sites": sites,
    }


def save_request(
    data: dict[str, Any],
    output_path: Path,
) -> None:
    """Save the request JSON to disk."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )


def run_site_service(
    site_name: str,
    service_name: str,
    service,
    request: ProvisionRequest,
    site,
) -> dict[str, str]:
    """Run one provisioning service and record its result."""

    print(f"\n[{site_name}] Starting {service_name}...")

    try:
        result = service(request, site)

        print(f"[{site_name}] {service_name}: completed")

        return {
            "site": site_name,
            "service": service_name,
            "status": "success",
            "result": str(result),
        }

    except Exception as exc:
        logger.exception(
            "Provisioning service failed: site=%s service=%s",
            site_name,
            service_name,
        )

        print(
            f"[{site_name}] {service_name}: FAILED - {exc}"
        )

        return {
            "site": site_name,
            "service": service_name,
            "status": "failed",
            "error": str(exc),
        }


def run_provisioning(
    request: ProvisionRequest,
) -> list[dict[str, str]]:
    """
    Execute the enabled provisioning services for every site.

    A failure in one service does not prevent other services
    or other sites from running.
    """

    results: list[dict[str, str]] = []

    for site in request.sites:
        print("\n====================================")
        print(f" Provisioning site: {site.name}")
        print("====================================")

        services = []

        if site.namespace.enabled:
            services.append(
                ("namespace", provision_namespace)
            )

        if site.argocd.enabled:
            services.append(
                ("argocd", provision_argo)
            )

        if site.monitoring.enabled:
            if site.monitoring.ingest:
                services.append(
                    (
                        "monitoring_ingest",
                        provision_monitoring_ingest,
                    )
                )

            if site.monitoring.export:
                services.append(
                    (
                        "monitoring_export",
                        provision_monitoring_export,
                    )
                )

        if not services:
            results.append(
                {
                    "site": site.name,
                    "service": "all",
                    "status": "skipped",
                    "reason": "No provisioning services enabled",
                }
            )
            print("No provisioning services enabled for this site.")
            continue

        for service_name, service in services:
            result = run_site_service(
                site_name=site.name,
                service_name=service_name,
                service=service,
                request=request,
                site=site,
            )

            results.append(result)

    return results


def print_summary(results: list[dict[str, str]]) -> None:
    """Print a summary of all provisioning operations."""

    print("\n====================================")
    print(" Provisioning Summary")
    print("====================================")

    for result in results:
        site = result["site"]
        service = result["service"]
        status = result["status"]

        print(f"{site} | {service} | {status.upper()}")

        if "error" in result:
            print(f"  Error: {result['error']}")

        if "reason" in result:
            print(f"  Reason: {result['reason']}")

    failed = sum(
        result["status"] == "failed"
        for result in results
    )

    succeeded = sum(
        result["status"] == "success"
        for result in results
    )

    skipped = sum(
        result["status"] == "skipped"
        for result in results
    )

    print("\nTotals:")
    print(f"  Successful: {succeeded}")
    print(f"  Failed:     {failed}")
    print(f"  Skipped:    {skipped}")

    if failed:
        print("\nProvisioning completed with failures.")
    else:
        print("\nAll requested provisioning operations completed.")


def main() -> None:
    """CLI entry point."""

    # 1. Collect request
    data = build_request_data()

    # 2. Display request
    print("\n====================================")
    print(" Generated Provision Request")
    print("====================================")

    print(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        )
    )

    # 3. Validate request
    print("\nValidating request...")

    try:
        request = ProvisionRequest.model_validate(data)

    except ValidationError as exc:
        print("\nINVALID PROVISION REQUEST")
        print(exc)
        return

    print("Request is valid.")

    # 4. Save request
    output_path = Path("request.json")

    try:
        save_request(data, output_path)
    except OSError as exc:
        print(f"Failed to save request: {exc}")
        return

    print(f"Request saved to: {output_path.resolve()}")

    # 5. Confirm execution
    print("\nThe next step may modify Git repositories.")

    if not ask_bool(
        "Run provisioning for all configured sites?",
        default=False,
    ):
        print("Provisioning cancelled.")
        return

    # 6. Execute services
    print("\n====================================")
    print(" Starting provisioning")
    print("====================================")

    results = run_provisioning(request)

    # 7. Print final summary
    print_summary(results)

    if any(result["status"] == "failed" for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
