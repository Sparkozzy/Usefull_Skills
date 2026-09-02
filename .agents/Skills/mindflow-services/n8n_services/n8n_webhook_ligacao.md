# Documentation: Webhook Ligação (n8n Workflow)

## Visão Geral

O workflow **Webhook Ligação** é o ponto de entrada centralizado para o recebimento de eventos assíncronos (Webhooks) enviados pela plataforma **Retell AI** durante e após a execução de chamadas telefônicas ativas e receptivas.

O objetivo deste workflow é:
1. **Persistência em Tempo Real:** Capturar o evento HTTP POST da Retell AI e registrar imediatamente os metadados brutos e consolidados da chamada na tabela `Retell_calls_Mindflow` do Supabase.
2. **Roteamento de Eventos:** Distinguir entre eventos de término imediato da ligação (`call_ended`) e eventos de conclusão de análise (`call_analyzed`).
3. **Filtro de Análise de Chamada:** Para chamadas analisadas com transcrição válida e sentimento não-negativo, disparar o sub-workflow `Call_analisys form`.
4. **Tratamento de Falhas e Retentativas:** Para chamadas que resultaram em erro de discagem (`dial_failed`, `dial_busy`), caixa postal (`voicemail_reached`) ou ausência de transcrição, o fluxo consulta o histórico de chamadas do lead na mesma hora/dia para determinar a frequência de retentativa:
   - Se houver **menos de 3 tentativas** na hora/dia: aguarda 5 minutos e dispara o workflow `Retentativa Mindflow`.
   - Se houver **3 ou mais tentativas** na hora/dia: aguarda 5.23 horas (~5 horas e 14 minutos) e dispara o workflow `Retentativa Mindflow`.

---

## Informações Gerais do Workflow

- **ID do Webhook (n8n Path):** `71ebee5e-0185-42e4-9259-91f4e19252d6`
- **URL Base de Produção:** `https://n8n-mcp-n8n.bkpxmb.easypanel.host/webhook/71ebee5e-0185-42e4-9259-91f4e19252d6`
- **Método HTTP:** `POST`
- **Credencial Supabase Utilizada:** `supabase Mindflow` (ID: `xPgzw7ayw9gmHNlh`)
- **Tabela Supabase Principal:** `Retell_calls_Mindflow`
- **Sub-Workflows Invocados:**
  - `Call_analisys form` (ID: `J518iCIzucLqNZml`)
  - `Retentativa Mindflow` (ID: `B_AOhnNcx8fvQZusnu9N0`)

---

## Diagrama de Fluxo (Mermaid Flowchart)

```mermaid
flowchart TD
    WH["Webhook (Retell Event POST)"] --> DA["Data_atual"]
    WH --> CR["Create a row (Supabase: Retell_calls_Mindflow)"]
    
    DA --> PDH["Pega data e hora (Format dd/MM/yyyy HH)"]
    PDH --> EF["Edit Fields (Extrai evento, Nome, Email, Numero, status, etc.)"]
    EF --> EV{"Evento (Switch)"}
    
    EV -->|"Call ended"| TE{"Tipo de erro (Switch)"}
    EV -->|"call_analyzed"| IF_VM{"If (voicemail_reached?)"}
    
    TE -->|"dial_failed / dial_busy"| CD["Consulta dados (Supabase: Retell_calls_Mindflow)"]
    
    IF_VM -->|SIM (Caixa Postal)| CD
    IF_VM -->|NÃO| IF1{"If1 (Tem Transcrição?)"}
    
    IF1 -->|NÃO| CD
    IF1 -->|SIM| IF2{"If2 (Sentimento Negativo?)"}
    
    IF2 -->|SIM (Negative)| END_NEG[Fim - Encerra sem análise]
    IF2 -->|NÃO| CA["Call_analysis (Execute Workflow: Call_analisys form)"]
    
    CD --> CT["Conta tentativas (Summarize count_data)"]
    CT --> C3{"<3? (Tentativas na hora < 3)"}
    
    C3 -->|SIM| W5["Wait 5 min"]
    C3 -->|NÃO| W5H["Wait (5.23 hours)"]
    
    W5 --> EW1["Execute Workflow1 (Retentativa Mindflow)"]
    W5H --> CRM["Call 'Retentativa Mindflow' (Retentativa Mindflow)"]
```

