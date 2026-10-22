#!/usr/bin/env python3
"""
Script de Auditoria e Diagnóstico Rápido da Infraestrutura (Easypanel & Traefik)
Executa via SSH no host 72.60.255.170 para inspecionar containers, rotas e saúde dos serviços.
"""

import os
import sys
from dotenv import load_dotenv

# Tenta carregar .env de múltiplos caminhos conhecidos
for env_path in [
    os.path.join(os.getcwd(), ".env"),
    os.path.join(os.path.dirname(__file__), "../../../.env"),
    "/home/ryanf/Downloads/mind-all/.env"
]:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        break

try:
    import paramiko
except ImportError:
    print("[ERRO] Biblioteca paramiko não encontrada. Instale com: pip install paramiko")
    sys.exit(1)

HOST = os.getenv("Host", "72.60.255.170").strip()
USER = os.getenv("User", "root").strip()
PASSWORD = os.getenv("Password", ",X7xfmWh6dj1x16.(zre").strip()

def run_remote_diagnostics():
    print(f"=== Conectando via SSH a {USER}@{HOST} ===")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(HOST, username=USER, password=PASSWORD, timeout=10)
    except Exception as e:
        print(f"[FALHA DE CONEXÃO SSH]: {e}")
        sys.exit(1)

    def exec_cmd(title, cmd):
        print(f"\n--- {title} ---")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        if out:
            print(out)
        if err:
            print(f"[STDERR]: {err}")
        return out

    # 1. Serviços e Containers
    exec_cmd("1. Serviços do Docker Swarm", "docker service ls")
    exec_cmd("2. Containers Ativos do Hub e Traefik", "docker ps --filter name=hub --filter name=traefik --format 'table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}'")

    # 2. Teste de Roteamento Interno pelo Traefik
    test_cmd = """
TRAEFIK_CID=$(docker ps -q --filter name=traefik)
if [ -n "$TRAEFIK_CID" ]; then
    echo ">> Testando tasks.hub_github:3000/health a partir do Traefik:"
    docker exec $TRAEFIK_CID wget -T 3 -qO- http://tasks.hub_github:3000/health || echo "FALHA no tasks.hub_github"
    
    echo -e "\n>> Testando tasks.hub_hub-backend:8000/health a partir do Traefik:"
    docker exec $TRAEFIK_CID wget -T 3 -qO- http://tasks.hub_hub-backend:8000/health || echo "FALHA no tasks.hub_hub-backend"
else
    echo "Container do Traefik não encontrado!"
fi
"""
    exec_cmd("3. Teste de Conectividade do Traefik via tasks.*", test_cmd)

    # 3. Últimos Logs de Erro do Traefik (502)
    exec_cmd("4. Requisições Recentes 502 no Traefik", "docker logs --tail 200 $(docker ps -q --filter name=traefik) 2>&1 | grep ' 502 ' | tail -n 10 || echo 'Nenhum 502 recente nos logs do Traefik'")

    ssh.close()
    print("\n=== Diagnóstico Concluído com Sucesso ===")

if __name__ == "__main__":
    run_remote_diagnostics()
