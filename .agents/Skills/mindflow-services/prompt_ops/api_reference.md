# PromptOps — API Reference

Serviço responsável pelo versionamento seguro, testes comparativos em tempo real (Arena A/B), execução e validação de ferramentas MCP reais, geração assistida por IA (Meta-Prompting) e bateria de avaliações automatizadas com Quality Gate para deploy em produção.

- **Base URL:** `https://prompt-ops-prompt-ops-api.bkpxmb.easypanel.host`
- **Protocolo:** REST (JSON) + SSE para MCP Tools
- **Repositório:** `https://github.com/Sparkozzy/Prompt_ops.git`
- **Quality Gate:** Mínimo de **90% de aprovação** nos evals para autorizar deploy para produção.

---

## 🧭 Sumário de Endpoints

### 1. Prompts de Produção (Leitura & Deploys)

#### `GET /api/v1/prompts/production/list`
Lista todos os prompts da tabela oficial `Prompts` no Supabase Master com detecção automática dos canais disponíveis por cliente.

**Resposta de Sucesso (200 OK):**
```json
[
  {
    "id": 1,
    "created_at": "2026-07-25T14:20:00Z",
    "Nome do cliente": "Mindflow",
    "Pormpt_Name": "First",
    "channels": ["whatsapp", "ligacao", "fup", "instagram"],
    "has_whatsapp": true,
    "has_ligacao": true,
    "has_fup": true,
    "has_insta": true
  }
]
```

#### `GET /api/v1/prompts/production/{prompt_id}?channel={channel}`
Obtém o conteúdo do prompt oficial para um canal específico (`whatsapp`, `ligacao`, `fup`, `instagram`).

- **Query Param `channel`:**
  - `whatsapp` (padrão): Mapeia para a coluna `Prompt_Text`.
  - `ligacao`: Mapeia para a coluna `"Ligação/txt"`.
  - `fup`: Mapeia para a coluna `prompt_fup`.
  - `instagram`: Mapeia para a coluna `"Prompt Insta"`.

#### `POST /api/v1/prompts/publish`
Publica uma versão aprovada diretamente na coluna correspondente da linha existente na tabela `Prompts` do Supabase.

> [!IMPORTANT]
> **Quality Gate Ativo:** A requisição retornará `400 Bad Request` se a versão selecionada tiver `eval_score < 0.90` (menos de 90% de aprovação).

**Payload:**
```json
{
  "version_id": "31c2653c-4d16-4332-829e-1b14c8363081",
  "author_email": "engenheiro@mindflow.com.br"
}
```

**Resposta:**
```json
{
  "success": true,
  "message": "Versão aprovada e publicada em produção no Supabase com sucesso!",
  "prompt_id": 1,
  "version_label": "v1.2.0-draft",
  "approval_rate": 1.0,
  "published_at": "2026-10-16T02:00:00Z"
}
```

---

### 2. Versionamento e Snapshots

#### `POST /api/v1/prompts/versions`
Cria uma nova versão de trabalho (draft) ou snapshot no banco dedicado PostgreSQL do PromptOps.

**Payload:**
```json
{
  "prompt_id": 1,
  "client_id": "2",
  "client_name": "Mindflow",
  "channel": "whatsapp",
  "version_label": "v1.2.0-draft",
  "prompt_text": "Você é o assistente comercial da MindFlow...",
  "model_name": "gpt-4o",
  "temperature": 0.7,
  "commit_message": "Refinamento do fluxo de agendamento",
  "author_email": "engenheiro@mindflow.com.br"
}
```

#### `GET /api/v1/prompts/versions?prompt_id={prompt_id}&channel={channel}`
Lista o histórico de versões registradas no banco dedicado, ordenadas decrescentemente por data de criação.

---

### 3. Arena A/B com Ferramentas MCP Reais

#### `POST /api/v1/arena/test-single`
Executa um turno de inferência contra uma versão com acionamento de MCP tools reais.

**Payload:**
```json
{
  "version_id": "5174de6a-f0d9-41c6-a2bd-ed11ed11e13a",
  "user_message": "Olá! Gostaria de agendar uma reunião nesta sexta às 14h.",
  "variables": {
    "nome": "Carlos",
    "telefone": "+5511999998888"
  },
  "chat_history": []
}
```

**Resposta:**
```json
{
  "version_id": "5174de6a-f0d9-41c6-a2bd-ed11ed11e13a",
  "version_label": "prod-1",
  "assistant_message": "Temos disponibilidade para sexta-feira às 14h! Vou agendar agora mesmo.",
  "tool_calls": [
    {
      "tool_name": "check_availability",
      "input_payload": { "client_id": "2", "data_inicial": "2026-10-16T14:00:00-03:00" },
      "output_payload": { "result": "{\"disponivel\": true}" },
      "latency_ms": 785,
      "status": "success"
    }
  ],
  "tokens_input": 3522,
  "tokens_output": 82,
  "latency_ms": 1068
}
```

#### `POST /api/v1/arena/test-compare`
Executa inferência concorrente (`asyncio.gather`) entre a Versão A e a Versão B, retornando latências, tokens consumidos e logs de ferramentas de ambos os modelos lado a lado.

---

### 4. Datasets de Avaliação (Evals) & Bateria de Testes

#### `POST /api/v1/evals/datasets`
Cadastra um novo caso de teste golden ou caso de refutação no dataset dedicado.

**Payload:**
```json
{
  "prompt_id": 38,
  "client_id": "7",
  "channel": "whatsapp",
  "scenario_name": "TOOL: Identificação Silenciosa do Morador por Telefone",
  "test_type": "single_turn",
  "input_data": {
    "variables": { "nome": "Juliana", "telefone": "+5551988881234" },
    "user_message": "Boa tarde, meu portão de garagem não está abrindo e não consigo entrar."
  },
  "expected_criteria": "Deve acionar silenciosamente a tool 'getUserByPhone' com o telefone do WhatsApp antes de qualquer pergunta cadastral.",
  "requires_tool": true,
  "expected_tool_name": "getUserByPhone",
  "is_refutation_case": true,
  "forbidden_literal_ids": ["1277", "275983", "15799"],
  "forbidden_symbolic_placeholders": ["singleAccountId", "singleUserId"],
  "created_by": "engenheiro@mindflow.com.br"
}
```

#### `GET /api/v1/evals/datasets?prompt_id={prompt_id}&channel={channel}`
Lista os casos de teste ativos cadastrados para o prompt e canal selecionados.

#### `PUT /api/v1/evals/datasets/{dataset_id}`
Atualiza os critérios ou inputs de um caso de teste existente, rastreando o autor da modificação (`updated_by`).

#### `DELETE /api/v1/evals/datasets/{dataset_id}`
Desativa (soft delete) um caso de teste obsoleto do dataset de avaliações, registrando `deleted_by` e `deleted_at`.

**Payload:**
```json
{
  "deleted_by": "engenheiro@mindflow.com.br"
}
```

#### `POST /api/v1/evals/run`
Dispara a bateria completa de avaliações para uma versão de prompt. Executa as chamadas MCP reais, submete o resultado ao LLM Juiz e atualiza o `eval_score` da versão.

**Payload:**
```json
{
  "version_id": "5174de6a-f0d9-41c6-a2bd-ed11ed11e13a",
  "triggered_by": "manual"
}
```

---

### 5. Meta-Prompting Assistido (Gerador)

#### `POST /api/v1/generator/suggest`
Recebe o prompt atual e uma instrução em linguagem natural, utilizando técnicas de engenharia de prompt (`gpt-4o`) para produzir a versão refinada e um diff unificado no formato Git.
