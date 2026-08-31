CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TYPE exam_status AS ENUM ('CREATED', 'ENCRYPTED', 'DISTRIBUTED', 'KEYS_BROADCAST', 'COMPLETED', 'CANCELLED');
CREATE TYPE download_status AS ENUM ('PENDING', 'DOWNLOADED', 'VERIFIED', 'FAILED');

CREATE TABLE exams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    scheduled_start TIMESTAMPTZ NOT NULL,
    duration_minutes INT NOT NULL,
    wrapped_dek BYTEA NOT NULL,
    blob_storage_uri VARCHAR(512),
    blob_sha256 CHAR(64),
    status exam_status DEFAULT 'CREATED',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE exams IS 'Stores metadata for encrypted exam packages';
COMMENT ON COLUMN exams.wrapped_dek IS 'DEK wrapped by KMS for this specific exam';

CREATE TABLE exam_centers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    center_code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    region VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE exam_centers IS 'Approved physical locations where exams are conducted';

CREATE TABLE superintendents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    center_id UUID REFERENCES exam_centers(id) ON DELETE RESTRICT,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    biometric_template_hash VARCHAR(128),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE superintendents IS 'Authorized personnel assigned to specific exam centers';

CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    exam_id UUID REFERENCES exams(id) ON DELETE SET NULL,
    center_id UUID REFERENCES exam_centers(id) ON DELETE SET NULL,
    superintendent_id UUID REFERENCES superintendents(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,
    metadata JSONB DEFAULT '{}',
    client_ip INET,
    device_fingerprint VARCHAR(128),
    request_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE audit_log IS 'Immutable log of critical system operations and security events';

CREATE TABLE key_broadcasts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    exam_id UUID UNIQUE REFERENCES exams(id) ON DELETE RESTRICT,
    broadcast_at TIMESTAMPTZ NOT NULL,
    kafka_topic VARCHAR(100),
    kafka_partition INT,
    kafka_offset BIGINT,
    confirmed_receipt BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE key_broadcasts IS 'Records when a decryption key was successfully broadcasted';

CREATE TABLE exam_center_assignments (
    exam_id UUID REFERENCES exams(id) ON DELETE CASCADE,
    center_id UUID REFERENCES exam_centers(id) ON DELETE CASCADE,
    download_status download_status DEFAULT 'PENDING',
    downloaded_at TIMESTAMPTZ,
    blob_checksum_verified BOOLEAN DEFAULT false,
    PRIMARY KEY (exam_id, center_id)
);

COMMENT ON TABLE exam_center_assignments IS 'Mapping of exams to authorized centers and status tracking';

-- Indexes
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);
CREATE INDEX idx_audit_log_exam_id ON audit_log(exam_id);
CREATE INDEX idx_audit_log_center_id ON audit_log(center_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_exams_scheduled_status ON exams(scheduled_start, status);
CREATE INDEX idx_exam_centers_code ON exam_centers(center_code);

-- Trigger function for updated_at
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_exams_modtime
    BEFORE UPDATE ON exams
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();
