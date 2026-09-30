# Quality gates

Gerado por `python scripts/quality_gate.py` em 30/09/2026 12:04. A integração (merge) só é permitida com todos os gates aprovados.

| Gate | Verificação | Limite | Obtido | Situação |
|---|---|---|---|---|
| G1 | Testes unitários | 100% passando, nenhum ignorado | 163/163 | ✅ passou |
| G2 | Testes de integração (MySQL) | 100% passando, nenhum ignorado | 15/15 | ✅ passou |
| G3 | Testes de aceitação (Gherkin) | 100% passando, nenhum ignorado | 13/13 | ✅ passou |
| G4 | Cobertura de linhas e ramos | total ≥ 90%, cada módulo ≥ 80% | 97.4% | ✅ passou |
| G5 | Complexidade ciclomática | ≤ 10 por função | máx. 10 (interpretar), média 2.8 | ✅ passou |
| G6 | Índice de manutenibilidade | ≥ 20 por módulo | mín. 43.6 (carregar_receita.py) | ✅ passou |
| G7 | Tamanho de módulos e funções | módulo ≤ 250 SLOC, função ≤ 50 linhas | maior módulo 162 SLOC; maior função 38 linhas | ✅ passou |
| G8 | Controle de dependências (import-linter) | todos os contratos mantidos | 4/4 contratos | ✅ passou |
| G9 | Verificação de tipos (Pyright) | 0 erros no código de produção | 0 erro(s) | ✅ passou |
| G10 | Testes de mutação | score ≥ 80% em cada módulo | 91.7% (727/793 mortos, nesta rodada) | ✅ passou |
