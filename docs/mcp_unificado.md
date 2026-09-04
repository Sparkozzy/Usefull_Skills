# MCP Unificado — Schedule Service (Mindflow)

> **Fonte da Verdade.** Este documento descreve o servidor MCP centralizado da Mindflow que substitui o MCP legado do n8n para **todos os agentes** (WhatsApp, Ligação, Instagram SDR).
> **URL Produção:** `https://schedule-service-github.bkpxmb.easypanel.host/sse`
> **Protocolo de Transporte:** SSE (Server-Sent Events)
> **Autenticação:** Bearer Token via Header `Authorization`

---

## Visão Geral da Arquitetura

```
┌──────────────────────────────────────────────────────────┐
│                   Agentes Mindflow                        │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │  WhatsApp   │  │  Retell AI   │  │  SDR Instagram │  │
│  │  General    │  │  (Ligação)   │  │  (n8n)         │  │
│  │  (Python)   │  │              │  │                │  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬────────┘  │
└─────────┼────────────────┼──────────────────┼───────────┘
          │    MCP / SSE   │                  │
          └────────────────┼──────────────────┘
                           ▼
          ┌────────────────────────────────────┐
          │    Schedule Service (MCP Unificado) │
          │    schedule-service-github           │
          │    bkpxmb.easypanel.host            │
          │  Tools:                             │
          │  • check_availability               │
          │  • schedule_appointment             │
          │  • send_whatsapp_message            │
          └────────────────┬───────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
   ┌─────────────────┐       ┌────────────────────┐
   │  Google Calendar │       │  Supabase + Redis  │
   │  (Agenda + Feriados)    │  (Agendamentos +    │
   └─────────────────┘       │   Z-API WhatsApp)  │
                              └────────────────────┘
```

---

## As 3 Ferramentas MCP

### 1. `check_availability` — Verificar Disponibilidade

**Quando usar:** SEMPRE antes de propor qualquer horário ao lead. Nunca assuma que um horário está livre sem consultar esta tool.

**O que faz automaticamente:**
- Verifica feriados nacionais do Brasil (Google Calendar)
- Filtra fins de semana
- Detecta conflitos com reuniões existentes
- Retorna slots de 1 hora com `available: true/false`

**Parâmetros obrigatórios:**

| Parâmetro | Tipo | Exemplo |
|---|---|---|
| `client_id` | string | `"2"` |
| `data_inicial` | ISO 8601 com timezone | `"2026-09-05T09:00:00-03:00"` |
| `data_final` | ISO 8601 com timezone | `"2026-09-05T18:00:00-03:00"` |

---

### 2. `schedule_appointment` — Agendar Reunião

**Quando usar:** Após lead confirmar horário livre + fornecer Nome, E-mail e Telefone.

**Parâmetros:**

| Parâmetro | Obrigatório | Tipo | Exemplo |
|---|---|---|---|
| `client_id` | Sim | string | `"2"` |
| `nome` | Sim | string | `"João Silva"` |
| `email` | Sim | string | `"joao@email.com"` |
| `numero` | Sim | string E.164 | `"+5548996027108"` |
| `canal` | Sim | `"whats"` ou `"ligacao"` | `"whats"` |
| `data_agendamento` | Sim | ISO 8601 com timezone | `"2026-09-05T14:00:00-03:00"` |
| `titulo` | Não | string | `"Atendimento - João Silva"` |
| `resumo` | Não | string | Desafios do lead discutidos |
| `agent_id` | Não | string | ID do agente para rastreabilidade |

---

### 3. `send_whatsapp_message` — Enviar Mensagem WhatsApp

**Quando usar:** Para confirmar agendamento por escrito ou enviar informações ao lead.

**Parâmetros:**

| Parâmetro | Obrigatório | Tipo |
|---|---|---|
| `client_id` | Sim | string |
| `phone` | Sim | string (`+55...` ou `55...`) |
| `message` | Sim | string |
| `execution_id` | Não | UUID — para vincular ao fluxo |
| `agent_id` | Não | string |

---

## Padrão de Integração — Python (whatsapp_general)

**Variáveis de ambiente obrigatórias:**
```env
SCHEDULE_MCP_URL=https://schedule-service-github.bkpxmb.easypanel.host/sse
SCHEDULE_MCP_API_KEY=mf_sk_2026_pre_call_xK9v3Qm7bR4wT1nZ
```

**Fallback automático:** Se as variáveis não existirem, o worker usa resposta simples sem MCP.

A integração está em `services/agent.py` → função `generate_llm_response_with_mcp`.

---

## Padrão de Integração — n8n

