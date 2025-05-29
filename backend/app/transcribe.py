import os
import requests
import logging
import subprocess

WHISPER_API_URL = os.getenv("WHISPER_API_URL", "http://whisper:9000/asr")

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
    
    # Verifica se o arquivo precisa de conversão
    _, ext = os.path.splitext(filepath)
    if ext.lower() in ['.m4a', '.aac']:
        # Converte para WAV usando ffmpeg
        try:
            converted_path = filepath.replace(ext, '.wav')
            subprocess.run([
                'ffmpeg', '-i', filepath, 
                '-acodec', 'pcm_s16le', 
                '-ar', '16000', 
                converted_path, '-y'
            ], check=True, capture_output=True)
            filepath = converted_path
            logging.info(f"Arquivo convertido para: {converted_path}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Erro na conversão do áudio: {e}")
            return f"Erro na conversão do áudio: {e}"
        except FileNotFoundError:
            logging.error("FFmpeg não encontrado. Tentando sem conversão...")
