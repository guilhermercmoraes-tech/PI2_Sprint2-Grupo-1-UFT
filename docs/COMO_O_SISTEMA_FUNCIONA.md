# Como o sistema funciona

Relatório do fluxo de trabalho do Sistema de Inteligência Tributária de Palmas, do dado bruto à decisão do gestor. Cada etapa tem um diagrama e aponta a seção correspondente do [modelo UML](REQUISITOS_UML.md).

**Legenda de todos os diagramas:** verde = implementado e testado na Sprint 2 · cinza tracejado = especificado, previsto para sprints seguintes.

---

## Visão geral: o fluxo completo

O sistema transforma dados públicos e administrativos em informação para planejar a arrecadação. O caminho tem oito etapas. As quatro primeiras formam a **camada de dados**, construída nesta sprint. As demais formam a **camada de serviço**, que usa essa base.

```mermaid
flowchart LR
    E1["1 · Coleta<br/>portais da Prefeitura"] --> E2["2 · Validação<br/>parser e regras"]
    E2 --> E3["3 · Armazenamento<br/>MySQL em 3FN"]
    E3 --> E4["4 · Estruturas em memória<br/>grafo · hash · heap"]
    E3 --> E5["5 · Sistema<br/>gestor e cidadão"]
    E4 --> E5
    E3 --> E6["6 · IA territorial<br/>estimativas"]
    E6 --> E5
    E5 --> E7["7 · Segurança e auditoria"]
    E2 -.-> E8["8 · Garantia de qualidade<br/>em todas as etapas"]
    E3 -.-> E8
    E4 -.-> E8

    classDef feito fill:#d4edda,stroke:#2e7d32,color:#1b3d1f
    classDef parcial fill:#fff3cd,stroke:#b8860b,color:#4d3800
    classDef planejado fill:#eeeeee,stroke:#9e9e9e,stroke-dasharray:5 5,color:#555
    class E2,E3,E4,E8 feito
    class E1,E7 parcial
    class E5,E6 planejado
```

| Etapa | Situação | Onde está |
|---|---|---|
| 1 Coleta | Parcial: CSV já baixado; coleta automática na Sprint 3 | `etl/amostra.py`, E3 |
| 2 Validação | Implementada | `etl/parser.py` |
| 3 Armazenamento | Implementado | `sql/schema.sql`, `etl/carregar_receita.py` |
| 4 Estruturas | Implementadas | `src/estruturas/` |
| 5 Sistema (gestor e cidadão) | Especificado | UML §2, §6, §11, §15–18 |
| 6 IA territorial | Especificada | UML §8–10 |
| 7 Segurança e auditoria | Parcial: tabelas, restrições e protocolos | UML §2.1, `PROTOCOLOS_SEGURANCA_AUDITORIA.md` |
| 8 Qualidade | Implementada | `scripts/quality_gate.py`, UML §23 |

---

## Etapa 1 — Coleta dos dados

Os dados vêm dos portais de transparência da Prefeitura. Hoje o arquivo `receita_acessoinformacao.csv` (176.993 linhas) já foi baixado; nesta sprint usamos uma **amostra de 10 linhas reais** (IPTU e ISSQN de janeiro de 2025). A coleta automática, com HTTPS verificado e intervalo entre requisições, fica para a Sprint 3.

```mermaid
sequenceDiagram
    autonumber
    participant P as Portal da Prefeitura
    participant C as Cliente de coleta (Sprint 3)
    participant A as Arquivo CSV
    participant M as etl/amostra.py

    rect rgb(238,238,238)
    Note over P,C: Planejado: coleta automática
    C->>P: GET via HTTPS (certificado verificado)
    P-->>C: dados de receita
    C->>A: grava o arquivo
    end
    rect rgb(212,237,218)
    Note over A,M: Implementado nesta sprint
    M->>A: lê as 176.993 linhas
    M->>M: filtra órgão 2798, jan/2025, IPTU e ISSQN
    M-->>A: grava a amostra de 10 linhas + número da linha de origem
    end
```

UML: §14 (interfaces externas) · E3 e `PROTOCOLOS_SEGURANCA_AUDITORIA.md` (protocolo P1).

