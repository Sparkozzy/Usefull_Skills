# Documentation: Retentativa Mindflow (n8n Workflow)

## Visão Geral

O workflow **Retentativa Mindflow** é o mecanismo responsável por re-executar chamadas telefônicas ativas via **Retell AI** para leads que não atenderam, cujas chamadas caíram em caixa postal ou apresentaram falhas de discagem em tentativas anteriores.

O objetivo deste workflow é aplicar uma política inteligente e resiliente de retentativas:
1. **Verificação de Agendamento Prévio:** Garante que o lead ainda não marcou reunião (consultando a tabela `Retell_Leads_Midflow`). Se a reunião já estiver marcada, a retentativa é cancelada imediatamente.
2. **Limite de Tentativas Globais:** Impõe um teto máximo de **15 tentativas** de ligação por lead (consultando a tabela `Retell_calls_Mindflow`).
3. **Respeito à Janela de Horário Comercial (BRT):** Avalia se o horário atual em Brasília (`America/Sao_Paulo`) está dentro da janela permitida (entre **09:00 e 19:00**). Se estiver fora da janela, o fluxo aguarda 1 hora em loop até entrar no horário comercial.
4. **Construção de Prompt e Contexto Dinâmico:** Busca o prompt mestre na tabela `Prompts` (ID=1), sanitiza caracteres especiais e adiciona a instrução contextual: *"Você já tentou contato com esta pessoa e não obteve sucesso, não mencione isso no início da ligação, apenas se o usuário mencionar."*
5. **Disparo da Chamada via API Retell:** Efetua uma requisição POST direta para a API da Retell AI (`https://api.retellai.com/v2/create-phone-call`).
6. **Rastreabilidade e Contagem de Leads:** Atualiza a contagem de tentativas na tabela `Retell_Leads_Midflow` ou cria o registro caso o lead ainda não esteja cadastrado.

---

## Informações Gerais do Workflow

- **ID do Workflow (n8n):** `B_AOhnNcx8fvQZusnu9N0`
- **Gatilho de Entrada:** Invocado por outro workflow (`Execute Workflow Trigger`).
- **Credencial Supabase Utilizada:** `supabase Mindflow` (ID: `xPgzw7ayw9gmHNlh`)
- **API Externa Consumida:** Retell AI API (`POST https://api.retellai.com/v2/create-phone-call`)
- **Agente Retell de Retentativa:** `agent_2117bcaaf68e8b7cc8e0d160f7`
- **Número Originador (Outbound):** `+41996852463`
- **Tabelas Supabase Impactadas:**
  - `Retell_Leads_Midflow` (Leitura, Inserção e Atualização)
  - `Retell_calls_Mindflow` (Leitura para contagem total de chamadas)
  - `Prompts` (Leitura do prompt ID 1)

---

## Diagrama de Fluxo (Mermaid Flowchart)

```mermaid
flowchart TD
    TR["When Executed by Another Workflow"] --> SB2["Supabase2 (Get Retell_Leads_Midflow por Email)"]
    SB2 --> FLT{"Filter (Reuniao_marcada is empty?)"}
    
    FLT -->|SIM (Sem reunião)| CD["Consulta dados (Supabase: Retell_calls_Mindflow por Numero)"]
    FLT -->|NÃO (Já agendou)| END_REUN[Fim - Reunião já agendada]
    
    CD --> CT["Conta tentativas (Summarize count_created_at)"]
    CT --> C15{"<15? (Tentativas totais < 15)"}
    
    C15 -->|NÃO| END_MAX[Fim - Limite de 15 tentativas atingido]
    C15 -->|SIM| C1["Code1 (Valida Horário BRT 09:00 - 19:00)"]
    
    C1 --> IF_HORA{"If2 (Dentro do horário?)"}
    
    IF_HORA -->|NÃO| W1["Wait1 (Wait 1 hour)"] --> SB2
    IF_HORA -->|SIM| GET_P["Get a row (Supabase: Prompts id=1)"]
    
    GET_P --> EF2["Edit Fields2 (Prepara prompt, contexto e variáveis)"]
    EF2 --> JS1["Code in JavaScript1 (Sanitiza prompt e monta JSON body)"]
    JS1 --> HTTP["HTTP Request2 (POST api.retellai.com/v2/create-phone-call)"]
    
    HTTP --> SB1["Supabase (Get Retell_Leads_Midflow por Numero)"]
    SB1 --> IF_EXISTS{"If (Lead existe no banco?)"}
    
    IF_EXISTS -->|SIM| EF1["Edit Fields1 (Incrementa tentativas: tent = tentativas + 1)"]
    IF_EXISTS -->|NÃO| CR["Create a row (Supabase: Retell_Leads_Midflow)"]
```

