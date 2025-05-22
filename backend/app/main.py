from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
import shutil
import os
import logging
from uuid import uuid4
from dotenv import load_dotenv
import unicodedata
import re

# Importações dos módulos separados
from database import (
    ALLOWED_EXTENSIONS,
    UPLOAD_DIR,
    create_or_update_audio_record,
)
from transcribe import transcribe_audio
from llm import call_llm_groq, call_llm_mistral

# Carrega variáveis do .env
load_dotenv()

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

def clean_llm_response(text):
    # Remove "Avaliação:" do início (com ou sem acento, com ou sem espaço após)
    text = re.sub(r"^(Avalia[cç][aã]o:?\s*)", "", text, flags=re.IGNORECASE)
    # Normaliza caracteres especiais (opcional: remova se quiser manter acentos)
    # text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return text.strip()

@app.get("/health", summary="Healthcheck")
def healthcheck():
    return {"status": "ok"}

@app.post("/upload/", summary="Upload de áudio e processamento")
async def upload_audio(
    id: int = Form(...),
    file: UploadFile = File(...),
    llm: str = Form("groq")
):
    """
    Recebe um arquivo de áudio, transcreve, envia para LLM (groq ou mistral) e retorna resposta.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Formato de áudio não suportado.")

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

    txt_path = audio_path + ".txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(transcription)

    prompt = "Você é um especialista em Usinagem e vai avaliar a transcrição do audio do aluno que explica o que está fazendo em um torno mecanico. Deve responder com uma avaliação e sugestões de melhorias, cuidados e pontos de atenção."

    if llm == "mistral":
        llm_response = call_llm_mistral(transcription, prompt)
    else:
        llm = "groq"
        llm_response = call_llm_groq(transcription, prompt)

    if llm_response.startswith("Erro"):
        logging.error(llm_response)
        raise HTTPException(status_code=500, detail=llm_response)

    llm_response_clean = clean_llm_response(llm_response)

    try:
        create_or_update_audio_record(
            id=id,
            audio_path=audio_path,
            transcription=transcription,
            llm_response=llm_response_clean,
            llm=llm
        )
    except Exception as e:
        logging.exception("Erro ao salvar no banco de dados")
        raise HTTPException(status_code=500, detail="Erro ao salvar no banco de dados.")

    return JSONResponse(
        content={
            "id": id,
            "audio_path": audio_path,
            "transcription": transcription,
            "llm_response": llm_response_clean,
            "llm": llm
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

    txt_path = audio_path + ".txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(transcription)

    return JSONResponse(
        content={
            "audio_path": audio_path,
            "transcription": transcription
        }
    )

@app.post("/llm-groq/", summary="Recebe texto e retorna resposta da LLM")
async def llm_endpoint(transcription: str = Form(...)):
    """
    Recebe uma transcrição e retorna a resposta da LLM.
    """
    prompt = "Você é um especialista em Usinagem e vai avaliar a transcrição do audio do aluno que explica o que está fazendo. Deve responder com uma avaliação e sugestões de melhorias, cuidados e pontos de atenção."
    llm_response = call_llm_groq(transcription, prompt)
    if llm_response.startswith("Erro"):
        logging.error(llm_response)
        raise HTTPException(status_code=500, detail=llm_response)
    llm_response_clean = clean_llm_response(llm_response)
    return JSONResponse(
        content={
            "llm_response": llm_response_clean,
            "llm": "groq"
        }
    )

@app.post("/llm-mistral/", summary="Recebe texto e retorna resposta da LLM Mistral")
async def llm_mistral_endpoint(transcription: str = Form(...)):
    """
    Recebe uma transcrição e retorna a resposta da LLM Mistral.
    """
    prompt = "Você é um especialista em Usinagem e vai avaliar a transcrição do audio do aluno que explica o que está fazendo. Deve responder com uma avaliação e sugestões de melhorias, cuidados e pontos de atenção."
    llm_response = call_llm_mistral(transcription, prompt)
    if llm_response.startswith("Erro"):
        logging.error(llm_response)
        raise HTTPException(status_code=500, detail=llm_response)
    llm_response_clean = clean_llm_response(llm_response)
    return JSONResponse(
        content={
            "llm_response": llm_response_clean,
            "llm": "mistral"
        }
    )