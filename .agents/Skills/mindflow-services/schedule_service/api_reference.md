# API Reference: `schedule_service`

O microserviço `schedule_service` gerencia agendamentos de consultas e checagem de disponibilidade de agenda multi-tenant de forma integrada com o **Google Calendar**, **Supabase**, **Z-API (WhatsApp)** e webhooks de **CRM**. Além de expor uma API HTTP/REST em FastAPI, o serviço oferece um servidor **MCP (Model Context Protocol)** para integração direta com agentes de IA.

---

## 🌐 Base URL

- **Ambiente de Produção (Easypanel):** `https://schedule-github.bkpxmb.easypanel.host`
- **Ambiente Local (Desenvolvimento):** `http://localhost:8000`

---

## 🔐 Autenticação

A autenticação da API REST é realizada via HTTP Bearer Token:

| Header | Tipo | Descrição |
| :--- | :--- | :--- |
| `Authorization` | `String` | Formato `Bearer <API_BEARER_TOKEN>`. |

---

## 📌 Endpoints REST

### 1. `POST /webhook/schedule`
Recebe solicitações de agendamento de reuniões/consultas, registra o evento no banco e enfileira o processamento em background via Redis ARQ worker.

- **URL Completa:** `POST https://schedule-github.bkpxmb.easypanel.host/webhook/schedule`
- **Status Code Sucesso:** `202 Accepted`
- **Header:** `Authorization: Bearer <TOKEN>`

#### Payload de Entrada (JSON)

```json
{
  "client_id": "cliente_alpha",
  "nome": "Carlos Eduardo",
  "email": "carlos@exemplo.com",
  "numero": "+5511988887777",
  "canal": "WhatsApp",
  "data_agendamento": "2026-08-28T15:00:00-03:00",
  "titulo": "Consulta Inicial de Alinhamento",
  "resumo": "Lead interessado no plano corporativo.",
  "agent_id": "agent_voice_01"
}
```

#### Parâmetros do Payload

| Campo | Tipo | Obrigatório | Descrição |
| :--- | :--- | :--- | :--- |
| `client_id` | `String` | Sim | Identificador do cliente no Supabase Master. |
| `nome` | `String` | Sim | Nome do lead/paciente. |
| `email` | `String` | Sim | E-mail do lead para envio do convite do Google Calendar. |
| `numero` | `String` | Sim | Número de telefone no formato internacional. |
| `canal` | `String` | Sim | Canal de origem (ex: `WhatsApp`, `Voz`, `Web`). |
| `data_agendamento` | `String` | Sim | Data e hora em formato ISO 8601 com timezone offset. |
| `titulo` | `String` | Não | Título do evento na agenda. |
| `resumo` | `String` | Não | Detalhes/observações do agendamento. |
| `agent_id` | `String` | Não | ID do agente acionador. |

#### Resposta de Sucesso (`202 Accepted`)

```json
{
  "status": "Accepted",
  "execution_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "message": "Agendamento recebido e enviado para processamento em background."
}
```

---

### 2. `POST /webhook/check-availability`
Consulta síncrona e concorrente de horários disponíveis na agenda do cliente dentro de um intervalo de datas.

- **URL Completa:** `POST https://schedule-github.bkpxmb.easypanel.host/webhook/check-availability`
- **Status Code Sucesso:** `200 OK`

#### Body JSON

```json
{
  "client_id": "cliente_alpha",
  "data_inicial": "2026-08-25T08:00:00-03:00",
  "data_final": "2026-08-25T18:00:00-03:00"
}
```

#### Resposta de Sucesso (`200 OK`)

```json
{
  "slots_disponiveis": [
    {
      "inicio": "2026-08-25T09:00:00-03:00",
      "fim": "2026-08-25T10:00:00-03:00"
    },
    {
      "inicio": "2026-08-25T14:00:00-03:00",
      "fim": "2026-08-25T15:00:00-03:00"
    }
  ]
}
```

---

## 🤖 Servidor MCP (FastMCP)

O arquivo `mcp_server.py` disponibiliza ferramentas MCP para assistentes de IA:

1. **`consultar_disponibilidade`**: Retorna os horários livres na agenda filtrando feriados e agendamentos conflitantes.
2. **`agendar_consulta`**: Executa o fluxo de criação de agendamento e notificação.
3. **`cancelar_agendamento`**: Cancela evento no Google Calendar e atualiza o Supabase.