**Fundamentação:** [L4] Kurose §8.6, p. 524–528 (TLS e truncamento); [T1]–[T3] (versões atuais de TLS); [R10] LGPD (coletar só o necessário); [D3] (arquivos e SHA-256).

---

## Etapa 2 — Validação: nenhum dado entra sem passar pelas regras

Cada linha do CSV é conferida antes de ir para o banco. Um erro de contrato (valor com fração de centavo, mês inválido) **interrompe a publicação**: o arquivo fica só na área de conferência (staging), e o erro é registrado.

```mermaid
flowchart TD
    L["Linha do CSV"] --> V1{"Ano, mês e órgão<br/>são números válidos?"}
    V1 -- não --> ERRO["ERRO de contrato<br/>registrado em resultado_validacao"]
    V1 -- sim --> V2{"Mês entre 1 e 12?"}
    V2 -- não --> ERRO
    V2 -- sim --> V3{"Valores sem<br/>fração de centavo?"}
    V3 -- não --> ERRO
    V3 -- sim --> V4{"Código está no<br/>mapeamento aprovado?"}
    V4 -- não --> NM["Conta não mapeada<br/>fica só no staging (INFO)"]
    V4 -- sim --> V5{"É conta-pai?"}
    V5 -- sim --> T["TOTAL<br/>só para conferência"]
    V5 -- não --> C["COMPONENTE<br/>principal, multas, dívida ativa…"]
    ERRO --> PARA["Publicação interrompida"]

    classDef feito fill:#d4edda,stroke:#2e7d32,color:#1b3d1f
    classDef erro fill:#f8d7da,stroke:#a71d2a,color:#5c0d14
    class L,V1,V2,V3,V4,V5,T,C,NM feito
    class ERRO,PARA erro
```

**Por que separar TOTAL e COMPONENTE:** o portal publica a conta-pai (total do IPTU) e também suas quatro partes. Somar tudo contaria o IPTU duas vezes. O sistema soma só os componentes e usa o total para conferir.

```mermaid
flowchart LR
    PAI["IPTU total<br/>1112500<br/>R$ 2.885.620,64"]
    PAI -- DETALHA --> C1["Principal<br/>R$ 2.274.951,38"]
    PAI -- DETALHA --> C2["Multas e juros<br/>R$ 100.668,50"]
    PAI -- DETALHA --> C3["Dívida ativa<br/>R$ 315.099,43"]
    PAI -- DETALHA --> C4["Dívida ativa: multas<br/>R$ 194.901,33"]
    C1 & C2 & C3 & C4 --> S["Soma = R$ 2.885.620,64<br/>confere com o total ✔"]

    classDef feito fill:#d4edda,stroke:#2e7d32,color:#1b3d1f
    class PAI,C1,C2,C3,C4,S feito
```

UML: §20.2 · Testes: `test_parser.py`, `carga_receita.feature`.

**Fundamentação:** [R3] CTN e [R4] MCASP §3.5 (etapas da receita); [D3] (contas-pai × componentes, 273 conciliações sem diferença); [D2] (regras de ETL).

---

## Etapa 3 — Armazenamento no banco

A carga é **idempotente**: o arquivo é identificado pelo SHA-256, e carregar o mesmo arquivo de novo não duplica nada. Tudo acontece numa única transação.

```mermaid
sequenceDiagram
    autonumber
    participant U as Equipe
    participant C as carregar_receita
    participant B as MySQL

    U->>C: carregar(amostra.csv)
    C->>C: calcula o SHA-256 do arquivo
    C->>B: esse SHA-256 já existe?
    alt arquivo já carregado
        B-->>C: sim (snapshot 1)
        C-->>U: nada foi duplicado
    else arquivo novo
        C->>B: BEGIN · cria fonte_snapshot
        C->>B: copia as linhas brutas para o staging
        C->>C: valida cada linha (Etapa 2)
        alt algum erro de contrato
            C->>B: registra o erro · COMMIT só do staging
        else tudo válido
            C->>B: órgão, contas (pais antes dos filhos), valores mensais, orçamento
            C->>B: registra a conciliação pai × componentes
            C->>B: COMMIT
        end
        C-->>U: resumo (componentes, totais, erros, divergências)
    end
```

