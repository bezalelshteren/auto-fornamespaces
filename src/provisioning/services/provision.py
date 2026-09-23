from pathlib import Path

from ..generators.argocd_objects.argocd import generate_argocd
from ..models.provision_request import ProvisionRequest


def provision(request: ProvisionRequest) -> dict:

    output_dir = (
        Path("generated")
        / request.tenant
        / request.environment
    )

    generate_argocd(
        request=request,
        output_dir=output_dir,
    )

    return {
        "status": "generated",
        "tenant": request.tenant,
        "environment": request.environment,
        "application": request.application,
        "output_directory": str(output_dir),
    }