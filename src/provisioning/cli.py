
import json
from .models.provision_request import ProvisionRequest
from .services.provision import provision_monitoring_export, provision_monitoring_ingest ,provision_namespace , provision_argo


def main():
    with open(r"C:\Users\User\OneDrive\מסמכים\request.json") as f:
        data = json.load(f)

    request = ProvisionRequest(**data)

    provision_namespace(request)
    provision_argo(request)
    provision_monitoring_ingest(request)
    provision_monitoring_export(request)


    print("created provision request successfully")


if __name__ == "__main__":
    main()