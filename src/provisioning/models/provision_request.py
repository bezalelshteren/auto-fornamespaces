
from pydantic import BaseModel, Field, model_validator


class NamespaceConfig(BaseModel):
    enabled: bool = True
    customer_yahalom: bool = False

    scc: list[str] | None = None

    @model_validator(mode="after")
    def validate_scc(self):
        if self.customer_yahalom and self.scc is None:
            raise ValueError(
                "scc is required when customer_yahalom is true"
            )

        if not self.customer_yahalom and self.scc is not None:
            raise ValueError(
                "scc is only allowed when customer_yahalom is true"
            )

        return self

class GitConfig(BaseModel):
    repo_url: str
    target_revision: str = "main"
    path: str


class ArgoCDConfig(BaseModel):
    enabled: bool = True
    application: bool = False
    application_set: bool = False
    gitops_repo_url: str | None = None

    @model_validator(mode="after")
    def validate_configuration(self):
        if self.application and self.application_set:
            raise ValueError(
                "application and application_set cannot both be true"
            )

        if not self.enabled and (
            self.application or self.application_set
        ):
            raise ValueError(
                "application/application_set cannot be enabled "
                "when Argo CD is disabled"
            )

        return self


class MonitoringConfig(BaseModel):
    enabled: bool = False

    ip: str | None = None
    ip_pmm: str | None = None
    ecs_token: str | None = None
    ecs_id: str | None = None

    @model_validator(mode="after")
    def validate_monitoring(self):
        if self.enabled:
            if self.ip is None or self.ip_pmm is None or self.ecs_token is None or self.ecs_id is None:
                raise ValueError(
                    "or ip or ip pmm or ecs_token or ecs_id is required when monitoring is enabled"
                )
        else:
            if any([
                self.ip is not None,
                self.ip_pmm is not None,
                self.ecs_token is not None,
                self.ecs_id is not None,
            ]):
                raise ValueError(
                    "Monitoring configuration cannot be provided "
                    "when monitoring is disabled"
                )

        return self


class ProvisionRequest(BaseModel):
    tenant: str = Field(min_length=1)
    team: str = Field(min_length=1)
    application: str = Field(min_length=1)
    lifecycle: str = Field(min_length=1)
    target_sites: list[str]

    git: GitConfig

    namespace_config: NamespaceConfig = NamespaceConfig()

    argocd: ArgoCDConfig = ArgoCDConfig()

    monitoring: MonitoringConfig = MonitoringConfig()