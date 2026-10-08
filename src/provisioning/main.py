from fastapi import FastAPI

from .services.provision import (
    provision_argo,
    provision_namespace,
    provision_monitoring_export,
    provision_monitoring_ingest,
)

from .models.provision_request import ProvisionRequest

from .services.logging_service import write_log_to_db


app = FastAPI(
    title="Provisioning Automation API"
)


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.post("/provision")
def create_provision(request: ProvisionRequest):

    write_log_to_db(
        level="INFO",
        message=f"Provision started for {request.application}",
    )

    result_argo = provision_argo(request=request)

    provision_namespace(request=request)

    provision_monitoring_ingest(request=request)

    provision_monitoring_export(request=request)

    write_log_to_db(
        level="INFO",
        message=f"Provision completed for {request.application}",
    )

    return {
        "status": "success"
    }