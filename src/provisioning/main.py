from fastapi import FastAPI
from .models.git_services import GitActions
from .services.provision import provision
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

    result = provision(request)

    return result