O banco tem dois módulos: **receita observada**, com dados reais, e **domínio operacional** (créditos, pagamentos, negociação), hoje com dados sintéticos, porque os dados públicos não contêm devedores.

```mermaid
flowchart LR
    subgraph A["Módulo A · receita observada (dados reais)"]
        FS[fonte_snapshot] --> STG[stg_receita_atual]
        FS --> CR[conta_receita]
        CR --> RCM[receita_componente_mensal]
        CR --> TIM[total_informado_mensal]
        CR --> ORC[orcamento_informado]
    end
    subgraph B["Módulo B · domínio operacional (dados sintéticos)"]
        SP[sujeito_passivo] --> RESP[responsabilidade_tributaria]
        CT[credito_tributario] --> RESP
        CT --> AJ[ajuste_credito]
        PG[pagamento] --> AP[apropriacao]
        CT --> AP
        CT --> ITN[item_negociacao]
        IM[imovel] --> CT
    end
    RCM --> V1(["v_tributo_mes"])
    TIM --> V2(["v_conciliacao_pai_filhos"])
    AP --> V3(["v_saldo_credito"])

    classDef feito fill:#d4edda,stroke:#2e7d32,color:#1b3d1f
    class FS,STG,CR,RCM,TIM,ORC,SP,RESP,CT,AJ,PG,AP,ITN,IM,V1,V2,V3 feito
```

Valores derivados, como saldo e arrecadação por tributo, **nunca são gravados**: as *views* (em forma de pílula no diagrama) os calculam sempre a partir dos movimentos.

UML: §5, §16.4, §20.1 · `docs/modelagem_er.md` · Testes: `test_banco.py`, `carga_receita.feature`.

**Fundamentação:** [E4] Valente cap. 4 (modelos); [L1] Rosen p. 805 (árvore B, estrutura dos índices do banco); [F1] manual do MySQL (CHECK, FK); [D3] (snapshot imutável por SHA-256).

---

## Etapa 4 — Estruturas de dados em memória

O banco guarda o estado confiável. Três estruturas aceleram as operações do dia a dia:

```mermaid
flowchart TB
    DB[("MySQL<br/>estado confiável")]
    DB --> H["Tabela hash<br/>acha um crédito pelo id em O(1)"]
    DB --> G["Grafo<br/>liga sujeito ↔ créditos ↔ imóveis<br/>percursos em O(V+E)"]
    DB --> F["Heap<br/>entrega a ação mais urgente<br/>em O(log n)"]
    H --> Q1["Qual é o registro do crédito 3?"]
    G --> Q2["Quais imóveis e créditos estão ligados ao sujeito 1?"]
    F --> Q3["Qual é a próxima ação do plano?"]

    classDef feito fill:#d4edda,stroke:#2e7d32,color:#1b3d1f
    class DB,H,G,F,Q1,Q2,Q3 feito
```

A fila de prioridade funciona como uma sala de espera ordenada. Quando a prioridade de uma ação muda, ela recebe uma nova senha, e a senha antiga é descartada quando é chamada:

```mermaid
sequenceDiagram
    participant G as Gestor
    participant F as Fila (heap)
    G->>F: inserir acao-1 (classe 2)
    G->>F: inserir acao-2 (classe 1)
    G->>F: inserir acao-3 (classe 1, score maior)
    G->>F: crédito da acao-3 foi pago → remover
    G->>F: extrair
    F-->>G: acao-2 (a acao-3 foi descartada)
    G->>F: extrair
    F-->>G: acao-1
```

UML: §20.4 · `docs/arquitetura_dados.md` · Testes: `test_heap.py`, `test_indice_hash.py`, `test_grafo.py`, `estruturas.feature`.

**Fundamentação:** [L1] Rosen §10.3, §10.4, §11.1, §11.4 (p. 668, 682, 686, 754, 789, 791); [L2] Lintzmayer & Mota cap. 12, 14 e 24 (p. 154–167, 173–174, 305–332); [L3] Gersting §5.6, Exemplos 49–51; [R11] Morin.

---