---

## Detalhamento dos Nós (Nodes)

### 1. When Executed by Another Workflow
- **Tipo:** `n8n-nodes-base.executeWorkflowTrigger` (v1.1)
- **Descrição:** Ponto de entrada do sub-workflow. Recebe os parâmetros do workflow pai (`Webhook Ligação`):
  - `evento`
  - `Nome`
  - `Email`
  - `data`
  - `Numero`
  - `status`
  - `disconnection_reason`
- **Entradas:** Invocação por `executeWorkflow`.
- **Saídas:** `Supabase2`.

### 2. Supabase2
- **Tipo:** `n8n-nodes-base.supabase` (v1)
- **Descrição:** Realiza a busca (`operation: get`) na tabela `Retell_Leads_Midflow` onde `email_lead == $json.Email` para obter o status atual do lead.
- **Entradas:** `When Executed by Another Workflow` ou `Wait1`.
- **Saídas:** `Filter`.

### 3. Filter (Verificação de Reunião Marcada)
- **Tipo:** `n8n-nodes-base.filter` (v2.2)
- **Descrição:** Filtra os registros para garantir que o campo `Reuniao_marcada` está **vazio** (`operation: empty`).
  - **Passa no filtro (Vazio):** Lead continua no fluxo de retentativa (`Consulta dados`).
  - **Não passa (Preenchido):** Fluxo encerra sem realizar nova discagem.
- **Entradas:** `Supabase2`.
- **Saídas:** `Consulta dados`.

### 4. Consulta dados
- **Tipo:** `n8n-nodes-base.supabase` (v1)
- **Descrição:** Busca (`operation: getAll`) todas as chamadas na tabela `Retell_calls_Mindflow` para o número do lead (`Numero == $json.Numero`).
- **Entradas:** `Filter`.
- **Saídas:** `Conta tentativas`.

### 5. Conta tentativas
- **Tipo:** `n8n-nodes-base.summarize` (v1.1)
- **Descrição:** Agrupa o histórico retornado e conta o total de chamadas efetuadas (`count_created_at`).
- **Entradas:** `Consulta dados`.
- **Saídas:** `<15?`.

### 6. <15?
- **Tipo:** `n8n-nodes-base.if` (v2.2)
- **Descrição:** Verifica se o total de tentativas do lead é menor que 15 (`count_created_at < 15`).
  - **TRUE:** Prossegue para validação de horário (`Code1`).
  - **FALSE:** Encerra a execução (atingiu o limite máximo de 15 ligações).
- **Entradas:** `Conta tentativas`.
- **Saídas:** `Code1` (TRUE) e Fim de execução (FALSE).

### 7. Code1 (Validação de Horário Brasília)
- **Tipo:** `n8n-nodes-base.code` (v2)
- **Descrição:** Executa código JavaScript para obter a hora local em `America/Sao_Paulo`:
  ```javascript
  const date = new Date(new Date().toLocaleString("en-US", { timeZone: "America/Sao_Paulo" }));
  const hours = date.getHours();
  const resultado = (hours >= 9 && hours < 19) ? "Dentro do horário" : "Fora do horário";
  return { json: { ...$json, dataHoraBrasilia, resultado } };
  ```
- **Entradas:** `<15?` (TRUE).
- **Saídas:** `If2`.

### 8. If2 (Verificação da Janela Comercial)
- **Tipo:** `n8n-nodes-base.if` (v2.2)
- **Descrição:** Avalia o resultado retornado pelo script JS: `resultado == 'Dentro do horário'`.
  - **TRUE:** Redireciona para `Get a row` (busca prompt para ligar).
  - **FALSE:** Redireciona para `Wait1` (esperar 1 hora).
- **Entradas:** `Code1`.
- **Saídas:** `Get a row` (TRUE) e `Wait1` (FALSE).

