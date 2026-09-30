from fastapi import FastAPI
from .services.provision import provision_argo, provision_namespace ,provision_monitoring
from .models.provision_request import ProvisionRequest


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

    result_argo = provision_argo(request=request)
    provision_namespace(request=request)
    provision_monitoring(request=request)
    return