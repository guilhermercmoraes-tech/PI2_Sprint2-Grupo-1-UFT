"""Extrai a amostra de 10 linhas usada no desenvolvimento da Sprint 2.

Critério (determinístico e reproduzível): órgão 2798 (Tesouro Municipal),
competência jan/2025, contas-pai de IPTU (1112500) e ISSQN (1114511) e
seus quatro componentes. Assim a amostra permite testar a conciliação
pai = soma dos filhos sem carregar as 176.993 linhas do arquivo.

Uso:
    python -m etl.amostra "<caminho>/receita_acessoinformacao (1).csv"
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "data" / "amostra" / "receita_amostra_10.csv"

ORGAO = "2798"
ANO = "2025"
MES = "1"
PAIS = ("1112500", "1114511")
CODIGOS = {p + s for p in PAIS for s in ("", "1", "2", "3", "4")}


def extrair(origem: Path, destino: Path = SAIDA) -> int:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(origem, encoding="utf-8-sig", newline="") as f:
        leitor = csv.DictReader(f, delimiter=";")
        campos = list(leitor.fieldnames or []) + ["linha_origem"]
        linhas = []
        # linha 1 do arquivo é o cabeçalho; a primeira linha de dados é a 2
        for numero, linha in enumerate(leitor, start=2):
            if (linha["orgao"] == ORGAO and linha["ano"] == ANO and linha["mes"] == MES
                    and linha["codigo_original"] in CODIGOS):
                linha["linha_origem"] = str(numero)
                linhas.append(linha)
    linhas.sort(key=lambda l: l["codigo_original"])
    with open(destino, "w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=campos, delimiter=";")
        escritor.writeheader()
        escritor.writerows(linhas)
    return len(linhas)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    total = extrair(Path(sys.argv[1]))
    print(f"{total} linhas gravadas em {SAIDA}")
