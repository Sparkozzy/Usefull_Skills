import os
import re
import sys
import time
import uuid
import glob
import pandas as pd
import httpx
from datetime import datetime

# Garantir UTF-8 no terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# --- CONFIGURAÇÕES OPERACIONAIS ---
PROMPT_ID = "33"
AGENT_ID = "agent_4f1dba5e5432cd193d324754bf"
API_URL = "https://call-github.bkpxmb.easypanel.host/webhook"
WORKFLOW_NAME = "pre_call_processing"
LISTA_DIR = "ListaATS"
INTERVALO_ENTRE_CHAMADAS_SEG = 3  # Intervalo de segurança para fila assíncrona


def carregar_api_key():
    api_key = os.getenv("WEBHOOK_API_KEY")
    if not api_key and os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("WEBHOOK_API_KEY="):
                    api_key = line.strip().split("=", 1)[1].strip()
                    break
    if not api_key:
        print("[ERRO] WEBHOOK_API_KEY não encontrada no ambiente nem no arquivo .env!")
        sys.exit(1)
    return api_key


def formatar_telefone(numero_raw):
    """
    Higieniza e normaliza telefone para padrão E.164 (+55...)
    """
    if pd.isna(numero_raw):
        return None
    num_str = re.sub(r"\D", "", str(numero_raw))
    if not num_str:
        return None
    
    # Se já tem 55 e DDD (ex: 5547999998888 -> 12 ou 13 dígitos)
    if num_str.startswith("55") and len(num_str) in [12, 13]:
        return f"+{num_str}"
    
    # Se tem 10 ou 11 dígitos (DDD + número)
    if len(num_str) in [10, 11]:
        return f"+55{num_str}"
    
    # Se já vier com código internacional diferente
    if len(num_str) >= 12:
        return f"+{num_str}"

    return None


def encontrar_arquivo_lista():
    arquivos = glob.glob(os.path.join(LISTA_DIR, "*.*"))
    arquivos_validos = [f for f in arquivos if f.endswith((".xlsx", ".xls", ".csv")) and not os.path.basename(f).startswith("~$")]
    if not arquivos_validos:
        return None
    # Pega o arquivo mais recente
    arquivos_validos.sort(key=os.path.getmtime, reverse=True)
    return arquivos_validos[0]


def carregar_leads(caminho_arquivo):
    print(f"[INFO] Lendo lista: {caminho_arquivo}")
    if caminho_arquivo.endswith(".csv"):
        # Tenta ler com delimitador ; ou ,
        try:
            df = pd.read_csv(caminho_arquivo, sep=";", dtype=str)
            if len(df.columns) <= 1:
                df = pd.read_csv(caminho_arquivo, sep=",", dtype=str)
        except Exception:
            df = pd.read_csv(caminho_arquivo, sep=None, engine="python", dtype=str)
    else:
        df = pd.read_excel(caminho_arquivo, dtype=str)

    # Identificar colunas de Telefone e Nome
    col_tel = None
    col_nome = None
    col_empresa = None

    for col in df.columns:
        c_low = col.lower().strip()
        if not col_tel and any(k in c_low for k in ["telefone", "celular", "phone", "numero", "contato", "whatsapp"]):
            col_tel = col
        elif not col_nome and any(k in c_low for k in ["nome", "contato_nome", "responsavel", "lead"]):
            col_nome = col
        elif not col_empresa and any(k in c_low for k in ["escritorio", "escritório", "empresa", "organizacao", "empresa"]):
            col_empresa = col

    if not col_tel:
        raise ValueError(f"Não foi possível identificar a coluna de telefone na planilha. Colunas encontradas: {list(df.columns)}")

    leads = []
    for idx, row in df.iterrows():
        raw_tel = row.get(col_tel)
        tel_formatado = formatar_telefone(raw_tel)
        if not tel_formatado:
            continue
        
        nome = str(row.get(col_nome, "")).strip() if col_nome and not pd.isna(row.get(col_nome)) else ""
        empresa = str(row.get(col_empresa, "")).strip() if col_empresa and not pd.isna(row.get(col_empresa)) else ""
        
        leads.append({
            "linha_original": idx + 2,
            "nome": nome,
            "telefone": tel_formatado,
            "empresa": empresa,
            "dados_extras": {k: str(v) for k, v in row.items() if not pd.isna(v)}
        })

    return leads


