---
name: corporate-prompt-generator
description: Gerador e refatorador de prompts corporativos de clientes da MindFlow (prompts armazenados na tabela Prompts do Supabase: WhatsApp, Ligação/Voz, Follow-Up e Instagram) com autoaprendizado estruturado em 4 fases (Teach-To-Learn, Absorção Crítica, Checagem de Regras e Self-Refine). USO RESTRITO: Acione EXCLUSIVAMENTE quando houver intencionalidade explícita de criar ou alterar prompts de atendimento de clientes da base de dados. NUNCA utilizar para prompts de código, agentes internos de engenharia ou sem intencionalidade real.
---

# SKILL — GERADOR DE PROMPTS CORPORATIVOS DE CLIENTES COM AUTOAPRENDIZADO

> ⚠️ **REGRA DE ESCOPO E INTENCIONALIDADE (INEGOCIÁVEL):**
> 1. **Foco Exclusivo em Prompts de Clientes (`Tabela Prompts`):** Esta skill existe **unicamente** para criar do zero ou alterar/refatorar prompts de agentes de clientes da MindFlow (colunas `Prompt_Text`, `"Ligação/txt"`, `prompt_fup` e `"Prompt Insta"` da tabela `Prompts` no Supabase, geridos via PromptOps).
> 2. **Proibição para Prompts de Código:** **NUNCA** confunda nem utilize esta skill para prompts de geração de código, desenvolvimento de software ou instruções internas de sistema.
> 3. **Acionamento Intencional:** **NUNCA** acione este fluxo deliberadamente sem que haja uma demanda real e explícita do usuário para construir ou modificar um prompt de cliente.

---

## BLOCO DE MEMÓRIA ATIVA

Este bloco é o estado vivo da skill. Reside fisicamente em:
- **Arquivo Oficial de Estado:** `.agents/Skills/corporate-prompt-generator/resources/active_memory.xml`
- **Sincronização Científica:** Conectado ao Livro-Razão [`docs/prompt_hypotheses_ledger.md`](../../../docs/prompt_hypotheses_ledger.md).
  - Regras `IMUTAVEL` correspondem a critérios fundacionais e **Teorias Consolidadas (`>= 8 pontos`)**.
  - Regras `MUTAVEL` correspondem a padrões emergentes e **Hipóteses em Teste (`-3 a +7 pontos`)**.
  - `<erros_registrados>` correspondem a incidentes e **Hipóteses Refutadas (`<= -4 pontos`, `❌ X REFUTADA`)**.

Deve ser lido no início e atualizado ao final de cada sessão de geração diretamente em `resources/active_memory.xml` (e entregue ao usuário quando operado em interface externa).

```xml
<memoria_ativa versao="1.0">

  <regras_de_geracao>
    <!-- Regras descobertas ou confirmadas sobre como gerar bons prompts
         para esta empresa. Classificadas por tipo. -->
    <regra tipo="IMUTAVEL" id="R001">
      Todo prompt deve declarar explicitamente persona, contexto,
      formato de output e critério de encerramento.
    </regra>
    <regra tipo="IMUTAVEL" id="R002">
      Estrutura de output sempre em XML ou Markdown conforme padrão
      da empresa. Nunca misturar os dois no mesmo bloco.
    </regra>
    <regra tipo="MUTAVEL" id="R003" ultima_atualizacao="">
      [Adicionar regras mutáveis descobertas em uso aqui]
    </regra>
  </regras_de_geracao>

  <padroes_de_briefing>
    <!-- Padrões recorrentes nos briefings desta empresa. -->
    <padrao id="P001" frequencia="alta">
      [Descrever padrão recorrente observado]
    </padrao>
  </padroes_de_briefing>

  <erros_registrados>
    <!-- Erros cometidos em gerações anteriores. Nunca apagar —
         apenas marcar como resolvido. -->
    <erro id="E001" status="aberto" data="">
      [Descrever o erro, a seção afetada e a causa raiz]
    </erro>
  </erros_registrados>

  <preferencias>
    <!-- Tom, formato, estilo e preferências confirmadas pelo usuário. -->
    <preferencia tipo="tom" confirmada="nao">
      [Ex: direto, técnico, sem rodeios]
    </preferencia>
    <preferencia tipo="markdown" confirmada="nao">
      [Ex: headers H2 para seções, blocos de código para exemplos]
    </preferencia>
    <preferencia tipo="xml" confirmada="nao">
      [Ex: tags em snake_case, atributos para metadados]
    </preferencia>
    <preferencia tipo="cadeias_de_pensamento" confirmada="nao">
      [Ex: CoT explícito sempre visível / interno / opcional]
    </preferencia>
  </preferencias>

  <melhorias_propostas>
    <!-- Melhorias sugeridas pelo usuário ainda não implementadas. -->
    <melhoria id="M001" status="pendente" data="">
      [Descrever a melhoria proposta e o contexto em que surgiu]
    </melhoria>
  </melhorias_propostas>

</memoria_ativa>
```