Use o nó `MCP Client` apontando para:
- **URL:** `https://schedule-service-github.bkpxmb.easypanel.host/sse`
- **Transport:** SSE
- **Auth:** Header `Authorization: Bearer mf_sk_2026_pre_call_xK9v3Qm7bR4wT1nZ`

---

## Declaração no System Prompt (XML Pattern Mindflow)

```xml
<Configuracao_Agente>
  <MCP_Server>
    <url>https://schedule-service-github.bkpxmb.easypanel.host/sse</url>
    <transporte>SSE</transporte>
    <client_id>{{ client_id }}</client_id>
  </MCP_Server>

  <Ferramentas>
    <tools>
      <tool name="check_availability">
        Verificar slots disponíveis na agenda.
        OBRIGATÓRIO usar ANTES de propor qualquer horário ao lead.
        A tool filtra automaticamente feriados BR e fins de semana.
        Parâmetros: client_id, data_inicial, data_final (ISO 8601 -03:00).
      </tool>
      <tool name="schedule_appointment">
        Agendar reunião no Google Calendar.
        Usar SOMENTE após lead confirmar horário e fornecer Nome, E-mail e Telefone.
        Parâmetros obrigatórios: client_id, nome, email, numero, canal, data_agendamento.
        canal deve ser "whats" para WhatsApp ou "ligacao" para voz.
      </tool>
      <tool name="send_whatsapp_message">
        Enviar mensagem de confirmação ao lead via WhatsApp (Z-API).
        Parâmetros obrigatórios: client_id, phone, message.
      </tool>
    </tools>
  </Ferramentas>

  <Regras_agendamento>
    <horario_permitido>09h às 18h</horario_permitido>
    <sem_finais_semana>true</sem_finais_semana>
    <sem_feriados>true</sem_feriados>
    <nao_agendar_datas_passadas>true</nao_agendar_datas_passadas>
    <fuso_horario>America/Sao_Paulo (UTC-3)</fuso_horario>
    <formato_data>ISO 8601 com offset explícito: ex. 2026-09-05T14:00:00-03:00</formato_data>
  </Regras_agendamento>

  <Script_Agendamento>
    <passo numero="1">Sondar perfil e desafios do lead. Registrar resumo para o campo "resumo".</passo>
    <passo numero="2">Perguntar preferência de data e horário.</passo>
    <passo numero="3">Chamar check_availability. NUNCA assumir disponibilidade.</passo>
    <passo numero="4">Se disponível: oferecer horário. Se não: apresentar alternativas (available: true).</passo>
    <passo numero="5">Coletar Nome e E-mail se não tiver.</passo>
    <passo numero="6">Chamar schedule_appointment com todos os dados.</passo>
    <passo numero="7">Chamar send_whatsapp_message com confirmação: data, hora e instruções.</passo>
  </Script_Agendamento>
</Configuracao_Agente>
```

---

## Tratamento de Erros

| Situação | Comportamento Esperado |
|---|---|
| Horário indisponível | A tool retorna `available: false`. Oferecer slots alternativos. |
| Fim de semana / Feriado | A tool identifica automaticamente. Sugerir próximo dia útil. |
| Erro na API | Não expor erro ao lead. Oferecer confirmação por WhatsApp em alguns minutos. |
| MCP fora do ar (Python) | `whatsapp_general` cai automaticamente no fallback sem agendamento. |

---

## Status de Migração dos Agentes

| Agente | MCP Antigo | MCP Unificado | Status |
|---|---|---|---|
| WhatsApp General (Python) | — | schedule-service | ✅ Integrado (09/2026) |
| Retell AI (Ligação) | n8n-mcp workflow | schedule-service | ⏳ Pendente migração |
| Helena WhatsApp (n8n) | n8n-mcp workflow | schedule-service | ⏳ Pendente migração |
| SDR Instagram (n8n) | n8n-mcp workflow | schedule-service | ⏳ Pendente migração |

> **Atenção:** O MCP antigo do n8n (`workflow: mcp`, ID `d1Rj8b4TmPpIaZIVd116T`) tem bug conhecido na tool `agendar_reuniao` retornando `Bad Request`. Priorizar migração para o schedule-service.

---

## Infraestrutura do Schedule Service (EasyPanel)

| Container | Função |
|---|---|
| `schedule_service_github` | API principal (FastAPI/FastMCP) — expõe as tools via SSE |
| `schedule_service_worker` | Worker ARQ — processa agendamentos de forma assíncrona |
| `schedule_service_schedule-redis` | Redis dedicado do schedule-service |

---

*Documento criado em 09/2026. Toda integração de novo agente com MCP deve referenciar este documento.*