## Etapa 5 — O sistema para o gestor e para o cidadão

Sobre a base de dados, o sistema oferece dois caminhos. O **servidor** planeja e acompanha a arrecadação. O **cidadão** consulta dados agregados e, se autenticado, acompanha os próprios processos.

```mermaid
flowchart TB
    subgraph SERV["Servidor da Sefin"]
        S1[Login] --> S2{Perfil permite?}
        S2 -- não --> S3[Negado e auditado]
        S2 -- sim --> S4[Painel do Plano Regional]
        S4 --> S5[Define meta e ações]
        S5 --> S6[Acompanha observado × estimado]
        S6 --> S7[Analisa solicitações e negociações]
    end
    subgraph CID["Cidadão"]
        C1[Mapa público<br/>só agregados] --> C2{Quer agir?}
        C2 -- sim --> C3[Login Gov.br]
        C3 --> C4[Solicita adesão ao plano]
        C4 --> C5[Acompanha status e negociação]
    end
    C4 -. chega ao .-> S7
    S7 -. atualiza .-> C5

    classDef planejado fill:#eeeeee,stroke:#9e9e9e,stroke-dasharray:5 5,color:#555
    class S1,S2,S3,S4,S5,S6,S7,C1,C2,C3,C4,C5 planejado
```

Cada processo segue uma máquina de estados. Toda mudança de estado é auditada (UML §18):

```mermaid
stateDiagram-v2
    [*] --> INICIADO
    INICIADO --> SOB_ANALISE : enviar
    SOB_ANALISE --> AGUARDANDO_DOCUMENTO : pede documento
    AGUARDANDO_DOCUMENTO --> SOB_ANALISE : documento recebido
    SOB_ANALISE --> EM_NEGOCIACAO : aprovar
    SOB_ANALISE --> CANCELADO : rejeitar
    EM_NEGOCIACAO --> CONCLUIDO : acordo cumprido
    EM_NEGOCIACAO --> CANCELADO : acordo rompido
    CONCLUIDO --> [*]
    CANCELADO --> [*]
```

Situação: as tabelas, restrições e estados existem no banco. As telas e os serviços são das próximas sprints. A regra "uma negociação ativa por crédito" já é garantida e testada no banco (`negociacao_saldo.feature`).

UML: §2, §6, §11, §15, §17, §18.

**Fundamentação:** [E4]–[E7] Valente (modelos, princípios, padrões, arquitetura); [L4] Kurose §2.2 e §8.4.5 (sessão HTTP e nonce); [R16] Gov.br; [R12] ISO 29148 (requisitos verificáveis).

---

## Etapa 6 — A IA territorial

A IA **não classifica pessoas**. Ela estima a arrecadação por **região × período × tributo** e aponta desvios. O sistema mostra a estimativa separada do valor observado.

```mermaid
flowchart LR
    D[(Dados históricos<br/>por região e mês)] --> VTC[Monta o vetor<br/>territorial VTC]
    VTC --> IAET[Calcula o índice<br/>IAET]
    VTC --> Q{Qual tributo?}
    IAET --> Q
    Q -- IPTU --> E1[Estratégia IPTU]
    Q -- ISS --> E2[Estratégia ISS]
    E1 & E2 --> R["Estimativa + intervalo<br/>+ desvio + versão do modelo"]
    R --> P[(Tabela previsao)]
    P --> T["Painel: observado × estimado<br/>com rótulos distintos"]
    COB{Dados suficientes?} -. não .-> IND["Estimativa indisponível"]
    D --> COB

    classDef planejado fill:#eeeeee,stroke:#9e9e9e,stroke-dasharray:5 5,color:#555
    classDef feito fill:#d4edda,stroke:#2e7d32,color:#1b3d1f
    class D,VTC,IAET,Q,E1,E2,R,T,COB,IND planejado
    class P feito
```

Situação: só a tabela `previsao` existe (com a restrição de que a estimativa fique dentro do intervalo). O modelo depende de dados territoriais que ainda não foram obtidos (PA-12).

UML: §8, §9, §10, §17.3.

