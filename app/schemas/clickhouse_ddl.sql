CREATE DATABASE IF NOT EXISTS civic_audit;

CREATE TABLE IF NOT EXISTS civic_audit.audit_events (
    tenant_id String,
    sequence UInt64,
    timestamp DateTime64(3, 'UTC'),
    source String,
    event_type LowCardinality(String),
    payload String,
    trace_id String,
    sig String,
    PRIMARY KEY (tenant_id, sequence)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (tenant_id, sequence, timestamp)
SETTINGS index_granularity = 8192;

CREATE MATERIALIZED VIEW IF NOT EXISTS civic_audit.audit_events_by_tenant
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (tenant_id, timestamp, sequence)
AS
SELECT
    tenant_id,
    sequence,
    timestamp,
    source,
    event_type,
    payload,
    trace_id,
    sig
FROM civic_audit.audit_events;

CREATE ROW POLICY IF NOT EXISTS tenant_access ON civic_audit.audit_events
    FOR SELECT
    USING (tenant_id = currentUser())
    TO ALL;

CREATE ROW POLICY IF NOT EXISTS tenant_write_access ON civic_audit.audit_events
    FOR INSERT
    USING (tenant_id = currentUser())
    TO ALL;

ALTER TABLE civic_audit.audit_events
    APPLY ROW POLICY tenant_access ON (*)
    APPLY ROW POLICY tenant_write_access ON (*)
    TO ALL;
