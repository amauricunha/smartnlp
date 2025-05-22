# SmartNLP Audio API

API para upload, transcrição e análise de áudios em português, integrando Whisper (OpenAI) para transcrição e LLMs (Groq, OpenAI, Hugging Face) para análise textual.

## Funcionalidades

- Recebe arquivos de áudio via POST.
- Salva arquivos e metadados em PostgreSQL.
- Transcreve áudios usando Whisper rodando em container.
- Envia transcrição para LLM (Groq, OpenAI, Hugging Face) com prompt customizado.
- Retorna resposta da LLM.
- Endpoints separados para transcrição e análise.
- Documentação automática via Swagger (`/docs`).

## Stack

- Python 3.11 + FastAPI
- PostgreSQL 15 (Docker)
- Whisper ASR Webservice (Docker)
- LLM: Groq (Llama-4), OpenAI GPT, Hugging Face (configurável)
- Docker Compose

## Como rodar

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

Crie (ou edite) o arquivo `.env` na raiz do projeto:

```
DATABASE_URL=postgresql://postgres:postgres@db:5432/smartnlp
UPLOAD_DIR=uploads
OPENAI_API_KEY=sua-chave-openai
GROQ_API_KEY=sua-chave-groq
WHISPER_API_URL=http://whisper:9000/asr
```

- Para usar Groq, crie uma conta em [https://console.groq.com/keys](https://console.groq.com/keys).
- Para OpenAI, crie uma chave em [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys).

### 4. Suba os containers

```sh
docker-compose up --build
```

Acesse a documentação interativa em:  
[http://localhost:8000/docs](http://localhost:8000/docs)

### 5. Endpoints principais

- `POST /upload/`  
  Upload de áudio, transcrição e análise LLM em um único fluxo.

- `POST /transcribe/`  
  Apenas transcrição do áudio.

- `POST /llm/`  
  Envia texto/transcrição e retorna resposta da LLM.

- `GET /health`  
  Healthcheck.

### 6. Exemplo de uso via `curl`

**Upload e análise completa:**
```sh
curl -X POST "http://localhost:8000/upload/" \
  -F "id=1" \
  -F "file=@audio_teste.m4a"
```

**Apenas transcrição:**
```sh
curl -X POST "http://localhost:8000/transcribe/" \
  -F "file=@audio_teste.m4a"
```

**Apenas análise LLM:**
```sh
curl -X POST "http://localhost:8000/llm/" \
  -F "transcription=Seu texto aqui"
```

### 7. Observações

- Os arquivos de áudio enviados ficam em `uploads/` (não versionados pelo git).
- O cache dos modelos Whisper fica em `cache/` (não versionado).
- O projeto já está pronto para produção e desenvolvimento local com hot reload.
- Para remover arquivos grandes do git, siga as instruções do `.gitignore` e use `git rm --cached`.

### 8. Troca de LLM

- Por padrão, a API usa Groq (Llama-4).
- Para usar OpenAI, ajuste a função `call_llm` e a variável de ambiente `OPENAI_API_KEY`.
- Para usar Hugging Face, ajuste a função `call_llm` e a variável `HF_API_TOKEN`.

---

## Licença

MIT

---

**Dúvidas ou sugestões?**  
Abra uma issue ou envie um PR!


