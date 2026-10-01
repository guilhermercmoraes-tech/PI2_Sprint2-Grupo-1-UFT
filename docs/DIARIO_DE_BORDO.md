# Diário de bordo — Sprint 2

Registro das atividades da Sprint 2 (15/09 a 02/10/2026), com a evidência de cada uma no repositório.

> **Como preencher:** cada integrante completa a coluna **Integrante(s)** e acrescenta suas próprias linhas (reuniões, pesquisas, revisões de commits). As linhas já registradas descrevem trabalho feito neste repositório, com assistência de um agente de IA (Claude Code), conforme declarado em `docs/parte2/5_manutencao_e_qualidade.md` §9.

| Data | Atividade | Integrante(s) | Evidência |
|---|---|---|---|
| 15/09 a 28/09 | *(atividades anteriores: reuniões, Documento de Arquitetura de Dados da Parte 1, protótipos individuais)* | _(preencher)_ | _(preencher)_ |
| 29/09 | Plano de implementação da sprint em formato de pipeline (E0–E7) | _(preencher)_ | `planejamento/Plano_Implementacao_Sprint2_Pipeline.pdf` |
| 29/09 | Revisão do documento de requisitos e UML (v2.0) com base na Nota Técnica | _(preencher)_ | `docs/REQUISITOS_UML.md` §0.1 |
| 29/09 | Esquema MySQL em 3FN (43 tabelas, 3 views), dados de referência e semente sintética | _(preencher)_ | `sql/schema.sql`, `sql/dados_referencia.sql`, `sql/seed_sintetico.sql` |
| 29/09 | Extração da amostra real (10 linhas) e carga idempotente com SHA-256 | _(preencher)_ | `etl/amostra.py`, `etl/carregar_receita.py` |
| 29/09 | Grafo, tabela hash e heap com testes (Parte 1) | _(preencher)_ | `src/estruturas/`, `tests/` |
| 29/09 | 16 consultas de validação e relatório automático | _(preencher)_ | `sql/validacao.sql`, `docs/validacao.md` |
| 29/09 | Documento E3 e verificação de HTTPS dos portais | _(preencher)_ | `docs/E3_integracao_segura.md` |
| 30/09 | Conferência das estruturas com Rosen, Lintzmayer & Mota e Gersting | _(preencher)_ | `docs/arquitetura_dados.md`, `docs/parte1/` |
| 30/09 | Protocolos de segurança de conexão e auditoria (Kurose & Ross) | _(preencher)_ | `docs/PROTOCOLOS_SEGURANCA_AUDITORIA.md` |
| 30/09 | Quality gates: testes Gherkin, cobertura, mutação, complexidade, dependências e tipos; refatoração de `carregar()` | _(preencher)_ | `scripts/quality_gate.py`, `docs/qualidade.md`, `.github/workflows/qualidade.yml` |
| 30/09 | Relatório do fluxo do sistema com diagramas e referências por etapa; UML v2.2 | _(preencher)_ | `docs/COMO_O_SISTEMA_FUNCIONA.md`, `docs/REQUISITOS_UML.md` |
| 30/09 | Documentos da Parte 1 por estrutura; correção da tabela hash (capacidade prima) | _(preencher)_ | `docs/parte1/`, `tests/test_indice_hash.py` |
| 30/09 | Documentos da Parte 2 (critérios), E3 e E4; nova verificação de TLS dos portais | _(preencher)_ | `docs/parte2/`, `docs/parte3/`, `docs/parte4/` |
| 30/09 | Repositório Git com commits por frente, direto na `main` (decisão da equipe: repositório novo, sem fork nem branch) | _(preencher)_ | `git log` |
| 01/10 | Revisão de consonância das Partes 1 a 4 com o código, reexecutando testes, banco, demonstrações, diagramas e mutação | _(preencher)_ | `REVISAO_CONSONANCIA_01-10-2026.md` |
| 01/10 | Correções: fila de prioridade (ação reinserida voltava com a prioridade antiga); contrato do arquivo antes da publicação, com snapshot `PUBLICADO`/`REJEITADO`; testes de propriedade; 3 lacunas que a mutação dava como equivalentes; verificador de sobreviventes; consultas V17 e V18; 3FN com as redundâncias controladas declaradas; escopo de permissão como chave estrangeira; README instalável; CI para a `main` única | _(preencher)_ | histórico do Git; `docs/qualidade.md`; `docs/mutacao.md` |
| 01/10 | Repositório publicado no GitHub, só com a `main` (14 commits); primeira execução dos quality gates no GitHub Actions: G1–G9 aprovados | _(preencher)_ | [github.com/guilhermercmoraes-tech/PI2_Sprint2-Grupo-1-UFT](https://github.com/guilhermercmoraes-tech/PI2_Sprint2-Grupo-1-UFT); [execução no Actions](https://github.com/guilhermercmoraes-tech/PI2_Sprint2-Grupo-1-UFT/actions/runs/36899758668) |
| _(a fazer)_ | Envio do link à coordenação (até 02/10, 23h59) | _(preencher)_ | — |
