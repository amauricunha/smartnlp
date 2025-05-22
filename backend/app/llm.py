import os
import requests

def call_llm_groq(transcription, prompt):
    """
    Usa a API Groq para gerar resposta baseada na transcrição.
    """
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_API_MODEL = os.getenv("GROQ_API_MODEL", "llama3-70b-8192")  # Defina o modelo padrão aqui
    if not GROQ_API_KEY:
        return "GROQ_API_KEY não configurada."
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": GROQ_API_MODEL,
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

def call_llm_mistral(transcription, prompt):
    """
    Usa a API Mistral para gerar resposta baseada na transcrição.
    """
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
    MISTRAL_API_MODEL = os.getenv("MISTRAL_API_MODEL", "mistral-medium")  # Defina o modelo padrão aqui
    if not MISTRAL_API_KEY:
        return "MISTRAL_API_KEY não configurada."
    try:
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": MISTRAL_API_MODEL,
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
                    return f"Erro Mistral: {msg}"
            except Exception:
                pass
            return f"Erro na chamada Mistral: {response.status_code} {response.text}"
    except Exception as e:
        return f"Erro na chamada Mistral: {str(e)}"
