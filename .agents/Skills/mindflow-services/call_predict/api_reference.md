# API Reference: `call_predict`

O microserviço `call_predict` é o motor preditivo de Machine Learning da MindFlow. Ele avalia o histórico de chamadas passadas do lead, calcula a probabilidade de conversão/atendimento via modelos **XGBoost (Lead Scoring)** e determina o momento exato do dia com maior chance de sucesso (**Timing Predict**) antes de encaminhar o lead para o microserviço `pre_call_processing`.

---

## 🌐 Base URL

- **Ambiente de Produção (Easypanel):** `https://call-predict-github.bkpxmb.easypanel.host`
- **Ambiente Local (Desenvolvimento):** `http://localhost:8000`

---

## 🔐 Autenticação

| Header | Tipo | Descrição |
| :--- | :--- | :--- |
| `X-API-Key` | `String` | Chave de segurança validada na integração entre microsserviços. |

---

## 📌 Endpoints HTTP

### 1. `POST /webhook/predict`
Dispara a análise preditiva completa de um lead e o enfileira para inferência assíncrona.

- **URL Completa:** `POST https://call-predict-github.bkpxmb.easypanel.host/webhook/predict`
- **Status Code Sucesso:** `202 Accepted`

#### Payload de Entrada (JSON)

```json
{
  "numero": "+5548999999999",
  "agent_id": "agent_1e4cfa23e3910c557d82167949",
  "nome": "Fernando Souza",
  "email": "fernando@exemplo.com",
  "Prompt_id": "24",
  "contexto": "Interessado em plano imobiliário",
  "empresa": "Imóveis Premium",
  "segmento": "Imobiliário"
}
```

#### Parâmetros do Payload

| Campo | Tipo | Obrigatório | Descrição |
| :--- | :--- | :--- | :--- |
| `numero` | `String` | Sim | Telefone formato E.164 iniciado por `+`. |
| `agent_id` | `String` | Sim | ID do agente Retell AI. |
| `nome` | `String` | Sim | Nome completo do lead. |
| `email` | `String` | Sim | E-mail do lead. |
| `Prompt_id` | `String` | Sim | ID do prompt na tabela `Prompts`. |
| `contexto` | `String` | Não | Contexto customizado para a chamada. |
| `empresa` | `String` | Não | Nome da empresa do lead. |
| `segmento` | `String` | Não | Segmento de mercado. |

#### Resposta de Sucesso (`202 Accepted`)

```json
{
  "status": "Accepted",
  "execution_id": "67f18a20-0082-411a-b333-6623091bb78a",
  "message": "Lead enfileirado para predição"
}
```

---

### 2. `GET /health`
Endpoint de verificação de disponibilidade da API e horário em UTC.

- **URL Completa:** `GET https://call-predict-github.bkpxmb.easypanel.host/health`

```json
{
  "status": "ok",
  "timestamp": "2026-08-25T18:00:00.000000+00:00"
}
```
