def build_log_extra(request, *, stage="provisioning", status="started", request_id=None, target_site=None):
    return {
        "request_id": request_id,
        "stage": stage,
        "status": status,
        "tenant": getattr(request, "tenant", None),
        "team": getattr(request, "team", None),
        "application": getattr(request, "application", None),
        "lifecycle": getattr(request, "lifecycle", None),
        "cluster": getattr(request, "cluster", None),
        "target_site": target_site,
    }
