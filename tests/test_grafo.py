from pathlib import Path

import pytest

from etl.carregar_receita import ler_csv
from etl.parser import interpretar
from src.estruturas.grafo import GrafoDirigido, grafo_contabil

AMOSTRA = Path(__file__).resolve().parent.parent / "data" / "amostra" / "receita_amostra_10.csv"


def grafo_da_amostra():
    contas = []
    for n, bruto in ler_csv(AMOSTRA):
        l = interpretar(bruto, n)
        c = l.classificacao
        contas.append((l.codigo_original, c.codigo_pai,
                       {"tributo": c.tributo, "papel": c.papel, "valor": l.valor_arrecadado_mes}))
    return grafo_contabil(contas)


class TestGrafoContabilReal:
    def test_tamanho(self):
        g = grafo_da_amostra()
        assert len(g) == 10 and g.num_arestas == 8

    def test_cada_pai_detalha_quatro_componentes(self):
        g = grafo_da_amostra()
        for pai in ("1112500", "1114511"):
            assert g.grau_saida(pai) == 4 and g.grau_entrada(pai) == 0
            assert all(g.grau_entrada(f) == 1 for f in g.sucessores(pai, "DETALHA"))

    def test_bfs_recupera_componentes_sem_duplicar_o_pai(self):
        g = grafo_da_amostra()
        alcancados = g.bfs("1112500")
        assert alcancados[0] == "1112500"
        folhas = [v for v in alcancados if g.grau_saida(v) == 0]
        assert sorted(folhas) == ["11125001", "11125002", "11125003", "11125004"]
        assert sum(g.atributos(v)["valor"] for v in folhas) == g.atributos("1112500")["valor"]

    def test_sem_ciclos_e_dois_componentes(self):
        g = grafo_da_amostra()
        assert not g.tem_ciclo()
        assert len(g.componentes_conexos()) == 2


class TestGrafoRelacoesSintetico:
    """Espelha sql/seed_sintetico.sql: sujeito 1 responde por 3 créditos em 2 imóveis."""

    def grafo(self):
        g = GrafoDirigido()
        for v in ["S1", "S2", "S3", "C1", "C2", "C3", "C4", "C5", "I1", "I2", "I3", "CE1"]:
            g.adicionar_vertice(v)
        for s, c in [("S1", "C1"), ("S1", "C2"), ("S1", "C3"), ("S2", "C3"), ("S2", "C4"), ("S3", "C5")]:
            g.adicionar_aresta(s, c, "RESPONDE_POR")
        for c, b in [("C1", "I1"), ("C2", "I1"), ("C3", "I2"), ("C4", "I3"), ("C5", "CE1")]:
            g.adicionar_aresta(c, b, "BASEADO_EM")
        return g

    def test_mesmo_sujeito_em_varias_inscricoes(self):
        g = self.grafo()
        imoveis = {b for c in g.sucessores("S1", "RESPONDE_POR") for b in g.sucessores(c)}
        assert imoveis == {"I1", "I2"}

    def test_corresponsavel_une_componentes(self):
        comps = self.grafo().componentes_conexos()
        assert sorted(len(c) for c in comps) == [3, 9]  # {S3,C5,CE1} e o restante ligado via C3

    def test_dfs_e_bfs_alcancam_os_mesmos_vertices(self):
        g = self.grafo()
        assert set(g.dfs("S1")) == set(g.bfs("S1")) == {"S1", "C1", "C2", "C3", "I1", "I2"}


def test_detecta_ciclo():
    g = GrafoDirigido()
    for v in "abc":
        g.adicionar_vertice(v)
    g.adicionar_aresta("a", "b")
    g.adicionar_aresta("b", "c")
    assert not g.tem_ciclo()
    g.adicionar_aresta("c", "a")
    assert g.tem_ciclo()


def test_aresta_para_vertice_inexistente():
    g = GrafoDirigido()
    g.adicionar_vertice("a")
    with pytest.raises(KeyError, match="vértice inexistente"):
        g.adicionar_aresta("a", "z")
    with pytest.raises(KeyError, match="vértice inexistente"):
        g.adicionar_aresta("z", "a")
    assert g.num_arestas == 0


# --- casos adicionados a partir dos mutantes sobreviventes (docs/mutacao.md) ---

def grafo_de(vertices, arestas):
    g = GrafoDirigido()
    for v in vertices:
        g.adicionar_vertice(v)
    for origem, destino, *rotulo in arestas:
        g.adicionar_aresta(origem, destino, *rotulo)
    return g


def test_diamante_nao_e_ciclo():
    # d é alcançado duas vezes (via b e via c) depois de concluído: não é aresta de retorno
    g = grafo_de("abcd", [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")])
    assert not g.tem_ciclo()


def test_ciclo_em_componente_posterior_e_detectado():
    # x→y é explorado primeiro; o ciclo p⇄q só é visto se a busca continuar nas raízes seguintes
    g = grafo_de(["x", "y", "p", "q"], [("x", "y"), ("p", "q"), ("q", "p")])
    assert g.tem_ciclo()


def test_sucessores_filtra_pelo_rotulo():
    g = grafo_de(["S", "C", "I"], [("S", "C", "RESPONDE_POR"), ("S", "I", "PROPRIETARIO")])
    assert g.sucessores("S", "RESPONDE_POR") == ["C"]
    assert g.sucessores("S", "PROPRIETARIO") == ["I"]
    assert sorted(g.sucessores("S")) == ["C", "I"]
    assert g.sucessores("S", "INEXISTENTE") == []


def test_dfs_segue_a_ordem_da_busca_recursiva_do_livro():
    # Lintzmayer & Mota, Algoritmo 24.12 (BuscaProfundidade recursiva em digrafos)
    g = grafo_de("abcdef", [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d"), ("d", "e"), ("c", "f")])

    def recursiva(v, visitados):
        visitados.append(v)
        for w in g.sucessores(v):
            if w not in visitados:
                recursiva(w, visitados)
        return visitados

    assert g.dfs("a") == recursiva("a", []) == ["a", "b", "d", "e", "c", "f"]
    assert g.bfs("a") == ["a", "b", "c", "d", "f", "e"]
