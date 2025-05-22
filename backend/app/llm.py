import os
import requests

def call_llm_groq(transcription, prompt):
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

def call_llm_mistral(transcription, prompt):
    """
    Usa a API Mistral para gerar resposta baseada na transcrição.
    """
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
    if not MISTRAL_API_KEY:
        return "MISTRAL_API_KEY não configurada."
    try:
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "mistral-large-latest",
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
