# Memory — Registro Contínuo de Lições Aprendidas (Reflexion & Operações)

Este arquivo é um **documento vivo** mantido pelo agente para aprendizado contínuo (framework *Reflexion*). Antes de realizar intervenções em código, banco de dados ou infraestrutura, o agente consulta este histórico para evitar a recorrência de erros conhecidos.

---

### [2026-10-22] — 502 Bad Gateway no Easypanel (VIP Swarm vs tasks.<service> & OOM no boot)
- **Contexto:** Subir o `hub_backend` (FastAPI) e o `hub` (Node.js) em produção no Easypanel após rebuild, e garantir a atualização analítica do dashboard.
- **Erro:** Traefik retornava `502 Bad Gateway` em `https://hub-github.bkpxmb.easypanel.host` e `https://hub-backend.bkpxmb.easypanel.host`.
- **Causa raiz:**
  1. **OOM / Freeze no boot:** O `hub_backend` rodava `run_daily_multi_tenant_etl()` síncrono no startup. Sem volume persistente, tentava baixar 222.000 chamadas para a memória RAM, estourando os limites do container (OOM Kill / exit 137) e gerando loop de reinício (PID voltava sempre para 7).
  2. **Dependência de timezone:** Imagens base Debian slim (`python:3.10-slim` e `node:alpine`) não contêm timezone data por padrão. O uso de `zoneinfo.ZoneInfo("America/Sao_Paulo")` sem o pacote `tzdata` quebrava a inicialização.
  3. **Roteamento Swarm VIP no Traefik:** O Easypanel gerou as regras do Traefik apontando para o Virtual IP do Swarm (`http://hub_github:3000/`). A tabela IPVS do kernel do host travou os VIPs (pacotes SYN sofrendo timeout de 6s). Ao mesmo tempo, a resolução direta de instâncias via `tasks.<service>` (ex: `http://tasks.hub_github:3000/`) funcionava instantaneamente (1ms).
- **Solução:**
  1. Removida a rotina pesada de Full Sync no ciclo de vida (`lifespan`) do FastAPI. Agendador cron diário mantido e rotas manuais preservadas.
  2. Adicionado `tzdata` no `apt-get` e no `requirements.txt`, e `PYTHONUNBUFFERED=1` no Dockerfile.
  3. Atualizado o roteamento em `/etc/easypanel/traefik/config/main.yaml` de `hub_github:3000` para `tasks.hub_github:3000` e de `hub_hub-backend:8000` para `tasks.hub_hub-backend:8000`.
- **Lição:**
  - **Sempre conectar diretamente via SSH (`72.60.255.170`)** para diagnosticar containers e Traefik sem pedir prints/logs ao usuário.
  - Em problemas de 502 no Easypanel onde o container está vivo (`docker ps`), inspecione se a rota do Traefik está presa no VIP (`host unreachable / timeout`). Teste imediatamente `wget http://tasks.<service>:<porta>` dentro do container do Traefik.
  - Nunca execute processos pesados de dados (ETL full sync) dentro do ciclo de boot de containers web.
