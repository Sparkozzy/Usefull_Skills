# Workflows e Arquitetura: `hub_backend`

O `hub_backend` é uma aplicação **FastAPI** responsável pela camada de inteligência de dados, Analytics e Dashboards do ecossistema MindFlow. Ele implementa uma pipeline de **ETL multi-tenant diária** agendada e expõe dados analíticos em tempo real.

---

## 🏗️ Arquitetura e Agendador Cron

```mermaid
flowchart TD
    A[APScheduler Cron: 3:00 AM BRT] -->|Executa| B[run_daily_multi_tenant_etl]
    B -->|Busca Tenants| C[(Supabase Master: client_configurations)]
    
    subgraph Multi-Tenant ETL Pipeline
        C -->|Itera sobre client_id| D[run_etl_pipeline(client_id)]
        D -->|Extrai Dados Brutos| E[(Retell AI / Supabase Retell_calls_Mindflow)]
        D -->|Calcula Métricas e Agregações| F[Transformação Pandas / SQL]
        F -->|Persiste Tabelas Analíticas| G[(Supabase do Cliente: metricas_diarias)]
    end

    H[Dashboard Frontend / Cliente] -->|GET /api/metrics/summary X-Client-ID| I[Routers FastAPI Multi-Tenant]
    I -->|Consulta Dinâmica| G
```

---

## 🛠️ Detalhes da Arquitetura Multi-Tenant

1. **Gestão de Conexões (`app/multi_tenant.py`):**
   - Mantém um cache de instâncias de clientes do SDK Supabase associadas ao `client_id`.
   - Consulta as credenciais (`supabase_url`, `supabase_key`) na tabela `client_configurations` do banco de dados Master.
   - Garante isolamento estrito de dados entre clientes distintos.

2. **Pipeline de ETL Diária (`app/etl.py`):**
   - Disparada automaticamente todos os dias às **3:00 AM BRT** via `APScheduler` (`AsyncIOScheduler`).
   - Normaliza datas para o fuso horário de **Brasília (`America/Sao_Paulo`)**.
   - Processa logs brutos da Retell AI (`Retell_calls_Mindflow`) e calcula:
     - Duração efetiva de chamadas.
     - Classificação de desconexão (`user_hangup`, `agent_hangup`, etc.).
     - Análise de sentimentos e transcrições.
     - Custos por ligação e por agente.
   - Atualiza agregados históricos para consultas instantâneas no dashboard.

3. **Convenção de Timezones:**
   - **Banco de Dados (Postgres/Supabase):** Armazenamento estrito em **UTC (ISO 8601)**.
   - **Camada de Aplicação / Métricas:** Manipulação interna e consolidação por hora/dia no fuso horário **`America/Sao_Paulo`**.
