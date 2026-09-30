# PI2 — Inteligência Tributária de Palmas

Projeto Integrador do Eixo II (BIINAR/UFT, 2026/2), Opção D. Sistema de apoio ao planejamento da arrecadação e à priorização da cobrança da dívida ativa de Palmas-TO, com IA de escopo territorial.

## Estrutura

```text
docs/        requisitos e UML, modelagem ER (3FN), arquitetura de dados, E3, validação
sql/         schema.sql (MySQL 8.4), dados_referencia.sql, seed_sintetico.sql, validacao.sql
etl/         amostra, parser/validação, carga idempotente, relatório de validação
src/estruturas/  grafo, tabela hash, heap de prioridade (Parte 1 da Sprint 2)
tests/       testes unitários e de integração (pytest)
data/amostra/    amostra pública de 10 linhas reais (único dado versionado)
scripts/     utilitários locais (MySQL portátil)
```

## Como executar

Requisitos: Python 3.12+ e MySQL 8.4.

```bash
python -m pip install -r requirements.txt
cp .env.example .env          # preencher DB_PASSWORD, PSEUDONIMO_SAL e DB_NAME_TESTE
```

Criar os bancos e o usuário da aplicação (uma vez, como root):

```sql
CREATE DATABASE pi2_tributario CHARACTER SET utf8mb4;
CREATE DATABASE pi2_tributario_teste CHARACTER SET utf8mb4;
CREATE USER 'pi2_app'@'localhost' IDENTIFIED BY '<senha forte>';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, INDEX, REFERENCES, CREATE VIEW, SHOW VIEW
  ON pi2_tributario.* TO 'pi2_app'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, INDEX, REFERENCES, CREATE VIEW, SHOW VIEW
  ON pi2_tributario_teste.* TO 'pi2_app'@'localhost';
```

Pipeline:

```bash
python -m etl.amostra "<caminho>/receita_acessoinformacao (1).csv"   # gera data/amostra (já versionada)
python -m etl.sql_runner                                             # recria esquema + referência + semente sintética
python -m etl.carregar_receita data/amostra/receita_amostra_10.csv   # carga idempotente (SHA-256)
python -m etl.relatorio_validacao                                    # executa sql/validacao.sql → docs/validacao.md
python -m pytest                                                     # todos os testes
```

`python -m etl.sql_runner` **apaga e recria** as tabelas do banco configurado em `DB_NAME`.

## Quality gates

Toda etapa de desenvolvimento e toda integração passa pelos mesmos gates (detalhes em `docs/REQUISITOS_UML.md` §23):

```bash
python -m pip install -r requirements-dev.txt
python scripts/quality_gate.py             # G1–G9: testes, cobertura, complexidade, tamanho, dependências, tipos
python scripts/quality_gate.py --mutacao   # inclui G10: testes de mutação (~20 min)
```

O script grava `docs/qualidade.md` e termina com código 1 se algum gate falhar. No GitHub, `.github/workflows/qualidade.yml` roda G1–G9 em cada push e G1–G10 em cada pull request para `main`.

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
