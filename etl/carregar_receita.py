"""Carga do CSV de receita (portal NUCLEOGOV) no MySQL.

Etapas (Relatório de Auditoria, p. 9): registrar snapshot por SHA-256 →
staging textual → interpretar e validar → classificar pelo mapeamento
aprovado → publicar em transação única. Reexecutar com o mesmo arquivo
não duplica dados (idempotência pelo hash).

Uso:
    python -m etl.carregar_receita data/amostra/receita_amostra_10.csv
"""
from __future__ import annotations

import csv
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

from etl.config import conectar
from etl.parser import Classificacao, ErroValidacao, LinhaReceita, conciliar, interpretar

VERSAO_PARSER = "0.1.0"
CAMPOS_STG = ("total", "orgao_nome", "unidade_nome", "codigo", "orgao", "ano", "mes", "descricao",
              "valor_orcado", "valor_arrecado_mes", "valor_arrecado_periodo", "covid",
              "unidade_id", "codigo_original")


@dataclass
class ResumoCarga:
    id_snapshot: int
    ja_existia: bool
    linhas_lidas: int
    componentes: int
    totais: int
    nao_mapeadas: int
    erros: int
    divergencias: int


def sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def ler_csv(caminho: Path) -> list[tuple[int, dict[str, str]]]:
    """Lê o CSV; usa a coluna linha_origem (amostra) ou o número da linha no arquivo."""
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        leitor = csv.DictReader(f, delimiter=";")
        return [(int(l["linha_origem"]) if l.get("linha_origem") else n, l)
                for n, l in enumerate(leitor, start=2)]


def carregar(caminho: Path, conexao=None, descricao: str | None = None) -> ResumoCarga:
    """Carrega o CSV em transação única; se o SHA-256 já existe, não grava nada."""
    caminho = Path(caminho)
    sha = sha256_arquivo(caminho)
    registros = ler_csv(caminho)
    propria = conexao is None
    con = conexao or conectar()
    try:
        with con.cursor() as cur:
            cur.execute("SELECT id_snapshot FROM fonte_snapshot WHERE sha256 = %s", (sha,))
            existente = cur.fetchone()
            if existente:
                return _resumo_existente(cur, existente[0], len(registros))
            resumo = _executar_carga(cur, caminho, sha, registros, descricao)
        con.commit()
        return resumo
    except Exception:
        con.rollback()
        raise
    finally:
        if propria:
            con.close()


def _executar_carga(cur, caminho: Path, sha: str, registros, descricao) -> ResumoCarga:
    id_snap = _registrar_snapshot(cur, caminho, sha, len(registros), descricao)
    _gravar_staging(cur, id_snap, registros)
    validas, erros = _interpretar_registros(cur, id_snap, registros)
    if erros:
        # Erro de contrato interrompe a promoção: nada além do staging é publicado.
        return ResumoCarga(id_snap, False, len(registros), 0, 0, 0, erros, 0)
    mapeadas = [l for l in validas if l.classificacao is not None]
    _publicar(cur, id_snap, mapeadas)
    divergencias = _registrar_conciliacao(cur, id_snap, mapeadas)
    componentes = sum(1 for l in mapeadas if _classe(l).papel == "COMPONENTE")
    return ResumoCarga(id_snap, False, len(registros), componentes, len(mapeadas) - componentes,
                       len(validas) - len(mapeadas), 0, divergencias)


def _registrar_snapshot(cur, caminho: Path, sha: str, total: int, descricao) -> int:
    cur.execute(
        "INSERT INTO fonte_snapshot (sha256, nome_arquivo, tamanho_bytes, total_linhas,"
        " versao_parser, descricao) VALUES (%s,%s,%s,%s,%s,%s)",
        (sha, caminho.name, caminho.stat().st_size, total, VERSAO_PARSER, descricao))
    return cur.lastrowid


def _gravar_staging(cur, id_snap: int, registros) -> None:
    cur.executemany(
        f"INSERT INTO stg_receita_atual (id_snapshot, linha_origem, {', '.join(CAMPOS_STG)})"
        f" VALUES (%s, %s, {', '.join(['%s'] * len(CAMPOS_STG))})",
        [(id_snap, n, *[l.get(c) for c in CAMPOS_STG]) for n, l in registros])


def _interpretar_registros(cur, id_snap: int, registros) -> tuple[list[LinhaReceita], int]:
    """Valida cada linha e registra erros, avisos e contas não mapeadas."""
    validas: list[LinhaReceita] = []
    erros = 0
    for n, bruto in registros:
        try:
            linha = interpretar(bruto, n)
        except ErroValidacao as exc:
            erros += 1
            _validacao(cur, id_snap, "CONTRATO_ENTRADA", "ERRO", n, str(exc))
            continue
        for aviso in linha.avisos:
            _validacao(cur, id_snap, "QUALIDADE", "AVISO", n, aviso)
        if linha.classificacao is None:
            _validacao(cur, id_snap, "CONTA_NAO_MAPEADA", "INFO", n,
                       f"código {linha.codigo_original} permanece só no staging")
        validas.append(linha)
    return validas, erros


