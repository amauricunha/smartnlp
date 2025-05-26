from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
import shutil
import os
import logging
from uuid import uuid4
from dotenv import load_dotenv

# Importações dos módulos separados
from database import (
    ALLOWED_EXTENSIONS,
    UPLOAD_DIR,
    create_or_update_audio_record,
    AudioRecord,  # Importa modelo
    SessionLocal, # Importa sessão para consulta
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
    area_especialista: str = Form(...),
    semestre_aluno: str = Form(...),    
    sa_descricao: str = Form(...), 
    etapa_descricao: str = Form(...),
    pratica_descricao: str = Form(...),
    parametros_descricao: str = Form(...),   
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

    prompt_v1 = ("Você é um especialista em " 
              + area_especialista + 
              " e vai avaliar a transcrição do audio do aluno que explica o que está fazendo. Deve responder com uma avaliação e sugestões de melhorias, cuidados e pontos de atenção. Considere que o aluno está em um ambiente de aprendizagem e não tem experiência. Também considere que o aluno pode ter dificuldades de comunicação e pode não usar a terminologia correta. Seja gentil e encorajador, mas também honesto e direto. Não use jargões técnicos ou termos complexos. Responda em português. Aluno está realizando essa prática: " 
              + pratica_descricao + 
              ". Desta Situação de Aprendizagem: " 
              + sa_descricao)
    
    prompt_v2 = (
        "Você é um Tutor de Inteligência Artificial especializado em práticas de laboratório de " + area_especialista + " para estudantes de educação profissional e superior. "
        "Sua tarefa é analisar a transcrição de áudio de um aluno que descreve o que está fazendo em uma atividade prática. "
        "Com base na transcrição, forneça um feedback pedagógico construtivo para ajudar o aluno a melhorar seu entendimento e execução da prática. "
        "Inclua uma avaliação geral, sugestões de melhoria, pontos de atenção importantes (especialmente relacionados à segurança) e reconheça os acertos. "
        "Lembre-se que o aluno está em um ambiente de aprendizado, no semestre " + semestre_aluno + " de contato com o laboratório."
        "Considere que ele está adquirindo experiência e pode ter dificuldades de comunicação, usando terminologia incorreta ou incompleta."
        "Seja gentil, paciente e encorajador, mas também honesto e direto em suas observações. "
        "Use uma linguagem clara e simples, evitando jargões técnicos complexos, como se estivesse conversando diretamente com o aluno no laboratório."
        "Sua resposta deve ser em português."
        "O aluno está realizando a seguinte prática: "+ pratica_descricao +", que faz parte da Situação de Aprendizagem: "+ sa_descricao +"."
        "Foque em avaliar se a descrição do aluno reflete um bom entendimento dos passos, dos parâmetros importantes como  " + parametros_descricao + " , dos cuidados de segurança  e da finalidade da etapa que está realizando."
        "Não avalie a qualidade da atividade em si, apenas a descrição verbal do aluno sobre suas ações e intenções."
    )
    prompt = (
        "Você é um Tutor IA de laboratório de " + area_especialista + " para estudantes (profissional/superior). "
        "Analise a transcrição de áudio de um aluno explicando sua prática. "
        "Forneça feedback pedagógico construtivo (avaliação, sugestões, pontos de atenção - **segurança**!, acertos). "
        "Considere que é um aluno em aprendizado no semestre(" + semestre_aluno + "), adquirindo experiência, com possíveis dificuldades de comunicação/terminologia. "
        "Seja gentil, paciente, encorajador, mas direto. Use linguagem simples, sem jargões, como em conversa no lab. "
        "Resposta em português. "
        "Prática em Execução: '" + pratica_descricao + "', da Etapa: '" + etapa_descricao + "', da Situação de Aprendizagem: '" + sa_descricao + "'. "
        "Avalie o entendimento da descrição sobre passos, parâmetros importantes (" + parametros_descricao + "), **cuidados de segurança**, e objetivo da etapa. "
        "Não avalie a qualidade física da prática, apenas a explicação verbal."
    )

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
    area_especialista: str = Form(...),
    semestre_aluno: str = Form(...),
    sa_descricao: str = Form(...),
    etapa_descricao: str = Form(...),
    pratica_descricao: str = Form(...),
    parametros_descricao: str = Form(...),
    transcription: str = Form(...)):
    """
    Recebe uma transcrição de audio de um aluno de usinagem e retorna a resposta da LLM Groq, considerando a prática e a situação de aprendizagem informadas.
    """
    prompt = (
        "Você é um Tutor IA de laboratório de " + area_especialista + " para estudantes (profissional/superior). "
        "Analise a transcrição de áudio de um aluno explicando sua prática. "
        "Forneça feedback pedagógico construtivo (avaliação, sugestões, pontos de atenção - **segurança**!, acertos). "
        "Considere que é um aluno em aprendizado no semestre(" + semestre_aluno + "), adquirindo experiência, com possíveis dificuldades de comunicação/terminologia. "
        "Seja gentil, paciente, encorajador, mas direto. Use linguagem simples, sem jargões, como em conversa no lab. "
        "Resposta em português. "
        "Prática em Execução: '" + pratica_descricao + "', da Etapa: '" + etapa_descricao + "', da Situação de Aprendizagem: '" + sa_descricao + "'. "
        "Avalie o entendimento da descrição sobre passos, parâmetros importantes (" + parametros_descricao + "), **cuidados de segurança**, e objetivo da etapa. "
        "Não avalie a qualidade física da prática, apenas a explicação verbal."
    )
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
    area_especialista: str = Form(...),
    semestre_aluno: str = Form(...),
    sa_descricao: str = Form(...),
    etapa_descricao: str = Form(...),
    pratica_descricao: str = Form(...),
    parametros_descricao: str = Form(...),
    transcription: str = Form(...)):
    """
    Recebe uma transcrição de audio de um aluno de usinagem e retorna a resposta da LLM Mistral, considerando a prática e a situação de aprendizagem informadas.
    """
    prompt = (
        "Você é um Tutor IA de laboratório de " + area_especialista + " para estudantes (profissional/superior). "
        "Analise a transcrição de áudio de um aluno explicando sua prática. "
        "Forneça feedback pedagógico construtivo (avaliação, sugestões, pontos de atenção - **segurança**!, acertos). "
        "Considere que é um aluno em aprendizado no semestre(" + semestre_aluno + "), adquirindo experiência, com possíveis dificuldades de comunicação/terminologia. "
        "Seja gentil, paciente, encorajador, mas direto. Use linguagem simples, sem jargões, como em conversa no lab. "
        "Resposta em português. "
        "Prática em Execução: '" + pratica_descricao + "', da Etapa: '" + etapa_descricao + "', da Situação de Aprendizagem: '" + sa_descricao + "'. "
        "Avalie o entendimento da descrição sobre passos, parâmetros importantes (" + parametros_descricao + "), **cuidados de segurança**, e objetivo da etapa. "
        "Não avalie a qualidade física da prática, apenas a explicação verbal."
    )
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

@app.get("/audio_records/", summary="Lista registros de áudio com paginação")
def list_audio_records(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)):
    """
    Retorna registros da tabela audio_records, ordenados do mais recente para o mais antigo.
    """
    db = SessionLocal()
    try:
        total = db.query(AudioRecord).count()
        records = (
            db.query(AudioRecord)
            .order_by(AudioRecord.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        items = [
            {
                "id": r.id,
                "audio_path": r.audio_path,
                "prompt": r.prompt,
                "transcription": r.transcription,
                "llm_groq": r.llm_groq,
                "llm_mistral": r.llm_mistral,
            }
            for r in records
        ]
        return {"total": total, "items": items}
    finally:
        db.close()