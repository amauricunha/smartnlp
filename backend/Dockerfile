FROM python:3.12-slim

WORKDIR /app

# Instala FFmpeg para conversão de áudio
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean

# Copiar apenas o arquivo requirements.txt para instalar dependências
COPY ./backend/app/requirements.txt /app/requirements.txt

# Instalar as dependências
RUN pip install --no-cache-dir -r /app/requirements.txt


COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
