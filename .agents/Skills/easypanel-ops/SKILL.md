---
name: easypanel-ops
description: "Guia operacional e de troubleshooting do servidor de produção Easypanel (72.60.255.170). Use para diagnosticar 502 Bad Gateway, inspecionar containers Docker/Swarm, debugar rotas Traefik e resolver problemas de conectividade diretamente via SSH de forma autônoma."
---

# Easypanel & Server Ops (Documento Vivo de Produção)

Este documento é a **referência operacional oficial** para gerenciamento, monitoramento e troubleshooting de infraestrutura da MindFlow no servidor de produção Easypanel. 

> [!IMPORTANT]
> **ESTE É UM DOCUMENTO VIVO:** Toda vez que um novo problema de infraestrutura, comportamento anômalo do Docker/Traefik ou solução for descoberto, o agente deve **obrigatoriamente atualizar este documento** na seção *"Catálogo de Erros e Soluções Conhecidas"*.

---

## 🚀 1. Regra de Autonomia Imediata (Zero Friction)

Quando o usuário reportar qualquer problema de infraestrutura em produção (*"está dando bad gateway"*, *"o backend caiu"*, *"rebuild falhou"*, *"não atualiza"*):

1. **NÃO peça logs, prints ou telas ao usuário.**
2. O agente tem acesso SSH direto configurado no `.env` do workspace.
3. Conecte-se imediatamente via SSH (`72.60.255.170`) ou execute o script auxiliar [`scripts/check_server_health.py`](file:///home/ryanf/Downloads/mind-all/Usefull_Skills/.agents/Skills/easypanel-ops/scripts/check_server_health.py).
4. Inspecione o estado real dos containers, logs de erro e tabelas do Traefik de forma independente.
5. Aplique a correção na fonte (código, Dockerfile, configuração de rede ou Traefik) e teste a resposta pública (`curl -s -i https://...`) antes de responder ao usuário.

---

## 🔑 2. Dados de Acesso ao Servidor

- **Host:** `72.60.255.170`
- **Usuário:** `root`
- **Credenciais:** Configuradas em `.env` (`MINDFLOW / Servidor Produção`)
- **Porta SSH:** `22`
- **Painel Web:** `https://72.60.255.170:3000` (ou domínio interno do Easypanel)

---

## 🏗️ 3. Arquitetura de Rede do Easypanel

O Easypanel orquestra os serviços utilizando **Docker Swarm**:

1. **Traefik (`easypanel-traefik`):**
   - Roda como serviço na porta `80` e `443`.
   - Lê arquivos dinâmicos em `/etc/easypanel/traefik/config/main.yaml`.
   - Conectado à rede overlay `easypanel`.
2. **Redes Overlay:**
   - `easypanel`: Rede compartilhada entre o Traefik e os serviços para roteamento público.
   - `easypanel-<projeto>`: Rede interna isolada por projeto (ex: `easypanel-hub` para comunicação entre `hub` e `hub-backend`).
3. **Resolução de Nomes no Swarm:**
   - `<serviço>` (ex: `hub_github`): Resolve para o **Virtual IP (VIP)** gerenciado por IPVS.
   - `tasks.<serviço>` (ex: `tasks.hub_github`): Resolve **diretamente para os IPs reais dos containers** ativos (DNS round-robin).

---

## ⚡ 4. O Fenômeno Swarm VIP vs `tasks.<serviço>` (502 Bad Gateway)

> [!WARNING]
> **Causa número 1 de "502 Bad Gateway" fantasma no Easypanel:**
> O container da aplicação está vivo, rodando e respondendo 200 na porta interna, mas o Traefik devolve 502 com timeout de 6 segundos.
> 
> **Por que ocorre?** O Traefik foi configurado com a URL do VIP (`http://hub_github:3000/`). A tabela IPVS do kernel do host pode travar ou perder a rota do VIP durante deploys e recriações de containers. O pacote TCP SYN sofre timeout.
>
> **Solução Imediata:** 
> Alterar a URL do serviço no arquivo `/etc/easypanel/traefik/config/main.yaml` para usar o prefixo `tasks.` (ex: `http://tasks.hub_github:3000/` e `http://tasks.hub_hub-backend:8000/`). O Traefik recarrega o arquivo em tempo real sem downtime e o tráfego volta instantaneamente.

---

## 📋 5. Protocolo de Diagnóstico em 4 Passos

Para investigar qualquer falha no servidor:

### Passo 1: Estado dos Serviços
```bash
docker service ls
docker ps
```
- Se o container estiver com `STATUS: Restarting` ou reiniciando a cada poucos segundos, é **Crash no Boot** (veja Passo 2).
- Se estiver `STATUS: Up`, mas o domínio público der 502, é **Roteamento de Rede / Traefik** (veja Passo 3).

### Passo 2: Investigar Logs de Crash da Aplicação
```bash
docker logs --tail 50 $(docker ps -q --filter name=<nome_do_servico>)
```
Erros comuns:
- `OOMKilled: true` ou saída 137: Container estourou a memória RAM.
- `ZoneInfoNotFoundError`: Falta do pacote `tzdata` na imagem base.
- `ERR_ERL_PERMISSIVE_TRUST_PROXY`: `express-rate-limit` sem `validate: { trustProxy: false }`.

### Passo 3: Testar Conexão Direta do Traefik para o Container
Entre no container do Traefik e teste o endpoint de saúde:
```bash
TRAEFIK_CID=$(docker ps -q --filter name=traefik)
# Teste via tasks (direto ao container):
docker exec $TRAEFIK_CID wget -T 3 -qO- http://tasks.<nome_servico>:<porta>/health
# Teste via VIP (se falhar, o VIP está travado):
docker exec $TRAEFIK_CID wget -T 3 -qO- http://<nome_servico>:<porta>/health
```

### Passo 4: Corrigir Traefik se o VIP estiver travado
Se o teste com `tasks.<serviço>` funcionar e o teste com VIP falhar:
```bash
sed -i 's|"url": "http://<nome_servico>:<porta>/"|"url": "http://tasks.<nome_servico>:<porta>/"|g' /etc/easypanel/traefik/config/main.yaml
```

---

## 📚 6. Catálogo de Erros e Soluções Conhecidas (Histórico Vivo)

### Caso 1: Full Sync no Startup (OOM Kill / Crash Loop)
- **Sintoma:** Container Uvicorn reinicia continuamente (PID volta sempre para 7 ou 1), log pára logo após startup.
- **Causa:** Pipeline de ETL automática rodando no `lifespan` do FastAPI sem base local, tentando carregar centenas de milhares de linhas para o Pandas.
- **Solução:** Remover ETL do startup. Manter apenas no cron agendado e expor rota manual `POST /api/etl/run`.

### Caso 2: Falta de `tzdata` em Imagens Slim
- **Sintoma:** `zoneinfo.ZoneInfoNotFoundError: 'No time zone found with key America/Sao_Paulo'`.
- **Causa:** Imagens `python:3.xx-slim` e `alpine` não incluem tabelas de timezone IANA.
- **Solução:** Adicionar `tzdata` no `apt-get` e `tzdata>=2024.1` no `requirements.txt`.

### Caso 3: Incompatibilidade de `trust proxy` com `express-rate-limit` v7/v8
- **Sintoma:** `ValidationError: The Express 'trust proxy' setting is true... code: 'ERR_ERL_PERMISSIVE_TRUST_PROXY'`.
- **Causa:** O Express configurado com `app.set('trust proxy', true)` é rejeitado por padrão pelo `express-rate-limit`.
- **Solução:** Usar `app.set('trust proxy', 1)` e adicionar `validate: { trustProxy: false }` nas opções do `rateLimit()`.

### Caso 4: Proxy Interno do Hub Frontend para o Backend
- **Sintoma:** Painel do Hub abre, mas todos os cards e gráficos mostram 502 Bad Gateway.
- **Causa:** O `server.js` tentava chamar o backend através de rota pública externa que não existia ou estava inacessível.
- **Solução:** Implementar fallback automático com `tasks.hub_hub-backend:8000` ou `http://hub_hub-backend:8000` via rede interna do Docker.

---

## 🔄 7. Regra para Atualização Desta Skill

Sempre que você, como agente, resolver um novo problema de infraestrutura, siga este fluxo:
1. Resolva o problema no servidor.
2. Adicione uma nova entrada na seção **6. Catálogo de Erros e Soluções Conhecidas** deste arquivo com: Sintoma, Causa e Solução.
3. Adicione o resumo no arquivo `docs/memory.md`.
4. Faça commit e push das atualizações para o repositório `Usefull_Skills`.
