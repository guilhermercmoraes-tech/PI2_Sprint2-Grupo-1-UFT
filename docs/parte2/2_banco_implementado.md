# Critério 2 — Banco implementado, com esquema versionado no repositório

> **Enunciado (Parte 2):** *"banco implementado (PostgreSQL, MySQL, SQLite ou MongoDB) com esquema versionado no repositório"*.
> **Evidências:** [`sql/schema.sql`](../../sql/schema.sql), [`sql/dados_referencia.sql`](../../sql/dados_referencia.sql), [`sql/seed_sintetico.sql`](../../sql/seed_sintetico.sql), testes de integração `tests/test_banco.py`.

## 1. O banco

| Item | Valor verificado em 30/09/2026 12:22 |
|---|---|
| SGBD | **MySQL 8.4.11** (InnoDB, `utf8mb4`) |
| Banco de desenvolvimento | `pi2_tributario`; testes em `pi2_tributario_teste`, recriado a cada execução |
| Objetos | **43 tabelas** e **3 views** |
| Esquema | `sql/schema.sql`: 95 comandos, reexecutável (remove e recria tudo) |
| Acesso | Usuário `pi2_app` com privilégios só nesses dois bancos; senha no `.env`, fora do Git; servidor ouvindo só em `127.0.0.1` |

## 2. Esquema versionado

Todo o banco é definido por arquivos de texto no repositório. Nada é criado à mão.

| Arquivo | Conteúdo | Ordem |
|---|---|---|
| `sql/schema.sql` | Tabelas, chaves, restrições, índices e views | 1 |
| `sql/dados_referencia.sql` | Domínios fixos: tributos, componentes, indicadores | 2 |
| `sql/seed_sintetico.sql` | Semente sintética do módulo operacional | 3 |
| `sql/validacao.sql` | As 16 consultas de validação (critério 4) | depois da carga |

```bash
python -m etl.sql_runner        # executa 1, 2 e 3 no banco do .env
```

Saída desta execução:

```text
schema.sql: 95 comandos
dados_referencia.sql: 3 comandos
seed_sintetico.sql: 30 comandos
```

> **Situação do versionamento:** o repositório Git existe localmente e o `.gitignore` já exclui senhas e dados gerados, mas **ainda não há commits nem envio ao GitHub**. O passo a passo está em `planejamento/Guia_GitHub_Sprint2.pdf`. Até esses commits serem feitos, o critério "esquema versionado no repositório" está **preparado, mas não cumprido**.

## 3. Restrições que protegem o modelo

As regras do modelo não dependem da disciplina de quem escreve os dados: o próprio banco as recusa.

| Regra | Mecanismo | Teste que prova (código de erro esperado) |
|---|---|---|
| Reimportar o mesmo arquivo não duplica a receita | `UNIQUE (sha256)` | `test_recarga_e_idempotente` |
| Conta TOTAL não entra na tabela de fatos | FK composta `(id_conta, papel)` + `CHECK` | `test_fato_rejeita_conta_total` (1452) |
| Mês entre 1 e 12 | `CHECK` | `test_mes_invalido_rejeitado` (3819) |
| Uma negociação ativa por crédito | PK de `credito_em_negociacao` | `test_uma_negociacao_ativa_por_credito` (1062) |
| Auditoria coerente com o tipo de ator | `CHECK ck_aud_ator` | `test_auditoria_exige_ator_coerente` (3819) |
| Dinheiro exato | `DECIMAL(18,2)` em toda coluna monetária | `test_saldo_derivado_dos_movimentos` |
| Crédito com base em imóvel **ou** cadastro econômico | `CHECK ck_cred_base` | — (restrição declarada) |
| Estimativa dentro do intervalo | `CHECK ck_prev_intervalo` | — (restrição declarada) |
| Σ apropriações ≤ pagamento | Não expressável em `CHECK` no MySQL | Consulta V09 (critério 4) |

## 4. Diagrama de classes do código da camada de dados

O banco é criado e alimentado por um pacote Python, `etl/`. O diagrama abaixo foi montado **a partir do código real** (classes, atributos e funções extraídos dos arquivos) e segue a notação do ESM, cap. 4, §4.3:
- cada módulo aparece como uma classe com estereótipo «módulo»;
- `+` indica função pública e `−` função interna (prefixo `_` em Python);
- `dataclass` são classes de dados;
- a herança aparece como seta com ponta triangular (§4.3.2), e a dependência (um módulo importa ou usa o outro) como seta tracejada (§4.3.3).

