from pydantic import BaseModel, Field


class Cluster(BaseModel):
    name: str
    server: str


class GitConfig(BaseModel):
    repo_url: str
    target_revision: str = "master"
    path: str


class HelmConfig(BaseModel):
    value_files: list[str] = []


class ArgoCDConfig(BaseModel):
    enabled: bool = True


class MonitoringConfig(BaseModel):
    enabled: bool = False
    profile: str | None = None


class ProvisionRequest(BaseModel):
    tenant: str = Field(min_length=1)
    lifecycle: str = Field(min_length=1)
    application: str = Field(min_length=1)

    cluster: Cluster

    git: GitConfig

    helm: HelmConfig = HelmConfig()

    argocd: ArgoCDConfig = ArgoCDConfig()

    monitoring: MonitoringConfig = MonitoringConfig()