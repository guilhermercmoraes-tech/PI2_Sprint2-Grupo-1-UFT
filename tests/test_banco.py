"""Testes de integração com MySQL. Usam o banco DB_NAME_TESTE, que é recriado.

São ignorados se o .env não tiver DB_PASSWORD e DB_NAME_TESTE.
"""
import os
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pymysql
import pytest

from etl.carregar_receita import carregar
from etl.config import conectar, config_banco
from etl.sql_runner import comandos, preparar_banco

pytestmark = pytest.mark.integracao

RAIZ = Path(__file__).resolve().parent.parent
AMOSTRA = RAIZ / "data" / "amostra" / "receita_amostra_10.csv"


@pytest.fixture(scope="module")
def con():
    cfg = config_banco()
    nome_teste = os.environ.get("DB_NAME_TESTE")
    if cfg is None or not nome_teste:
        pytest.skip("MySQL de teste não configurado no .env")
    c = conectar(replace(cfg, banco=nome_teste))
    preparar_banco(c, com_seed=True)
    carregar(AMOSTRA, conexao=c)
    yield c
    c.close()


def um(con, sql, params=()):
    with con.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def rejeita(con, codigo_erro, *sqls):
    """Executa os comandos e exige que o último falhe com o código MySQL esperado."""
    with pytest.raises(pymysql.MySQLError) as erro:
        with con.cursor() as cur:
            for sql in sqls:
                cur.execute(sql)
    con.rollback()
    assert erro.value.args[0] == codigo_erro, erro.value.args


def todos(con, sql, params=()):
    with con.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def test_carga_da_amostra(con):
    assert um(con, "SELECT COUNT(*) FROM stg_receita_atual")[0] == 10
    assert um(con, "SELECT COUNT(*) FROM receita_componente_mensal")[0] == 8
    assert um(con, "SELECT COUNT(*) FROM total_informado_mensal")[0] == 2


def test_recarga_e_idempotente(con):
    r = carregar(AMOSTRA, conexao=con)
    assert r.ja_existia
    assert um(con, "SELECT COUNT(*) FROM fonte_snapshot")[0] == 1
    assert um(con, "SELECT COUNT(*) FROM receita_componente_mensal")[0] == 8


def test_conciliacao_sem_divergencia(con):
    linhas = todos(con, "SELECT codigo_tributo, total_informado, soma_componentes, componentes, diferenca"
                        " FROM v_conciliacao_pai_filhos ORDER BY codigo_tributo")
    assert linhas == (
        ("IPTU", Decimal("2885620.64"), Decimal("2885620.64"), 4, Decimal("0.00")),
        ("ISSQN", Decimal("21802997.01"), Decimal("21802997.01"), 4, Decimal("0.00")),
    )


def test_view_tributo_mes_soma_so_componentes(con):
    assert dict(todos(con, "SELECT codigo_tributo, arrecadado FROM v_tributo_mes")) == {
        "IPTU": Decimal("2885620.64"), "ISSQN": Decimal("21802997.01")}


def test_orcamento_nao_e_multiplicado(con):
    assert um(con, "SELECT COUNT(*) FROM orcamento_informado")[0] == 10
    assert um(con, "SELECT o.valor_orcado FROM orcamento_informado o JOIN conta_receita c USING (id_conta)"
                   " WHERE c.codigo_original = '1112500'")[0] == Decimal("112219000.00")


def test_fato_rejeita_conta_total(con):
    id_total = um(con, "SELECT id_conta FROM conta_receita WHERE papel = 'TOTAL' LIMIT 1")[0]
    rejeita(con, 1452, "INSERT INTO receita_componente_mensal (id_conta, mes, valor_arrecadado, linha_origem)"
                       f" VALUES ({id_total}, 2, 1.00, 1)")  # FK composta (id_conta, papel)


def test_mes_invalido_rejeitado(con):
    id_comp = um(con, "SELECT id_conta FROM conta_receita WHERE papel = 'COMPONENTE' LIMIT 1")[0]
    rejeita(con, 3819, "INSERT INTO receita_componente_mensal (id_conta, mes, valor_arrecadado, linha_origem)"
                       f" VALUES ({id_comp}, 13, 1.00, 1)")  # CHECK ck_rcm_mes


