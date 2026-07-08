-- Snapshot da vitrine PanelDX recebida via sync em lote
CREATE TABLE IF NOT EXISTS paneldx_vitrine_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sync_id UUID NOT NULL UNIQUE,
    payload JSONB NOT NULL,
    planos_count INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'paneldx',
    published_at TIMESTAMP,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_paneldx_vitrine_snapshots_received
    ON paneldx_vitrine_snapshots (received_at DESC);