---

## INSTRUÇÃO DE INICIALIZAÇÃO

Ao iniciar uma sessão intencional de criação ou alteração de prompt de cliente:
1. Leia o arquivo `.agents/Skills/corporate-prompt-generator/resources/active_memory.xml` (ou o bloco `<memoria_ativa>` recebido no contexto) inteiro antes de qualquer outra ação.
2. Carregue as regras como restrições ativas — **imutáveis têm prioridade**.
3. Carregue os erros registrados como alertas a evitar ativamente.
4. Carregue as preferências como padrão de output desta sessão.
5. Registre internamente: `"Estou operando com memória da versão X"`.
6. Se o bloco estiver vazio ou ausente $\rightarrow$ opere com os padrões base desta skill e sinalize ao usuário que nenhuma memória foi carregada.

---

## FASE 0 — ATIVAÇÃO DE CRITÉRIOS (Teach-To-Learn ancorado)

Execute antes de processar o briefing. Não derive critérios do briefing — aplique os critérios abaixo como âncora fixa, complementados pela memória ativa.

### Mapa fixo de critérios desta empresa

- **Elementos inegociáveis em todo prompt gerado:**
  1. Persona declarada com escopo de autoridade
  2. Contexto de uso (quem vai usar, em qual situação e canal da tabela `Prompts`)
  3. Formato de output especificado (XML ou Markdown — nunca ambos no mesmo bloco)
  4. Restrições explícitas (o que o modelo NÃO deve fazer)
  5. Critério de encerramento (quando o modelo considera a tarefa completa)
  6. Cadeia de pensamento declarada (visível, interna ou opcional)

- **Erros clássicos a evitar ativamente:**
  - Colapsar persona e tom em uma única instrução vaga
  - Especificar formato sem exemplificar a estrutura esperada
  - Criar restrições negativas sem alternativa positiva
  - Omitir o público-alvo do prompt
  - Usar CoD de maneira interna e encadeada, possibilitando a combinação desse encadeamento com LATS ou encrustá-lo em outros laços de raciocínio neural — cadeia de pensamento sem influência real no output
  - Misturar XML e Markdown no mesmo bloco de output

- **Tensões a monitorar:**
  - Especificidade vs. reusabilidade (prompt muito específico não escala)
  - Controle do output vs. liberdade criativa do modelo
  - CoD explícito (verboso) vs. CoD interno (compacto)
  - Brevidade da instrução vs. completude da especificação

- **Threshold de qualidade — o prompt está pronto quando:**
  - É autoexplicativo sem o briefing
  - Um modelo sem contexto prévio o executaria corretamente
  - Não contém instrução que contradiz outra instrução
  - O formato de output pode ser validado programaticamente
  - A cadeia de pensamento está conectada ao output, não flutuando

- **Hierarquia de autoridade (árbitro de conflitos):**
  ```text
  Regra IMUTÁVEL da memória ativa
    > Critério fixo desta Fase 0
      > Regra MUTÁVEL da memória ativa
        > Campo do briefing
          > Decisão livre
  ```