### 9. Wait1 (Pausa Fora de Horário)
- **Tipo:** `n8n-nodes-base.wait` (v1.1)
- **Descrição:** Pausa a execução por 1 hora se estiver fora do horário comercial (ex: madrugada ou noite) e re-executa a checagem no `Supabase2`.
- **Entradas:** `If2` (FALSE).
- **Saídas:** `Supabase2`.

### 10. Get a row (Busca de Prompt Mestre)
- **Tipo:** `n8n-nodes-base.supabase` (v1)
- **Descrição:** Busca o prompt de sistema na tabela `Prompts` onde `id == 1`.
- **Entradas:** `If2` (TRUE).
- **Saídas:** `Edit Fields2`.

### 11. Edit Fields2
- **Tipo:** `n8n-nodes-base.set` (v3.4)
- **Descrição:** Prepara as variáveis para o disparo da ligação:
  - `prompt`: texto do prompt obtido em `Ligação/txt`
  - `numero`: número do lead
  - `nome`: nome do lead
  - `contexto`: `"[Status]. Você já tentou contato com esta pessoa e não obteve sucesso, não mencione isso no inicio da ligação, apenas se usuário mencionar."`
  - `email`: e-mail do lead
- **Entradas:** `Get a row`.
- **Saídas:** `Code in JavaScript1`.

### 12. Code in JavaScript1
- **Tipo:** `n8n-nodes-base.code` (v2)
- **Descrição:** Sanitiza o texto do prompt (removendo quebras de linha `\n`, `\r`, caracteres de markdown e aspas duplas) e estrutura o JSON body para a chamada Retell AI:
  ```json
  {
    "from_number": "+41996852463",
    "to_number": "data.numero",
    "override_agent_id": "agent_2117bcaaf68e8b7cc8e0d160f7",
    "metadata": {},
    "retell_llm_dynamic_variables": {
      "customer_name": "data.nome",
      "prompt": "cleanPrompt",
      "now": "ISO String",
      "contexto": "data.contexto",
      "email": "data.email",
      "numero_do_lead": "data.numero"
    },
    "custom_sip_headers": {
      "X-Custom-Header": "Custom Value"
    }
  }
  ```
- **Entradas:** `Edit Fields2`.
- **Saídas:** `HTTP Request2`.

### 13. HTTP Request2 (Disparo da Chamada Retell AI)
- **Tipo:** `n8n-nodes-base.httpRequest` (v4.2)
- **Descrição:** Faz a requisição POST para a API da Retell AI em `https://api.retellai.com/v2/create-phone-call` enviando o header `Authorization: Bearer key_540f92...` e o body configurado no nó anterior.
- **Entradas:** `Code in JavaScript1`.
- **Saídas:** `Supabase`.

### 14. Supabase (Consulta Lead para Atualização)
- **Tipo:** `n8n-nodes-base.supabase` (v1)
- **Descrição:** Busca (`operation: get`) na tabela `Retell_Leads_Midflow` pelo número para qual a chamada foi efetuada (`Numero == $json.to_number`).
- **Entradas:** `HTTP Request2`.
- **Saídas:** `If`.

### 15. If (Checagem de Existência do Lead)
- **Tipo:** `n8n-nodes-base.if` (v2.2)
- **Descrição:** Verifica se o número do lead já existe na tabela `Retell_Leads_Midflow` (`Numero` not empty).
  - **TRUE:** Redireciona para `Edit Fields1` (incrementa contagem).
  - **FALSE:** Redireciona para `Create a row` (cria novo registro).
- **Entradas:** `Supabase`.
- **Saídas:** `Edit Fields1` (TRUE) e `Create a row` (FALSE).

### 16. Create a row
- **Tipo:** `n8n-nodes-base.supabase` (v1)
- **Descrição:** Se o lead não existia em `Retell_Leads_Midflow`, insere uma nova linha com:
  - `email_lead`: E-mail do lead
  - `tentativas`: "1"
  - `Data_horario_ligação`: Data atual
  - `Nome`: Nome do lead
  - `Numero`: Telefone do lead
- **Entradas:** `If` (FALSE).
- **Saídas:** Nenhum nó posterior.

### 17. Edit Fields1
- **Tipo:** `n8n-nodes-base.set` (v3.4)
- **Descrição:** Se o lead já existia em `Retell_Leads_Midflow`, calcula a nova contagem de tentativas (`tent = Number($json.tentativas) + 1`) para atualizar a tabela.
- **Entradas:** `If` (TRUE).
- **Saídas:** Nenhum nó posterior.
