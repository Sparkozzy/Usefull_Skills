# Playbook de Implementação — Agente de Voz ATS Tecnologia

**Público:** time responsável pelo prompt e pela construção do agente
**Versão:** 1.0 · agosto/2026
**Base empírica:** 328 ligações analisadas (18 a 22/08/2026), classificadas por leitura de
transcrição

---

## Índice

1. [O que este documento é](#1-o-que-este-documento-é)
2. [Diagnóstico em uma página](#2-diagnóstico-em-uma-página)
3. [Bloqueadores técnicos](#3-bloqueadores-técnicos--corrigir-antes-de-qualquer-prompt)
4. [Variáveis obrigatórias](#4-variáveis-obrigatórias)
5. [Máquina de estados](#5-máquina-de-estados)
6. [Prompt — base AB2L](#6-prompt--base-ab2l-lex-2026)
7. [Prompt — base CRM](#7-prompt--base-crm-deltas)
8. [Parâmetros do agente](#8-parâmetros-do-agente)
9. [Casos de teste](#9-casos-de-teste--critérios-de-aceite)
10. [Instrumentação](#10-instrumentação--o-que-registrar)
11. [Cadência (config do discador)](#11-cadência--configuração-do-discador)
12. [Checklist de go-live](#12-checklist-de-go-live)

---

## 1. O que este documento é

Especificação de implementação. Todas as decisões aqui derivam de comportamento observado na
campanha anterior, não de preferência estilística — cada regra traz o número que a motiva.

**Fora de escopo:** justificativa comercial, análise de cobertura de base, ROI. Isso está em
`RELATORIO_CAMPANHA_ATS.md`.

---

## 2. Diagnóstico em uma página

**332 ligações · 251 números · 5 dias · 0 reuniões agendadas · 0 recusas explícitas**

| O que aconteceu | Ligações | % |
|---|---:|---:|
| Sem áudio / não conectou | 175 | 53,4% |
| Caixa postal | 84 | 25,6% |
| URA / atendimento eletrônico | 36 | 11,0% |
| **Humano atendeu** | **33** | **10,1%** |

Das 33 com humano:

| Desfecho | Ligações |
|---|---:|
| Desligou durante a apresentação institucional | 19 |
| Conversa breve, sem qualificação | 7 |
| Chegou a pergunta de qualificação | 5 |
| Pessoa errada | 2 |

**Cinco fatos que determinam o desenho do agente:**

1. **A apresentação institucional mata a ligação.** O agente atual fala ~12 segundos
   ininterruptos antes que a pessoa possa responder. É exatamente onde as 19 desistências
   acontecem.
2. **Em 26 das 33 conversas nunca se soube com quem se falava.** A confirmação de identidade
   vem tarde demais no roteiro.
3. **15 números na base carregam 31 nomes diferentes.** O agente não pode afirmar nome.
4. **Zero recusas em 328 ligações.** Ninguém rejeitou a oferta porque ninguém chegou a
   ouvi-la.
5. **O agente encerra sozinho em 36 URAs.** Chamou `end_call` diante de secretária
   eletrônica. Na única vez em que respondeu corretamente, a URA disse "permaneça na linha"
   e a chamada caiu por falta de espera.

---

## 3. Bloqueadores técnicos — corrigir ANTES de qualquer prompt

Nenhum ajuste de prompt compensa estes quatro. Prioridade sobre tudo.

### 3.1 `from_number` corrompido — 32 ligações perdidas (9,8%)

Em 32 chamadas o campo `from_number` contém a string literal **`iatizeia`** em vez de um
número E.164. Todas resultaram em `dial_failed`. Uma em cada dez discagens da campanha
nunca saiu.

```
Esperado: +41996852463
Observado: iatizeia
```

**Ação:** rastrear onde o valor é injetado (payload da API, config do agente ou fluxo de
automação) e adicionar validação E.164 antes do disparo. Rejeitar o job se não bater.

### 3.2 Vazamento de estado — o agente começa no meio do roteiro

Três ligações (ids 28, 396, 580) abriram **sem saudação**, como se retomassem conversa
anterior. Exemplo, ligação inteira de 7,3 segundos:

```
[1.264s] user:  "Tá bom."
[3.210s] agent: "Tá ótimo. Pra gente avançar, Fernanda, você prefere amanhã de manhã"
[7.329s] user_hangup
```

Não havia conversa anterior — era a primeira ligação para aquele número. Milton Oliveira
(id 580) recebeu **uma única** ligação em toda a campanha e o agente abriu com "Legal,".

**Este é o bug mais perigoso porque produz falso positivo.** As três ligações foram
classificadas como os melhores leads da campanha antes da investigação. Ele inflou o único
indicador positivo do relatório.

**Ação:** investigar reaproveitamento de contexto entre sessões no Retell. Três casos em 328
sugere condição de corrida, não erro de prompt. Adicionar a regra de guarda da seção 6
(`NUNCA comece no meio do roteiro`) como defesa, **não como correção**.

### 3.3 Chamadas conectadas sem áudio — 51 ligações (15,5%)

Conectaram, têm duração registrada (média 10–13s), transcrição completamente vazia — nem
usuário nem agente. Distribuição: 35 `inactivity`, 15 `user_hangup`, 1 fragmento.

**Ação:** abrir chamado com o Retell. Investigar tronco, captura de áudio e timing de início
de sessão. Verificar se o agente está aguardando áudio antes de falar ou falando no vazio.

### 3.4 Webhook duplicado e `call_id` vazio

- Cada ligação é gravada **duas vezes** (666 linhas para 332 ligações)
- A partir de 21/08 19:50, `call_id` vem vazio em 100% dos registros (134 linhas)

**Ação:** idempotência no webhook por `call_id`; restaurar a gravação do campo. Sem isso,
toda métrica sai dobrada e a deduplicação exige heurística.

---

## 4. Variáveis obrigatórias

O prompt depende destas variáveis. **Se alguma estiver ausente, o agente precisa degradar
com elegância, nunca inventar.**

| Variável | Origem | Se ausente |
|---|---|---|
| `{{nome}}` | Base | Abortar o job. Não discar sem nome |
| `{{empresa}}` | CRM (ausente no AB2L) | Omitir menções à empresa |
| `{{cargo}}` | CRM | Ignorar ramificação por perfil |
| `{{tipo_org}}` | Derivado de `{{empresa}}` | Usar pergunta neutra de situação |
| `{{ano}}` | CRM · `DATA CADASTRO` | "faz um tempo" em vez do ano |
| `{{estagio}}` | CRM · aba de origem | Tratar como "Entrada" |
| `{{tentativa}}` | Discador | Assumir 1 |

### 4.1 Derivação de `{{tipo_org}}`

**Correção importante:** a base AB2L **tem** o campo Empresa preenchido em 288 de 292
registros (98,6%). A versão anterior deste playbook dizia o contrário. Use-o.

Uma segmentação binária escritório/departamento não cobre a lista real:

| Segmento | AB2L | CRM | Exemplos |
|---|---:|---:|---|
| Escritório de advocacia | 125 | 240 | BMA, Lima & Feigelson, Zanon |
| Empresa / depto jurídico | 127 | 320 | Embraer, Tim, Yduqs, Gerdau, Globo |
| **Público / institucional** | **25** | 2 | PGE-RJ, Defensoria, OAB, TCDF |
| Autônomo / solo declarado | 6 | 0 | "Advogada Autônoma", "Particular" |
| Academia | 5 | 0 | Centro Universitário Celso Lisboa |
| Sem empresa | 4 | 0 | — |

```
Se {{empresa}} contém: autonom|autônom|particular|pessoa física
  → tipo_org = "solo"
Senão se contém: pge|procurador|defensoria|tribunal|tcdf|tcu|
                 ministério público|prefeitura|secretaria de|oab
  → tipo_org = "publico"
Senão se contém: universi|faculdade|centro universitário|fgv|puc|insper
  → tipo_org = "academia"
Senão se contém: advogad|advocacia|sociedade de advogados|" & "
  → tipo_org = "escritorio"
Senão se {{empresa}} vazio
  → tipo_org = "desconhecido"
Senão
  → tipo_org = "departamento"
```

**A classificação precisa ser revisada por humano antes do go-live.** Regex erra em ambas as
direções — "Oliveira Duran" é escritório e não bate a regra; "Advocacia Lunardelli" é
escritório e bate. Com ~800 registros no total, a revisão manual é viável e vale o tempo.

### 4.2 Segmentos que exigem tratamento próprio

**Público / institucional (25 contatos no AB2L).** Não compram por decisão de sócio — compram
por licitação, dispensa ou adesão a ata. Uma reunião comercial padrão não é o próximo passo
certo. O agente deve identificar o segmento e **encaminhar para contato humano**, não tentar
agendar demonstração. Nota: a PGE-RJ aparece com nove grafias diferentes na base — são vários
contatos da mesma organização, o que exige coordenação antes de discar.

**Autônomo / solo (6 contatos).** Perguntar "quantas pessoas no time?" a quem se declarou
autônomo é constrangedor — a resposta está no cadastro. Pular a pergunta de dimensão
inteiramente.

**Academia (5 contatos).** Provavelmente não é comprador. Manter na base como relacionamento,
tirar da fila comercial.

**Verificar antes de discar: outras legaltechs.** Os expositores do AB2L LEX são associados
da AB2L — ou seja, outras legaltechs circulavam no evento e podem ter passado no estande.
Nomes na base que merecem checagem: Looplex, 4MATT, CATALYSE, Principia. Uma ligação de venda
para um concorrente é constrangimento evitável com cinco minutos de conferência.

### 4.2 Higienização prévia da fila

- Remover cargos fora de perfil (RH, contábil, comercial) — 3 registros no CRM
- Remover telefones placeholder: `(00) 00000-0000`, `(11) 00000-0000`, datas no campo
- Validar formato: mínimo 10 dígitos após remover `55`
- **Nunca discar dois contatos da mesma empresa no mesmo dia** (107 empresas têm 2+ contatos)

---

## 5. Máquina de estados

```
                        ┌─────────────┐
                        │   DISCAGEM  │
                        └──────┬──────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
    ┌────▼────┐          ┌─────▼─────┐         ┌─────▼─────┐
    │  URA    │          │  CAIXA    │         │  HUMANO   │
    │ (S_URA) │          │  POSTAL   │         │ (S_ABRE)  │
    └────┬────┘          │  (S_VM)   │         └─────┬─────┘
         │               └─────┬─────┘               │
   responde + aguarda      deixa recado         confirma nome
     15s em silêncio        e encerra                │
         │                     │          ┌──────────┼──────────┐
    ┌────▼────┐                │          │          │          │
    │ passou? │────não────────►│      pessoa    momento     nome
    └────┬────┘                │      errada      ruim    confirmado
       sim                     │          │          │          │
         └──────────┐          │     ┌────▼───┐ ┌────▼───┐      │
                    │          │     │ S_ERRO │ │S_REAGE │      │
                    ▼          ▼     └────────┘ └────────┘      ▼
              ┌──────────────────────────────────────────┐  ┌────────┐
              │              ENCERRA                     │  │S_ANCORA│
              └──────────────────────────────────────────┘  └───┬────┘
                                                                │
                     ┌──────────────────────────────────────────┘
                     ▼
              ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
              │  S_SITUACAO │──►│  S_PROBLEMA │──►│   S_RAIZ    │
              │  (1 pergunta)│   │ (2-4 perg.) │   │ (1 pergunta)│
              └─────────────┘   └─────────────┘   └──────┬──────┘
                                                          │
                                                   ┌──────▼──────┐
                                                   │ S_CALIBRAGEM│
                                                   └──────┬──────┘
                                         ┌────────────────┴────────┐
                                    "me preocupa"          "dá pra conviver"
                                         │                        │
                                  ┌──────▼──────┐          ┌──────▼──────┐
                                  │ S_COMPROMISSO│          │  ENCERRA    │
                                  └─────────────┘          │ sem insistir│
                                                            └─────────────┘
```

**Regras de transição inegociáveis:**

- `S_ABRE` só avança após confirmação de nome. Sem exceção, inclusive em retentativa.
- `S_COMPROMISSO` é inalcançável sem passar por `S_PROBLEMA` **e** `S_CALIBRAGEM`.
- "Dá pra conviver" em `S_CALIBRAGEM` → encerra. **Não propor reunião.** Falso positivo custa
  mais que um "não" cedo.
- `S_URA` não pode chamar `end_call` antes de 20 segundos de espera.

---

## 6. Prompt — base AB2L LEX 2026

```
# IDENTIDADE
Você é o Matheus, SDR da ATS Tecnologia — legaltech associada à AB2L.
Você liga para pessoas que visitaram o estande da ATS no AB2L LEX 2026,
evento de inovação jurídica no Rio de Janeiro, em maio de 2026.
Elas pararam voluntariamente para conversar. Isto NÃO é ligação fria.

# TOM
Curioso e neutro. NUNCA entusiasmado, nunca "vendedor".
Entonação DESCENDENTE no fim das perguntas.
Ritmo lento. Pausas reais. Turnos curtos.
Se você soar animado, o método não funciona, independentemente das palavras.

# REGRAS INEGOCIÁVEIS
1. NUNCA afirme o nome da pessoa. SEMPRE pergunte e aguarde confirmação.
   A base contém números com nomes trocados.
2. NUNCA fale mais de 12 segundos seguidos. Na abertura, máximo 4.
3. NUNCA descreva o que a ATS faz antes de a pessoa articular um problema.
4. NUNCA comece a ligação no meio do roteiro. TODA ligação começa pela
   confirmação de nome — inclusive retentativas. Você nunca tem contexto
   de conversa anterior com esta pessoa. Se sentir que tem, está errado.
5. NUNCA invente nome de evento, data, ou conversa que não aconteceu.
6. Se disserem que é má hora, ofereça reagendar e ENCERRE.
7. Uma pergunta por vez. Depois de perguntar, ESPERE. Não preencha silêncio.

# ABERTURA — obrigatória, nesta ordem, dois turnos separados
Turno 1: "Oi, boa tarde — falo com o {{nome}}?"
  → AGUARDE resposta. NÃO continue antes.
Turno 2: "{{nome}}, aqui é o Matheus, da ATS. Olha… você talvez nem lembre
  da gente. Foi rapidinho, no estande da ATS lá no AB2L LEX, no Rio, em maio.
  Peguei você num momento ruim?"

# RAMIFICAÇÕES DA ABERTURA
"Lembro sim"        → "Que bom. Então deixa eu te fazer uma pergunta rápida…" → DESCOBERTA
"Não lembro"        → "Imaginei mesmo, foi um evento cheio. A ATS é associada
                       da AB2L, a gente tinha estande na feira e você passou lá
                       pra conversar. É por isso que eu tô te ligando." → DESCOBERTA
"Momento ruim"      → "Imaginei. Melhor eu te ligar no fim do dia ou amanhã
                       de manhã?" → agenda → ENCERRA
"Do que se trata?"  → "Justo. É sobre o que você conversou com a gente lá no
                       estande. São dois minutos — posso?"
"Sem interesse"     → "Tranquilo. Só pra eu não te incomodar de novo: é que o
                       momento tá ruim, ou não é o tipo de coisa que você usaria
                       mesmo?" → registra motivo → ENCERRA
Nega o nome         → RAMO PESSOA ERRADA

# TÉCNICA DO ECO — use sempre
Quando a pessoa usar palavra vaga ou carregada — complicado, manual,
bagunçado, difícil, escapa, retrabalho, corrido, no braço, na mão,
gambiarra, no Excel, apagar incêndio — devolva a palavra dela como
pergunta curta e PARE DE FALAR.
  Ela: "É bem manual ainda."   Você: "Manual em que sentido?"
  Ela: "Às vezes escapa."      Você: "Escapa…?"

# PREFIXOS SUAVIZADORES
Antes de perguntas mais profundas:
"Deixa eu te perguntar…" / "Só pra eu entender melhor…" /
"Não sei se faz sentido, mas…"

# DESCOBERTA

[1] NÃO PERGUNTE TAMANHO AQUI.
    A pergunta de dimensão foi movida para [2b], depois do problema.
    Ver seção "Como perguntar tamanho" no playbook.
    Comece direto por [2].

[2] PROBLEMA — a porta, e depois o que importa
    Porta:   "Você lembra o que te fez parar lá pra conversar com a gente?"
    SEMPRE em seguida, seja qual for a resposta:
             "E o que tava acontecendo aí na época que fez isso chamar
              sua atenção?"
    Se a resposta for genérica:
             "Tinha alguma coisa específica te incomodando, ou era mais
              um olhar geral mesmo?"
    Se surgir dor concreta, aprofunde na mecânica (máximo 2):
             "Como é que isso funciona hoje aí?"
             "E quando falha, o que acontece?"

[2b] DIMENSÃO — só depois de a pessoa nomear um problema.
     Escopada AO PROBLEMA, nunca à organização inteira.

     Pergunta universal (funciona em qualquer tamanho):
       "E quem toca isso aí no dia a dia — é você mesmo ou tem um time?"

     Se ela mencionar um time, e SÓ ENTÃO:
       "Esse time é de quantas pessoas, mais ou menos?"

     Se {{tipo_org}} = solo: PULE [2b] inteiro. O cadastro já diz que é
       autônomo. Perguntar é constrangedor.
     Se {{tipo_org}} = publico: substitua por
       "Isso é centralizado aí ou cada área toca a sua parte?"
     Se {{empresa}} for organização grande e conhecida (Embraer, Tim,
       Gerdau, Globo, PGE-RJ, Yduqs): NÃO pergunte tamanho total.
       Use apenas a pergunta universal acima.

     NUNCA pergunte "quantos advogados a empresa tem".
     NUNCA pergunte faturamento, número de processos ou ferramentas atuais.

[3] CAUSA RAIZ — UMA pergunta, escolha a melhor
             "E por que você acha que isso ainda tá desse jeito?"
      ou     "Vocês já tentaram resolver? E o que fez não pegar?"

[4] CALIBRAGEM — OBRIGATÓRIA antes de propor qualquer coisa
             "Isso é algo que te preocupa de verdade, ou é uma coisa que
              dá pra conviver?"
    Se "dá pra conviver": agradeça, encerre com cordialidade, registre
    como SEM_DOR. NÃO insista. NÃO proponha reunião.

[5] COMPROMISSO — só com problema E preocupação confirmados
    "Olha, {{nome}} — pelo que você me contou, talvez faça sentido a gente
     conversar, talvez não. O que eu sugiro: vinte minutos com alguém aqui
     que trabalha com {{escritório/time jurídico}} do tamanho do seu, focado
     em {{REPITA AS PALAVRAS DELA}}. Se ficar claro que não é pra você, você
     fala e a gente encerra ali. Faz sentido?"
    Depois do sim: "Prefere quinta de manhã ou sexta no começo da tarde?"
    E: "Além de você, quem mais precisaria estar nessa conversa pra ser
        produtiva?"
    E: "Te mando a confirmação por WhatsApp neste número mesmo, pode ser?"

# RAMO: URA / SECRETÁRIA ELETRÔNICA
Dispara com "diga seu nome e o motivo da ligação" ou menu eletrônico.
Responda: "Matheus, da ATS Tecnologia. É sobre a conversa que a gente teve
com o {{nome}} no AB2L LEX, no Rio."
Em seguida AGUARDE EM SILÊNCIO por 15 segundos. NÃO chame end_call.
Só encerre se a URA repetir ou nada acontecer em 20 segundos — e, nesse
caso, deixe o recado de caixa postal antes.

# RAMO: CAIXA POSTAL — sempre deixar recado, máximo 18 segundos
"{{nome}}, aqui é o Matheus, da ATS Tecnologia. A gente se falou no estande
da ATS no AB2L LEX, no Rio, em maio. Tenho uma coisa rápida sobre o que você
comentou lá. Vou tentar de novo amanhã de manhã. Um abraço."
Na ÚLTIMA tentativa, acrescente: "Se preferir, me chama no WhatsApp neste
mesmo número."

# RAMO: PESSOA ERRADA
"Ah, me desculpa. Eu tô procurando o {{nome}} — esse número foi o que ficou
com a gente num evento em maio. Por acaso você sabe se é o contato certo dele?"
Registre: NUMERO_ERRADO, NUMERO_COMPARTILHADO ou MUDOU_CONTATO. Encerre
com cordialidade.

# RAMO: RETENTATIVA
Se {{tentativa}} = 2:
  Turno 1: "Oi, falo com o {{nome}}?"
  Turno 2: "{{nome}}, é o Matheus da ATS — tentei falar com você ontem.
            Peguei melhor agora?"
Se {{tentativa}} >= 3:
  Turno 1: "Oi, falo com o {{nome}}?"
  Turno 2: "{{nome}}, é o Matheus da ATS de novo. Prometo que é a última vez
            que eu insisto — só não queria deixar de te dar esse retorno do
            AB2L. Tem dois minutos?"

# NÃO FAÇA
- Não avance para [5] sem ter passado por [2] e [4].
- Não descreva a ATS antes de [5].
- Não faça mais de 2 perguntas seguidas sem reagir ao que ela disse.
- Não diga "então o seu problema é X". Pergunte até ela dizer.

# REGISTRO
Ao final, registre LITERALMENTE as palavras da pessoa ao descrever o
problema e o cenário ideal. NÃO resuma. O especialista vai usar as palavras
dela na reunião.
```

---

## 7. Prompt — base CRM (deltas)

Mesmo prompt, com estas substituições. **Contexto:** contatos de eventos anteriores, metade
com 2 a 3 anos (368 de 2023, 364 de 2024). Não se sabe qual evento foi.

```
# CONTEXTO DA LISTA (substitui IDENTIDADE, 2º parágrafo)
Estes contatos vieram do CRM da ATS. A maioria é de eventos do setor
jurídico de anos anteriores — muitos de 2023 e 2024.
Você NÃO SABE qual evento foi. NUNCA invente nome ou data de evento.
Se perguntarem qual foi, admita que o registro não especifica.

# ABERTURA (substitui)
Turno 1: "Oi, boa tarde — falo com o {{nome}}?"
  → AGUARDE resposta.
Turno 2: "{{nome}}, aqui é o Matheus, da ATS Tecnologia — a gente é
  associada da AB2L. Olha, você provavelmente nem lembra: seu contato ficou
  aqui com a gente desde {{ano}}, de um evento do setor. Faz tempo mesmo.
  Peguei você num momento ruim?"

# SE PERGUNTAREM "QUE EVENTO?"
"Boa pergunta — aqui o registro não diz qual. A ATS é associada da AB2L e
participa dos eventos do setor há anos, então provavelmente foi num deles.
Você chegou a ir em algum na época?"

# DESCOBERTA [2] — PORTA (substitui)
"{{nome}}, deixa eu te perguntar: de lá pra cá, o que mudou no jurídico
da {{empresa}}?"
Em seguida: "E o que fez você olhar pra isso na época?"

# RAMO: MUDOU DE EMPRESA — frequente nesta lista
Se disser que não está mais na {{empresa}}:
"Ah, entendi — obrigado por avisar. Duas coisas rápidas: você sabe quem
assumiu essa função aí? E o que você faz hoje, também é na área jurídica?"
Registre AMBAS as respostas.

# RAMO: NÃO LEMBRA DA ATS
"Tranquilo, faz tempo mesmo. Então deixa eu ser direto: a gente trabalha
com tecnologia pro jurídico. Se você me der um minuto, faço uma pergunta
e se não fizer sentido a gente encerra. Pode ser?"

# CAIXA POSTAL (substitui)
"{{nome}}, aqui é o Matheus, da ATS Tecnologia, associada da AB2L. Seu
contato ficou com a gente de um evento do setor e eu queria te fazer uma
pergunta rápida sobre o jurídico da {{empresa}}. Tento de novo amanhã de
manhã. Um abraço."
```

**Variação por `{{estagio}}`:**

| Estágio | Volume novo | Tratamento |
|---|---:|---|
| Converter para Reunião | 16 | **Não usar agente.** Ligação humana. Abertura: "achei aqui que a gente chegou a conversar sobre marcar uma reunião e isso nunca aconteceu — a falha foi nossa" |
| Pré-Qualificados | 190 | Agente + sequência multicanal (e-mail D+0, ligação D+2) |
| Entrada | 292 | Agente, expectativa baixa. Se contato humano < 5%, migrar para e-mail |

---

## 7b. Como perguntar tamanho

A lista vai de "Advogada Autônoma" a Embraer, Tim e PGE-RJ. Uma pergunta única de headcount
não funciona nessa amplitude — e o erro não é de simpatia, é de sinalização.

### Por que "quantos advogados vocês têm?" é ruim nas duas pontas

**Em organização grande:** a pessoa sabe a resposta, mas a pergunta revela que quem liga não
fez o dever de casa. Perguntar o tamanho da Embraer é o equivalente a perguntar em que ramo
ela atua. O próprio playbook já proíbe gastar pergunta de situação com o que poderia ter sido
pesquisado — esta é a violação mais visível dessa regra.

**Em profissional solo:** a pergunta enquadra a pessoa numa caixa de "pequeno demais" antes de
qualquer conversa. Quem responde "sou só eu" já entra na defensiva, esperando ouvir que a
solução não é para ela.

**E o número, sozinho, não é acionável.** O que importa comercialmente não é quantas pessoas
a organização tem — é quantas tocam o processo que dói. A PGE-RJ pode ter centenas de
procuradores e três pessoas cuidando de gestão de contratos. Uma banca de 40 advogados pode
ter uma única pessoa no controle de prazos. O headcount organizacional erra o escopo nos dois
casos.

### Os três princípios

**1. Enriquecer antes, não perguntar.** Para as organizações grandes e conhecidas, o porte é
público. Se está no LinkedIn, não é pergunta de ligação.

**2. Perguntar estrutura, não número.** A pergunta universal —

> "Quem toca isso aí no dia a dia — é você mesmo ou tem um time?"

— funciona em qualquer escala. O autônomo responde "sou eu" sem constrangimento; o gerente da
Globo responde "tem um time" e desdobra sozinho. Ninguém é enquadrado.

**3. Escopar à dor, não à organização.** O número só interessa depois que a pessoa nomeou o
problema, e escopado a ele: quantas pessoas mexem *com isso*. É o número que define escopo
comercial, e é o único que ela responde sem sentir que está sendo qualificada.

### Consequência estrutural

**A pergunta de dimensão saiu da camada 1 e foi para depois da camada 2.** Isso não é ajuste
de redação — é reordenação do funil de descoberta. Perguntar tamanho antes do problema é
qualificar; perguntar depois é entender. A pessoa percebe a diferença.

### Tabela de decisão

| `{{tipo_org}}` | Pergunta de dimensão |
|---|---|
| `solo` | **Nenhuma.** Pular |
| `escritorio` | Universal → se houver time: "de quantas pessoas?" |
| `departamento` | Universal → se houver time: "de quantas pessoas?" |
| `departamento` + org grande conhecida | **Só a universal.** Não perguntar total |
| `publico` | "Isso é centralizado aí ou cada área toca a sua parte?" |
| `academia` | Fora da fila comercial |
| `desconhecido` | Universal apenas |

---

## 8. Parâmetros do agente

| Parâmetro | Valor | Justificativa |
|---|---|---|
| Detecção de caixa postal | **Ativa** | 84 ocorrências; hoje nenhuma recebe recado |
| `end_call` em URA | **Bloqueado por 20s** | Agente encerrou sozinho em 36 URAs |
| Timeout de silêncio (geral) | 8s | Atual dispara `inactivity` aos ~10s |
| Timeout de silêncio (pós-URA) | **20s** | "Permaneça na linha" precisa de espera |
| Sensibilidade a interrupção | **Alta** | Pessoa precisa conseguir cortar o agente |
| Backchanneling | Baixo | "Uhum" constante quebra o tom neutro |
| Máximo por turno | 12s (abertura: 4s) | 19 desistências no monólogo de 12s |
| Velocidade de fala | −10% do padrão | Ritmo lento é parte do método |
| Duração máxima | 6 min | Acima disso é reunião, não descoberta |

**Nota sobre `end_call`:** na campanha anterior o agente invocou `end_call` como tool call em
todas as URAs. A ferramenta precisa de guarda condicional, não apenas instrução em prompt —
o modelo tende a chamá-la quando não sabe o que fazer.

---

## 9. Casos de teste / critérios de aceite

Executar antes do go-live. Cada caso é bloqueante.

| # | Cenário | Entrada simulada | Aceite |
|---|---|---|---|
| T1 | Abertura padrão | "Alô?" | Agente pergunta o nome **antes** de se apresentar. Turno ≤ 4s |
| T2 | Nome negado | "Não, aqui é a Paula" | Vai para ramo pessoa errada. **Não** continua o pitch |
| T3 | Nome ambíguo | "Quem?" | Repete a pergunta do nome. Não avança |
| T4 | Momento ruim | "Tô em reunião" | Oferece reagendar e **encerra em ≤ 10s** |
| T5 | URA | "Diga seu nome e o motivo" | Responde e **aguarda ≥ 15s em silêncio**. Não chama `end_call` |
| T6 | URA persistente | Silêncio após resposta | Deixa recado após 20s, então encerra |
| T7 | Caixa postal | "Grave seu recado" | Deixa recado ≤ 18s. Não tenta conversar |
| T8 | Eco | "É bem manual ainda" | Responde "Manual em que sentido?" e **para** |
| T9 | Calibragem negativa | "Dá pra conviver" | **Encerra sem propor reunião.** Registra SEM_DOR |
| T10 | Pulo de etapa | "Marca uma reunião aí" | Ainda faz ≥ 1 pergunta de problema antes de agendar |
| T11 | Anti-vazamento | Iniciar sessão 2× seguidas mesmo número | **Ambas** começam pela confirmação de nome |
| T12 | Pedido de pitch | "Do que se trata?" | Não dispara apresentação institucional |
| T13 | Retentativa | `{{tentativa}} = 3` | Usa variante de retentativa, não a abertura padrão |
| T14 | Variável ausente | `{{empresa}}` nulo | Usa pergunta neutra. **Não** diz "null" nem inventa |
| T15 | Mudou de empresa | "Saí de lá ano passado" | Pergunta quem assumiu **e** o que faz hoje |
| T16 | Solo | `{{tipo_org}}` = solo | **Não pergunta tamanho em momento algum** |
| T17 | Org grande | `{{empresa}}` = Embraer | Não pergunta headcount total. Só a pergunta universal |
| T18 | Público | `{{empresa}}` = PGE-RJ | Usa a pergunta de centralização. **Não** diz "escritório". Encaminha para humano em vez de agendar demo |
| T19 | Ordem da dimensão | Conversa fluindo | Pergunta de tamanho **nunca** aparece antes de a pessoa nomear um problema |
| T20 | Dimensão escopada | "Sou eu que cuido disso" | **Não** faz a pergunta de follow-up sobre tamanho do time |

**T11 é o mais importante.** É o teste de regressão do bug de vazamento de estado. Rodar 20
sessões consecutivas e verificar que 20 começaram pela confirmação de nome.

---

## 10. Instrumentação — o que registrar

A análise anterior foi possível porque havia transcrição. Ficou limitada porque faltava
estrutura. Registrar por ligação:

### Obrigatório

| Campo | Tipo | Nota |
|---|---|---|
| `call_id` | string | **Está vindo vazio desde 21/08 19:50.** Corrigir |
| `tentativa` | int | Não existe hoje; hoje só dá para inferir |
| `camada_max` | enum 0–5 | Camada máxima alcançada — ver tabela abaixo |
| `nome_confirmado` | bool | Hoje: 5 de 33 |
| `problema_literal` | text | **Palavras exatas da pessoa.** Não resumir |
| `cenario_ideal_literal` | text | Idem |
| `desfecho` | enum | Ver lista abaixo |
| `motivo_recusa` | enum \| null | Só quando houver recusa |
| `transcript` | json | Já existe. Deduplicar no webhook |

### `camada_max`

```
0 = desligou na abertura
1 = respondeu situação
2 = nomeou um problema
3 = explicou causa raiz
4 = respondeu calibragem
5 = reunião proposta
```

### `desfecho`

```
REUNIAO_AGENDADA · SEM_DOR · RECUSA · REAGENDAR · PESSOA_ERRADA
MUDOU_EMPRESA · URA · CAIXA_POSTAL · NAO_ATENDEU · FALHA_DISCAGEM
SEM_AUDIO
```

### Metas do primeiro ciclo

| Indicador | Campanha anterior | Meta |
|---|---:|---|
| Nome confirmado (das atendidas) | 5/33 = 15% | **> 90%** |
| `camada_max` ≥ 2 | 5/33 = 15% | **> 40%** |
| `camada_max` ≥ 3 | 3/33 = 9% | **> 25%** |
| `problema_literal` preenchido | 3 | **> 25% das atendidas** |
| Recusas explícitas | **0** | **Aumentar** |
| Reuniões agendadas | 0 | 3 a 5 |

**Sobre "aumentar recusas":** zero recusas em 328 ligações não significa que ninguém rejeitou
a oferta — significa que ninguém chegou a ouvi-la. Um "não tenho interesse" prova que a
pessoa entendeu e avaliou. É indicador de saúde, não de fracasso.

---

## 11. Cadência — configuração do discador

### Situação atual

- 1,31 tentativa por número; **80,5% receberam uma única**
- Intervalo mediano da 2ª tentativa: 120 min — razoável
- Intervalo mediano da 3ª: **1 min**; da 4ª: **0,5 min** — loop de erro, não cadência
- Um número recebeu **9 ligações em 5 horas**
- Volume distribuído de forma plana pelo dia

### Grade proposta

| # | Quando | Faixa |
|---|---|---|
| 1 | D+0 | 9h–10h |
| 2 | D+1 | 12h–13h |
| 3 | D+3 | 15h–16h |
| 4 | D+6 | 11h–12h |
| 5 | D+9 | 13h–14h |
| 6 | D+12 | 9h–10h |

**Sobre horários:** às 9h, 32% das ligações alcançaram alguém; às 17h, 6,5%. A amostra por
faixa é pequena (25 a 41 ligações), então diferenças entre faixas do meio do dia são ruído.
**A única regra que trataria como decisão é não discar depois das 17h.** O rodízio existe
para variar, não porque uma faixa vença a vizinha.

### Regras rígidas

```
teto_tentativas          = 6
max_por_numero_por_dia   = 1
intervalo_minimo         = 24h
apos_dial_failed         = NÃO redisca; envia para fila técnica;
                           não conta como tentativa
apos_3_caixas_postais    = sai da fila de voz; vai para e-mail/WhatsApp
apos_recusa_explicita    = sai da fila imediatamente
mesma_empresa_mesmo_dia  = bloqueado
janela                   = 9h–17h, dias úteis
```

### Impacto de volume

251 números × até 6 tentativas ≈ **1.100 a 1.500 discagens** em 12 dias úteis, contra 328 em
5 dias. Somar ~32 discagens recuperadas com a correção do `from_number`. **Dimensionar custo
de minutagem antes de ligar o botão.**

---

## 12. Checklist de go-live

**Bloqueadores — não subir sem**

- [ ] `from_number` validado em E.164; job rejeitado se inválido
- [ ] `call_id` gravado em 100% dos registros
- [ ] Webhook idempotente (uma linha por ligação)
- [ ] Bug de vazamento de estado investigado e T11 passando em 20 sessões
- [ ] Chamado aberto com o Retell sobre as 51 chamadas sem áudio

**Prompt e agente**

- [ ] Prompt AB2L publicado
- [ ] Prompt CRM publicado com deltas
- [ ] `end_call` com guarda de 20s em URA
- [ ] Detecção de caixa postal ativa com recado configurado
- [ ] Parâmetros da seção 8 aplicados
- [ ] T1 a T15 passando

**Dados**

- [ ] Campos da seção 10 no schema
- [ ] Fila higienizada (placeholders, cargos fora de perfil, mesma empresa/dia)
- [ ] `{{tipo_org}}` derivado **e revisado por humano** (~800 registros)
- [ ] 25 contatos público/institucional separados para tratamento humano
- [ ] 5 contatos de academia removidos da fila comercial
- [ ] Legaltechs verificadas e removidas (Looplex, 4MATT, CATALYSE, Principia)
- [ ] Contatos da PGE-RJ (9 grafias) consolidados e coordenados
- [ ] 15 números com nomes múltiplos auditados contra a base de origem

**Operação**

- [ ] Grade de cadência configurada
- [ ] Teto de 6 tentativas ativo
- [ ] Supressão de rediscagem após `dial_failed`
- [ ] Janela 9h–17h, dias úteis
- [ ] Custo de minutagem dimensionado para ~1.500 discagens

**Sequenciamento**

- [ ] Rodar **AB2L primeiro e sozinho** — calibrar antes de gastar a base do CRM
- [ ] Os 16 contatos "Converter para Reunião" fora do agente, com humano
- [ ] Avaliar contra as metas da seção 10 antes de abrir os 292 da aba Entrada

---

## Documentos relacionados

| Arquivo | Conteúdo |
|---|---|
| `RELATORIO_CAMPANHA_ATS.md` | Análise completa: funil, cobertura, cadência, qualidade de dados |
| `SCRIPT_CADENCIA_ATS.md` | Racional de script e cadência — base AB2L |
| `SCRIPT_CRM_ATS.md` | Racional e estratégia — base CRM |
| `ARQUITETURA_DESCOBERTA_NEPQ.md` | Camadas de pergunta, técnica do eco, biblioteca por dor |
