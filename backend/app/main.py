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

@app.get("/health", summary="Healthcheck")
def healthcheck():
    return {"status": "ok"}

@app.post("/avaliacao/", summary="Upload de áudio e avaliação das LLMs Groq e Mistral")
async def avaliacao(
    id: int = Form(...),
    pratica_descricao: str = Form(...),
    sa_descricao: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Recebe um arquivo de áudio, a descrição da prática e a situação de aprendizagem, transcreve o audio, envia para a LLMs Groq e Mistral e retorna resposta, salvando em banco de dados.
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

    prompt = ("Você é um especialista em Usinagem e vai avaliar a transcrição do audio do aluno que explica o que está fazendo em um torno mecanico. Deve responder com uma avaliação e sugestões de melhorias, cuidados e pontos de atenção. Considere que o aluno está em um ambiente de aprendizagem e não tem experiência. Também considere que o aluno pode ter dificuldades de comunicação e pode não usar a terminologia correta. Seja gentil e encorajador, mas também honesto e direto. Não use jargões técnicos ou termos complexos. Responda em português. Aluno está nessa pratica: " + pratica_descricao + ". Desta Situação de Aprendizagem: " + sa_descricao)

    llm_response_mistral = call_llm_mistral(transcription, prompt)
    llm_response_groq = call_llm_groq(transcription, prompt)

    if llm_response_mistral.startswith("Erro"):
        logging.error(llm_response_mistral)
        raise HTTPException(status_code=500, detail=llm_response_mistral)

    if llm_response_groq.startswith("Erro"):
        logging.error(llm_response_groq)
        raise HTTPException(status_code=500, detail=llm_response_groq)

    try:
        create_or_update_audio_record(
            id=id,
            audio_path=audio_path,            
            prompt=prompt,
            transcription=transcription,
            llm_groq=llm_response_groq,
            llm_mistral=llm_response_mistral
        )
    except Exception as e:
        logging.exception("Erro ao salvar no banco de dados")
        raise HTTPException(status_code=500, detail="Erro ao salvar no banco de dados.")

    return JSONResponse(
        content={
            "id": id,
            "audio_path": audio_path,
            "prompt": prompt,
            "transcription": transcription,
            "llm_response_groq": llm_response_groq,
            "llm_response_mistral": llm_response_mistral
        }
    )

@app.post("/transcribe/", summary="Transcreve apenas o áudio")
async def transcribe_audio_endpoint(file: UploadFile = File(...)):
    """
    Recebe um arquivo de áudio, salva no servidor e retorna a transcrição.
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

@app.post("/llm-groq/", summary="Recebe Descrição da SA, Descrição da Pratica e Transcriçaõ do Audio do Aluno em texto e retorna resposta da LLM Groq")
async def llm_endpoint(
    sa_descricao: str = Form(...),
    pratica_descricao: str = Form(...),
    transcription: str = Form(...)):
    """
    Recebe uma transcrição de audio de um aluno de usinagem e retorna a resposta da LLM Groq, considerando a prática e a situação de aprendizagem informadas.
    """
    prompt = ("Você é um especialista em Usinagem e vai avaliar a transcrição do audio do aluno que explica o que está fazendo. Deve responder com uma avaliação e sugestões de melhorias, cuidados e pontos de atenção. Considere que o aluno está em um ambiente de aprendizagem e não tem experiência. Também considere que o aluno pode ter dificuldades de comunicação e pode não usar a terminologia correta. Seja gentil e encorajador, mas também honesto e direto. Não use jargões técnicos ou termos complexos. Responda em português. Aluno está nessa prática: " + pratica_descricao + ". Desta Situação de Aprendizagem: " + sa_descricao)
    llm_response = call_llm_groq(transcription, prompt)
    if llm_response.startswith("Erro"):
        logging.error(llm_response)
        raise HTTPException(status_code=500, detail=llm_response)
    return JSONResponse(
        content={
            "prompt": prompt,
            "llm_response": llm_response,
            "llm": "groq"
        }
    )

@app.post("/llm-mistral/", summary="Recebe Descrição da SA, Descrição da Pratica e Transcriçaõ do Audio do Aluno em texto e retorna resposta da LLM Mistral")
async def llm_mistral_endpoint(
    sa_descricao: str = Form(...),
    pratica_descricao: str = Form(...),
    transcription: str = Form(...)):
    """
    Recebe uma transcrição de audio de um aluno de usinagem e retorna a resposta da LLM Mistral, considerando a prática e a situação de aprendizagem informadas.
    """
    prompt = ("Você é um especialista em Usinagem e vai avaliar a transcrição do audio do aluno que explica o que está fazendo. Deve responder com uma avaliação e sugestões de melhorias, cuidados e pontos de atenção. Considere que o aluno está em um ambiente de aprendizagem e não tem experiência. Também considere que o aluno pode ter dificuldades de comunicação e pode não usar a terminologia correta. Seja gentil e encorajador, mas também honesto e direto. Não use jargões técnicos ou termos complexos. Responda em português. Aluno está nessa prática: " + pratica_descricao + ". Desta Situação de Aprendizagem: " + sa_descricao)
    llm_response = call_llm_mistral(transcription, prompt)
    if llm_response.startswith("Erro"):
        logging.error(llm_response)
        raise HTTPException(status_code=500, detail=llm_response)
    return JSONResponse(
        content={
            "prompt": prompt,
            "llm_response": llm_response,
            "llm": "mistral"
        }
    )