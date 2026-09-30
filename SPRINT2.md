# Sprint 2 — Arquitetura de Dados e Banco (15/09 a 02/10/2026)

## O que foi feito

- **Parte 1 — estruturas de dados:** grafo (lista de adjacência), tabela hash (encadeamento separado) e heap binária com fila de prioridade versionada, implementadas do zero, com análise Big-O e um documento por estrutura ([docs/parte1/](docs/parte1/README.md)). A tabela hash passou a usar capacidade prima, depois que um teste revelou chaves concentradas num único *bucket*.
- **Parte 2 — banco:** modelo ER em 3FN com 43 tabelas e 3 views em MySQL 8.4 ([docs/modelagem_er.md](docs/modelagem_er.md), [sql/schema.sql](sql/schema.sql)). Carga idempotente de **dados reais** (amostra de 10 linhas do portal de transparência) com linhagem até a linha do CSV. 16 consultas de validação executadas e documentadas ([docs/validacao.md](docs/validacao.md)). Evidências por critério em [docs/parte2/](docs/parte2/README.md).
- **E3:** HTTPS verificado nos dois hosts (certificados válidos, TLS 1.2 e 1.3) e protocolos de conexão e auditoria fundamentados em Kurose ([docs/parte3/](docs/parte3/README.md)).
- **Testes e qualidade:** 191 testes (163 unitários, 15 de integração com MySQL, 13 cenários Gherkin) e 10 quality gates aprovados: cobertura 97%, mutação 91,7%, complexidade ≤ 10, dependências e tipos ([docs/qualidade.md](docs/qualidade.md)). Configurados para rodar em cada push no GitHub Actions (workflow ainda não executado: o repositório não está no GitHub).

## Decisões de modelagem

1. **Dois módulos:** receita observada (dados reais) e domínio operacional (estrutura com dados sintéticos identificados). Os CSVs públicos não têm devedores, dívidas, vencimentos nem localização.
2. **Conta-pai ≠ componente:** só os 4 componentes são somados; o total da conta-pai fica em tabela de conferência. Somar tudo duplicaria a receita (verificado na amostra).
3. **Snapshot com SHA-256:** reimportar o mesmo arquivo não cria receita nova.
4. **Nenhum valor derivado persistido:** saldo, valor venal total e arrecadado por tributo são views.
5. **Dinheiro em DECIMAL; códigos como texto;** orçamento guardado uma vez por vigência, não por mês.
6. **Uma negociação ativa por crédito** garantida pela PK de `credito_em_negociacao`.
7. **Pseudonimização** de CPF/CNPJ com sal secreto; não tratada como anonimização.

## Divisão de trabalho

| Integrante | Frente | Entregáveis |
|---|---|---|
| _(nome)_ | 1 — Modelagem ER e 3FN | `docs/modelagem_er.md`, diagramas ER |
| _(nome)_ | 2 — Esquema MySQL | `sql/schema.sql`, `sql/dados_referencia.sql` |
| _(nome)_ | 3 — ETL e LGPD | `etl/`, `data/amostra/` |
| _(nome)_ | 4 — Estruturas de dados | `src/estruturas/`, `tests/test_{grafo,heap,indice_hash}.py` |
| _(nome)_ | 5 — Validação, E3 e relatório | `sql/validacao.sql`, `docs/validacao.md`, `docs/parte3/`, este arquivo, [diário de bordo](docs/DIARIO_DE_BORDO.md) |

## Impedimentos levados para a Sprint 3

1. **Dados de dívida ativa:** sem créditos, pagamentos e inscrições da Sefin, o módulo operacional só tem dados sintéticos. Pedido institucional descrito em PA-12.
2. **Escopo do score (PA-14):** o enunciado pede score individual de recuperabilidade; o modelo prioriza o território. Decisão pendente com o professor.
3. **Portal NUCLEOGOV respondeu 403** a partir da rede de teste; faltam os caminhos exatos dos endpoints usados na extração de 07/07/2026.
4. **Carga completa:** validar o pipeline com as 176.993 linhas e com a base histórica (`receita_palmas.csv`, cujos meses de 2016–2018 repetem o valor anual).
5. **Entrega no GitHub:** commits, branch `sprint2`, pull request e primeira execução do workflow de qualidade (guia em `planejamento/`).
