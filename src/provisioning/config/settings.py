from pathlib import Path


# ============================================================
# Project
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[3]


# ============================================================
# Git repository
# ============================================================

GIT_REPO_URL = (
    "https://github.com/bezalelshteren/argocd-registry.git"
)

GIT_REPO_PATH = (
    BASE_DIR / "git-repo"
)


# ============================================================
# Git repository structure
# ============================================================

ARGO_PROJECT_ROOT = (
    "argoproject"
)


# ============================================================
# Templates
# ============================================================

TEMPLATES_DIR = (
    BASE_DIR / "templates"
)

ARGOCD_TEMPLATES_DIR = (
    TEMPLATES_DIR / "argocd_objects"
)


# ============================================================
# Generated files
# ============================================================

GENERATED_DIR = (
    BASE_DIR / "generated"
)
