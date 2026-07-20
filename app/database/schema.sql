PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS episodes (
    episode_id TEXT PRIMARY KEY,
    creation_date TEXT NOT NULL,
    story_category TEXT NOT NULL,
    main_character_type TEXT NOT NULL,
    character_description TEXT NOT NULL,
    hook_type TEXT NOT NULL,
    ending_type TEXT NOT NULL,
    duration INTEGER NOT NULL CHECK (duration BETWEEN 25 AND 35),
    providers_used TEXT NOT NULL,
    generation_cost_estimate REAL NOT NULL DEFAULT 0,
    final_video_path TEXT,
    generation_status TEXT NOT NULL DEFAULT 'story_ready',
    approval_status TEXT NOT NULL DEFAULT 'pending',
    upload_status TEXT NOT NULL DEFAULT 'not_ready',
    youtube_video_id TEXT,
    continuation_score REAL,
    story_json_path TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS characters (
    character_id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL,
    species TEXT NOT NULL,
    description_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (episode_id) REFERENCES episodes(episode_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS scenes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id TEXT NOT NULL,
    scene_number INTEGER NOT NULL CHECK (scene_number BETWEEN 1 AND 6),
    duration_seconds INTEGER NOT NULL CHECK (duration_seconds BETWEEN 4 AND 6),
    narration TEXT NOT NULL,
    visual_prompt TEXT NOT NULL,
    motion_prompt TEXT NOT NULL,
    emotion TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    UNIQUE (episode_id, scene_number),
    FOREIGN KEY (episode_id) REFERENCES episodes(episode_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS generation_jobs (
    job_id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    current_stage TEXT NOT NULL,
    error_message TEXT,
    idempotency_key TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (episode_id) REFERENCES episodes(episode_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id TEXT NOT NULL,
    scene_number INTEGER,
    asset_type TEXT NOT NULL,
    provider TEXT NOT NULL,
    file_path TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (episode_id) REFERENCES episodes(episode_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS quality_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id TEXT NOT NULL UNIQUE,
    report_path TEXT NOT NULL,
    passed INTEGER NOT NULL DEFAULT 0,
    confidence_score REAL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (episode_id) REFERENCES episodes(episode_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS youtube_uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id TEXT NOT NULL UNIQUE,
    youtube_video_id TEXT,
    privacy_status TEXT NOT NULL DEFAULT 'private',
    upload_status TEXT NOT NULL DEFAULT 'not_requested',
    uploaded_at TEXT,
    FOREIGN KEY (episode_id) REFERENCES episodes(episode_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id TEXT NOT NULL,
    measured_at TEXT NOT NULL,
    views INTEGER NOT NULL DEFAULT 0,
    likes INTEGER NOT NULL DEFAULT 0,
    comments INTEGER NOT NULL DEFAULT 0,
    average_view_duration REAL,
    average_percentage_viewed REAL,
    subscribers_gained INTEGER NOT NULL DEFAULT 0,
    continuation_score REAL,
    FOREIGN KEY (episode_id) REFERENCES episodes(episode_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS story_experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id TEXT NOT NULL UNIQUE,
    story_category TEXT NOT NULL,
    character_type TEXT NOT NULL,
    hook_type TEXT NOT NULL,
    ending_type TEXT NOT NULL,
    selection_weight REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (episode_id) REFERENCES episodes(episode_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_episodes_creation_date
ON episodes(creation_date);

CREATE INDEX IF NOT EXISTS idx_scenes_episode
ON scenes(episode_id, scene_number);

CREATE INDEX IF NOT EXISTS idx_metrics_episode
ON performance_metrics(episode_id, measured_at);

CREATE TABLE IF NOT EXISTS web_generation_jobs (
    job_id TEXT PRIMARY KEY,
    episode_id TEXT,
    job_type TEXT NOT NULL,
    scene_number INTEGER,
    status TEXT NOT NULL,
    current_stage TEXT NOT NULL,
    progress_percent INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    idempotency_key TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    updated_at TEXT NOT NULL,
    staging_directory TEXT,
    archive_directory TEXT,
    FOREIGN KEY (episode_id) REFERENCES episodes(episode_id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_web_jobs_active_episode
ON web_generation_jobs(episode_id)
WHERE episode_id IS NOT NULL AND status IN ('queued', 'running');

CREATE INDEX IF NOT EXISTS idx_web_jobs_created
ON web_generation_jobs(created_at DESC);
