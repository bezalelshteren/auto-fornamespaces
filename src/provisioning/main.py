
from fastapi import FastAPI, HTTPException

from .models.provision_request import ProvisionRequest
from .services.provision import (
    provision_argo,
    provision_namespace,
    provision_monitoring_export,
    provision_monitoring_ingest,
    provision_argocd_infra,
)

app = FastAPI(
    title="Provisioning Automation API"
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/provision")
def create_provision(request: ProvisionRequest):
    """
    Validate the request and provision every configured site.

    Each site has its own Namespace, ArgoCD and Monitoring
    configuration.
    """


    results = []

    try:
        # ------------------------------------------------------
        # Process each site independently
        # ------------------------------------------------------

        for site in request.sites:
            site_name = site.name


            site_result = {
                "site": site_name,
                "status": "success",
                "components": {},
            }


            # Namespace

            if site.namespace.enabled:
                provision_namespace(
                    request=request,
                    site=site,
                )

                site_result["components"]["namespace"] = "success"
            else:
                site_result["components"]["namespace"] = "skipped"

            # ArgoCD


            if site.argocd.enabled:
                provision_argo(
                    request=request,
                    site=site,

                )

                site_result["components"]["argocd"] = "success"
            else:
                site_result["components"]["argocd"] = "skipped"

            # Monitoring

            if site.monitoring.enabled:

                if site.monitoring.ingest:
                    provision_monitoring_ingest(
                        request=request,
                        site=site,
                    )

                    site_result["components"]["monitoring_ingest"] = (
                        "success"
                    )
                else:
                    site_result["components"]["monitoring_ingest"] = (
                        "skipped"
                    )

                if site.monitoring.export:
                    provision_monitoring_export(
                        request=request,
                        site=site,
                    )

                    site_result["components"]["monitoring_export"] = (
                        "success"
                    )
                else:
                    site_result["components"]["monitoring_export"] = (
                        "skipped"
                    )

            else:
                site_result["components"]["monitoring_ingest"] = "skipped"
                site_result["components"]["monitoring_export"] = "skipped"

            results.append(site_result)

        infra_result = provision_argocd_infra(request)

        results.append({
            "component": "argocd_infrastructure",
            "result": infra_result,
        })

    except Exception as exc:


        raise HTTPException(
            status_code=500,
            detail={
                "status": "failed",
                "error": str(exc),
                "results": results,
            },
        ) from exc


    return {
        "status": "success",
        "application": request.application,
        "results": results,
    }
