# Workflows e Arquitetura — `post_call_processing`

O **`post_call_processing`** foi arquitetado seguindo o padrão de **Event-Driven Workflows (EDW)** e rastreabilidade Mestre-Detalhe do ecossistema MindFlow.

---

## 🏗️ Diagrama de Arquitetura e Roteamento

```mermaid
graph TD
    WH["POST /webhook/post-call/{client_id}"] -->|Autenticação Token| Auth["client_configurations (Master DB)"]
    Auth -->|Background Task| WF1["1. post_call_webhook_ligacao"]
    
    WF1 -->|Ingestão Bruta| DB_CALLS["Retell_calls_Mindflow (Tenant DB)"]
    WF1 -->|Valida Flag Call_predict| RouteDecision{"Call_predict Enabled?"}
    
    RouteDecision -->|True| CP["call_predict API"]
    RouteDecision -->|False| WF2["2. post_call_analysis_ai"]
    
    WF2 -->|1. History Check (DISTINCT call_id)| DB_CALLS
    WF2 -->|2. Few-shot RAG| MasterRAG["documents_fil (Master DB)"]
    WF2 -->|3. Decisão IA (gpt-4.1-nano)| AgentLLM["Agente de Decisão"]
    
    AgentLLM -->|Ligar? == True| WF3["3. post_call_retentativa"]
    AgentLLM -->|Ligar? == False| EndNoCall["Fim (min = 0)"]
    
    WF3 -->|Checa Agendamento| DB_AGEND["agendamentos (Tenant DB)"]
    WF3 -->|Valida Limite 1h| HourlyCheck{"Limite 1h?"}
    HourlyCheck -->|Liberado| PCP["pre_call_processing API"]
    
    PCP -->|Disparo de Chamada| Retell["Retell AI API"]
    
    subgraph AUDITORIA_EDW["Camada EDW"]
        WF1 -->|Mestre/Detalhe| EDW_M["workflow_executions"]
        WF2 -->|Mestre/Detalhe| EDW_S["workflow_step_executions"]
        WF3 -->|Mestre/Detalhe| EDW_S
    end
```

---

## ⚡ Workflows Detalhados

### 1. Workflow: `post_call_webhook_ligacao` (Ingestão & Roteamento Inicial)

- **Propósito:** Ponto de entrada mestre. Responsável pela ingestão imediata em tempo real e encaminhamento.
- **Passos (Nodes):**
  1. `raw_ingestion`: Grava/Atualiza evento bruto em `Retell_calls_Mindflow` (tenant DB).
  2. `route_decision`: Checa a flag `call_predict_enabled` / `Call_predict` em `client_configurations` (Supabase Master).
     - Se `True`: encaminha para o microsserviço `call_predict`.
     - Se `False`: encaminha para `post_call_analysis_ai`.

---

### 2. Workflow: `post_call_analysis_ai` (Agente de Decisão por IA & RAG)

- **Propósito:** Processamento de inteligência pós-chamada. Um agente autônomo baseado em LLM decide se deve ligar para o lead e em quantos minutos.
- **Passos (Nodes):**
  1. `history_check`: Consulta chamadas anteriores na `Retell_calls_Mindflow` do tenant.
     - **Regra de Contagem de Ligações:** A contagem de tentativas passadas é realizada agrupando por `call_id`s **únicos** (`count(DISTINCT call_id)` onde `call_id` não é nulo).
     - **Filtro de Limite na Última Hora:** Verifica o número de ligações realizadas para aquele número nos últimos 60 minutos.
  2. `vector_rag_master`:
     - ⚠️ **REGRA OBRIGATÓRIA DE RAG:** A busca de exemplos Few-Shot na tabela `documents_fil` é executada **estritamente no Supabase Master (projeto principal "Ryan")**, via `get_supabase_master()`, nunca no banco isolado do cliente.
  3. `agent_evaluation`:
     - O Agente de IA (`gpt-4.1-nano` / LangChain) analisa a transcrição e o contexto RAG, produzindo um JSON estruturado:
       - `Ligar?` (boolean)
       - `min` (number - minutos de espera)
       - `causa_raiz` (`Humano`, `Caixa Postal`, `URA`, `Queda`, `Falha`)
       - `nivel_interesse` (`Quente`, `Morno`, `Frio`, `Nulo`)
       - `alerta_sdr` (string)
       - `context` (string)
       - `drop_state` (`Abertura`, `Discovery`, `Pitch`, `Close`, `Nulo`)
  4. `update_call_record`: Atualiza `Retell_calls_Mindflow` com transcrição sanitizada, resumo para CRM e métricas de custo.
  5. `decision_routing`: Se `Ligar? == true`, aciona a `post_call_retentativa` passando os `min` minutos recomendados.

---

### 3. Workflow: `post_call_retentativa` (Execução de Agendamento e Rediscagem)

- **Propósito:** Aplicação de regras de retentativa e disparo de rediscagem.
- **⚠️ Tabela Descontinuada:** A tabela `Retell_Leads_Midflow` foi oficialmente descontinuada e **não é consultada nem atualizada**.
- **Passos (Nodes):**
  1. `check_meeting_scheduled`: Consulta exclusivamente a tabela `agendamentos` (tenant DB). Se o lead possui reunião com `status == 'agendado'`, aborta com `aborted_meeting_already_scheduled`.
  2. `check_hourly_limit`: Valida se o limite de ligações por hora para o número foi atingido.
  3. `calculate_wait_window`: Aguarda os `min` minutos recomendados pelo Agente e ajusta o disparo para a janela comercial válida de Brasília (`America/Sao_Paulo`, 09:00–18:00, Seg-Sex).
  4. `build_pre_call_payload`: Monta o payload estruturado para o microsserviço de disparo.
  5. `dispatch_pre_call_service`:
     - ⚠️ **REGRA DE DISPARO:** O disparo é realizado via requisição POST HTTP para a API interna do microsserviço **`pre_call_processing`** (`PRE_CALL_PROCESSING_URL`). **Nunca chama a API externa da Retell AI diretamente**.
  6. `finalize_edw_record`: Finaliza o rastreio no EDW (`workflow_executions`). **Nunca escreve linhas na `Retell_calls_Mindflow`** (essa tabela é alimentada exclusivamente pelos webhooks recebidos da Retell AI).

---

## 🗄️ Tabelas Supabase Utilizadas

| Tabela | Localização | Ação no Workflow |
| :--- | :--- | :--- |
| `client_configurations` | **Supabase Master (Ryan)** | Leitura de credenciais de tenant e flag `call_predict_enabled`. |
| `documents_fil` | **Supabase Master (Ryan)** | Consulta de embeddings RAG (Few-Shot). |
| `Retell_calls_Mindflow` | **Supabase Tenant** | Leitura de histórico (distinct `call_id`) e Ingestão de eventos brutos de webhook. |
| `agendamentos` | **Supabase Tenant** | Trava de verificação de reunião agendada (`status == 'agendado'`). |
| `workflow_executions` | **Supabase Tenant** | Registro mestre EDW (`post_call_webhook_ligacao`, `post_call_analysis_ai`, `post_call_retentativa`). |
| `workflow_step_executions` | **Supabase Tenant** | Registro de detalhe/nós EDW com inputs, outputs e logs. |
