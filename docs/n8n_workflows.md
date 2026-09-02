# Documentação de Serviços n8n (MindFlow EDW)

Este documento centraliza a visão geral e arquitetura dos fluxos n8n mantidos na infraestrutura da MindFlow. Estes fluxos são preservados em n8n por sua elevada customização em tempo real e não serão migrados para Python no momento.

---

## Workflows Mapeados

| Workflow | Tipo | Função Principal | Documentação Detalhada |
| :--- | :--- | :--- | :--- |
| **Webhook Ligação** | Webhook Receiver (HTTP POST) | Recebe eventos de ligação do Retell AI, salva log completo no Supabase (`Retell_calls_Mindflow`), roteia análises e agenda retentativas. | [n8n_webhook_ligacao.md](file:///home/ryanf/Downloads/mind-all/Usefull_Skills/.agents/Skills/mindflow-services/n8n_services/n8n_webhook_ligacao.md) |
| **Retentativa Mindflow** | Sub-workflow (`executeWorkflow`) | Controla políticas de re-discagem (verificação de reunião marcada em `Retell_Leads_Midflow`, teto de 15 tentativas, janela de horário BRT 09:00-19:00, montagem de prompt contextual e disparo na API Retell). | [n8n_retentativa.md](file:///home/ryanf/Downloads/mind-all/Usefull_Skills/.agents/Skills/mindflow-services/n8n_services/n8n_retentativa.md) |

---

## Integração com o Ecossistema MindFlow

```mermaid
flowchart TD
    Retell[Retell AI Platform] -->|Webhook Event POST| WH["n8n: Webhook Ligação"]
    
    WH -->|Log em Tempo Real| Supabase1[(Supabase: Retell_calls_Mindflow)]
    
    WH -->|call_analyzed + Sentimento OK| CA["n8n Sub-workflow: Call_analisys form"]
    WH -->|Caixa postal / Falha / Sem transcrição| WH_WAIT{"<3 tentativas na hora?"}
    
    WH_WAIT -->|Sim| W5[Pausa 5 min] --> RET["n8n Sub-workflow: Retentativa Mindflow"]
    WH_WAIT -->|Não| W5H[Pausa 5.23h] --> RET
    
    RET -->|Verifica Reunião| Supabase2[(Supabase: Retell_Leads_Midflow)]
    RET -->|Verifica Limite <15| Supabase1
    RET -->|Dentro do Horário BRT 09:00-19:00| PromptDB[(Supabase: Prompts)]
    
    RET -->|Disparo POST api.retellai.com| Retell
```
