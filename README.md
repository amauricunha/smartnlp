# SmartNLP Audio API

API para upload, transcrição e análise de áudios em português, integrando Whisper (OpenAI) para transcrição e LLMs (Groq, Mistral) para análise textual.

## ✨ Funcionalidades

- Recebe arquivos de áudio via POST.
- Salva arquivos e metadados em PostgreSQL.
- Transcreve áudios usando Whisper rodando em container.
- Envia transcrição para LLM (Groq, Mistral) com prompt customizado.
- Retorna resposta da LLM.
- Endpoints separados para transcrição e análise.
- Documentação automática via Swagger (`/docs`).
- Pronto para rodar localmente, em Docker.

## 🚀 Stack

- Python 3.11 + FastAPI
- PostgreSQL 15 (Docker)
- Whisper ASR Webservice (Docker)
- LLM: Groq (Llama-4), Mistral
- Docker Compose
- Frontend: HTML + JS puro (gravação e envio de áudio)

## 🛠️ Como rodar

### 1. Pré-requisitos

- [Docker](https://www.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- (Opcional) [Git](https://git-scm.com/)

### 2. Clone o projeto

```sh
git clone https://github.com/amauricunha/smartnlp.git
cd smartnlp
```

### 3. Configure o `.env`

Crie (ou edite) o arquivo `.env` na raiz do projeto (./backend):

```
DATABASE_URL=postgresql://postgres:postgres@db:5432/smartnlp
UPLOAD_DIR=uploads
WHISPER_MODEL=base
WHISPER_API_URL=http://whisper:9000/asr
GROQ_API_URL=http://groq:8080
GROQ_API_KEY=sua_key
GROQ_API_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
MISTRAL_API_URL=http://mistral:8080
MISTRAL_API_KEY=sua_key
MISTRAL_API_MODEL=mistral-large-latest
```

- Para usar Groq, crie uma conta e chave em [https://console.groq.com/keys](https://console.groq.com/keys).
- Para Mistral, crie uma conta e chave em [https://console.mistral.ai/](https://console.mistral.ai/).

### 4. Suba os containers

```sh
docker-compose up --build
```

Acesse a documentação interativa em:  
[http://localhost:8000/docs](http://localhost:8000/docs)

### 5. Frontend Web

Abra `frontend/index.html` no navegador para gravar e enviar áudio diretamente pelo browser.

### 6. Endpoints principais

- `POST /upload/`  
  Upload de áudio, transcrição e análise LLM em um único fluxo.

- `POST /transcribe/`  
  Apenas transcrição do áudio.

- `POST /llm-groq/`  
  Envia texto/transcrição e retorna resposta da LLM Groq.

- `POST /llm-mistral/`  
  Envia texto/transcrição e retorna resposta da LLM Mistral.

- `GET /health`  
  Healthcheck.

### 7. Exemplos de uso via `curl`

**Upload e análise completa:**
```sh
curl -X POST "http://localhost:8000/upload/" \
  -F "id=1" \
  -F "llm=groq" \
  -F "file=@audio_teste.webm"
```

**Apenas transcrição:**
```sh
curl -X POST "http://localhost:8000/transcribe/" \
  -F "file=@audio_teste.webm"
```

**Apenas análise LLM Groq:**
```sh
curl -X POST "http://localhost:8000/llm-groq/" \
  -F "transcription=Seu texto aqui"
```

**Apenas análise LLM Mistral:**
```sh
curl -X POST "http://localhost:8000/llm-mistral/" \
  -F "transcription=Seu texto aqui"
```

### 8. Observações

- Os arquivos de áudio enviados ficam em `uploads/` (não versionados pelo git).
- O cache dos modelos Whisper fica em `cache/` (não versionado).
- O projeto já está pronto para produção e desenvolvimento local com hot reload.
- Para remover arquivos grandes do git, siga as instruções do `.gitignore` e use `git rm --cached`.

### 9. Troca de LLM

- Ajuste o modelo no GROQ_API_MODEL, no arquivo .env. Por padrão usar meta-llama/llama-4-scout-17b-16e-instruct
- Ajuste o modelo no MISTRAL_API_MODEL, no arquivo .env. Por padrão usar mistral-large-latest

---

## 📄 Licença

MIT

---

**Dúvidas ou sugestões?**  
Abra uma issue ou envie um PR!


