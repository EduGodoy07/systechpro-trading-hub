import subprocess
import json
import requests
from typing import Optional


def run_ollama_cli(prompt: str, model: str = 'local', timeout: int = 30) -> Optional[str]:
    """Run Ollama via CLI as a subprocess. Returns stdout or None on error."""
    try:
        # Example: ollama run <model> --prompt "..."
        # Using a simple invocation; adjust model name as needed.
        completed = subprocess.run(['ollama', 'run', model, '--', prompt], capture_output=True, text=True, timeout=timeout)
        if completed.returncode != 0:
            return None
        return completed.stdout.strip()
    except Exception:
        return None


def run_ollama_http(prompt: str, model: str = 'local', base_url: str = 'http://127.0.0.1:11434', timeout: int = 10) -> Optional[str]:
    """Call local Ollama HTTP API with basic fallbacks. Returns text or None on error."""
    endpoints = [
        f'{base_url}/api/generate',
        f'{base_url}/api/completions',
        f'{base_url}/api/responses',
    ]
    payload = {
        'model': model,
        'prompt': prompt,
    }
    headers = {'Content-Type': 'application/json'}
    for ep in endpoints:
        try:
            resp = requests.post(ep, json=payload, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                # Try to extract text from common shapes
                try:
                    data = resp.json()
                    if isinstance(data, dict):
                        # common keys
                        for key in ('text', 'completion', 'output', 'result'):
                            if key in data:
                                return data[key]
                        # nested choices
                        if 'choices' in data and isinstance(data['choices'], list) and len(data['choices']) > 0:
                            ch = data['choices'][0]
                            if isinstance(ch, dict) and 'text' in ch:
                                return ch['text']
                    # fallback to raw text
                    return resp.text
                except Exception:
                    return resp.text
        except Exception:
            continue
    return None


def generate(prompt: str, prefer_http: bool = True, model: str = 'local') -> str:
    """High-level helper: try HTTP then CLI and return a string result or error message."""
    if prefer_http:
        out = run_ollama_http(prompt, model=model)
        if out:
            return out
    out = run_ollama_cli(prompt, model=model)
    if out:
        return out
    return 'LLM unavailable (check Ollama server or CLI)'
