CREATE TABLE IF NOT EXISTS audio_records (
    id INTEGER PRIMARY KEY,
    audio_path VARCHAR NOT NULL,
    transcription TEXT,
    llm_response TEXT,
    llm VARCHAR NOT NULL
);