**Fundamentação:** [R1]–[R2] (tax gap); [R6]–[R7] (cobrança e analytics); [R8] (índice composto IAET); [R9] (validação temporal); [R13] (divulgação de agregados); [R17]–[R20] (evidências e Model Card); [E6] Strategy.

---

## Etapa 7 — Segurança e auditoria

Toda conexão é cifrada, e toda ação relevante deixa um registro. A auditoria usa, sobre os próprios registros, os mesmos mecanismos que protegem mensagens na rede (Kurose, cap. 8).

```mermaid
flowchart LR
    A[Ação de usuário,<br/>serviço ou tarefa] --> Z{Autorizado?}
    Z -- sim --> OK[Executa]
    Z -- não --> NEG[Nega]
    OK & NEG --> R["Registro de auditoria<br/>ator · recurso · ação · resultado<br/>nunca senha ou token"]
    R --> MAC["MAC encadeado<br/>HMAC(registro + MAC anterior)"]
    MAC --> SEQ[Número de sequência<br/>sem lacunas]
    SEQ --> SELO[Selo periódico<br/>guardado fora do banco]

    classDef feito fill:#d4edda,stroke:#2e7d32,color:#1b3d1f
    classDef planejado fill:#eeeeee,stroke:#9e9e9e,stroke-dasharray:5 5,color:#555
    class R feito
    class A,Z,OK,NEG,MAC,SEQ,SELO planejado
```

Situação: a tabela de auditoria e a regra do ator coerente existem e são testadas (`auditoria.feature`). A cadeia de MAC, a sequência e o selo estão especificados no protocolo, mas não implementados.

UML: §2.1, §13 · `PROTOCOLOS_SEGURANCA_AUDITORIA.md`.

**Fundamentação:** [L4] Kurose §8.3.2 p. 510 (MAC/HMAC), §8.6 p. 526–528 (sequência e truncamento), §9.3.4 p. 572 (controle de acesso por visões); [T4] RFC 2104; [R10] LGPD.

---

## Etapa 8 — Garantia de qualidade em cada integração

Nenhuma mudança entra no código principal sem passar pelos 10 quality gates.

```mermaid
flowchart LR
    DEV[Desenvolvedor altera o código] --> LOCAL["quality_gate.py<br/>G1–G9"]
    LOCAL -- reprovado --> DEV
    LOCAL -- aprovado --> PUSH[git push]
    PUSH --> CI["GitHub Actions<br/>G1–G9 com MySQL"]
    CI -- reprovado --> DEV
    CI -- aprovado --> PR[Pull request para main]
    PR --> CI2["GitHub Actions<br/>G1–G10 com mutação"]
    CI2 -- reprovado --> DEV
    CI2 -- aprovado --> MERGE[Merge na main]

    classDef feito fill:#d4edda,stroke:#2e7d32,color:#1b3d1f
    classDef parcial fill:#fff3cd,stroke:#b8860b,color:#4d3800
    class DEV,LOCAL feito
    class PUSH,CI,PR,CI2,MERGE parcial
```

Os gates rodam localmente e foram aprovados (resultado em `docs/qualidade.md`). O workflow do GitHub Actions está pronto, mas ainda não foi executado, porque o repositório não está no GitHub (amarelo no diagrama).

UML: §23.

**Fundamentação:** [E8]–[E10] Valente (testes, refactoring, DevOps); [R12] ISO 29148 (verificação); [F2]–[F9] ferramentas.

---

## Referências literárias e acadêmicas

As referências estão agrupadas por tipo e marcadas com as **etapas do fluxo** que fundamentam (ver [COMO_O_SISTEMA_FUNCIONA.md](COMO_O_SISTEMA_FUNCIONA.md)):

| Etapa | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| Nome | Coleta | Validação | Armazenamento | Estruturas de dados | Sistema (gestor e cidadão) | IA territorial | Segurança e auditoria | Qualidade |

Páginas pela numeração impressa das obras. Os IDs `[R…]` e `[E…]` são os mesmos da Nota Técnica que fundamentou a revisão do UML.

### Matriz referência × etapa

