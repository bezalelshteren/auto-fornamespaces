CREATE TABLE IF NOT EXISTS provisioning_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    level VARCHAR(20) NOT NULL,
    logger VARCHAR(255),
    stage VARCHAR(100),
    status VARCHAR(50),
    tenant VARCHAR(255),
    team VARCHAR(255),
    application VARCHAR(255),
    lifecycle VARCHAR(100),
    cluster VARCHAR(255),
    target_site VARCHAR(255),
    request_id UUID,
    message TEXT NOT NULL,
    duration_ms BIGINT,
    error TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_provisioning_logs_timestamp ON provisioning_logs (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_provisioning_logs_request_id ON provisioning_logs (request_id);
CREATE INDEX IF NOT EXISTS idx_provisioning_logs_tenant_application ON provisioning_logs (tenant, application);
CREATE INDEX IF NOT EXISTS idx_provisioning_logs_status ON provisioning_logs (status);
CREATE INDEX IF NOT EXISTS idx_provisioning_logs_stage ON provisioning_logs (stage);