def test_uma_negociacao_ativa_por_credito(con):
    rejeita(con, 1062,  # PK de credito_em_negociacao
            "INSERT INTO negociacao (id_negociacao, data_inicio, status, origem_dado)"
            " VALUES (2, '2025-06-01', 'ATIVA', 'SINTETICO')",
            "INSERT INTO item_negociacao VALUES (2, 3)",
            "INSERT INTO credito_em_negociacao VALUES (3, 2)")
    assert um(con, "SELECT COUNT(*) FROM negociacao")[0] == 1


def test_saldo_derivado_dos_movimentos(con):
    saldos = dict(todos(con, "SELECT id_credito, saldo FROM v_saldo_credito"))
    assert saldos == {1: Decimal("0.00"), 2: Decimal("1620.00"), 3: Decimal("4400.00"),
                      4: Decimal("540.00"), 5: Decimal("7300.00")}


def test_auditoria_exige_ator_coerente(con):
    rejeita(con, 3819,  # CHECK ck_aud_ator
            "INSERT INTO registro_auditoria (id_correlacao, tipo_ator, id_usuario, id_ator_sistema,"
            " recurso_acessado, acao_executada, resultado)"
            " VALUES (UUID(), 'USUARIO', NULL, NULL, 'PLANO:1', 'CONSULTAR', 'PERMITIDO')")


def test_consultas_de_validacao_executam(con):
    texto = (RAIZ / "sql" / "validacao.sql").read_text(encoding="utf-8")
    with con.cursor() as cur:
        for cmd in comandos(texto):
            cur.execute(cmd)
            cur.fetchall()


# --- caminhos de erro e utilitários que dependem do banco ---

CAMPOS_CSV = ("total;orgao_nome;unidade_nome;codigo;orgao;ano;mes;descricao;valor_orcado;"
              "valor_arrecado_mes;valor_arrecado_periodo;covid;unidade_id;codigo_original")


def csv_temporario(tmp_path, nome, linhas):
    caminho = tmp_path / nome
    caminho.write_text(CAMPOS_CSV + "\n" + "\n".join(linhas) + "\n", encoding="utf-8-sig")
    return caminho


def test_fracao_de_centavo_interrompe_a_publicacao(con, tmp_path):
    arq = csv_temporario(tmp_path, "invalido.csv", [
        "1;TESOURO;;1.1;2798;2025;2;X;10;1.005;1.005;0;;11125001"])
    r = carregar(arq, conexao=con)
    assert (r.erros, r.componentes, r.totais) == (1, 0, 0)
    assert um(con, "SELECT COUNT(*) FROM stg_receita_atual WHERE id_snapshot = %s", (r.id_snapshot,))[0] == 1
    assert um(con, "SELECT COUNT(*) FROM conta_receita WHERE id_snapshot = %s", (r.id_snapshot,))[0] == 0
    assert um(con, "SELECT regra, gravidade FROM resultado_validacao WHERE id_snapshot = %s",
              (r.id_snapshot,)) == ("CONTRATO_ENTRADA", "ERRO")


def test_conta_nao_mapeada_e_aviso_ficam_registrados(con, tmp_path):
    arq = csv_temporario(tmp_path, "nao_mapeada.csv", [
        "1;TESOURO;;9.9;2798;2025;3;;10;5.00;6.00;0;;999999"])
    r = carregar(arq, conexao=con)
    assert (r.erros, r.nao_mapeadas, r.componentes) == (0, 1, 0)
    regras = {x[0] for x in todos(con, "SELECT regra FROM resultado_validacao WHERE id_snapshot = %s",
                                  (r.id_snapshot,))}
    assert {"CONTA_NAO_MAPEADA", "QUALIDADE"} <= regras


def test_divergencia_de_conciliacao_e_registrada(con, tmp_path):
    arq = csv_temporario(tmp_path, "divergente.csv", [
        "1;TESOURO;;1.0;2798;2024;5;IPTU;10;100.00;100.00;0;;1112500",
        "1;TESOURO;;1.1;2798;2024;5;P;10;99.00;99.00;0;;11125001"])
    r = carregar(arq, conexao=con)
    assert r.divergencias == 1
    assert um(con, "SELECT gravidade FROM resultado_validacao WHERE id_snapshot = %s"
                   " AND regra = 'CONCILIACAO_PAI_FILHOS'", (r.id_snapshot,))[0] == "ERRO"


def test_relatorio_de_validacao_executa_todos_os_blocos(con, tmp_path):
    from etl.relatorio_validacao import gerar
    destino = tmp_path / "validacao.md"
    assert gerar(con, destino) == 16
    texto = destino.read_text(encoding="utf-8")
    assert "## V16" in texto and "2.885.620,64" in texto