| Ref. | Obra (resumo) | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|---|
| [L1] | Rosen — Matemática discreta | | | ● | ● | | | | |
| [L2] | Lintzmayer & Mota — Algoritmos e estruturas de dados | | | | ● | | | | |
| [L3] | Gersting — Fundamentos matemáticos | | | | ● | | | | |
| [L4] | Kurose & Ross — Redes de computadores | ● | | | | ● | | ● | |
| [R11] | Morin — Open Data Structures | | | | ● | | | | |
| [E4]–[E7] | Valente — modelos, princípios, padrões, arquitetura | | | ● | | ● | ● | | |
| [E8]–[E10] | Valente — testes, refactoring, DevOps | | | | | | | | ● |
| [R12] | ISO/IEC/IEEE 29148 — requisitos | | | | | ● | | | ● |
| [R1]–[R2] | OCDE e FMI — tax gap | | | | | ● | ● | | |
| [R3] | Código Tributário Nacional | | ● | ● | ● | ● | | | |
| [R4] | MCASP — etapas da receita | | ● | ● | | ● | | | |
| [R5] | Constituição Federal | | | ● | | ● | | | |
| [R6]–[R9] | OCDE, FMI, OECD/JRC, James et al. — cobrança, analytics, indicadores, aprendizado | | | | | | ● | | |
| [R17]–[R20] | Santos; Carvalho Jr.; Cabello et al.; Mitchell et al. | | | | | | ● | | |
| [R10] | LGPD | ● | | ● | | ● | | ● | |
| [R13] | Sweeney — k-anonimato | | | | | ● | ● | ● | |
| [R16] | Roteiro Gov.br | | | | | ● | | ● | |
| [T1]–[T7] | RFCs de TLS, HMAC, hash e cookies | ● | | | | ● | | ● | |
| [D1]–[D4] | Documentos do projeto | ● | ● | ● | ● | ● | ● | ● | ● |
| [F1]–[F9] | Ferramentas e manuais | | | ● | | | | | ● |

### Livros consultados

**[L1]** ROSEN, Kenneth H. *Discrete Mathematics and Its Applications*. 7. ed. New York: McGraw-Hill, 2012.
- Etapa 4 — §10.3, p. 668: representação por **lista de adjacência** (Exemplo 1, Tabela 1).
- Etapa 4 — §10.4, p. 682 e p. 686 (Definição 5): **componentes conexos** e grafo dirigido **fracamente conexo**.
- Etapa 4 — §11.4, Algoritmo 1 (DFS), p. 789, e Algoritmo 2 (BFS), p. 791: busca em profundidade e em largura, **O(e)** passos.
- Etapa 4 — §11.1, Teorema 5 e Corolário 1, p. 754: altura ⌈logₘ l⌉ de árvore balanceada, base do **O(log n)** da heap.
- Etapa 3 — Exercícios suplementares do cap. 11, p. 805: **árvore B** de grau k, estrutura dos índices do MySQL/InnoDB.
- Etapa 4 — §4.5, p. 287–288: função de dispersão h(k) = k mod m e **colisão**.

**[L2]** LINTZMAYER, Carla Negri; MOTA, Guilherme Oliveira. *Análise de Algoritmos e de Estruturas de Dados*. (versão em PDF consultada).
- Etapa 4 — cap. 12, §12.1, p. 154–167: **heap binário** (construção, inserção, remoção, alteração).
- Etapa 4 — cap. 14, p. 173–174: **tabelas hash**, colisões inevitáveis, O(1) no caso médio.
- Etapa 4 — cap. 24, Algoritmos 24.5 e 24.11 (BFS, p. 310 e 322), 24.7 (DFS iterativa, p. 316), 24.9 e 24.12 (DFS recursiva, p. 320 e 322), 24.10 (componentes, p. 321): comparados com o código em 2.000 digrafos aleatórios, com ordem de visita idêntica.
- Etapa 4 — §24.4.2, p. 330–332: um digrafo admite ordenação topológica se, e somente se, **não tem ciclos**.

**[L3]** GERSTING, Judith L. *Fundamentos matemáticos para a ciência da computação: matemática discreta e suas aplicações*. Rio de Janeiro: LTC. (edição do PDF consultado).
- Etapa 4 — Seção 5.6 "A poderosa função mod", subseção *Dispersão*: Exemplo 49 (h(x) = x mod t), **Exemplo 50 e Figura 5.29 (encadeamento)**, reproduzido em `estruturas.feature`; texto após o Exemplo 51: **fator de carga** e recomendação de tabela de tamanho primo.

