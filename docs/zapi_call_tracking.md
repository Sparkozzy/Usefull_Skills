# Traqueamento de Chamadas WhatsApp Z-API (PostgreSQL Próprio)

## 📌 Mecanismo de Traqueamento Implementado

A aplicação **`zapi_voice_service`** possui um banco de dados PostgreSQL próprio para persistir o histórico completo e métricas de todas as chamadas telefônicas realizadas via WhatsApp.

---

## 📊 Estrutura da Tabela `voice_calls`

Cada ligação finalizada salva um registro na tabela `voice_calls` do PostgreSQL da aplicação com a seguinte estrutura:

| Campo na Tabela | Tipo | Origem no Service | Descrição |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | Auto-gerado (`PRIMARY KEY`) | ID interno do banco |
| `call_id` | `VARCHAR(255)` | UUID v4 gerado na chamada | Identificador único da chamada no Mindflow |
| `client_id` | `VARCHAR(100)` | Request body | ID do cliente contratante |
| `phone_number` | `VARCHAR(50)` | Request body / Z-API `phone` | Telefone do destinatário da chamada |
| `duration_seconds` | `INTEGER` | Calculado (`end_time - start_time`) | Duração total da ligação em segundos |
| `transcript` | `TEXT` | `session_audio.get_full_transcript()` | Transcrição completa da conversa (`User: ...`, `Agent: ...`) |
| `call_summary` | `TEXT` | `session_audio.generate_call_summary()` | Resumo inteligente gerado via LLM |
| `disconnection_reason` | `VARCHAR(100)` | Evento de encerramento (`user_hangup`, `error`, etc) | Motivo do encerramento da chamada |
| `status` | `VARCHAR(50)` | `completed` | Status final da chamada |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Auto-gerado | Data/hora UTC de criação |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | Auto-gerado | Data/hora UTC de atualização |

---

## 🛠️ DDL do Banco de Dados PostgreSQL Próprio

O script abaixo é verificado e executado automaticamente na inicialização da aplicação (`on_startup`), mas pode ser criado manualmente:

```sql
CREATE TABLE IF NOT EXISTS voice_calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id VARCHAR(255) UNIQUE NOT NULL,
    client_id VARCHAR(100) NOT NULL,
    phone_number VARCHAR(50) NOT NULL,
    duration_seconds INTEGER DEFAULT 0,
    transcript TEXT,
    call_summary TEXT,
    disconnection_reason VARCHAR(100),
    status VARCHAR(50) DEFAULT 'completed',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_voice_calls_client_id ON voice_calls(client_id);
CREATE INDEX IF NOT EXISTS idx_voice_calls_call_id ON voice_calls(call_id);
```

---

## 🔑 Variável de Ambiente Necessária no Easypanel

No serviço `zapi_voice_service` no Easypanel, adicione:

- **Chave**: `DATABASE_URL`
- **Valor**: `postgresql://<USER>:<PASSWORD>@<HOST>:5432/<DB_NAME>`

Exemplo no Easypanel:
`postgresql://zapi_user:sua_senha_aqui@zapi-voice-db:5432/zapi_voice_db`

---

## 🔗 Traceabilidade EDW Master

Além do PostgreSQL próprio da aplicação (`voice_calls`), a auditoria mestre é mantida no Supabase EDW:
1. **`workflow_executions`**: Registra o workflow com status (`SUCCESS`/`FAILED`).
2. **`workflow_step_executions`**: Registra a execução dos nós com os dados e métricas finalizadas.