---

## Detalhamento dos Nós (Nodes)

### 1. Webhook
- **Tipo:** `n8n-nodes-base.webhook` (v2.1)
- **Descrição:** Ponto de entrada HTTP POST configurado no Retell AI. Recebe os dados brutos do evento da chamada em `body.event` (ex: `call_ended`, `call_analyzed`) e os detalhes da chamada em `body.call`.
- **Entradas:** Gatilho externo HTTP POST (Retell AI).
- **Saídas:** `Data_atual` e `Create a row`.

### 2. Data_atual
- **Tipo:** `n8n-nodes-base.dateTime` (v2)
- **Descrição:** Obtém o timestamp atual do sistema para cálculo de data/hora da chamada.
- **Entradas:** `Webhook`.
- **Saídas:** `Pega data e hora`.

### 3. Pega data e hora
- **Tipo:** `n8n-nodes-base.dateTime` (v2)
- **Descrição:** Formata o timestamp de `Data_atual` no formato customizado `dd/MM/yyyy HH` atribuindo ao campo `hora_e_dia`. Isso permite agrupar tentativas de ligações por janela de 1 hora.
- **Entradas:** `Data_atual`.
- **Saídas:** `Edit Fields`.

### 4. Edit Fields
- **Tipo:** `n8n-nodes-base.set` (v3.4)
- **Descrição:** Extrai e normaliza os campos essenciais do payload recebido do Webhook Retell AI:
  - `evento`: `body.event`
  - `Nome`: `body.call.retell_llm_dynamic_variables.nome`
  - `Email`: `body.call.retell_llm_dynamic_variables.email`
  - `data(hora)`: `hora_e_dia`
  - `Numero`: `body.call.to_number`
  - `status`: `body.call.call_status`
  - `disconnection_reason`: `body.call.disconnection_reason`
  - `hora_e_dia`: `$now.format("dd/MM/yyyy HH")`
- **Entradas:** `Pega data e hora`.
- **Saídas:** `Evento`.

### 5. Create a row
- **Tipo:** `n8n-nodes-base.supabase` (v1)
- **Descrição:** Insere imediatamente uma nova linha na tabela `Retell_calls_Mindflow` do Supabase com todos os metadados da ligação (Nome, Email, Numero, status, call_id, call_type, agent_id, agent_version, agent_name, transcript, recording_url, disconnection_reason, custos ElevenLabs/LLM/combinado, token usage, Duracao, data).
- **Entradas:** `Webhook`.
- **Saídas:** Nenhum nó posterior (Nó de persistência/log em paralelo).

### 6. Evento
- **Tipo:** `n8n-nodes-base.switch` (v3.2)
- **Descrição:** Roteia o fluxo baseado no tipo do evento informado em `$json.evento`:
  - **Saída 0 (`Call ended`):** Redireciona para o nó `Tipo de erro` se `evento == 'call_ended'`.
  - **Saída 1 (`call_analyzed`):** Redireciona para o nó `If` (Caixa postal) se `evento == 'call_analyzed'`.
- **Entradas:** `Edit Fields`.
- **Saídas:** `Tipo de erro` (Saída 0) ou `If` (Saída 1).

### 7. Tipo de erro
- **Tipo:** `n8n-nodes-base.switch` (v3.2)
- **Descrição:** Avalia o motivo da desconexão (`disconnection_reason`) quando o evento é `call_ended`:
  - **Saída 0 (`Falha`):** Se `disconnection_reason == 'dial_failed'`.
  - **Saída 1 (`dial_busy`):** Se `disconnection_reason == 'dial_busy'`.
- **Entradas:** `Evento` (Saída `Call ended`).
- **Saídas:** `Consulta dados` (para ambas as saídas).

### 8. If (Verificação de Caixa Postal)
- **Tipo:** `n8n-nodes-base.if` (v2.2)
- **Descrição:** Avalia se o evento `call_analyzed` indicou queda na caixa postal: `disconnection_reason == 'voicemail_reached'`.
  - **TRUE:** Redireciona para `Consulta dados` (para agendar retentativa).
  - **FALSE:** Redireciona para `If1` (para checar transcrição).
- **Entradas:** `Evento` (Saída `call_analyzed`).
- **Saídas:** `Consulta dados` (TRUE) e `If1` (FALSE).

