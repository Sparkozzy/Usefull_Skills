# Workflows e Arquitetura: `whatsapp_general`

O `whatsapp_general` implementa uma arquitetura resiliente baseada em **FastAPI**, **Redis Inbound Debounce**, **ARQ Workers**, **OpenAI Whisper/GPT-4** e **Supabase Multi-Tenant** sob as diretrizes de rastreabilidade **EDW**.

---

## 🏗️ Arquitetura de Recebimento e Debounce Redis

Para evitar que o robô envie múltiplas respostas separadas quando o usuário digita várias mensagens sequenciais no WhatsApp, o sistema utiliza o padrão **Redis Debounce**:

```mermaid
flowchart TD
    A[Z-API / CRM Webhook] -->|Mensagem de Entrada| B[FastAPI Endpoint]
    B -->|Sanitiza Telefone E.164 + Transcreve Áudio| C[NormalizedMessage]
    
    subgraph Inbound Debounce (20 segundos)
        C -->|1. RPUSH texto da mensagem| D[(Redis List: whatsapp_buffer:client:phone)]
        D -->|2. Tira Snapshot Inicial| E[pre_messages]
        E -->|3. Aguarda 20 segundos assíncronos| F[asyncio.sleep(20)]
        F -->|4. Tira Snapshot Final| G[post_messages]
    end
    
    G -->|pre_messages == post_messages?| H{Thread Vencedora?}
    H -->|Não| I[Descarta Thread - Outra requisição assumiu]
    H -->|Sim| J[Limpa Buffer + Concatena Mensagens]
    J -->|Cria Registro Mestre PENDING| K[(Supabase Tenant: workflow_executions)]
    J -->|Enfileira Worker Task| L[(Redis ZSET: arq:queue)]
```

---

## 🔄 Fluxo de Processamento do Worker (`process_whatsapp_response`)

```mermaid
flowchart TD
    L[(Redis ARQ Queue)] -->|Inicia Task| W[process_whatsapp_response]
    
    W -->|Passo 1| P1[whatsapp_flow_blacklist_check]
    P1 -->|Lead Blacklisted?| B1[Cancela Workflow]
    P1 -->|Clean| P2[whatsapp_flow_lead_check_create]
    
    P2 -->|Passo 3| P3[whatsapp_flow_update_last_msg_time]
    P3 -->|Passo 4| P4[whatsapp_flow_fetch_prompt]
    P4 -->|Passo 5| P5[whatsapp_flow_load_history]
    
    P5 -->|Passo 6: Chama OpenAI GPT-4 com Fallback| P6[whatsapp_flow_llm_response]
    
    P6 -->|Tipo de Resposta| R{Texto ou Áudio?}
    R -->|Áudio| T1[whatsapp_flow_tts_generation] --> T2[whatsapp_flow_send_audio Z-API]
    R -->|Texto| T3[whatsapp_flow_format_text_response] --> T4[whatsapp_flow_send_messages com 1.5s delay]
    
    T2 --> P8[whatsapp_flow_save_memory]
    T4 --> P8
    P8 -->|Salva n8n_chat_histories human/ai| M[(Supabase Tenant)]
    P8 -->|Atualiza status mestre para SUCCESS| K[(Supabase Tenant: workflow_executions)]
```

---

## ⚡ Regras de Negócio e Funcionalidades Chave

1. **Transcrição Automática de Áudio:**
   - Mensagens de voz recebidas no formato `AUDIO` da Z-API têm a URL do arquivo extraída e enviada ao modelo **OpenAI Whisper** (`transcribe_audio`), convertendo a fala do lead em texto e prefixando com `Audio: {texto}` antes de entrar no buffer do Redis.

2. **Verificação de Blacklist:**
   - Antes de consumir tokens de IA, a tabela `Blacklist_Mindflow` é consultada. Se o número estiver bloqueado, a execução é encerrada com status `SUCCESS` e resultado `ignored_blacklisted`.

3. **Fallback Dinâmico de LLM:**
   - A chamada à IA tenta utilizar o modelo principal configurado no cliente (ex: `gpt-4` com temperatura `0.8`). Em caso de instabilidade da OpenAI ou limite de taxa, o sistema executa um fallback automático para `gpt-4o-mini` (temperatura `0.7`).

4. **Fragmentação de Respostas em Texto:**
   - Para simular digitação humana natural no WhatsApp, respostas em texto extensas são fragmentadas em pequenas mensagens por um nó formatador e enviadas sequencialmente com um intervalo de **1.5 segundos** entre cada envio.

