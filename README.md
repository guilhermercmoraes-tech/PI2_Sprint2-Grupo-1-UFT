# PI2 — Inteligência Tributária de Palmas

Projeto Integrador do Eixo II (BIINAR/UFT, 2026/2), Opção D. Sistema de apoio ao planejamento da arrecadação e à priorização da cobrança da dívida ativa de Palmas-TO, com IA de escopo territorial.

## Estrutura

```text
docs/        requisitos e UML, modelagem ER (3FN), arquitetura de dados, E3, validação
sql/         schema.sql (MySQL 8.4), dados_referencia.sql, seed_sintetico.sql, validacao.sql
etl/         amostra, parser/validação, carga idempotente, relatório de validação
src/estruturas/  grafo, tabela hash, heap de prioridade (Parte 1 da Sprint 2)
tests/       testes unitários, de integração (MySQL) e de aceitação em Gherkin (tests/aceitacao)
data/amostra/    amostra pública de 10 linhas reais (único dado versionado)
scripts/     quality gates, testes de mutação, demonstração da Parte 1 e MySQL portátil
```

## Como executar

Requisitos: Python 3.12+ e MySQL 8.4.

```bash
python -m pip install -r requirements-dev.txt   # execução + testes + quality gates
cp .env.example .env                            # preencher DB_PASSWORD e DB_NAME_TESTE
```

Só para executar o ETL, sem testes, basta `requirements.txt`.

Criar os bancos e o usuário da aplicação (uma vez, como root):

```sql
CREATE DATABASE pi2_tributario CHARACTER SET utf8mb4;
CREATE DATABASE pi2_tributario_teste CHARACTER SET utf8mb4;
CREATE USER 'pi2_app'@'127.0.0.1' IDENTIFIED BY '<senha forte>';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, INDEX, REFERENCES, CREATE VIEW, SHOW VIEW
  ON pi2_tributario.* TO 'pi2_app'@'127.0.0.1';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, INDEX, REFERENCES, CREATE VIEW, SHOW VIEW
  ON pi2_tributario_teste.* TO 'pi2_app'@'127.0.0.1';
```

O host `127.0.0.1` é o mesmo de `DB_HOST` no `.env`. Separar um usuário só de leitura e escrita (sem `CREATE`, `DROP` e `ALTER`) para a aplicação é pendência registrada em `docs/PROTOCOLOS_SEGURANCA_AUDITORIA.md` (A5).

Pipeline:

```bash
python -m etl.amostra "<caminho>/receita_acessoinformacao (1).csv"   # gera data/amostra (já versionada)
python -m etl.sql_runner                                             # recria esquema + referência + semente sintética
python -m etl.carregar_receita data/amostra/receita_amostra_10.csv   # valida o contrato e publica ou reprova; idempotente
python -m etl.relatorio_validacao                                    # executa sql/validacao.sql → docs/validacao.md
python -m pytest                                                     # todos os testes
```

`python -m etl.sql_runner` **apaga e recria** as tabelas do banco configurado em `DB_NAME`.

## Quality gates

Toda etapa de desenvolvimento e toda integração passa pelos mesmos gates (detalhes em `docs/REQUISITOS_UML.md` §23):

```bash
python scripts/quality_gate.py             # G1–G9: testes, cobertura, complexidade, tamanho, dependências, tipos
python scripts/quality_gate.py --mutacao   # inclui G10: testes de mutação (lento: de 7 a 20 min, conforme a máquina)
```

O script grava `docs/qualidade.md` e termina com código 1 se algum gate falhar. No GitHub, `.github/workflows/qualidade.yml` roda G1–G9 em cada push para a `main` e G1–G10, com mutação, toda segunda-feira e sob demanda (aba Actions → Run workflow). O repositório usa só a `main`, com desenvolvimento baseado no tronco: cada integração passa pelos gates (ver `docs/parte4/README.md`).

## Dados

- **Reais:** receita do portal de transparência de Palmas. Neste estágio, só a amostra de 10 linhas (IPTU e ISSQN, jan/2025, órgão 2798).
- **Sintéticos:** todo o módulo operacional (sujeitos, créditos, imóveis, pagamentos, negociação), marcado `origem_dado = 'SINTETICO'`. Os dados públicos não contêm devedores nem dívidas individuais.
- Nenhum dado pessoal, credencial ou base completa é versionado.

## Documentos

- [Como o sistema funciona](docs/COMO_O_SISTEMA_FUNCIONA.md) — fluxo de trabalho com diagramas e referências por etapa
- [Requisitos e UML](docs/REQUISITOS_UML.md)
- [Modelagem ER e 3FN](docs/modelagem_er.md)
- [Arquitetura de dados (Parte 1)](docs/arquitetura_dados.md)
- [Parte 1 por estrutura: grafo, heap e tabela hash](docs/parte1/README.md) — explicação, Big-O, código, execução e testes
- [Parte 2: ER em 3FN, banco implementado e populado, consultas de validação](docs/parte2/README.md) — um documento por critério, com diagramas de classes
- [Parte 3: E3 — integração segura com a fonte](docs/parte3/README.md) — HTTPS verificado, protocolos e credenciais
- [Parte 4: E4 — relatório da sprint](docs/parte4/README.md) — SPRINT2.md, divisão de trabalho e [diário de bordo](docs/DIARIO_DE_BORDO.md)
- [Integração segura (E3)](docs/E3_integracao_segura.md)
- [Protocolos de segurança de conexão e auditoria](docs/PROTOCOLOS_SEGURANCA_AUDITORIA.md)
- [Validação SQL](docs/validacao.md)
- [Quality gates](docs/qualidade.md) e [testes de mutação](docs/mutacao.md)
- [Relatório da Sprint 2](SPRINT2.md)
