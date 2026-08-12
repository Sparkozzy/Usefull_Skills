# API Reference: `pre_call_processing`

O microserviço `pre_call_processing` é responsável por receber solicitações de ligações telefônicas individuais ou em lote (via CSV), efetuar higienização de dados, agendamento temporal persistente em fila Redis (ARQ) e efetuar chamadas via integração com a API da **Retell AI**.

---

## 🌐 Base URL

- **Ambiente de Produção (Easypanel):** `https://call-github.bkpxmb.easypanel.host`
- **Ambiente Local (Desenvolvimento):** `http://localhost:8000`

---

## 🔐 Autenticação

Todas as chamadas para os endpoints deste microserviço exigem autenticação via Header HTTP:

| Header | Tipo | Descrição |
| :--- | :--- | :--- |
| `X-API-Key` | `String` | Chave de segurança configurada na variável `WEBHOOK_API_KEY`. |

---

## 📌 Endpoints

### 1. `POST /webhook`
Dispara uma ligação individual imediatamente ou em horário futuro programado.

- **URL Completa:** `POST https://call-github.bkpxmb.easypanel.host/webhook`
- **Status Code Sucesso:** `202 Accepted`
- **Headers:** `X-API-Key: <CHAVE>`

#### Payload de Entrada (JSON)

```json
{
  "workflow_name": "pre_call_processing",
  "execution_id": "exec_1234567890",
  "numero": "+5548999999999",
  "nome": "João Silva",
  "email": "joao.silva@exemplo.com",
  "agent_id": "agent_1e4cfa23e3910c557d82167949",
  "Prompt_id": "24",
  "quando_ligar": "2026-08-25T14:30:00-03:00",
  "empresa": "Tech Solutions",
  "segmento": "SaaS B2B",
  "contexto": "Lead demontrou interesse no plano Enterprise",
  "from_number": "+5511999998888"
}
```

#### Parâmetros do Payload

| Campo | Tipo | Obrigatório | Descrição |
| :--- | :--- | :--- | :--- |
| `workflow_name` | `String` | Sim | Nome do workflow acionador. |
| `execution_id` | `String` | Sim | ID único de rastreabilidade do cliente/evento. |
| `numero` | `String` | Sim | Telefone no formato E.164 iniciado obrigatoriamente por `+` (ex: `+5548999999999`). |
| `nome` | `String` | Sim | Nome do destinatário da ligação (higienizado automaticamente). |
| `email` | `String` | Sim | E-mail do cliente (aceita `.` ou string vazia como fallback). |
| `agent_id` | `String` | Não | ID do agente Retell para sobreposição (`override_agent_id`). |
| `Prompt_id` | `String` | Não | ID ou nome do prompt cadastrado na tabela `Prompts` do Supabase. |
| `quando_ligar` | `String` | Não | Timestamp ISO 8601 com offset de timezone. Se omitido/passado, a ligação é disparada imediatamente. |
| `empresa` | `String` | Não | Nome da empresa para injeção de variáveis no prompt. |
| `segmento` | `String` | Não | Segmento de atuação. |
| `contexto` | `String` | Não | Contexto customizado para a IA da Retell AI. |
| `from_number` | `String` | Não | Número remetente cadastrado na Retell AI. |

#### Resposta de Sucesso (`202 Accepted`)

```json
{
  "status": "success",
  "message": "Webhook aceito, registro mestre criado e delegado para a fila persistente.",
  "execution_db_id": "b3f6c8d2-4e2a-412b-98df-89212ab56789"
}
```

---

### 2. `POST /webhook/csv`
Envia um arquivo CSV contendo múltiplos leads para agendamento em lote com distribuição temporal de disparos (frequência configurável).

- **URL Completa:** `POST https://call-github.bkpxmb.easypanel.host/webhook/csv`
- **Content-Type:** `multipart/form-data`
- **Status Code Sucesso:** `200 OK`

#### Parâmetros do Form (`Form Data`)

| Campo | Tipo | Obrigatório | Descrição |
| :--- | :--- | :--- | :--- |
| `file` | `UploadFile` | Sim | Arquivo `.csv` com colunas obrigatórias `numero`, `nome`, `email`. |
| `horario_inicio` | `String` | Sim | Horário inicial permitido no formato `HH:MM` (ex: `08:00`). |
| `horario_fim` | `String` | Sim | Horário final permitido no formato `HH:MM` (ex: `20:00`). |
| `frequencia` | `Float` | Sim | Intervalo em segundos entre cada disparo (mínimo `1.0`). |
| `agent_id` | `String` | Sim | ID do agente da Retell AI. |
| `prompt_id` | `String` | Sim | ID do prompt na tabela `Prompts`. |
| `contexto` | `String` | Não | Contexto global aplicado a todos os leads do lote. |

#### Resposta de Sucesso (`200 OK`)

```json
{
  "status": "success",
  "message": "Arquivo CSV validado com sucesso e enfileirado para processamento assíncrono.",
  "batch_id": "c71a4f00-302a-4e89-9a00-9831a298bc71",
  "total_leads": 150
}
```

---

### 3. `POST /webhook/csv/cancel`
Botão de pânico e kill-switch emergencial para interromper disparos de lotes ativos.

- **URL Completa:** `POST https://call-github.bkpxmb.easypanel.host/webhook/csv/cancel`
- **Status Code Sucesso:** `200 OK`

#### Parâmetros do Form (`Form Data`)

| Campo | Tipo | Obrigatório | Descrição |
| :--- | :--- | :--- | :--- |
| `batch_id` | `String` | Não | ID do lote a cancelar. Se omitido, cancela **todos** os lotes ativos globais. |

#### Resposta de Sucesso (`200 OK`)

```json
{
  "status": "success",
  "message": "Interrupção do lote c71a4f00-302a-4e89-9a00-9831a298bc71 ativada. Novos disparos foram bloqueados com sucesso.",
  "batch_id": "c71a4f00-302a-4e89-9a00-9831a298bc71"
}
```

---

### 4. `POST /webhook/csv/update-frequency`
Altera dinamicamente o intervalo de tempo entre disparos de um lote em andamento.

- **URL Completa:** `POST https://call-github.bkpxmb.easypanel.host/webhook/csv/update-frequency`
- **Status Code Sucesso:** `200 OK`

#### Body JSON

```json
{
  "batch_id": "c71a4f00-302a-4e89-9a00-9831a298bc71",
  "frequencia": 120.0
}
```

---

### 5. `GET /webhook/csv/active`
Lista todos os lotes de CSV ativos (`RUNNING` ou `PENDING`) com contagem de leads pendentes no Redis.

- **URL Completa:** `GET https://call-github.bkpxmb.easypanel.host/webhook/csv/active`
- **Status Code Sucesso:** `200 OK`

---

### 6. `GET /webhook/debug/redis`
Endpoint de diagnóstico para inspeção de chaves e estado da fila ARQ Redis em tempo real.

- **URL Completa:** `GET https://call-github.bkpxmb.easypanel.host/webhook/debug/redis`

---

## ⚠️ Códigos de Erro Comuns

| Código | Descrição |
| :--- | :--- |
| `401 Unauthorized` | Header `X-API-Key` ausente ou divergente da variável `WEBHOOK_API_KEY`. |
| `400 Bad Request` | Número de telefone sem `+`, intervalo de horário inválido ou colunas CSV ausentes. |
| `422 Unprocessable Entity` | Erro no formato JSON ou campos obrigatórios Pydantic ausentes. |
| `500 Internal Server Error` | Erro de conexão com Supabase ou falha crítica no enfileiramento Redis. |