Ao final da Fase 0, declare internamente:
```text
MAPA DE CRITÉRIOS ATIVO:
- Versão da memória carregada: [versão ou "nenhuma"]
- Erros da memória que monitorarei: [liste ids]
- Preferências de formato ativas: [liste]
- Tensões esperadas para este briefing: [liste]
```

---

## FASE 1 — ABSORÇÃO CRÍTICA DO BRIEFING

**Não gere o prompt ainda.**
Para cada campo do briefing (ou solicitação de alteração do prompt do cliente), produza:

```xml
<analise_campo>
  <campo>[nome]</campo>
  <valor>[o que foi informado]</valor>
  <interpretacao>[o que isso significa para o prompt]</interpretacao>
  <ambiguidade tipo="sim|nao">[se sim: descreva exatamente]</ambiguidade>
  <conflito_interno tipo="sim|nao">[se sim: campos em tensão]</conflito_interno>
  <conflito_memoria tipo="sim|nao">[se sim: qual regra ou erro da memória ativa]</conflito_memoria>
</analise_campo>
```

Ao final, produza a síntese:

```xml
<sintese_absorcao>
  <campos_prontos>[liste]</campos_prontos>
  <campos_ambiguos>
    <item campo="" suposicao_adotada=""/>
  </campos_ambiguos>
  <conflitos_internos>
    <item campos="" resolucao=""/>
  </conflitos_internos>
  <conflitos_com_memoria>
    <item regra_ou_erro="" resolucao=""/>
  </conflitos_com_memoria>
  <campos_ausentes_criticos>[liste — apenas os que impactam estrutura]</campos_ausentes_criticos>
  <erros_da_memoria_ativos>[ids dos erros do bloco de memória relevantes]</erros_da_memoria_ativos>
</sintese_absorcao>
```

**Gatilho de pausa:** Se houver ambiguidade em campo que impacta diretamente persona, formato de output ou restrição principal $\rightarrow$ **pause e pergunte ao usuário antes de avançar**. Para campos secundários, adote a suposição e registre.

---

## FASE 2 — CHECAGEM DE REGRAS

**Não gere o prompt ainda.**
Para cada elemento estrutural do prompt a ser gerado:

```xml
<checagem_elemento>
  <elemento>[nome: persona / contexto / formato / restrição / CoT / etc.]</elemento>
  <regra_aplicavel>[id da regra da memória ou critério fixo da Fase 0]</regra_aplicavel>
  <tipo>IMUTAVEL | MUTAVEL | CRITERIO_FIXO | DECISAO_LIVRE</tipo>
  <conflito_entre_regras tipo="sim|nao">[se sim: qual prevalece pela hierarquia]</conflito_entre_regras>
  <decisao>[como será construído]</decisao>
</checagem_elemento>
```

Ao final:

```xml
<mapa_de_regras>
  <imutaveis_ativas>[ids]</imutaveis_ativas>
  <mutaveis_ativas>[ids]</mutaveis_ativas>
  <ignoradas_por_conflito>
    <item regra="" justificativa=""/>
  </ignoradas_por_conflito>
  <decisoes_livres>[elementos sem cobertura de regra]</decisoes_livres>
</mapa_de_regras>
```

---

## FASE 3A — GERAÇÃO DO PROMPT

Gere o prompt final do cliente respeitando:
- Hierarquia de autoridade declarada na Fase 0
- Síntese da Fase 1
- Mapa de regras da Fase 2
- Formato de output da memória ativa (XML ou Markdown conforme preferência)

Delimite o prompt gerado:

```markdown
<!-- PROMPT GERADO — INÍCIO -->

[prompt completo aqui]

<!-- PROMPT GERADO — FIM -->
```

---

## FASE 3B — AUDITORIA INTERNA (Self-Refine)

**Obrigatória. Máximo 2 rodadas. Execute antes de entregar.**

