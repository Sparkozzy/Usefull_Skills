# API Reference — `post_call_processing`

O microsserviço **`post_call_processing`** é um serviço centralizado em Python (FastAPI + Supabase Multi-Tenant + EDW) responsável pelo recebimento de webhooks pós-chamada, persistência imediata, análise inteligente por Agente de IA com RAG no Supabase Master e execução de políticas de retentativa de discagem via microsserviços internos.

- **Base URL (Easypanel Produção):** `https://post-call-processing-api.bkpxmb.easypanel.host`
- **Autenticação:** Token na Query string (`token`) ou Header (`X-MindFlow-Token`).

---

## 📌 Endpoints

### 1. Verification Health Check

Verifica o status operacional e a saúde da aplicação.

- **URL:** `/health`
- **Método:** `GET`
- **Autenticação:** Nenhuma (Pública)

#### Exemplo de Resposta (`200 OK`):
```json
{
  "status": "ok",
  "service": "post_call_processing"
}
```

---

### 2. Webhook Pós-Chamada (`POST /webhook/post-call/{client_id}`)

Endpoint principal para recebimento de webhooks de ligação. Valida a autenticação do tenant no Supabase Master e processa o fluxo de forma **estritamente assíncrona** em segundo plano (`BackgroundTasks`).

- **URL:** `/webhook/post-call/{client_id}`
- **Método:** `POST`
- **Query Parameters:**
  - `token` (obrigatório, string): Token `mindflow_api_token` cadastrado na tabela `client_configurations` do Supabase Master.
- **Headers Aceitos:**
  - `X-MindFlow-Token` (opcional, string): Alternativa ao parâmetro de consulta `token`.

#### Payload de Exemplo (Entrada Webhook Retell AI):
```json
{
  "event": "call_analyzed",
  "timestamp": 1741520000,
  "call": {
    "call_id": "call_98f12a3b4c5d6e7f",
    "to_number": "+5585982021030",
    "from_number": "+41996852463",
    "agent_id": "agent_1e4cfa23e3910c557d82167949",
    "agent_name": "Kaique - SDR MindFlow",
    "agent_version": "1.2.0",
    "disconnection_reason": "user_hangup",
    "transcript": "User: Alô?\nAgent: Oi, Márcio? Aqui é o Caíque da MindFlow...\nUser: Agora não posso falar, me liga depois.",
    "recording_url": "https://api.retellai.com/recordings/call_98f12a3b4c5d6e7f.wav",
    "call_status": "ended",
    "duration_ms": 45000,
    "combined_cost": 0.042,
    "llm_cost": 0.02,
    "e2e_latency": {
      "eleven_labs_cost": 0.022
    },
    "call_analysis": {
      "user_sentiment": "neutral",
      "call_summary": "Lead atendeu porém estava ocupado e pediu para ligar mais tarde."
    },
    "retell_llm_dynamic_variables": {
      "customer_name": "Márcio Feitoza",
      "nome": "Márcio Feitoza",
      "email": "marcio@exemplo.com.br"
    }
  }
}
```

#### Respostas HTTP:

##### `200 OK` (Recebido e Processamento Assíncrono Iniciado)
```json
{
  "status": "success",
  "client_id": "cliente-a",
  "message": "Webhook recebido com sucesso. Processamento pós-ligação iniciado em background."
}
```

##### `401 Unauthorized` (Token Inválido ou Cliente Inexistente)
```json
{
  "detail": "Cliente 'cliente-a' não encontrado ou token de segurança inválido."
}
```

##### `400 Bad Request` (Payload JSON Malformado)
```json
{
  "detail": "Payload JSON inválido."
}
```
