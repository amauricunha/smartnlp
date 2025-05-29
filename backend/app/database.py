import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
print(f"Conectando ao banco de dados: {DATABASE_URL}")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL não configurada. Verifique as variáveis de ambiente.")
print(f"Diretório de upload: {UPLOAD_DIR}")
if not UPLOAD_DIR:
    raise ValueError("UPLOAD_DIR não configurada. Verifique as variáveis de ambiente.")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class AudioRecord(Base):
    __tablename__ = "audio_records"
    id = Column(Integer, primary_key=True, index=True)
    audio_path = Column(String, nullable=False)
    prompt = Column(Text)
    transcription = Column(Text)
    llm_groq = Column(Text)
    llm_mistral = Column(Text)  

Base.metadata.create_all(bind=engine)

ALLOWED_EXTENSIONS = [".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".webm"]

def create_or_update_audio_record(id, prompt, audio_path, transcription, llm_groq, llm_mistral):
    db = SessionLocal()
    try:
        audio_record = AudioRecord(
            id=id,
            audio_path=audio_path,
            prompt=prompt,
            transcription=transcription,
            llm_groq=llm_groq,
            llm_mistral=llm_mistral
        )
        db.merge(audio_record)
        db.commit()
    finally:
        db.close()

# Exporta modelo e sessão para uso externo
__all__ = [
    "ALLOWED_EXTENSIONS",
    "UPLOAD_DIR",
    "create_or_update_audio_record",
    "AudioRecord",
    "SessionLocal",
]