```xml
<auditoria>
  <item criterio="Todos os elementos inegociáveis da Fase 0 presentes"
        status="ok|falha" correcao=""/>
  <item criterio="Mapa de regras da Fase 2 respeitado integralmente"
        status="ok|falha" correcao=""/>
  <item criterio="Nenhuma instrução contradiz outra no prompt"
        status="ok|falha" correcao=""/>
  <item criterio="Formato de output especificado sem ambiguidade"
        status="ok|falha" correcao=""/>
  <item criterio="Prompt autoexplicativo sem o briefing"
        status="ok|falha" correcao=""/>
  <item criterio="CoT conectado ao output, não decorativo"
        status="ok|falha" correcao=""/>
  <item criterio="Erros da memória ativa foram evitados"
        status="ok|falha" correcao=""/>
  <rodada_atual>1</rodada_atual>
  <status_geral>aprovado|reprovado</status_geral>
</auditoria>
```

Se `status_geral = reprovado` após 2 rodadas $\rightarrow$ aplique as correções possíveis, registre o restante nos Alertas e entregue com aviso explícito.

---

## MAPA DE DECISÕES & ALERTAS

```xml
<mapa_decisoes>
  <secao nome="" origem="briefing|regra_id|fase0|decisao_livre"
         justificativa="" referencia_exata=""/>
</mapa_decisoes>

<alertas>
  <alerta tipo="suposicao|sem_cobertura|conflito_imutavel|correcao_3b|revisao_usuario">
    [descrição do alerta]
  </alerta>
</alertas>
```

---

## ATUALIZAÇÃO DA MEMÓRIA ATIVA

Execute ao final de cada sessão. Atualize o arquivo `.agents/Skills/corporate-prompt-generator/resources/active_memory.xml` e entregue também o bloco atualizado ao usuário:

```xml
<atualizacao_memoria>

  <regras>
    <!-- Nova regra mutável identificada? -->
    <nova_regra tipo="MUTAVEL" origem="decisao_livre|feedback_usuario"
                justificativa=""/>
    <!-- Regra mutável existente deve ser revisada? -->
    <revisao_regra id="" motivo=""/>
  </regras>

  <erros>
    <!-- Novo erro cometido nesta sessão? -->
    <novo_erro secao_afetada="" causa_raiz="" como_evitar=""/>
    <!-- Erro existente foi resolvido? -->
    <erro_resolvido id="" solucao_aplicada=""/>
  </erros>

  <preferencias>
    <!-- Preferência confirmada ou alterada pelo usuário? -->
    <atualizacao_preferencia tipo="" valor_anterior="" valor_novo=""
                             confirmada_pelo_usuario="sim|nao"/>
  </preferencias>

  <melhorias>
    <!-- Melhoria proposta pelo usuário nesta sessão? -->
    <nova_melhoria descricao="" contexto="" prioridade="alta|media|baixa"/>
    <!-- Melhoria implementada? -->
    <melhoria_implementada id="" como_foi_aplicada=""/>
  </melhorias>

</atualizacao_memoria>
```

Ao final, persista e apresente o bloco `<memoria_ativa>` completo e atualizado.

---

## INSTRUÇÃO FINAL — TRATAMENTO DE FEEDBACK

Ao receber feedback sobre o prompt de cliente gerado, classifique antes de agir:

1. **A seção criticada veio de briefing?**
   $\rightarrow$ Problema no briefing, não na skill. Oriente o usuário a ajustar o campo.
2. **Veio de regra IMUTÁVEL?**
   $\rightarrow$ **NÃO alterar.** Emitir alerta. Explicar o conflito ao usuário.
3. **Veio de regra MUTÁVEL?**
   $\rightarrow$ Candidato a atualização. Registrar em `<atualizacao_memoria>` (e vincular à hipótese correspondente em `docs/prompt_hypotheses_ledger.md`).
4. **Veio de critério fixo da Fase 0?**
   $\rightarrow$ Avaliar se o critério precisa de refinamento para este tipo de briefing.
   $\rightarrow$ Registrar como melhoria proposta antes de qualquer alteração.
5. **Veio de decisão livre?**
   $\rightarrow$ Registrar como nova regra `MUTAVEL` com escopo adequado.
6. **Causa incerta?**
   $\rightarrow$ Perguntar explicitamente ao usuário antes de registrar qualquer coisa.
