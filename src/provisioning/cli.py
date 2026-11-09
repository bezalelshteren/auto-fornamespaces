import argparse
import json
import logging
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .models.provision_request import ProvisionRequest

from .services.provision import (
    provision_argo,
    provision_namespace,
    provision_monitoring_export,
    provision_monitoring_ingest,
    provision_argocd_infra,
)


logger = logging.getLogger("provisioning.cli")


# ============================================================
# Project paths
# ============================================================

# Project structure:
#
# automation-for-namespace/
# ├── request.json
# ├── pyproject.toml
# └── src/
#     └── provisioning/
#         └── cli.py

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_REQUEST_FILE = PROJECT_ROOT / "request.json"


# ============================================================
# Load JSON
# ============================================================

def load_request_data(input_path: Path) -> dict[str, Any]:
    """
    Load provisioning request from JSON.
    """

    if not input_path.is_file():
        raise FileNotFoundError(
            f"Request file not found: {input_path}"
        )

    try:
        with input_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in '{input_path}': "
            f"line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            "The JSON root must be an object."
        )

    return data


# ============================================================
# Provisioning execution error
# ============================================================

class ProvisioningExecutionError(Exception):
    """
    Holds partial provisioning results when an operation fails.
    """

    def __init__(
        self,
        message: str,
        results: list[dict[str, Any]],
    ):
        super().__init__(message)
        self.results = results


# ============================================================
# Run provisioning
# ============================================================

def run_provisioning(
    request: ProvisionRequest,
) -> list[dict[str, Any]]:
    """
    Execute provisioning using the same flow as the FastAPI endpoint.

    Execution order:

    1. Process every configured site.
    2. Provision namespace when enabled.
    3. Provision ArgoCD when enabled.
    4. Provision monitoring ingest/export when enabled.
    5. Run ArgoCD INFRA once, after all sites are processed.

    If an operation fails, execution stops and partial results are preserved.
    """

    results: list[dict[str, Any]] = []

    try:

        # ----------------------------------------------------
        # Process each site independently
        # ----------------------------------------------------

        for site in request.sites:

            site_name = site.name

            print("\n====================================")
            print(f" Provisioning site: {site_name}")
            print("====================================")

            site_result = {
                "site": site_name,
                "status": "success",
                "components": {},
            }

            # ------------------------------------------------
            # Namespace
            # ------------------------------------------------

            if site.namespace.enabled:

                print(f"[{site_name}] Starting namespace...")

                provision_namespace(
                    request=request,
                    site=site,
                )

                site_result["components"]["namespace"] = "success"

                print(f"[{site_name}] Namespace completed.")

            else:

                site_result["components"]["namespace"] = "skipped"

            # ------------------------------------------------
            # ArgoCD
            # ------------------------------------------------

            if site.argocd.enabled:

                print(f"[{site_name}] Starting argocd...")

                provision_argo(
                    request=request,
                    site=site,
                )

                site_result["components"]["argocd"] = "success"

                print(f"[{site_name}] ArgoCD completed.")

            else:

                site_result["components"]["argocd"] = "skipped"

            # ------------------------------------------------
            # Monitoring
            # ------------------------------------------------

            if site.monitoring.enabled:

                # Monitoring ingest
                if site.monitoring.ingest:

                    print(
                        f"[{site_name}] Starting monitoring_ingest..."
                    )

                    provision_monitoring_ingest(
                        request=request,
                        site=site,
                    )

                    site_result["components"]["monitoring_ingest"] = (
                        "success"
                    )

                    print(
                        f"[{site_name}] Monitoring ingest completed."
                    )

                else:

                    site_result["components"]["monitoring_ingest"] = (
                        "skipped"
                    )

                # Monitoring export
                if site.monitoring.export:

                    print(
                        f"[{site_name}] Starting monitoring_export..."
                    )

                    provision_monitoring_export(
                        request=request,
                        site=site,
                    )

                    site_result["components"]["monitoring_export"] = (
                        "success"
                    )

                    print(
                        f"[{site_name}] Monitoring export completed."
                    )

                else:

                    site_result["components"]["monitoring_export"] = (
                        "skipped"
                    )

            else:

                site_result["components"]["monitoring_ingest"] = "skipped"

                site_result["components"]["monitoring_export"] = "skipped"

            # ------------------------------------------------
            # Save site result
            # ------------------------------------------------

            results.append(site_result)

        # ----------------------------------------------------
        # ArgoCD INFRA
        # ----------------------------------------------------
        #
        # IMPORTANT:
        # This must run ONCE, after all sites have been processed.
        #
        # The INFRA provisioner receives the complete request and
        # handles the relevant INFRA repositories itself.
        #
        # This is the same behavior as the FastAPI endpoint.
        # ----------------------------------------------------

        print("\n====================================")
        print(" Starting ArgoCD INFRA provisioning")
        print("====================================")

        infra_result = provision_argocd_infra(request)

        results.append(
            {
                "component": "argocd_infrastructure",
                "result": infra_result,
            }
        )

        print("[INFRA] Provisioning completed.")

    except Exception as exc:

        logger.exception(
            "Provisioning execution failed."
        )

        raise ProvisioningExecutionError(
            str(exc),
            results,
        ) from exc

    return results


