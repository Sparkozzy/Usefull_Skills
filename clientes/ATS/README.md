# Backup ATS Tecnologia - Mindflow

Este diretório contém o backup completo das informações da **ATS Tecnologia**, estruturado entre **Ativos** (elementos para uso operacional contínuo) e **Legado** (documentação histórica e arquivos de apoio).

---

## 🚀 1. Ativos (Em Uso Operacional)

Localizados em: `clientes/ATS/ativos/`

### A. Prompts Supabase (`ativos/prompts_supabase/`)
Extraídos diretamente da tabela `Prompts` do Supabase Master (`ghayhpwthdbmnpsptcnb.supabase.co`):
- **[prompt_33_ats_ligacao_matheus.md](file:///c:/Users/valgo/OneDrive/Documentos/USKILL_ATUALIZADO/clientes/ATS/ativos/prompts_supabase/prompt_33_ats_ligacao_matheus.md)**: Prompt de ligação ativa (Matheus) com instruções detalhadas de abordagem, triagem de leads, contorno de objeções e agendamento.
- **[prompt_101_ats_evento.md](file:///c:/Users/valgo/OneDrive/Documentos/USKILL_ATUALIZADO/clientes/ATS/ativos/prompts_supabase/prompt_101_ats_evento.md)**: Prompt focado no evento ATS / abordagem institucional.
- **`prompts_supabase_raw.json`**: Dump JSON bruto dos registros retornados pelo banco.

### B. Agente Retell AI (`ativos/retell_agent/`)
Extraído diretamente da API do Retell AI (`api.retellai.com`):
- **[AGENTE_RETELL_ATS.md](file:///c:/Users/valgo/OneDrive/Documentos/USKILL_ATUALIZADO/clientes/ATS/ativos/retell_agent/AGENTE_RETELL_ATS.md)**:
  - **Agent ID:** `agent_4f1dba5e5432cd193d324754bf`
  - **Agent Name:** `Agente ATS`
  - **Voice:** `11labs-Adrian` (Multilingual)
  - **LLM ID:** `llm_c041f19c06154f024a5983eb8ab7` (`gpt-4o-mini`)
  - **Funções / Tools:** Definição completa das chamadas de ferramentas (`transfer_call`, `end_call`, etc.) e mensagem inicial.
- **`agent_retell_raw.json`** e **`llm_retell_raw.json`**: Definições brutas da API do Retell.

---

## 📦 2. Legado (Consulta e Histórico)

Localizados em: `clientes/ATS/legado/`

- **`documentos/`**:
  - Contrato assinado (`Contrato ATS Mindflow [assinado].pdf`)
  - Atas de Onboarding e reuniões comerciais com equipe ATS
  - Relatório de Homologação e testes de IA
  - Relatórios de Conversão (`Relatorio_Conversao_ATS_31ago.pdf` e `.docx`)
  - Apresentações e materiais institucionais (`Folder_ATS_AB2L_Rio_2026.pdf`, `Soluções_ATS_geral.pdf`, `Palestra_Soberania_Digital.pdf`, etc.)
  - Playbook do Agente ATS (`PLAYBOOK_AGENTE_ATS.md`) e prompts legados em texto
- **`leads_e_dados/`**:
  - Planilhas formatadas de leads (`Leads_08-10-26_formatado.xlsx`)
  - Bases de disparo de escritórios de advocacia (`escritorios_advocacia_disparo_formatado.csv` e `..._api.csv`)
  - Histórico de chamadas (`ats_calls.csv`)
- **`audios/`**:
  - Gravações e amostras de ligações reais (`ligação_mais1min.wav`, `recording.wav`)
- **`scripts_disparo/`**:
  - Scripts Python legados de trigger via webhook (`disparar_ats.py`) e consulta de banco (`check_ats_db.py`, `inspect_ats_db.py`)
