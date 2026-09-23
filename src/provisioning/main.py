from fastapi import FastAPI

from .models.provision_request import ProvisionRequest
from .services.provision import provision


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

    result = provision(request)

    return result