**[L4]** KUROSE, James F.; ROSS, Keith W. *Redes de computadores e a Internet: uma abordagem top-down*. 6. ed. São Paulo: Pearson, 2013.
- Etapa 5 — §2.2.1 e §2.2.4, p. 73 e 79–81: HTTP sem estado e sessão com cookies.
- Etapa 7 — §8.1, p. 496–497: propriedades de comunicação segura e modelo do intruso.
- Etapa 7 — §8.3, p. 508–514: funções de hash, **MAC/HMAC** (p. 510) e autoridades certificadoras (p. 514), base da cadeia de MAC da auditoria.
- Etapa 5 e 7 — §8.4.5, p. 518: **nonce** e autenticação "ao vivo".
- Etapas 1, 5 e 7 — §8.6, p. 524–528: **SSL/TLS**, handshake, números de sequência e ataque por truncamento.
- Etapa 7 — §8.7, p. 528–531: IPsec, ESP e VPN.
- Etapa 7 — §8.9, p. 538–545: firewall, DMZ e sistemas de detecção de invasão.
- Etapa 7 — §9.3.4, p. 570–572: SNMPv3, anti-repetição e controle de acesso por visões.

**[R11]** MORIN, Pat. *Open Data Structures: An Introduction*. Athabasca University Press, 2013. https://opendatastructures.org/ — Etapa 4: tabelas hash, heaps e grafos.

**[E4]–[E10]** VALENTE, Marco Tulio. *Engenharia de Software Moderna*. (capítulos fornecidos pela equipe).
- [E4] cap. 4 Modelos — Etapas 3 e 5: diagramas UML formais deste documento.
- [E5] cap. 5 Princípios de projeto — Etapa 3: separação entre parser, repositório e serviços.
- [E6] cap. 6 Padrões de projeto — Etapas 5 e 6: Strategy (IPTU/ISS), Adaptador, Fachada.
- [E7] cap. 7 Arquitetura — Etapa 5: monólito modular.
- [E8] cap. 8 Testes — Etapa 8: testes unitários, de integração e de sistema.
- [E9] cap. 9 Refactoring — Etapa 8: divisão de `carregar()` sem mudar o comportamento.
- [E10] cap. 10 DevOps — Etapa 8: integração contínua e quality gates.

### Normas, legislação e artigos (Nota Técnica)

- **[R1]** OECD. *Tax Administration 2024*, cap. 11: Tax gap estimation. Paris, 2024. — Etapas 5 e 6.
- **[R2]** HUTTON, Eric. *The Revenue Administration-Gap Analysis Program*. IMF TNM 2017/004. https://doi.org/10.5089/9781475583618.005 — Etapas 5 e 6.
- **[R3]** BRASIL. Lei nº 5.172/1966 (Código Tributário Nacional), arts. 114, 142, 150, 198 e 201. — Etapas 2 a 5: lançamento, crédito, dívida ativa.
- **[R4]** BRASIL. STN. *Manual de Contabilidade Aplicada ao Setor Público*, 11. ed., Parte I, §3.5. — Etapas 2, 3 e 5: etapas da receita.
- **[R5]** BRASIL. Constituição Federal de 1988, arts. 156, 156-A e 167, IV. — Etapas 3 e 5.
- **[R6]** OECD. *Working Smarter in Tax Debt Management*. 2014. https://doi.org/10.1787/9789264223257-en — Etapa 6.
- **[R7]** ASLETT, J. et al. *Tax Administration: Essential Analytics for Compliance Risk Management*. IMF TNM 2024/001. https://doi.org/10.5089/9798400260063.005 — Etapa 6.
- **[R8]** OECD; EU; EC-JRC. *Handbook on Constructing Composite Indicators*. 2008. https://doi.org/10.1787/9789264043466-en — Etapa 6: IAET.
- **[R9]** JAMES, G. et al. *An Introduction to Statistical Learning: with Applications in Python*. Springer, 2023. — Etapa 6: validação temporal, sem vazamento.
- **[R10]** BRASIL. Lei nº 13.709/2018 (LGPD). — Etapas 1, 3, 5 e 7: pseudonimização, finalidade, retenção.
- **[R12]** ISO/IEC/IEEE 29148:2018. *Requirements engineering*. — Etapas 5 e 8: requisitos verificáveis e rastreáveis.
- **[R13]** SWEENEY, Latanya. k-anonymity: a model for protecting privacy. *IJUFKS*, v. 10, n. 5, 2002. — Etapas 5, 6 e 7: divulgação de agregados.
- **[R16]** GOVERNO FEDERAL. *Roteiro de Integração do Login Único gov.br*. https://acesso.gov.br/roteiro-tecnico/ — Etapas 5 e 7.
- **[R17]** SANTOS, Rubens Q. Estimando a arrecadação da Dívida Ativa da União com Machine Learning. *Revista da CGU*, v. 14, n. 26, 2022. — Etapa 6.
- **[R18]** CARVALHO JÚNIOR, Pedro H. B. *Panorama do IPTU*. Ipea, TD 2419, 2018. — Etapa 6.
- **[R19]** CABELLO, O. G. et al. Inovação e eficiência na administração tributária local. *RAP*, v. 60, 2026. — Etapa 6.
- **[R20]** MITCHELL, Margaret et al. Model Cards for Model Reporting. FAT*, 2019. https://arxiv.org/abs/1810.03993 — Etapa 6: documentação do modelo.

