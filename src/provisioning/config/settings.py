from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]



GIT_REPO_FOR_ARGOCD_OBJECTS = (
    "https://github.com/bezalelshteren/argocd-registry.git"
)

GIT_REPO_FOR_NAMESPACES_OBJECTS = (
    "https://github.com/bezalelshteren/cluster-registry.git"
)

GIT_REPO_FOR_MONTORING_OBJECTS = (
    "https://github.com/bezalelshteren/monitoring-registry.git"
)

GIT_REPO_URL = (
    "https://github.com/bezalelshteren/argocd-registry.git"
)


ARGO_PROJECT_ROOT = (
    "argoproject"
)

TEMPLATES_DIR = (
    BASE_DIR / "templates"
)

ARGOCD_TEMPLATES_DIR = (
        TEMPLATES_DIR / "argocd_objects"
)
NAMESPACE_TEMPLATES_DIR = (
    TEMPLATES_DIR / "namespace-objects"
)
MONITORING_TEMPLATES_DIR = (
    TEMPLATES_DIR / "monitoring-objects"
)

ARGO_DIR_TARGET = (
    BASE_DIR / "git-repos" / "argocd-registry"
)

NAMESPACE_DIR_TARGET = (
    BASE_DIR / "git-repos" / "cluster-registry"
)
MONITORING_DIR_TARGET = (
    BASE_DIR / "git-repos" / "monitoring-registry"
)

NAMESPACE_REPOSITORIES = {
    "dev1": {
        "git_repo": "https://github.com/bezalelshteren/cluster-registry.git",
        "local_path": Path( BASE_DIR / "git-repos" / "cluster-registry"),
    },
    "prd1": {
        "git_repo": "https://github.com/company/namespaces-prd.git",
        "local_path": Path( BASE_DIR / "git-repos" / "cluster-registry" / "namespaces-prd"),
    },"stg1": {
        "git_repo": "https://github.com/company/namespaces-stg.git",
        "local_path": Path( BASE_DIR / "git-repos" / "cluster-registry" / "namespaces-stg"),
    },
}