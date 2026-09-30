"""Interpretação e validação das linhas de receita_acessoinformacao.csv.

Regras da nota técnica e do Relatório de Auditoria (29/09/2026):
- códigos são texto (não converter para número; zeros e comprimento importam);
- dinheiro em Decimal exato; fração de centavo é rejeitada; sinal é preservado;
- valor_arrecado_periodo = valor_arrecado_mes nesta extração (não somar os dois);
- conta-pai (TOTAL) serve só para conferência; a medida aditiva são os 4 componentes;
- conta sem mapeamento aprovado não é classificada por adivinhação.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

CENTAVO = Decimal("0.01")

# Mapeamento aprovado (Relatório de Auditoria, p. 6): conta-pai por tributo e vigência.
PAIS_POR_TRIBUTO = {
    "IPTU": {"2019-2021": "1118011", "2022-2026": "1112500"},
    "ISSQN": {"2019-2021": "1118023", "2022-2026": "1114511"},
    "ITBI": {"2019-2021": "1118014", "2022-2026": "1112530"},
}
COMPONENTE_POR_SUFIXO = {
    "1": "PRINCIPAL",
    "2": "MULTAS_JUROS",
    "3": "DIVIDA_ATIVA",
    "4": "DIVIDA_ATIVA_MULTAS_JUROS",
}


class ErroValidacao(ValueError):
    """Violação de contrato de entrada que impede a promoção da linha."""


@dataclass(frozen=True)
class Classificacao:
    tributo: str
    papel: str                 # TOTAL | COMPONENTE
    componente: str | None     # None quando papel = TOTAL
    codigo_pai: str | None     # None quando papel = TOTAL


@dataclass
class LinhaReceita:
    linha_origem: int
    orgao: int
    orgao_nome: str
    ano: int
    mes: int
    codigo_original: str
    codigo_formatado: str
    descricao: str
    valor_orcado: Decimal
    valor_arrecadado_mes: Decimal
    classificacao: Classificacao | None
    avisos: list[str] = field(default_factory=list)


def para_decimal(texto: str, campo: str) -> Decimal:
    """Converte texto monetário ('1234.5', '-10', '173.104,07') em Decimal exato."""
    bruto = (texto or "").strip()
    if not bruto:
        raise ErroValidacao(f"{campo}: valor vazio")
    if "," in bruto:  # formato brasileiro: ponto de milhar, vírgula decimal
        bruto = bruto.replace(".", "").replace(",", ".")
    try:
        valor = Decimal(bruto)
    except InvalidOperation as exc:
        raise ErroValidacao(f"{campo}: '{texto}' não é número") from exc
    if not valor.is_finite():
        raise ErroValidacao(f"{campo}: '{texto}' não é finito")
    if valor != valor.quantize(CENTAVO):
        raise ErroValidacao(f"{campo}: '{texto}' tem fração de centavo")
    return valor.quantize(CENTAVO)


def _vigencia(ano: int) -> str:
    return "2019-2021" if ano <= 2021 else "2022-2026"


def classificar(codigo_original: str, ano: int) -> Classificacao | None:
    """Classifica a conta pelo mapeamento aprovado; devolve None se não mapeada."""
    for tributo, pais in PAIS_POR_TRIBUTO.items():
        pai = pais[_vigencia(ano)]
        if codigo_original == pai:
            return Classificacao(tributo, "TOTAL", None, None)
        if (len(codigo_original) == len(pai) + 1 and codigo_original.startswith(pai)
                and codigo_original[-1] in COMPONENTE_POR_SUFIXO):
            return Classificacao(tributo, "COMPONENTE",
                                 COMPONENTE_POR_SUFIXO[codigo_original[-1]], pai)
    return None


def interpretar(linha: dict[str, str], linha_origem: int) -> LinhaReceita:
    """Valida e converte uma linha do CSV. Levanta ErroValidacao em violação de contrato."""
    try:
        ano = int(linha["ano"])
        mes = int(linha["mes"])
        orgao = int(linha["orgao"])
    except (KeyError, ValueError) as exc:
        raise ErroValidacao(f"linha {linha_origem}: ano/mês/órgão inválido") from exc
    if not 1 <= mes <= 12:
        raise ErroValidacao(f"linha {linha_origem}: mês {mes} fora de 1..12")

    codigo = (linha.get("codigo_original") or "").strip()
    if not codigo:
        raise ErroValidacao(f"linha {linha_origem}: codigo_original vazio")

    arrecadado = para_decimal(linha["valor_arrecado_mes"], "valor_arrecado_mes")
    periodo = para_decimal(linha["valor_arrecado_periodo"], "valor_arrecado_periodo")
    avisos = []
    if periodo != arrecadado:
        avisos.append("valor_arrecado_periodo difere de valor_arrecado_mes")
    descricao = (linha.get("descricao") or "").strip()
    if not descricao:
        avisos.append("descrição ausente")

    return LinhaReceita(
        linha_origem=linha_origem,
        orgao=orgao,
        orgao_nome=(linha.get("orgao_nome") or "").strip(),
        ano=ano,
        mes=mes,
        codigo_original=codigo,
        codigo_formatado=(linha.get("codigo") or "").strip(),
        descricao=descricao,
        valor_orcado=para_decimal(linha["valor_orcado"], "valor_orcado"),
        valor_arrecadado_mes=arrecadado,
        classificacao=classificar(codigo, ano),
        avisos=avisos,
    )


def conciliar(linhas: list[LinhaReceita]) -> list[tuple[tuple, Decimal, Decimal]]:
    """Compara cada TOTAL com a soma dos seus componentes na mesma competência.

    Devolve [(chave, valor_total, soma_componentes)] apenas das divergências.
    Um total sem os 4 componentes também é divergência.
    """
    totais: dict[tuple, Decimal] = {}
    somas: dict[tuple, Decimal] = {}
    contagem: dict[tuple, int] = {}
    for l in linhas:
        c = l.classificacao
        if c is None:
            continue
        pai = l.codigo_original if c.papel == "TOTAL" else c.codigo_pai
        chave = (l.orgao, l.ano, l.mes, pai)
        if c.papel == "TOTAL":
            totais[chave] = l.valor_arrecadado_mes
        else:
            somas[chave] = somas.get(chave, Decimal("0.00")) + l.valor_arrecadado_mes
            contagem[chave] = contagem.get(chave, 0) + 1
    divergencias = []
    for chave, total in totais.items():
        soma = somas.get(chave, Decimal("0.00"))
        if soma != total or contagem.get(chave, 0) != 4:
            divergencias.append((chave, total, soma))
    return divergencias
