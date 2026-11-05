from pathlib import Path
import logging
from ...config.settings import GIT_REPO_FOR_INFRA_OBJECTS

logger = logging.getLogger(__name__)


def provision_infra_argocd(
    request,
    site,
    infra_repo_path: Path,
    generate_argocd_objects,
) -> dict:
    """
    בודקת אם Namespace ו-Monitoring קיימים ב-infra.
    אם רכיב enabled וחסר, מפעילה יצירת אובייקטי Argo CD.
    רכיב שאינו enabled נזנח ללא בדיקה.
    """

    results = {}

    components = {
        "namespace": request.namespace,
        "monitoring": site.monitoring,
    }

    for component_name, component_config in components.items():

        # רכיב שאינו enabled לא נבדק כלל.
        if not component_config.enabled:
            logger.info(
                "Skipping %s: component is disabled",
                component_name,
            )
            results[component_name] = "disabled"
            continue

        # מבנה infra:
        # infra/blackops/{site}/{tenant}/
        tenant_path = (
            infra_repo_path
            / "blackops"
            / site.name
            / request.tenant
        )

        # הנתיב הזה צריך להיות מותאם למבנה האמיתי
        # שמבדיל בין Namespace ל-Monitoring בתוך ה-tenant.
        component_path = tenant_path / component_name

        logger.info(
            "Checking infra component: component=%s path=%s",
            component_name,
            component_path,
        )

        if component_path.exists():
            logger.info(
                "Skipping %s: already exists in infra",
                component_name,
            )
            results[component_name] = "already_exists"
            continue

        logger.info(
            "Component %s is missing; generating Argo CD objects",
            component_name,
        )

        # הפונקציה שתועבר לכאן צריכה ליצור AppProject
        # ו-ApplicationSet עבור הרכיב הספציפי.
        generate_argocd_objects(
            request=request,
            site=site,
            component=component_name,
        )

        results[component_name] = "created"

    return results

