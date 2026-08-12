# API Reference: `hub_backend`

O microserviço `hub_backend` fornece a API REST de Analytics Multi-Tenant da plataforma MindFlow. Ele agrega métricas de atendimento telefônico (Retell AI) e interações de WhatsApp, calcula estatísticas de funil, fadiga de leads, motivos de desconexão, distribuição horária e performance de agentes.

---

## 🌐 Base URL

- **Ambiente de Produção (Easypanel):** `https://hub-backend-github.bkpxmb.easypanel.host`
- **Ambiente Local (Desenvolvimento):** `http://localhost:8000`

---

## 🔐 Autenticação & Multi-Tenancy

O serviço opera com arquitetura **Multi-Tenant**. O cliente é identificado enviando o ID no Header HTTP ou via parâmetro de busca:

| Header / Query Param | Tipo | Descrição |
| :--- | :--- | :--- |
| `X-Client-ID` ou `client_id` | `String` | ID do cliente cadastrado na tabela `client_configurations` do Supabase Master. Se omitido, assume o cliente padrão `2`. |

---

## 📌 Endpoints Principais

### 1. Métricas Gerais (`/api/metrics`)
- **`GET https://hub-backend-github.bkpxmb.easypanel.host/api/metrics/summary`**: Retorna resumo das métricas globais de chamadas (total de ligações, duração média, custo acumulado, taxa de conversão, pontuação média de sentimento).
- **`GET https://hub-backend-github.bkpxmb.easypanel.host/api/metrics/daily`**: Retorna a evolução temporal diária de chamadas para gráficos de linha/barras.

#### Parâmetros de Filtro Comuns (Query Params)

| Parâmetro | Tipo | Descrição |
| :--- | :--- | :--- |
| `start_date` | `String (ISO)` | Data/Hora inicial de filtro em UTC. |
| `end_date` | `String (ISO)` | Data/Hora final de filtro em UTC. |
| `agent_id` | `String` | Filtrar por um agente específico da Retell AI. |
| `client_id` | `String` | ID do tenant cliente. |

---

### 2. Funil de Conversão (`/api/funnel`)
- **`GET https://hub-backend-github.bkpxmb.easypanel.host/api/funnel/summary`**: Retorna as etapas do funil de atendimento (Leads Contatados → Atendidos → Qualificados → Agendados) com contagens e taxas de conversão de cada etapa.

---

### 3. Chamadas Detalhadas (`/api/calls`)
- **`GET https://hub-backend-github.bkpxmb.easypanel.host/api/calls`**: Retorna lista paginada de chamadas gravadas com filtros por data, status, agente e telefone.
- **`GET https://hub-backend-github.bkpxmb.easypanel.host/api/calls/{call_id}`**: Retorna detalhes completos de uma chamada específica (áudio URL, transcrição na íntegra, análise de sentimento, custo e desconexão).

---

### 4. Análise de Fadiga (`/api/fatigue`)
- **`GET https://hub-backend-github.bkpxmb.easypanel.host/api/fatigue`**: Retorna métricas de re-tentativa e fadiga por lead (quantidade de chamadas recebidas por número, taxa de atendimento por quantidade de tentativas).

---

### 5. Distribuição Horária (`/api/hours`)
- **`GET https://hub-backend-github.bkpxmb.easypanel.host/api/hours/distribution`**: Retorna histograma de ligações por hora do dia (em fuso `America/Sao_Paulo`), identificando horários de pico e maior taxa de conversão.

---

### 6. Desconexões (`/api/disconnections`)
- **`GET https://hub-backend-github.bkpxmb.easypanel.host/api/disconnections/reasons`**: Retorna agrupamento por causa de término da chamada (`user_hangup`, `agent_hangup`, `call_transfer`, `inactivity`, `error`).

---

### 7. Performance de Agentes (`/api/agents`)
- **`GET https://hub-backend-github.bkpxmb.easypanel.host/api/agents`**: Lista métricas comparativas entre diferentes agentes de IA (volume de chamadas, duração média, conversão e custo acumulado por agente).

---

### 8. Agendamentos (`/api/agendamentos`)
- **`GET https://hub-backend-github.bkpxmb.easypanel.host/api/agendamentos/summary`**: Retorna total de reuniões e consultas confirmadas via robô de atendimento.

---

### 9. Analytics de WhatsApp (`/api/whatsapp`)
- **`GET https://hub-backend-github.bkpxmb.easypanel.host/api/whatsapp/metrics`**: Métricas de mensagens recebidas/enviadas, volume de conversas por lead e tempo médio de resposta no canal WhatsApp.

---

## ⚡ Exemplo de Resposta (`GET /api/metrics/summary`)

```json
{
  "total_calls": 1420,
  "successful_calls": 980,
  "conversion_rate": 0.6901,
  "average_duration_seconds": 184.5,
  "total_cost_usd": 42.15,
  "average_sentiment_score": 4.2
}
```
