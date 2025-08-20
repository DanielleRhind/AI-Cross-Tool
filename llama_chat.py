import os 
def chat(prompt: str, *, model: str = "llama3") -> str:
    """
    Ask the local Ollama model *model* the *prompt* and return its text answer.
    """
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    url = f"{host}/api/chat"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
