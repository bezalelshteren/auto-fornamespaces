from ..models.provision_request import ProvisionRequest


def build_names(request: ProvisionRequest) -> dict[str, str]:
    tenant = request.tenant
    lifecycle = request.lifecycle
    application = request.application

    return {
        "namespace": f"{tenant}-{lifecycle}-{application}",
        "project_name": f"{tenant}-{lifecycle}",
        "application_name": f"{tenant}-{lifecycle}-{application}",
        "application_set_name": f"{tenant}-{lifecycle}-applications",
    }