### Especificações técnicas (RFCs)

- **[T1]** RFC 8446 — TLS 1.3. — Etapas 1, 5 e 7.
- **[T2]** RFC 8996 — descontinuação de TLS 1.0 e 1.1. — Etapas 1 e 7.
- **[T3]** RFC 9325 / BCP 195 — recomendações de uso seguro de TLS. — Etapas 1 e 7.
- **[T4]** RFC 2104 — HMAC. — Etapa 7: cadeia de MAC da auditoria.
- **[T5]** RFC 6151 — MD5 inadequado para segurança. — Etapa 7.
- **[T6]** RFC 6194 — considerações de segurança do SHA-1. — Etapa 7.
- **[T7]** RFC 6265 e draft-ietf-httpbis-rfc6265bis — cookies HTTP e atributo `SameSite`. — Etapa 5.

### Documentos do projeto

- **[D1]** UFT/BIINAR. *Tarefa do PI — Sprint 2: Arquitetura de Dados e Banco* (`PI_Sprint2_Entrega02out2026.pdf`). — Todas as etapas: entregáveis e rubrica.
- **[D2]** *PI2 — Nota Técnica: fundamentação científica, diagnóstico dos dados e revisão do UML* (29/09/2026). — Etapas 2, 3, 5 e 6.
- **[D3]** *Palmas — Auditoria dos CSVs fornecidos* (`Relatorio_Palmas.pdf`, 29/09/2026). — Etapas 1 a 4: snapshot SHA-256, pais × componentes, valores de 2025.
- **[D4]** *Projeto Integrador — Opção D: Inteligência Tributária de Palmas* (enunciado geral). — Contexto de todas as etapas.

### Ferramentas e manuais

- **[F1]** Oracle. *MySQL 8.4 Reference Manual* — restrições CHECK, FOREIGN KEY e índices InnoDB. — Etapa 3.
- **[F2]** pytest. — Etapa 8.
- **[F3]** pytest-bdd e Cucumber Gherkin (sintaxe `Funcionalidade/Cenário/Dado/Quando/Então`). — Etapa 8.
- **[F4]** coverage.py (cobertura de linhas e ramos). — Etapa 8.
- **[F5]** cosmic-ray (testes de mutação). — Etapa 8.
- **[F6]** radon e xenon (complexidade ciclomática, índice de manutenibilidade, SLOC). — Etapa 8.
- **[F7]** import-linter (contratos de dependência). — Etapa 8.
- **[F8]** Pyright (verificação de tipos). — Etapa 8.
- **[F9]** GitHub Actions (integração contínua). — Etapa 8.
