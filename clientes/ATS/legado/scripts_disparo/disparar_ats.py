import os
import uuid
import httpx

API_URL = "https://call-github.bkpxmb.easypanel.host/webhook"

payload_data = {
    "workflow_name": "pre_call_processing",
    "execution_id": f"exec_{uuid.uuid4().hex[:12]}",
    "numero": "+5547997804224",
    "nome": "Ivan",
    "email": "",
    "agent_id": "agent_4f1dba5e5432cd193d324754bf",
    "Prompt_id": "33",
    "contexto": "Disparo manual ATS para o Ivan"
}

api_key = None
if os.path.exists(".env"):
    with open(".env", "r") as env_file:
        for line in env_file:
            if line.strip().startswith("WEBHOOK_API_KEY="):
                api_key = line.strip().split("=", 1)[1].strip()

if not api_key:
    api_key = os.getenv("WEBHOOK_API_KEY")

if not api_key:
    print("Erro: A chave de API (WEBHOOK_API_KEY) não foi encontrada.")
    exit(1)

headers = {
    "X-API-Key": api_key,
    "Content-Type": "application/json"
}

print(f"Disparando ligação para {payload_data['nome']} ({payload_data['numero']}) com Prompt ID {payload_data['Prompt_id']} e Agente {payload_data['agent_id']}...")
try:
    response = httpx.post(API_URL, headers=headers, json=payload_data, timeout=30.0)
    print(f"Status Code: {response.status_code}")
    print("Resposta da API:")
    print(response.json() if response.headers.get("content-type") == "application/json" else response.text)
except Exception as e:
    print("Ocorreu um erro ao tentar enviar o webhook:", e)