def _registrar_conciliacao(cur, id_snap: int, mapeadas: list[LinhaReceita]) -> int:
    divergencias = conciliar(mapeadas)
    for (orgao, ano, mes, pai), total, soma in divergencias:
        _validacao(cur, id_snap, "CONCILIACAO_PAI_FILHOS", "ERRO", None,
                   f"órgão {orgao} {ano}-{mes:02d} conta {pai}: total {total} ≠ soma {soma}")
    if not divergencias:
        _validacao(cur, id_snap, "CONCILIACAO_PAI_FILHOS", "INFO", None,
                   "todas as contas-pai conferem com a soma dos componentes")
    return len(divergencias)


def _publicar(cur, id_snap: int, linhas: list[LinhaReceita]) -> None:
    _publicar_orgaos(cur, linhas)
    ids = _publicar_contas(cur, id_snap, linhas)
    _publicar_valores(cur, ids, linhas)


def _publicar_orgaos(cur, linhas: list[LinhaReceita]) -> None:
    for orgao in {(l.orgao, l.orgao_nome) for l in linhas}:
        cur.execute("INSERT INTO orgao (codigo_orgao, nome) VALUES (%s, %s)"
                    " ON DUPLICATE KEY UPDATE codigo_orgao = codigo_orgao", orgao)


def _publicar_contas(cur, id_snap: int, linhas: list[LinhaReceita]) -> dict[tuple, int]:
    """Insere as contas (pais antes dos componentes) e devolve (ano, órgão, código) → id_conta."""
    ids: dict[tuple, int] = {}
    ordenadas = sorted(linhas, key=lambda l: _classe(l).papel != "TOTAL")
    for l in ordenadas:
        c = _classe(l)
        chave = (l.ano, l.orgao, l.codigo_original)
        if chave in ids:
            continue
        id_pai = ids[(l.ano, l.orgao, c.codigo_pai)] if c.papel == "COMPONENTE" else None
        cur.execute(
            "INSERT INTO conta_receita (id_snapshot, ano, codigo_orgao, codigo_original,"
            " codigo_formatado, papel, codigo_tributo, codigo_componente, id_conta_pai)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (id_snap, l.ano, l.orgao, l.codigo_original, l.codigo_formatado, c.papel,
             c.tributo, c.componente, id_pai))
        ids[chave] = cur.lastrowid
    return ids


def _publicar_valores(cur, ids: dict[tuple, int], linhas: list[LinhaReceita]) -> None:
    """Grava os valores mensais e o orçamento, este só quando o valor muda."""
    orcamento_vigente: dict[int, object] = {}
    for l in sorted(linhas, key=lambda x: (x.ano, x.orgao, x.codigo_original, x.mes)):
        id_conta = ids[(l.ano, l.orgao, l.codigo_original)]
        tabela = "total_informado_mensal" if _classe(l).papel == "TOTAL" else "receita_componente_mensal"
        cur.execute(f"INSERT INTO {tabela} (id_conta, mes, valor_arrecadado, descricao_bruta, linha_origem)"
                    " VALUES (%s,%s,%s,%s,%s)",
                    (id_conta, l.mes, l.valor_arrecadado_mes, l.descricao or None, l.linha_origem))
        if orcamento_vigente.get(id_conta) != l.valor_orcado:
            cur.execute("INSERT INTO orcamento_informado (id_conta, mes_inicio, valor_orcado)"
                        " VALUES (%s,%s,%s)", (id_conta, l.mes, l.valor_orcado))
            orcamento_vigente[id_conta] = l.valor_orcado


def _classe(linha: LinhaReceita) -> Classificacao:
    """Classificação de uma linha já filtrada como mapeada."""
    if linha.classificacao is None:
        raise ValueError(f"linha {linha.linha_origem} sem classificação")
    return linha.classificacao


def _validacao(cur, id_snap, regra, gravidade, linha, evidencia) -> None:
    cur.execute("INSERT INTO resultado_validacao (id_snapshot, regra, gravidade, linha_origem, evidencia)"
                " VALUES (%s,%s,%s,%s,%s)", (id_snap, regra, gravidade, linha, evidencia[:500]))


def _resumo_existente(cur, id_snap: int, lidas: int) -> ResumoCarga:
    cur.execute("SELECT papel, COUNT(*) FROM conta_receita WHERE id_snapshot = %s GROUP BY papel", (id_snap,))
    por_papel = dict(cur.fetchall())
    return ResumoCarga(id_snap, True, lidas, por_papel.get("COMPONENTE", 0), por_papel.get("TOTAL", 0),
                       0, 0, 0)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    r = carregar(Path(sys.argv[1]), descricao="Amostra Sprint 2")
    if r.ja_existia:
        print(f"Snapshot {r.id_snapshot} já carregado (mesmo SHA-256): nada foi duplicado.")
    else:
        print(f"Snapshot {r.id_snapshot}: {r.linhas_lidas} linhas lidas · {r.componentes} componentes · "
              f"{r.totais} totais · {r.nao_mapeadas} não mapeadas · {r.erros} erros · "
              f"{r.divergencias} divergências de conciliação")