# ============================================================
# Print summary
# ============================================================

def print_summary(
    results: list[dict[str, Any]],
    error: str | None = None,
) -> None:
    """
    Print provisioning execution summary.
    """

    print("\n====================================")
    print(" Provisioning Summary")
    print("====================================")

    for result in results:

        # ----------------------------------------------------
        # Site result
        # ----------------------------------------------------

        if "site" in result:

            site_name = result["site"]

            print(f"\nSite: {site_name}")
            print(f"Status: {result['status'].upper()}")

            for component, status in result["components"].items():

                print(
                    f"  {component}: {status.upper()}"
                )

        # ----------------------------------------------------
        # INFRA result
        # ----------------------------------------------------

        elif result.get("component") == "argocd_infrastructure":

            print("\nComponent: argocd_infrastructure")

            print(
                f"Result: {result.get('result')}"
            )

    # --------------------------------------------------------
    # Execution status
    # --------------------------------------------------------

    if error:

        print("\n====================================")
        print(" PROVISIONING FAILED")
        print("====================================")

        print(f"Error: {error}")

    else:

        print("\n====================================")
        print(" PROVISIONING COMPLETED")
        print("====================================")

        print("All provisioning operations completed successfully.")


# ============================================================
# CLI arguments
# ============================================================

def parse_args() -> argparse.Namespace:
    """
    Parse CLI arguments.

    Default:
        request.json from project root.

    Optional:
        --request path/to/another-request.json
    """

    parser = argparse.ArgumentParser(
        description="Run provisioning from a JSON request file."
    )

    parser.add_argument(
        "--request",
        type=Path,
        default=DEFAULT_REQUEST_FILE,
        help=(
            "Path to provisioning JSON file. "
            f"Default: {DEFAULT_REQUEST_FILE}"
        ),
    )

    return parser.parse_args()


# ============================================================
# Main
# ============================================================

def main() -> None:
    """
    Main CLI execution.

    1. Load request.json.
    2. Validate request.
    3. Run all site provisioning operations.
    4. Run ArgoCD INFRA once.
    5. Print summary.
    """

    args = parse_args()

    input_path = args.request.expanduser().resolve()

    print("\n====================================")
    print(" Provisioning Automation")
    print("====================================")

    print(f"Project root: {PROJECT_ROOT}")
    print(f"Request file: {input_path}")

    # --------------------------------------------------------
    # 1. Load JSON
    # --------------------------------------------------------

    try:

        data = load_request_data(input_path)

    except (OSError, ValueError) as exc:

        print(f"\nFailed to load request: {exc}")

        raise SystemExit(1) from exc

    # --------------------------------------------------------
    # 2. Display request
    # --------------------------------------------------------

    print("\n====================================")
    print(" Loaded Provision Request")
    print("====================================")

    print(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        )
    )

    # --------------------------------------------------------
    # 3. Validate request
    # --------------------------------------------------------

    print("\nValidating request...")

    try:

        request = ProvisionRequest.model_validate(data)

    except ValidationError as exc:

        print("\nINVALID PROVISION REQUEST")

        print(exc)

        raise SystemExit(1) from exc

    print("Request is valid.")

    # --------------------------------------------------------
    # 4. Run provisioning
    # --------------------------------------------------------

    print("\n====================================")
    print(" Starting provisioning")
    print("====================================")

    try:

        results = run_provisioning(request)

    except ProvisioningExecutionError as exc:

        print_summary(
            results=exc.results,
            error=str(exc),
        )

        raise SystemExit(1) from exc

    # --------------------------------------------------------
    # 5. Print summary
    # --------------------------------------------------------

    print_summary(results)

    print("\nProvisioning finished successfully.")


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    main()