def executar_disparos(leads, api_key, simulacao=False):
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }

    total = len(leads)
    sucessos = 0
    falhas = 0

    print(f"\n==========================================")
    print(f"🚀 INICIANDO DISPARO ATS (Prompt: {PROMPT_ID} | Agente: {AGENT_ID})")
    print(f"📊 Total de leads validados: {total}")
    print(f"⚙️ Modo: {'[SIMULAÇÃO / DRY RUN]' if simulacao else '[DISPARO REAL]'}")
    print(f"==========================================\n")

    for i, lead in enumerate(leads, 1):
        contexto_detalhes = []
        if lead['empresa']:
            contexto_detalhes.append(f"Escritório/Empresa: {lead['empresa']}")
        contexto = " | ".join(contexto_detalhes) if contexto_detalhes else "Disparo Lista ATS"

        payload = {
            "workflow_name": WORKFLOW_NAME,
            "execution_id": f"exec_ats_{uuid.uuid4().hex[:10]}",
            "numero": lead["telefone"],
            "nome": lead["nome"],
            "email": "",
            "agent_id": AGENT_ID,
            "Prompt_id": PROMPT_ID,
            "contexto": contexto
        }

        print(f"[{i}/{total}] Destinatário: {lead['nome'] or 'Sem Nome'} ({lead['telefone']})")

        if simulacao:
            print(f"   --> [SIMULADO] Payload preparado com sucesso. Execution ID: {payload['execution_id']}")
            sucessos += 1
            time.sleep(0.1)
            continue

        try:
            with httpx.Client(timeout=30.0) as client:
                res = client.post(API_URL, headers=headers, json=payload)
                if res.status_code == 200:
                    print(f"   ✅ [SUCESSO] Webhook aceito! Status: {res.status_code}")
                    sucessos += 1
                else:
                    print(f"   ❌ [FALHA] Status {res.status_code}: {res.text}")
                    falhas += 1
        except Exception as e:
            print(f"   ⚠️ [EXCEÇÃO] Erro ao conectar no webhook: {e}")
            falhas += 1

        if i < total and not simulacao:
            time.sleep(INTERVALO_ENTRE_CHAMADAS_SEG)

    print(f"\n==========================================")
    print(f"🏁 RESUMO DO DISPARO:")
    print(f"✅ Sucessos: {sucessos}")
    print(f"❌ Falhas: {falhas}")
    print(f"==========================================")


def main():
    api_key = carregar_api_key()
    arquivo = encontrar_arquivo_lista()

    if not arquivo:
        print(f"[ALERTA] Nenhum arquivo Excel (.xlsx, .xls) ou .csv encontrado na pasta '{LISTA_DIR}/'.")
        print(f"👉 Adicione a planilha final na pasta '{LISTA_DIR}/' e execute novamente este script!")
        return

    # Verificar argumentos da linha de comando
    simulacao = "--simular" in sys.argv or "--dry-run" in sys.argv

    try:
        leads = carregar_leads(arquivo)
        if not leads:
            print(f"[AVISO] Nenhum lead com telefone válido encontrado no arquivo {arquivo}.")
            return
        
        print(f"[OK] {len(leads)} leads prontos para disparo.")
        
        if not simulacao and "--executar" not in sys.argv:
            print("\n-------------------------------------------------------------")
            print("🛑 Por segurança, execute com:")
            print("   python disparar_ligacoes_ats.py --simular   (Para validar os leads sem ligar)")
            print("   python disparar_ligacoes_ats.py --executar  (Para efetuar as chamadas reais)")
            print("-------------------------------------------------------------")
            return

        executar_disparos(leads, api_key, simulacao=simulacao)

    except Exception as e:
        print(f"[ERRO CRÍTICO] {e}")


if __name__ == "__main__":
    main()
