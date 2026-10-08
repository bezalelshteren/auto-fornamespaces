from ..models.provision_request import ProvisionRequest


def build_names(request: ProvisionRequest) -> dict[str, str]:
    tenant = request.tenant
    lifecycle = request.lifecycle
    application = request.application
    cluster = request.cluster

    return {

        "tenant": tenant,
        "lifecycle": lifecycle,
        "chart_monitoring": "monitoring-stack-ingest",
        "chart_monitoring_ingest_version": "1.0.0",
        "chart_namespace": "namespace-stack",
        "chart_namespace_version" : "1.0.0",
        "chart_namespace_yahalom": "namespace-stack-yahalom",
        "chart_namespace_yahalom_version" : "1.0.0",
        "namespace": f"{tenant}-{lifecycle}-{application}",
        "project_name": f"{tenant}-{lifecycle}",
        "application_name": f"{tenant}-{lifecycle}-{application}",
        "application_set_name": f"{tenant}-{lifecycle}-applications",
    }