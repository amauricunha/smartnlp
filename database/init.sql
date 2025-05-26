CREATE TABLE IF NOT EXISTS audio_records (
    id INTEGER PRIMARY KEY,
    audio_path VARCHAR NOT NULL,
    prompt TEXT NOT NULL,
    transcription TEXT,
    llm_groq TEXT,
    llm_mistral TEXT);

--ALTER TABLE audio_records
--ADD COLUMN IF NOT EXISTS llm_groq TEXT,
--ADD COLUMN IF NOT EXISTS llm_mistral TEXT,
--ADD COLUMN IF NOT EXISTS transcription TEXT,
--ADD COLUMN IF NOT EXISTS prompt TEXT;
--ADD COLUMN IF NOT EXISTS audio_path VARCHAR NOT NULL;
