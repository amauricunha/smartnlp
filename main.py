from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import shutil
import os
import requests
import subprocess
from uuid import uuid4
import logging
from dotenv import load_dotenv
import openai

# Carrega variáveis do .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/smartnlp")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class AudioRecord(Base):
    __tablename__ = "audio_records"
    id = Column(Integer, primary_key=True, index=True)
    audio_path = Column(String, nullable=False)
    transcription = Column(Text)
    llm_response = Column(Text)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SmartNLP Audio API",
    description="Recebe áudio, transcreve, envia para LLM e retorna resposta.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
WHISPER_API_URL = os.getenv("WHISPER_API_URL", "http://whisper:9000/asr")

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".flac"}

def transcribe_audio(filepath):
    """
    Usa o Whisper como serviço HTTP para transcrever o áudio.
    Faz várias tentativas caso o serviço ainda esteja subindo.
    Melhora o tratamento de resposta inválida e log detalhado.
    Também trata respostas vazias do Whisper e loga o corpo da resposta.
    Ajusta a requisição para usar os parâmetros corretos da API Whisper.
    """
    import time
    max_retries = 5
    for attempt in range(max_retries):
        try:
            with open(filepath, "rb") as f:
                files = {"audio_file": (os.path.basename(filepath), f, "application/octet-stream")}
                params = {
                    "encode": "true",
                    "task": "transcribe",
                    "language": "pt",
                    "output": "json"
                }
                response = requests.post(
                    WHISPER_API_URL,
                    params=params,
                    files=files,
                    timeout=180
                )
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                raw_text = response.text.strip()
                if raw_text == "":
                    logging.error(f"Whisper API respondeu 200 mas corpo vazio. Headers: {response.headers}")
                    raise Exception("Resposta vazia da Whisper API (texto vazio).")
                try:
                    result = response.json()
                    text = result.get("text", "")
                    if not text.strip():
                        logging.error(f"Transcrição vazia retornada pela Whisper API. JSON: {result}")
                        raise Exception("Transcrição vazia retornada pela Whisper API.")
                    return text.strip()
                except Exception:
                    if raw_text:
                        logging.warning(f"Whisper API retornou texto puro: {raw_text[:200]}")
                        return raw_text
                    else:
                        raise Exception(f"Resposta vazia ou inválida da Whisper API: {response.text}")
            else:
                logging.error(f"Whisper API error: {response.status_code} {response.text}")
                raise Exception(f"Whisper API error: {response.status_code} {response.text}")
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(3)
            else:
                logging.error(f"Erro na transcrição após {max_retries} tentativas: {str(e)}")
                return f"Erro na transcrição: {str(e)}"

def call_llm(transcription, prompt):
    """
    Usa a API Groq para gerar resposta baseada na transcrição.
    """
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    if not GROQ_API_KEY:
        return "GROQ_API_KEY não configurada."
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": transcription}
            ]
        }
        response = requests.post(url, headers=headers, json=data, timeout=60)
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        else:
            try:
                err = response.json()
                msg = err.get("error", {}).get("message", "")
                if msg:
                    return f"Erro Groq: {msg}"
            except Exception:
                pass
            return f"Erro na chamada Groq: {response.status_code} {response.text}"
    except Exception as e:
        return f"Erro na chamada Groq: {str(e)}"

@app.get("/health", summary="Healthcheck")
def healthcheck():
    return {"status": "ok"}

@app.post("/upload/", summary="Upload de áudio e processamento")
async def upload_audio(id: int = Form(...), file: UploadFile = File(...)):
    """
    Recebe um arquivo de áudio, transcreve, envia para LLM e retorna resposta.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Formato de áudio não suportado.")

    # Gera nome único para o arquivo
    unique_name = f"{id}_{uuid4().hex}{ext}"
    audio_path = os.path.join(UPLOAD_DIR, unique_name)
    try:
        with open(audio_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logging.exception("Erro ao salvar arquivo de áudio")
        raise HTTPException(status_code=500, detail="Erro ao salvar arquivo de áudio.")

    transcription = transcribe_audio(audio_path)
    if transcription.startswith("Erro"):
        logging.error(transcription)
        raise HTTPException(status_code=500, detail=transcription)

    # Salva a transcrição como arquivo txt (opcional)
    txt_path = audio_path + ".txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(transcription)

    prompt = "Você é um assistente que responde perguntas baseadas em áudios transcritos."
    llm_response = call_llm(transcription, prompt)
    if llm_response.startswith("Erro"):
        logging.error(llm_response)
        raise HTTPException(status_code=500, detail=llm_response)

    db = SessionLocal()
    audio_record = AudioRecord(
        id=id,
        audio_path=audio_path,
        transcription=transcription,
        llm_response=llm_response
    )
    db.merge(audio_record)
    db.commit()
    db.close()

    return JSONResponse(
        content={
            "id": id,
            "audio_path": audio_path,
            "transcription": transcription,
            "llm_response": llm_response
        }
    )

@app.post("/transcribe/", summary="Transcreve apenas o áudio")
async def transcribe_audio_endpoint(file: UploadFile = File(...)):
    """
    Recebe um arquivo de áudio e retorna apenas a transcrição.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Formato de áudio não suportado.")
    unique_name = f"transcribe_{uuid4().hex}{ext}"
    audio_path = os.path.join(UPLOAD_DIR, unique_name)
    try:
        with open(audio_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logging.exception("Erro ao salvar arquivo de áudio")
        raise HTTPException(status_code=500, detail="Erro ao salvar arquivo de áudio.")

    transcription = transcribe_audio(audio_path)
    if transcription.startswith("Erro"):
        logging.error(transcription)
        raise HTTPException(status_code=500, detail=transcription)

    # Salva a transcrição como arquivo txt (opcional)
    txt_path = audio_path + ".txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(transcription)

    return JSONResponse(
        content={
            "audio_path": audio_path,
            "transcription": transcription
        }
    )

@app.post("/llm/", summary="Recebe texto e retorna resposta da LLM")
async def llm_endpoint(transcription: str = Form(...)):
    """
    Recebe uma transcrição e retorna a resposta da LLM.
    """
    prompt = "Você é um especialista em Usinagem e vai avaliar a transcrição do audio do aluno que explica o que está fazendo. Deve responder com uma avaliação e sugestões de melhorias, cuidados e pontos de atenção."
    llm_response = call_llm(transcription, prompt)
    if llm_response.startswith("Erro"):
        logging.error(llm_response)
        raise HTTPException(status_code=500, detail=llm_response)
    return JSONResponse(
        content={
            "llm_response": llm_response
        }
    )