### 9. If1 (Verificação de Transcrição)
- **Tipo:** `n8n-nodes-base.if` (v2.2)
- **Descrição:** Verifica se existe conteúdo transcrito na ligação (`transcript_object[0].content` existe).
  - **TRUE:** Redireciona para `If2` (avaliação de sentimento).
  - **FALSE:** Redireciona para `Consulta dados` (sem fala/resposta, processa retentativa).
- **Entradas:** `If` (FALSE).
- **Saídas:** `If2` (TRUE) e `Consulta dados` (FALSE).

### 10. If2 (Verificação de Sentimento Negativo)
- **Tipo:** `n8n-nodes-base.if` (v2.2)
- **Descrição:** Verifica se o sentimento do usuário analisado pela Retell foi negativo (`call_analysis.user_sentiment == 'negative'`).
  - **TRUE:** Interrompe o processamento (não envia lead para análise nem retentativa).
  - **FALSE:** Redireciona para `Call_analysis`.
- **Entradas:** `If1` (TRUE).
- **Saídas:** Sem nós conectados (TRUE) e `Call_analysis` (FALSE).

### 11. Call_analysis
- **Tipo:** `n8n-nodes-base.executeWorkflow` (v1.2)
- **Descrição:** Invoca o sub-workflow `Call_analisys form` (`J518iCIzucLqNZml`) repassando a transcrição completa, número, nome do lead, prompt do agente e e-mail.
- **Entradas:** `If2` (FALSE).
- **Saídas:** Nenhum nó posterior.

### 12. Consulta dados
- **Tipo:** `n8n-nodes-base.supabase` (v1)
- **Descrição:** Consulta na tabela `Retell_calls_Mindflow` do Supabase todas as chamadas onde `Numero == $json.Numero` E `data == $json.hora_e_dia`.
- **Entradas:** `Tipo de erro`, `If` (TRUE), `If1` (FALSE).
- **Saídas:** `Conta tentativas`.

### 13. Conta tentativas
- **Tipo:** `n8n-nodes-base.summarize` (v1.1)
- **Descrição:** Agrupa as linhas retornadas pela consulta e calcula o total de ocorrências em `count_data`.
- **Entradas:** `Consulta dados`.
- **Saídas:** `<3?`.

### 14. <3?
- **Tipo:** `n8n-nodes-base.if` (v2.2)
- **Descrição:** Avalia se o número de tentativas na hora atual é menor que 3 (`count_data < 3`).
  - **TRUE:** Redireciona para `Wait 5 min`.
  - **FALSE:** Redireciona para `Wait` (5.23 horas).
- **Entradas:** `Conta tentativas`.
- **Saídas:** `Wait 5 min` (TRUE) e `Wait` (FALSE).

### 15. Wait 5 min
- **Tipo:** `n8n-nodes-base.wait` (v1.1)
- **Descrição:** Coloca a execução em espera por 5 minutos antes da nova discagem.
- **Entradas:** `<3?` (TRUE).
- **Saídas:** `Execute Workflow1`.

### 16. Wait (5.23 horas)
- **Tipo:** `n8n-nodes-base.wait` (v1.1)
- **Descrição:** Coloca a execução em espera por 5.23 horas (5 horas e 14 minutos) antes de agendar nova discagem.
- **Entradas:** `<3?` (FALSE).
- **Saídas:** `Call 'Retentativa Mindflow'`.

### 17. Execute Workflow1
- **Tipo:** `n8n-nodes-base.executeWorkflow` (v1.2)
- **Descrição:** Dispara o sub-workflow `Retentativa Mindflow` (`B_AOhnNcx8fvQZusnu9N0`) enviando evento, nome, email, data atual (`$now`), número, status/contexto e motivo de desconexão após a pausa de 5 min.
- **Entradas:** `Wait 5 min`.
- **Saídas:** Nenhum nó posterior.

### 18. Call 'Retentativa Mindflow'
- **Tipo:** `n8n-nodes-base.executeWorkflow` (v1.2)
- **Descrição:** Dispara o sub-workflow `Retentativa Mindflow` (`B_AOhnNcx8fvQZusnu9N0`) enviando evento, nome, email, data da tentativa, número, status/contexto e motivo de desconexão após a pausa longa de 5.23 horas.
- **Entradas:** `Wait`.
- **Saídas:** Nenhum nó posterior.