5. **Memória de Conversa Persistente (`n8n_chat_histories`):**
   - As últimas 10 interações são recuperadas para compor o contexto do chat. Ao final do processamento, tanto a mensagem concatenada do usuário (`human`) quanto a resposta gerada (`ai`) são persistidas com timestamps UTC.

6. **Suporte Multi-MCP Dinâmico por Tenant (`mcp_urls`):**
   - No worker (`call_agent_llm`), a lista `mcp_urls` (`text[]`) é lida da tabela `client_configurations` do Supabase Master para aquele `client_id`.
   - Utilizando `AsyncExitStack` em `generate_llm_response_with_mcp` (`services/agent.py`), o worker conecta simultaneamente a todas as URLs dos MCPs ativos (ex: `schedule_service` + MCP customizado do cliente), combina as ferramentas expostas e repassa o conjunto de funções para o modelo OpenAI (`gpt-4.1` / `gpt-4o`).

---

## 🎯 Arquitetura de Follow-Up Autônomo (`fup_flow`)

O módulo de Follow-Up automatiza o reengajamento inteligente de leads sem sobrecarregar a fila conversacional inbound:

```mermaid
flowchart TD
    A[POST /webhook/whatsapp/fup/client_id] --> B[FastAPI Endpoint]
    B -->|Cria Registro Mestre PENDING| K[(Supabase Tenant: workflow_executions)]
    B -->|Inicia background task| W[process_fup_request]
    
    W -->|Passo 1| S1[fup_flow_fetch_prompt_and_config]
    S1 -->|Busca Lead, Prompt e Configs| SB[(Supabase Master / Tenant)]
    
    S1 -->|Passo 1.1: Sem custom_context?| S11{fup_flow_check_inactivity}
    S11 -->|< 10 min de inatividade?| AB[Aborta FUP: lead_interacted_recently_skipped]
    S11 -->|>= 10 min de inatividade| S2[fup_flow_llm_agent]
    
    S2 -->|Decisão Determinística em JSON| DJ[acao, quando_executar, conteudo]
    DJ -->|Passo 3| S3[fup_flow_validate_permissions]
    S3 -->|Valida client_configurations| S4[fup_flow_schedule_action]
    
    S4 -->|Enfileira no ARQ com _defer_until| R[(Redis ZSET: arq:queue)]
    
    subgraph Execução Agendada no Worker
        R -->|No horário agendado| EX[execute_scheduled_fup_action]
        EX -->|Checa inatividade novamente| CHK{Inatividade < 10min?}
        CHK -->|Sim| CANC[Cancela envio agendado]
        CHK -->|Não| ACT{Canal Escolhido}
        ACT -->|agendar_mensagem| DISP1[Z-API send_text]
        ACT -->|audio| DISP2[TTS + Z-API send_audio]
        ACT -->|figurinha| DISP3[Z-API send-sticker]
        ACT -->|ligawhats| DISP4[pre_call_processing /call whats]
        ACT -->|ligacao| DISP5[pre_call_processing /webhook X-API-Key + Prompt_id]
    end
```

### Regras de Negócio do Follow-Up:
1. **Janela de Inatividade de 10 Minutos:**
   - O lead precisa estar sem interação por pelo menos 10 minutos (600s) tanto no momento da análise do agente (`fup_flow_check_inactivity`), quanto no momento exato do disparo final (`execute_scheduled_fup_action`). Se o lead responder a qualquer momento, o follow-up é descartado.
2. **Saída Estrita em JSON:**
   - O agente LLM responde estritamente no schema `{ acao, quando_executar, conteudo, justificativa }` com até 3 tentativas automáticas de correção.
3. **Validação de Permissões Multi-Tenant:**
   - Permissões verificadas na tabela `client_configurations`: `fup`, `can_send_fup_audio`, `fup_ligawhats`, `fup_ligacao`. Fallbacks automáticos são acionados caso um canal não esteja contratado pelo cliente.
4. **Integração com Telefonia Convencional (`pre_call_processing`):**
   - Quando a ação decidida é `ligacao`, o worker despacha uma chamada HTTP com o header `X-API-Key` e os parâmetros obrigatórios `Prompt_id`, `agent_id`, `numero`, `nome` e `email` para o endpoint `/webhook` do `pre_call_processing`, gerando a ligação via Retell AI.
