import random
from datetime import date

import pytest

from src.estruturas.heap_prioridade import FilaPrioridadeVersionada, HeapBinaria


class TestHeapBinaria:
    def test_extrai_em_ordem(self):
        rnd = random.Random(1)
        dados = [rnd.randint(-1000, 1000) for _ in range(500)]
        h = HeapBinaria()
        for x in dados:
            h.inserir(x)
            assert h.valida()
        assert [h.extrair() for _ in range(len(dados))] == sorted(dados)

    def test_construcao_em_lote(self):
        dados = list(range(100, 0, -1))
        h = HeapBinaria(dados)
        assert h.valida() and h.topo() == 1 and len(h) == 100

    def test_valida_detecta_heap_invalida(self):
        h = HeapBinaria([1, 2, 3])
        h._a = [1, 5, 3, 4]      # filho 4 menor que o pai 5 (índice 1)
        assert not h.valida()
        h._a = [2, 1]
        assert not h.valida()

    def test_vazia(self):
        with pytest.raises(IndexError):
            HeapBinaria().extrair()
        with pytest.raises(IndexError):
            HeapBinaria().topo()


class TestFilaPrioridade:
    """Chave = (classe_prioridade, prazo, -score_sintético). Menor = mais urgente."""

    def fila(self):
        f = FilaPrioridadeVersionada()
        f.inserir("acao-1", (2, date(2026, 10, 15), -0.40))
        f.inserir("acao-2", (1, date(2026, 10, 5), -0.10))
        f.inserir("acao-3", (1, date(2026, 10, 5), -0.90))
        f.inserir("acao-4", (3, date(2026, 11, 1), -0.99))
        return f

    def test_ordem_lexicografica(self):
        f = self.fila()
        ordem = [f.extrair()[0] for _ in range(len(f))]
        # classe 1 primeiro; no mesmo prazo, maior score sintético primeiro
        assert ordem == ["acao-3", "acao-2", "acao-1", "acao-4"]

    def test_empate_total_respeita_ordem_de_chegada(self):
        f = FilaPrioridadeVersionada()
        chegada = ["e", "b", "d", "a", "c"]  # fora da ordem alfabética: o desempate é pela chegada
        for id_ in chegada:
            f.inserir(id_, (1, date(2026, 1, 1)))
        assert [f.extrair()[0] for _ in range(5)] == chegada

    def test_atualizacao_invalida_versao_anterior(self):
        f = self.fila()
        f.inserir("acao-4", (0, date(2026, 9, 30), 0.0))  # prioridade elevada
        assert len(f) == 4 and f.entradas_na_heap == 5
        assert f.extrair()[0] == "acao-4"
        restantes = [f.extrair()[0] for _ in range(len(f))]
        assert "acao-4" not in restantes  # entrada antiga descartada

    def test_remocao_por_pagamento(self):
        f = self.fila()
        f.remover("acao-3")
        assert f.espiar()[0] == "acao-2"
        assert len(f) == 3

    def test_prioridade_rebaixada_descarta_a_entrada_antiga(self):
        f = self.fila()
        f.inserir("acao-2", (9, date(2026, 12, 31), 0.0))  # entrada antiga fica no topo da heap
        assert [f.extrair()[0] for _ in range(len(f))] == ["acao-3", "acao-1", "acao-4", "acao-2"]

    def test_extrair_depois_de_remover_o_topo(self):
        f = self.fila()
        f.remover("acao-3")
        assert f.extrair()[0] == "acao-2"

    def test_reconstruir_descarta_obsoletas(self):
        f = self.fila()
        f.remover("acao-4")
        for i in range(10):
            f.inserir("acao-1", (2, date(2026, 10, 15), -i / 10))
        f.reconstruir()
        assert f.entradas_na_heap == len(f) == 3
        assert [f.extrair()[0] for _ in range(3)] == ["acao-3", "acao-2", "acao-1"]

    def test_chave_incompleta_rejeitada(self):
        with pytest.raises(ValueError):
            FilaPrioridadeVersionada().inserir("x", (1, None))

    def test_fila_vazia(self):
        f = FilaPrioridadeVersionada()
        with pytest.raises(IndexError):
            f.extrair()
        f.inserir("x", (1,))
        f.remover("x")
        with pytest.raises(IndexError):
            f.espiar()
