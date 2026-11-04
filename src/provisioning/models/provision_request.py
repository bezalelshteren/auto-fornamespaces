from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    model_validator,
)


class StrictModel(BaseModel):
    """
    Base model for all provisioning request models.

    Reject fields that are not explicitly defined.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class CPUConfig(StrictModel):
    request: str | None = None
    limit: str | None = None


class MemoryConfig(StrictModel):
    request: str | None = None
    limit: str | None = None


class StorageConfig(StrictModel):
    size: str = Field(min_length=1)
    storage_class: str = Field(min_length=1)


class ComputeConfig(StrictModel):
    cpu: CPUConfig | None = None
    memory: MemoryConfig | None = None
    storage: StorageConfig | None = None



class NamespaceConfig(StrictModel):
    enabled: bool = True
    lifecycle: str | None = None

    @model_validator(mode="after")
    def validate_namespace(self):
        if self.enabled and not self.lifecycle:
            raise ValueError(
                "lifecycle is required when namespace is enabled"
            )

        return self


class ArgoCDConfig(StrictModel):
    enabled: bool = False

    type: Literal["application", "application_set"] | None = None

    git_repo_url: HttpUrl | None = None

    @model_validator(mode="after")
    def validate_argocd(self):
        if self.enabled:
            if self.type is None:
                raise ValueError(
                    "ArgoCD type is required when ArgoCD is enabled"
                )

            if self.git_repo_url is None:
                raise ValueError(
                    "git_repo_url is required when ArgoCD is enabled"
                )

        else:
            if self.type is not None:
                raise ValueError(
                    "ArgoCD type must be null when ArgoCD is disabled"
                )

            if self.git_repo_url is not None:
                raise ValueError(
                    "git_repo_url must be null when ArgoCD is disabled"
                )

        return self


class MonitoringConfig(StrictModel):
    enabled: bool = False

    ingest: bool = False

    export: bool = False

    ecs_id: str | None = None

    ecs_token: str | None = None

    ip: str | None = None

    webhook_url: str | None = None



    @model_validator(mode="after")
    def validate_monitoring(self):
        # Monitoring cannot have active components when disabled.
        if not self.enabled:
            if self.ingest or self.export:
                raise ValueError(
                    "Monitoring ingest/export cannot be enabled "
                    "when monitoring is disabled"
                )

            return self

        # At least one component must be enabled.
        if not (self.ingest or self.export):
            raise ValueError(
                "At least one of ingest or export must be enabled "
                "when monitoring is enabled"
            )

        # Ingest requirements.
        if self.ingest:
            if not self.ecs_id:
                raise ValueError(
                    "ecs_id is required when monitoring ingest is enabled"
                )

            if not self.ecs_token:
                raise ValueError(
                    "ecs_token is required when monitoring ingest is enabled"
                )

        # Export requirements.
        if self.export:
            if not self.webhook_url:
                raise ValueError(
                    "webook-url-url-url-url is required when monitoring export is enabled"
                )

        return self


class SiteConfig(StrictModel):
    name: str = Field(min_length=1)

    namespace: NamespaceConfig

    argocd: ArgoCDConfig

    monitoring: MonitoringConfig

    @model_validator(mode="after")
    def validate_site_name(self):
        if not self.name.strip():
            raise ValueError(
                "Site name cannot be empty or contain only whitespace"
            )

        return self


class ProvisionRequest(StrictModel):
    tenant: str = Field(min_length=1)

    team: str = Field(min_length=1)

    application: str = Field(min_length=1)

    ldap_group: str = Field(min_length=1)

    customer_yahalom: bool = False

    # Required for Yahalom customers.
    scc: str | None = None

    custom: bool = False

    compute: ComputeConfig | None = None

    sites: list[SiteConfig] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_request(self):
        # Reject empty strings for required identifiers.
        required_fields = {
            "tenant": self.tenant,
            "team": self.team,
            "application": self.application,
            "ldap_group": self.ldap_group,
        }

        for field_name, value in required_fields.items():
            if not value.strip():
                raise ValueError(
                    f"{field_name} cannot be empty or contain only whitespace"
                )

        # Yahalom customers must provide an SCC value.
        if self.customer_yahalom:
            if not self.scc or not self.scc.strip():
                raise ValueError(
                    "scc is required when customer_yahalom is true"
                )
        elif self.scc is not None:
            raise ValueError(
                "scc can only be provided when customer_yahalom is true"
            )

        # Site names must be unique.
        site_names = [site.name for site in self.sites]

        if len(site_names) != len(set(site_names)):
            raise ValueError(
                "Each site name must be unique"
            )

        # Custom compute configuration is allowed only when custom=True.
        if not self.custom and self.compute is not None:
            raise ValueError(
                "compute cannot be provided when custom is false"
            )

        return self