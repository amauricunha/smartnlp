FROM python:3.12-slim

WORKDIR /app

# Copiar apenas o arquivo requirements.txt para instalar dependências
COPY ./backend/app/requirements.txt /app/requirements.txt

# Instalar as dependências
RUN pip install --no-cache-dir -r /app/requirements.txt


COPY . .
COPY ./backend/app/wait-for-it.sh .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
