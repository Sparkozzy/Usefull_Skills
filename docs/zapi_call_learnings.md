# Aprendizados e Integração Z-API Chamadas de Voz (Nativo & SIP)

## 📌 Resumo da Arquitetura

Após análises das APIs nativas da Z-API e validações dos endpoints, a integração do microserviço **`zapi_voice_service`** suporte duas modalidades de chamadas telefônicas no WhatsApp:

1. **Chamadas por Disparo com Mídia Dinâmica (`POST /send-call`)**:
   - Envia sinal de toque para o WhatsApp de destino.
   - Requer obrigatoriamente um link **HTTPS** (`callAudioUrl`) apontando para a voz sintetizada pelo motor OpenAI TTS (`voice_id="nova"`).

2. **Chamadas Conversacionais de Voz em Tempo Real via SIP (`sip.z-api.io`)**:
   - Conecta ao servidor SIP `sip.z-api.io:5060` da Z-API.
   - Utiliza autenticação efêmera via `GET /call-token` (`ek-...`).
   - Recebe e transmite pacotes de voz bidirecionais via `ZapiSipEngine`.

---

## 🔑 Credenciais SIP da Instância Z-API

Endpoint de verificação ativo:
- **`GET https://zapi-voice-service-api.bkpxmb.easypanel.host/sip/info/2`**

Retorno validado:
```json
{
  "status": "success",
  "sip_credentials": {
    "host": "sip.z-api.io",
    "user": "3F5BBCC13F9441E00E5886B9FA2A227D",
    "sip_token": "ek-...",
    "active": true
  }
}
```

---

## 📊 Persistência no PostgreSQL Exclusivo

Toda chamada (encerrada via `BYE` no SIP ou `DISCONNECTED` no Webhook) salva os dados na tabela `voice_calls`:
- `call_id`: UUID único.
- `duration_seconds`: Duração total em segundos.
- `transcript`: Transcrição formatada "User / Agent".
- `call_summary`: Resumo automático gerado por LLM.
- `status`: Status final (`completed`).
