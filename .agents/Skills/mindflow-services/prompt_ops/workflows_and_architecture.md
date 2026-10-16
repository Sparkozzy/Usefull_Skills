# PromptOps — Workflows, Arquitetura e Engenharia

O **PromptOps** é a plataforma de governança, testes e deploy contínuo de prompts da MindFlow. Ele elimina a edição manual e desprotegida de prompts no banco de dados de produção através de um fluxo estruturado com versionamento, Arena A/B, execução real de servidores MCP e Quality Gate rigoroso (> 90%).

---

## 🏗️ Arquitetura do Sistema

```mermaid
graph TD
    UI[Hub Frontend / PromptOps Web UI] -->|REST API| API[PromptOps FastAPI]
    
    API -->|Leitura e Snapshots| SupaMaster[(Supabase Master: Tabela Prompts)]
    API -->|Versionamento e Evals Logs| DedicatedDB[(PostgreSQL Dedicado: PromptOps)]
    API -->|Descoberta MCP| SupaClients[(Supabase: client_configurations)]
    
    API -->|SSE / Tool Calling| MCPSched[MCP: schedule_service]
    API -->|SSE / Tool Calling| MCPKravi[MCP: n8n-mcp-kravi]
    
    API -->|Inferência Modelo & Tools| OpenAI[OpenAI API: gpt-4o]
    API -->|LLM Juiz Imparcial| Judge[OpenAI API: LLM Judge]
    
    API -->|Quality Gate >= 90%| Deploy[Deploy Seguro: UPDATE Prompts]
    Deploy --> SupaMaster
```

---

## 🔄 Fluxo Operacional (End-to-End)

1. **Seleção de Prompt & Canal (Opção B):**
   - No dropdown principal do Hub, o usuário seleciona o cliente e canal desejado (ex: `Mindflow — 💬 WhatsApp` ou `ATS — 📞 Ligação / Voz`).
   - A API busca os dados diretamente na coluna oficial da tabela `Prompts` no Supabase Master:
     - `Prompt_Text` para **WhatsApp**.
     - `"Ligação/txt"` para **Ligação / Voz**.
     - `prompt_fup` para **Follow-Up**.
     - `"Prompt Insta"` para **Instagram**.
   - É criado automaticamente um snapshot no banco dedicado (`prod-<canal>-1`).

2. **Criação de Drafts e Edição Assistida:**
   - O engenheiro de prompt cria um novo draft (`v1.x.0-draft`) no Editor ou utiliza o Gerador de Prompts com IA (`POST /generator/suggest`), que gera sugestões automáticas e um diff visual unificado no formato Git.

3. **Arena A/B (Execução Concorrente com Ferramentas MCP Reais):**
   - O engenheiro testa a nova versão lado a lado com a versão em produção.
   - O PromptOps consulta a tabela `client_configurations` para obter os `mcp_urls` do cliente.
   - Conecta aos servidores via SSE oficial (`mcp.client.sse.sse_client` com `mcp==1.27.2`).
   - As ferramentas reais (`check_availability`, `getUserByPhone`, `make_phone_call`, etc.) são executadas e os resultados retornados são injetados no histórico para o modelo formular a resposta final.
   - Todos os inputs, outputs e latências das tools são auditados na tabela `tool_execution_logs`.

4. **Bateria de Avaliações (Evals) & Quality Gate:**
   - A versão é submetida a uma bateria de casos de teste automatizados (cenários de atendimento, objeções reais e testes de ativação mandatória de tools).
   - O **LLM Juiz** avalia de forma estrita e determinística:
     - Se o caso exigia uma ferramenta específica (ex: `check_availability` ou `getUserByPhone`) e ela não foi chamada ou foi chamada incorretamente, o caso é **automaticamente reprovado**.
     - A resposta gerada é validada contra a rubrica de critérios esperados.
   - É calculado o índice de aprovação (`approval_rate`):
     - **Score >= 90%:** Versão recebe o status `approved` e o botão **Publicar em Produção** é liberado.
     - **Score < 90%:** O deploy é **bloqueado**. O engenheiro deve ajustar o prompt e reexecutar a bateria.

5. **Deploy Atômico em Produção:**
   - Ao acionar `POST /api/v1/prompts/publish`, a API atualiza a coluna correspondente da linha existente no Supabase Master sem alterar o ID do cliente nem quebrar dependências de webhooks externos.

---

## 🛠️ Conexão e Regras com Servidores MCP

| Servidor MCP | Endpoint SSE | Ferramentas Ativas | Clientes Principais |
| :--- | :--- | :--- | :--- |
| **Schedule Service** | `https://schedule-service-github.bkpxmb.easypanel.host/sse` | `check_availability`, `schedule_appointment`, `make_phone_call`, `send_whatsapp_message` | Mindflow, ATS, Kravi Comercial, My Gain |
| **Kravi MCP (n8n)** | `https://n8n-mcp.mindflow-ia.com/mcp/mcp-kravi-iatize` | `getUserByPhone`, `getUserByCPF`, `getUserByEmail`, `loadSituatorAccounts` | Kravi SAC, Kravi Gestores de Contratos |

- **Header de Autenticação:** `Authorization: Bearer mf_sk_2026_pre_call_xK9v3Qm7bR4wT1nZ`.
- **Regra de Transporte:** Os servidores rejeitam chamadas HTTP POST diretas sem handshake SSE (HTTP 406). O consumo deve sempre utilizar o protocolo oficial SSE com stream bidirecional.
