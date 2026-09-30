# Modelagem Entidade-Relacionamento (3FN) — Sprint 2

Banco: **MySQL 8.4** · Esquema versionado: [`sql/schema.sql`](../sql/schema.sql) · Origem do modelo: [`REQUISITOS_UML.md`](REQUISITOS_UML.md) §16 e §20.1.

O banco tem dois módulos:

| Módulo | Conteúdo | Dados no piloto |
|---|---|---|
| **A — Receita observada** | Arrecadação mensal por conta, órgão e competência, com linhagem até a linha do CSV | **Reais**: amostra de 10 linhas de `receita_acessoinformacao.csv` |
| **B — Domínio operacional** | Território, sujeitos passivos, créditos, dívida ativa, pagamentos, negociação, identidade, auditoria, plano e indicadores | **Sintéticos**, marcados `origem_dado = 'SINTETICO'` — os CSVs públicos não contêm devedores, dívidas nem imóveis |

---

## 1. Diagrama ER — Módulo A (receita observada)

```mermaid
erDiagram
    FONTE_SNAPSHOT ||--o{ STG_RECEITA_ATUAL : "contém linhas brutas"
    FONTE_SNAPSHOT ||--o{ CONTA_RECEITA : "origina"
    FONTE_SNAPSHOT ||--o{ RESULTADO_VALIDACAO : "registra"
    ORGAO ||--o{ CONTA_RECEITA : "responde por"
    TRIBUTO ||--o{ CONTA_RECEITA : "classifica"
    COMPONENTE_RECEITA |o--o{ CONTA_RECEITA : "tipifica (só COMPONENTE)"
    CONTA_RECEITA |o--o{ CONTA_RECEITA : "pai DETALHA componentes"
    CONTA_RECEITA ||--o{ RECEITA_COMPONENTE_MENSAL : "papel = COMPONENTE"
    CONTA_RECEITA ||--o{ TOTAL_INFORMADO_MENSAL : "papel = TOTAL"
    CONTA_RECEITA ||--o{ ORCAMENTO_INFORMADO : "orçada em"

    FONTE_SNAPSHOT {
        int id_snapshot PK
        char sha256 UK "SHA-256 do arquivo"
        varchar nome_arquivo
        bigint tamanho_bytes
        int total_linhas
        varchar versao_parser
        datetime data_carga
    }
    STG_RECEITA_ATUAL {
        int id_snapshot PK,FK
        int linha_origem PK "linha no CSV original"
        varchar campos_originais "14 colunas em texto"
    }
    ORGAO {
        int codigo_orgao PK
        varchar nome
    }
    TRIBUTO {
        varchar codigo_tributo PK "IPTU, ISSQN, ITBI"
        varchar nome
        varchar versao_regra
    }
    COMPONENTE_RECEITA {
        varchar codigo_componente PK
        char sufixo UK "1 a 4"
        varchar nome
    }
    CONTA_RECEITA {
        int id_conta PK
        int id_snapshot FK
        smallint ano
        int codigo_orgao FK
        varchar codigo_original "texto; UK com snapshot, ano, órgão"
        varchar codigo_formatado
        enum papel "TOTAL | COMPONENTE"
        varchar codigo_tributo FK
        varchar codigo_componente FK "NULL se TOTAL"
        int id_conta_pai FK "NULL se TOTAL"
    }
    RECEITA_COMPONENTE_MENSAL {
        int id_conta PK,FK
        tinyint mes PK "1 a 12"
        enum papel FK "fixo COMPONENTE"
        decimal valor_arrecadado
        varchar descricao_bruta
        int linha_origem
    }
    TOTAL_INFORMADO_MENSAL {
        int id_conta PK,FK
        tinyint mes PK
        enum papel FK "fixo TOTAL"
        decimal valor_arrecadado
        varchar descricao_bruta
        int linha_origem
    }
    ORCAMENTO_INFORMADO {
        int id_conta PK,FK
        tinyint mes_inicio PK "mês a partir do qual vale"
        decimal valor_orcado
    }
    RESULTADO_VALIDACAO {
        int id_resultado PK
        int id_snapshot FK
        varchar regra
        enum gravidade
        int linha_origem
        varchar evidencia
    }
```

## 2. Diagrama ER — Módulo B (domínio operacional)

