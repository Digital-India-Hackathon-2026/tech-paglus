CREATE TABLE IF NOT EXISTS vision_analysis_sessions (
    analysis_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    status TEXT NOT NULL,
    crop TEXT,
    plant_part TEXT,
    growth_stage TEXT,
    harvest_stage TEXT,
    location TEXT,
    consent_status INTEGER NOT NULL DEFAULT 0,
    model_version TEXT,
    severity TEXT,
    affected_percentage REAL,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_vision_history ON vision_analysis_sessions(owner_id, created_at DESC);

CREATE TABLE IF NOT EXISTS vision_uploaded_images (
    image_id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL REFERENCES vision_analysis_sessions(analysis_id) ON DELETE CASCADE,
    original_name TEXT,
    mime_type TEXT,
    sha256 TEXT,
    width INTEGER,
    height INTEGER,
    quality_status TEXT,
    original_path TEXT,
    annotated_path TEXT,
    zoom_path TEXT,
    consent_status INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_vision_images_analysis ON vision_uploaded_images(analysis_id);

CREATE TABLE IF NOT EXISTS vision_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id TEXT NOT NULL REFERENCES vision_analysis_sessions(analysis_id) ON DELETE CASCADE,
    image_id TEXT REFERENCES vision_uploaded_images(image_id) ON DELETE CASCADE,
    task TEXT,
    label TEXT,
    confidence REAL,
    model_version TEXT,
    metadata_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_vision_predictions_analysis ON vision_predictions(analysis_id, task);

CREATE TABLE IF NOT EXISTS vision_detected_diseases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id TEXT NOT NULL REFERENCES vision_analysis_sessions(analysis_id) ON DELETE CASCADE,
    image_id TEXT REFERENCES vision_uploaded_images(image_id) ON DELETE CASCADE,
    disease_name TEXT,
    category TEXT,
    confidence REAL,
    alternative_rank INTEGER
);

CREATE TABLE IF NOT EXISTS vision_detected_pests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id TEXT NOT NULL REFERENCES vision_analysis_sessions(analysis_id) ON DELETE CASCADE,
    image_id TEXT REFERENCES vision_uploaded_images(image_id) ON DELETE CASCADE,
    pest_name TEXT,
    confidence REAL,
    lifecycle_stage TEXT,
    directly_visible INTEGER,
    crop_part TEXT,
    damage_type TEXT,
    bbox_json TEXT
);

CREATE TABLE IF NOT EXISTS vision_damage_regions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id TEXT NOT NULL REFERENCES vision_analysis_sessions(analysis_id) ON DELETE CASCADE,
    image_id TEXT REFERENCES vision_uploaded_images(image_id) ON DELETE CASCADE,
    label TEXT,
    confidence REAL,
    affected_fraction REAL,
    bbox_json TEXT,
    mask_json TEXT,
    method TEXT
);

CREATE TABLE IF NOT EXISTS vision_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id TEXT NOT NULL REFERENCES vision_analysis_sessions(analysis_id) ON DELETE CASCADE,
    recommendation_type TEXT,
    title TEXT,
    detail TEXT,
    cost_category TEXT,
    verification_status TEXT
);

CREATE TABLE IF NOT EXISTS vision_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id TEXT NOT NULL REFERENCES vision_analysis_sessions(analysis_id) ON DELETE CASCADE,
    owner_id TEXT,
    verdict TEXT NOT NULL,
    crop_correct INTEGER,
    disease_correct INTEGER,
    pest_correct INTEGER,
    treatment_helpful INTEGER,
    corrected_label TEXT,
    expert_diagnosis TEXT,
    notes TEXT,
    dataset_candidate_status TEXT NOT NULL DEFAULT 'pending_expert_review',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_vision_feedback_review ON vision_feedback(dataset_candidate_status, created_at DESC);
