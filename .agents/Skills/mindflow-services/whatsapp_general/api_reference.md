# API Reference: `whatsapp_general`

O microserviço `whatsapp_general` é a plataforma multi-tenant de atendimento conversacional via **WhatsApp** da MindFlow. Ele recebe webhooks da **Z-API** e de conectores de **CRM**, transcreve áudios com **OpenAI Whisper**, aplica **Inbound Debounce** via Redis, executa agentes conversacionais com **OpenAI GPT-4/GPT-4o-mini**, gera respostas em voz (**TTS**) ou mensagens curtas fragmentadas, e mantém a memória de chat sincronizada no Supabase.

---

## 🌐 Base URL

- **Ambiente de Produção (Easypanel):** `https://whatsapp-github.bkpxmb.easypanel.host`
- **Ambiente Local (Desenvolvimento):** `http://localhost:8000`

---

## 🔐 Autenticação

A segurança dos webhooks é mantida validando o token exclusivo cadastrado por cliente:

| Header / Query | Tipo | Descrição |
| :--- | :--- | :--- |
| `X-MindFlow-Token` ou `Authorization: Bearer <TOKEN>` ou `?token=<TOKEN>` | `String` | Token de segurança validado contra o campo `mindflow_api_token` da tabela `client_configurations` do Supabase Master. |

---

## 📌 Endpoints HTTP

### 1. `POST /webhook/whatsapp/zapi/{client_id}`
Endpoint padrão para recebimento de webhooks enviados pela **Z-API**.

- **URL Completa:** `POST https://whatsapp-github.bkpxmb.easypanel.host/webhook/whatsapp/zapi/{client_id}`
- **Status Code Sucesso:** `200 OK`
- **Path Parameter:** `client_id` (ID do cliente no Supabase Master).

#### Payload de Entrada Exemplo (Z-API - Texto)

```json
{
  "eventType": "MESSAGE_RECEIVED",
  "instanceId": "3B9210",
  "messageId": "AB12345678",
  "phone": "5511999998888",
  "content": {
    "type": "TEXT",
    "text": "Olá! Gostaria de agendar uma demonstração do sistema.",
    "details": {
      "sender_from": "5511999998888",
      "sender_name": "Mariana Souza"
    }
  }
}
```

#### Payload de Entrada Exemplo (Z-API - Áudio)

```json
{
  "eventType": "MESSAGE_RECEIVED",
  "content": {
    "type": "AUDIO",
    "details": {
      "sender_from": "5511999998888",
      "file": {
        "publicUrl": "https://z-api.io/media/audio_sample.ogg"
      }
    }
  }
}
```

#### Payload de Entrada Exemplo (Z-API - PDF / Documento)

```json
{
  "eventType": "MESSAGE_RECEIVED",
  "content": {
    "type": "DOCUMENT",
    "text": "Segue comprovante em anexo",
    "details": {
      "sender_from": "5511999998888",
      "file": {
        "publicUrl": "https://z-api.io/media/fatura.pdf",
        "fileName": "fatura.pdf"
      }
    }
  }
}
```
> **Processamento de PDF:** A 1ª página do PDF é baixada em memória e resumida/classificada pelo modelo `gpt-4o-mini`, repassando o resultado no buffer para o agente principal.

#### Resposta do Debounce (Se for a thread vencedora)

```json
{
  "status": "accepted",
  "message": "Message buffered and execution scheduled.",
  "execution_id": "f5a04910-14e3-4c92-a1f9-901d81a70081"
}
```

#### Resposta do Debounce (Se novas mensagens chegaram durante a janela de 20s)

```json
{
  "status": "discarded",
  "message": "New messages arrived. Thread discarded."
}
```

---

### 2. `POST /webhook/whatsapp/crm/{client_id}`
Endpoint para receber mensagens enviadas via hub de CRM (`direction == "FROM_HUB"`).

- **URL Completa:** `POST https://whatsapp-github.bkpxmb.easypanel.host/webhook/whatsapp/crm/{client_id}`
- **Status Code Sucesso:** `200 OK`
- **Path Parameter:** `client_id`.

#### Body JSON Exemplo

```json
{
  "content": {
    "direction": "FROM_HUB",
    "type": "TEXT",
    "text": "Quais são os horários disponíveis?",
    "details": {
      "sender_from": "+5511999998888"
    }
  }
}
```

---

## ⚠️ Tratamento de Erros e Validação

- Caso ocorra falha de validação no modelo Pydantic (`422 Unprocessable Entity`), a API registra a tentativa falha diretamente na tabela `workflow_executions` do Supabase do cliente para rastreabilidade de suporte técnico antes de responder ao remetente.