```mermaid
erDiagram
    REGIAO ||--o{ QUADRA : contém
    QUADRA ||--o{ LOTE : contém
    LOTE ||--o{ IMOVEL : contém
    LOTE ||--o{ LOTE_VIA : ""
    VIA ||--o{ LOTE_VIA : "dá acesso"
    IMOVEL ||--o{ AVALIACAO_PVG : "avaliado por ano"

    SUJEITO_PASSIVO ||--o{ CADASTRO_ECONOMICO : exerce
    SUJEITO_PASSIVO ||--o{ RESPONSABILIDADE_TRIBUTARIA : assume
    CREDITO_TRIBUTARIO ||--|{ RESPONSABILIDADE_TRIBUTARIA : "atribuído a"
    TRIBUTO ||--o{ CREDITO_TRIBUTARIO : origina
    IMOVEL |o--o{ CREDITO_TRIBUTARIO : "base IPTU"
    CADASTRO_ECONOMICO |o--o{ CREDITO_TRIBUTARIO : "base ISS"
    CREDITO_TRIBUTARIO ||--o{ AJUSTE_CREDITO : "ajustado por"
    INSCRICAO_DIVIDA_ATIVA ||--|{ INSCRICAO_CREDITO : inscreve
    CREDITO_TRIBUTARIO ||--o{ INSCRICAO_CREDITO : ""
    PAGAMENTO ||--o{ APROPRIACAO : "reparte em"
    CREDITO_TRIBUTARIO ||--o{ APROPRIACAO : recebe
    NEGOCIACAO ||--|{ ITEM_NEGOCIACAO : abrange
    CREDITO_TRIBUTARIO ||--o{ ITEM_NEGOCIACAO : ""
    ITEM_NEGOCIACAO ||--o| CREDITO_EM_NEGOCIACAO : "reserva exclusiva"

    USUARIO ||--o| SERVIDOR_PALMAS : "é um"
    USUARIO ||--o| CIDADAO : "é um"
    PERFIL_PERMISSAO ||--o{ SERVIDOR_PALMAS : atribuído
    PERFIL_PERMISSAO ||--o{ PERFIL_CONCEDE : ""
    PERMISSAO ||--o{ PERFIL_CONCEDE : ""
    CIDADAO ||--o{ REPRESENTACAO : exerce
    SUJEITO_PASSIVO ||--o{ REPRESENTACAO : "representado"
    USUARIO |o--o{ REGISTRO_AUDITORIA : "ator humano"

    REGIAO ||--o{ PLANO_ARRECADACAO : possui
    TRIBUTO ||--o{ PLANO_ARRECADACAO : "objeto de"
    PLANO_ARRECADACAO ||--o{ ACAO_PLANO : contém
    PLANO_ARRECADACAO ||--o{ SOLICITACAO_ADESAO : recebe
    CIDADAO ||--o{ SOLICITACAO_ADESAO : realiza
    SUJEITO_PASSIVO ||--o{ SOLICITACAO_ADESAO : "em nome de"
    INDICADOR ||--o{ VALOR_INDICADOR : "medido em"
    REGIAO |o--o{ VALOR_INDICADOR : "refere-se"
    REGIAO |o--o{ PREVISAO : "refere-se"
    TRIBUTO ||--o{ PREVISAO : ""

    CREDITO_TRIBUTARIO {
        int id_credito PK
        varchar codigo_tributo FK
        smallint exercicio
        date data_constituicao
        date data_vencimento
        decimal valor_principal
        enum situacao_exigibilidade
        int id_imovel FK "IPTU"
        int id_cadastro FK "ISS"
    }
    APROPRIACAO {
        int id_apropriacao PK
        int id_pagamento FK
        int id_credito FK
        decimal valor_principal
        decimal valor_encargos
    }
    CREDITO_EM_NEGOCIACAO {
        int id_credito PK "no máximo 1 ativa"
        int id_negociacao FK
    }
    REGISTRO_AUDITORIA {
        bigint id_registro PK
        char id_correlacao
        enum tipo_ator "USUARIO | SERVICO | TAREFA"
        int id_usuario FK
        varchar recurso_acessado
        varchar acao_executada
        enum resultado
    }
```

Os atributos completos de todas as tabelas estão em [`sql/schema.sql`](../sql/schema.sql).

---

## 3. Normalização

### 3.1 1FN
Todos os atributos são atômicos. As 14 colunas do CSV ficam em texto no staging; na publicação, cada medida vira uma linha (conta × mês), e não há grupos repetidos (ex.: o histórico com `valor_jan … valor_dez` não é copiado para colunas mensais).

### 3.2 2FN
Nas tabelas com chave composta, cada atributo não chave depende da chave inteira:

