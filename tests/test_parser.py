from decimal import Decimal

import pytest

from etl.parser import ErroValidacao, classificar, conciliar, interpretar, para_decimal


def linha(**over):
    base = {
        "orgao": "2798", "orgao_nome": "TESOURO MUNICIPAL", "ano": "2025", "mes": "1",
        "codigo": "1.1.1.2.50.0.1", "codigo_original": "11125001", "descricao": "IPTU - PRINCIPAL",
        "valor_orcado": "96032000", "valor_arrecado_mes": "2274951.38",
        "valor_arrecado_periodo": "2274951.38",
    }
    base.update(over)
    return base


class TestDecimal:
    def test_formatos_aceitos(self):
        assert para_decimal("2274951.38", "v") == Decimal("2274951.38")
        assert para_decimal("100668.5", "v") == Decimal("100668.50")
        assert para_decimal("96032000", "v") == Decimal("96032000.00")
        assert para_decimal("173.104,07", "v") == Decimal("173104.07")

    def test_negativo_e_preservado(self):
        assert para_decimal("-10.5", "v") == Decimal("-10.50")

    @pytest.mark.parametrize("texto", ["10.005", "", "abc", "NaN", "Infinity"])
    def test_rejeita_invalidos(self, texto):
        with pytest.raises(ErroValidacao):
            para_decimal(texto, "v")


class TestClassificacao:
    def test_pai_e_componentes_2022_2026(self):
        assert classificar("1112500", 2025).papel == "TOTAL"
        c = classificar("11125003", 2025)
        assert (c.tributo, c.papel, c.componente, c.codigo_pai) == (
            "IPTU", "COMPONENTE", "DIVIDA_ATIVA", "1112500")

    def test_mudanca_de_codigo_em_2022(self):
        assert classificar("1118011", 2021).tributo == "IPTU"
        assert classificar("1118011", 2022) is None
        assert classificar("1112500", 2021) is None

    def test_pai_alternativo_nao_e_mapeado(self):
        # 111250 também representa IPTU na fonte: somá-lo duplicaria a receita
        assert classificar("111250", 2025) is None

    def test_sufixo_invalido_nao_e_componente(self):
        assert classificar("11125009", 2025) is None


class TestInterpretar:
    def test_codigo_permanece_texto(self):
        l = interpretar(linha(codigo_original="0011"), 2)
        assert l.codigo_original == "0011"

    def test_mes_fora_do_intervalo(self):
        with pytest.raises(ErroValidacao):
            interpretar(linha(mes="13"), 2)

    def test_periodo_diferente_gera_aviso(self):
        l = interpretar(linha(valor_arrecado_periodo="1.00"), 2)
        assert any("periodo" in a for a in l.avisos)

    def test_descricao_ausente_gera_aviso(self):
        assert "descrição ausente" in interpretar(linha(descricao=""), 2).avisos


def test_conciliar_detecta_componente_faltando():
    pai = interpretar(linha(codigo_original="1112500", valor_arrecado_mes="10",
                            valor_arrecado_periodo="10"), 2)
    filho = interpretar(linha(valor_arrecado_mes="10", valor_arrecado_periodo="10"), 3)
    # soma confere, mas faltam 3 componentes
    assert len(conciliar([pai, filho])) == 1


# --- casos adicionados a partir dos mutantes sobreviventes (docs/mutacao.md) ---

class TestLimites:
    @pytest.mark.parametrize("texto", ["10.006", "-10.005"])
    def test_fracao_de_centavo_em_qualquer_direcao(self, texto):
        with pytest.raises(ErroValidacao):
            para_decimal(texto, "v")

    @pytest.mark.parametrize("mes", ["0", "13"])
    def test_mes_invalido(self, mes):
        with pytest.raises(ErroValidacao):
            interpretar(linha(mes=mes), 2)

    @pytest.mark.parametrize("mes", ["1", "12"])
    def test_meses_extremos_validos(self, mes):
        assert interpretar(linha(mes=mes), 2).mes == int(mes)

    @pytest.mark.parametrize("campos", [{"ano": "dois mil"}, {"orgao": "x"}])
    def test_campos_numericos_invalidos(self, campos):
        with pytest.raises(ErroValidacao):
            interpretar(linha(**campos), 2)

    def test_campo_obrigatorio_ausente(self):
        bruto = linha()
        del bruto["orgao"]
        with pytest.raises(ErroValidacao):
            interpretar(bruto, 2)

    @pytest.mark.parametrize("ano", [2019, 2020, 2021])
    def test_vigencia_antiga_para_todo_2019_2021(self, ano):
        assert classificar("11180111", ano).tributo == "IPTU"

    def test_codigo_mais_longo_que_componente_nao_e_mapeado(self):
        assert classificar("111250011", 2025) is None


class TestCamposTextuais:
    def test_campos_preservados(self):
        l = interpretar(linha(), 2)
        assert (l.descricao, l.orgao_nome, l.codigo_formatado) == (
            "IPTU - PRINCIPAL", "TESOURO MUNICIPAL", "1.1.1.2.50.0.1")
        assert l.avisos == []

    def test_periodo_maior_tambem_gera_aviso(self):
        l = interpretar(linha(valor_arrecado_periodo="9999999.99"), 2)
        assert any("periodo" in a for a in l.avisos)

    def test_classificacao_e_imutavel(self):
        from dataclasses import FrozenInstanceError
        c = classificar("1112500", 2025)
        with pytest.raises(FrozenInstanceError):
            c.tributo = "ISSQN"


class TestConciliar:
    def componentes(self, valores, mes="1"):
        return [interpretar(linha(codigo_original=f"1112500{i}", mes=mes, valor_arrecado_mes=v,
                                  valor_arrecado_periodo=v), 10 + i) for i, v in enumerate(valores, start=1)]

    def pai(self, valor, mes="1"):
        return interpretar(linha(codigo_original="1112500", mes=mes, valor_arrecado_mes=valor,
                                 valor_arrecado_periodo=valor), 2)

    def test_quatro_componentes_com_soma_certa(self):
        assert conciliar([self.pai("10"), *self.componentes(["1", "2", "3", "4"])]) == []

    @pytest.mark.parametrize("total", ["9", "11"])
    def test_soma_diferente_do_total(self, total):
        assert len(conciliar([self.pai(total), *self.componentes(["1", "2", "3", "4"])])) == 1

    def test_componente_duplicado_e_divergencia(self):
        comp = self.componentes(["1", "2", "3", "4"])
        assert len(conciliar([self.pai("11"), *comp, comp[0]])) == 1

    def test_linha_nao_mapeada_no_meio_nao_interrompe(self):
        nao_mapeada = interpretar(linha(codigo_original="999999"), 1)
        assert conciliar([nao_mapeada, self.pai("11"), *self.componentes(["1", "2", "3", "4"])]) != []