```mermaid
classDiagram
    direction TB
    class config {
        <<módulo>>
        +RAIZ : Path
        +carregar_env(caminho: Path) None
        +config_banco() ConfigBanco | None
        +conectar(cfg, autocommit) Connection
    }
    class ConfigBanco {
        <<dataclass frozen>>
        +host : str
        +porta : int
        +banco : str
        +usuario : str
        +senha : str
    }
    class parser {
        <<módulo>>
        +CENTAVO : Decimal
        +PAIS_POR_TRIBUTO : dict
        +COMPONENTE_POR_SUFIXO : dict
        +para_decimal(texto, campo) Decimal
        +classificar(codigo_original, ano) Classificacao | None
        +interpretar(linha, linha_origem) LinhaReceita
        +conciliar(linhas) list
        -_vigencia(ano) str
    }
    class ErroValidacao {
        <<exception>>
    }
    class ValueError
    class Classificacao {
        <<dataclass frozen>>
        +tributo : str
        +papel : str
        +componente : str | None
        +codigo_pai : str | None
    }
    class LinhaReceita {
        <<dataclass>>
        +linha_origem : int
        +orgao : int
        +ano : int
        +mes : int
        +codigo_original : str
        +valor_orcado : Decimal
        +valor_arrecadado_mes : Decimal
        +avisos : list~str~
    }
    class carregar_receita {
        <<módulo>>
        +VERSAO_PARSER : str
        +sha256_arquivo(caminho) str
        +ler_csv(caminho) list
        +carregar(caminho, conexao=None, descricao=None) ResumoCarga
        -_executar_carga(cur, caminho, sha, registros, descricao) ResumoCarga
        -_registrar_snapshot(cur, caminho, sha, total, descricao) int
        -_gravar_staging(cur, id_snap, registros) None
        -_interpretar_registros(cur, id_snap, registros) tuple
        -_registrar_conciliacao(cur, id_snap, mapeadas) int
        -_publicar(cur, id_snap, linhas) None
        -_publicar_orgaos(cur, linhas) None
        -_publicar_contas(cur, id_snap, linhas) dict
        -_publicar_valores(cur, ids, linhas) None
    }
    class ResumoCarga {
        <<dataclass>>
        +id_snapshot : int
        +ja_existia : bool
        +linhas_lidas : int
        +componentes : int
        +totais : int
        +nao_mapeadas : int
        +erros : int
        +divergencias : int
    }
    class sql_runner {
        <<módulo>>
        +comandos(texto) list~str~
        +executar_arquivo(conexao, caminho) int
        +preparar_banco(conexao, com_seed) None
    }
    class relatorio_validacao {
        <<módulo>>
        +blocos(texto) list
        +formatar(v) str
        +gerar(conexao, destino) int
        +main() None
        -_tabela(colunas, linhas) list~str~
    }
    class amostra {
        <<módulo>>
        +extrair(origem, destino) int
    }

    ValueError <|-- ErroValidacao
    config ..> ConfigBanco : cria
    parser ..> ErroValidacao : lança
    parser ..> LinhaReceita : cria
    LinhaReceita "*" --> "0..1" Classificacao : classificacao
    carregar_receita ..> parser : usa
    carregar_receita ..> config : conectar
    carregar_receita ..> ResumoCarga : devolve
    sql_runner ..> config : conectar
    relatorio_validacao ..> sql_runner : comandos
    relatorio_validacao ..> config : conectar
```

`LinhaReceita` aparece com os atributos principais; o conjunto completo tem 12 campos (`etl/parser.py`).

### 4.1 Princípios de projeto aplicados

| Princípio (ESM, cap. 5) | Onde aparece |
|---|---|
| **Coesão** (§5.4, p. 12) | Cada módulo tem uma responsabilidade: `parser` valida e classifica, `carregar_receita` persiste, `sql_runner` executa scripts, `relatorio_validacao` documenta |
| **Acoplamento** (§5.5, p. 13) | O `parser` não conhece banco nem configuração. Isso não é só convenção: é um **contrato verificado automaticamente** pelo import-linter (gate G8) |
| **Ocultamento de informação** (§5.3, p. 6) | A carga expõe só `carregar()`; os 11 passos internos são privados (`_executar_carga`, `_publicar_contas`…) |
| **Arquitetura em camadas** (ESM cap. 7, §7.2, p. 4) | Camadas verificadas pelo import-linter: `relatorio_validacao · carregar_receita · amostra` → `sql_runner` → `config · parser`. Uma camada só usa as de baixo |
| **Código aberto a customizações por injeção de dependência** (*Fundamentos de Manutenção de Software*, cap. 4, §4.4, p. 12–15) | `carregar(caminho, conexao=None)` e `gerar(conexao, destino)` recebem a conexão de fora. Os testes injetam a conexão do banco de teste, e a mesma função atende o uso real |

```mermaid
flowchart TB
    subgraph C1["Camada de aplicação"]
        RV[relatorio_validacao]
        CR[carregar_receita]
        AM[amostra]
    end
    subgraph C2["Camada de execução SQL"]
        SR[sql_runner]
    end
    subgraph C3["Camada base"]
        CF[config]
        PA[parser]
    end
    RV --> SR
    RV --> CF
    CR --> CF
    CR --> PA
    SR --> CF
    PA -. "proibido: pymysql, config, carregar_receita, sql_runner" .-x CF
```

### 4.2 Métricas do código (medidas pelos quality gates)

O ESM, §5.7 (p. 33–38), apresenta métricas de tamanho, coesão, acoplamento e complexidade, e adverte que **não devem ser tratadas como metas**, e sim como indicadores. Nos gates, elas funcionam como limite de alerta:

| Métrica | Medida atual | Limite do gate |
|---|---|---|
| Complexidade ciclomática por função (§5.7.4, p. 38) | máx. 10, média 2,8 | ≤ 10 |
| Tamanho (§5.7.1) | maior módulo 162 SLOC; maior função 38 linhas | ≤ 250 SLOC; ≤ 50 linhas |
| Acoplamento entre módulos | 4/4 contratos de dependência mantidos | todos |

A complexidade de `carregar()` era **18** antes da refatoração por extração de método (ESM cap. 9, §9.2.1, p. 4); hoje a função mais complexa da carga tem complexidade 6.

**Referências:** ESM cap. 4 §4.3 (p. 8–16); cap. 5 §5.3–5.5 (p. 6–13) e §5.7 (p. 33–38); cap. 7 §7.2 (p. 4); cap. 9 §9.2.1 (p. 4). *Fundamentos de Manutenção de Software*, cap. 4 §4.4 (p. 12–15). Manual do MySQL 8.4 (restrições `CHECK` e `FOREIGN KEY`).