| Tabela | Chave | Dependências funcionais |
|---|---|---|
| `receita_componente_mensal` | (id_conta, mes) | valor_arrecadado, descricao_bruta, linha_origem → dependem da conta **e** do mês (a descrição muda em 77 grupos conta/mês na fonte) |
| `orcamento_informado` | (id_conta, mes_inicio) | valor_orcado → depende da conta e do início da vigência (orçamento muda em 16 grupos na fonte) |
| `avaliacao_pvg` | (id_imovel, ano_avaliacao) | categoria, área, valores venais → dependem do imóvel **no ano** |
| `responsabilidade_tributaria` | (id_credito, id_sujeito, papel) | vigência, fundamento |

### 3.3 3FN
Nenhum atributo não chave depende de outro atributo não chave:

| Decisão | Motivo |
|---|---|
| `orgao_nome` sai da conta/fato e vai para `orgao` | codigo_orgao → nome (dependência transitiva) |
| Nome do tributo e do componente em tabelas próprias | codigo_tributo → nome; codigo_componente → nome, sufixo |
| **Nenhum valor derivado é coluna** | saldo (`v_saldo_credito`), valor venal total, arrecadado por tributo (`v_tributo_mes`), gap e percentual da meta são calculados. Evita anomalias de atualização. |
| Totais (pais) separados dos componentes | O total é derivável da soma dos filhos; é mantido **só para conferência** em `total_informado_mensal`, nunca somado ao fato (`v_conciliacao_pai_filhos`). |
| Associações N:M em tabelas próprias | `lote_via`, `inscricao_credito`, `item_negociacao`, `perfil_concede`, `responsabilidade_tributaria` |
| Orçamento guardado só quando muda | O CSV repete o valor anual nos 12 meses; replicá-lo seria redundância e induziria a somar 12 vezes. |

### 3.4 Redundâncias controladas (documentadas)

| Coluna | Por que existe | Por que não gera anomalia |
|---|---|---|
| `papel` em `receita_componente_mensal` / `total_informado_mensal` | Alvo de uma **FK composta** `(id_conta, papel) → conta_receita`: o banco rejeita uma conta TOTAL na tabela de fatos (e vice-versa) sem trigger | Valor fixado por `CHECK`; não pode divergir da conta |
| `credito_em_negociacao` | Garante **no máximo uma negociação ativa por crédito** (RF-18) pela PK, inclusive sob concorrência | A linha é criada/removida na mesma transação que muda `negociacao.status`; a consulta V13 detecta desvio |
| `usuario.tipo` | Discriminador da especialização `servidor_palmas` / `cidadao` | Informativo; as subtabelas são a fonte da verdade |

---

## 4. Restrições que protegem o modelo

| Regra | Mecanismo |
|---|---|
| Reimportar o mesmo arquivo não duplica receita | `UNIQUE (sha256)` em `fonte_snapshot` |
| Conta única por snapshot, ano, órgão e código | `uq_conta` |
| Conta TOTAL não entra no fato; COMPONENTE não entra na conferência | FK composta + `CHECK` de papel |
| Mês entre 1 e 12 | `CHECK` |
| Componente tem pai e componente; total não tem | `ck_conta_papel` |
| Crédito baseado em imóvel **ou** cadastro econômico | `ck_cred_base` |
| Vencimento ≥ constituição · vigência fim ≥ início | `CHECK` |
| Uma negociação ativa por crédito | PK de `credito_em_negociacao` |
| Auditoria de usuário exige id_usuario; de serviço/tarefa exige id do ator de sistema | `ck_aud_ator` |
| Observado × estimado separados; estimativa dentro do intervalo | tabelas `valor_indicador` × `previsao`; `ck_prev_intervalo` |
| Indicador DISPONIVEL ⇔ valor preenchido | `ck_vi_disp` |
| Dinheiro exato | `DECIMAL(18,2)` em todas as colunas monetárias |
| Σ apropriações ≤ pagamento | Não expressável em CHECK no MySQL: validado pela consulta V09 e pelo serviço |

Todas foram exercitadas em `tests/test_banco.py`, que confere o código de erro MySQL de cada rejeição (1452 FK, 3819 CHECK, 1062 PK).

## 5. Índices

Além das PKs, UKs e índices automáticos das FKs: `conta_receita (ano, codigo_orgao)`, `credito_tributario (codigo_tributo, exercicio)` e `(situacao_exigibilidade)`, `inscricao_divida_ativa (situacao)`, `responsabilidade_tributaria (id_sujeito)`, `acao_plano (status, classe_prioridade, data_prevista)` para a fila, `registro_auditoria (id_correlacao)` e `(data_hora)`. Medir as consultas com a base completa antes de ampliar.
