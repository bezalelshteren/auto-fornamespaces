from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]

GIT_REPO_PATH = BASE_DIR / "git-repos"


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



GENERATED_DIR = (
    BASE_DIR / BASE_DIR / "git-repos" / "argocd-registry"
)
