"""Funções principais de anonimização, síntese e exportação para Excel.

O pipeline aprende apenas distribuições e categorias agregadas da base de entrada.
As linhas originais nunca são copiadas para a saída: cada linha publicada é nova,
tem seus quase-identificadores generalizados e recebe perturbação controlada.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from faker import Faker

from .schema import (
    COLUNAS_IDENTIFICADOR_DIRETO,
    COLUNAS_OBRIGATORIAS,
    COLUNAS_SAIDA,
    DICIONARIO_SAIDA,
    REGIAO_POR_CIDADE,
)

DATA_REFERENCIA = pd.Timestamp("2025-01-01")
ESTRESSE_BINS = [-np.inf, 3.99, 6.99, np.inf]
ESTRESSE_LABELS = ["baixo", "moderado", "alto"]
CONFIANCA_BINS = [-np.inf, 0.599, 0.799, 0.899, np.inf]
CONFIANCA_LABELS = ["baixa", "moderada", "alta", "muito alta"]
TIPOS_MUTAVEIS = ("especie_pet", "humor_predominante", "canal_captura")


def _validar_colunas(base: pd.DataFrame) -> None:
    faltantes = [col for col in COLUNAS_OBRIGATORIAS if col not in base.columns]
    if faltantes:
        raise ValueError(
            "A base de entrada não contém as colunas obrigatórias: "
            + ", ".join(faltantes)
        )
    if base.empty:
        raise ValueError("A base de entrada está vazia.")


def _faixa_etaria(data_nascimento: pd.Series) -> pd.Series:
    idade = ((DATA_REFERENCIA - data_nascimento).dt.days / 365.2425).round(0)
    idade = idade.clip(lower=18, upper=100)
    return pd.cut(
        idade,
        bins=[17, 24, 34, 44, 54, 64, np.inf],
        labels=["18-24", "25-34", "35-44", "45-54", "55-64", "65+"],
        include_lowest=True,
    ).astype("string")


def anonimizar_base(base: pd.DataFrame) -> pd.DataFrame:
    """Remove identificadores diretos e generaliza campos de ligação indireta."""

    _validar_colunas(base)
    trabalho = base.copy()
    trabalho["data_nascimento"] = pd.to_datetime(
        trabalho["data_nascimento"], errors="coerce"
    )
    trabalho["data_evento"] = pd.to_datetime(trabalho["data_evento"], errors="coerce")
    if trabalho["data_nascimento"].isna().all() or trabalho["data_evento"].isna().all():
        raise ValueError("As colunas de data devem conter ao menos um valor válido.")

    estresse = pd.to_numeric(trabalho["nivel_estresse"], errors="coerce")
    confianca = pd.to_numeric(trabalho["confianca_analise"], errors="coerce")
    sessao = pd.to_numeric(trabalho["sessao_minutos"], errors="coerce")
    estresse = estresse.fillna(estresse.median()).clip(0, 10)
    confianca = confianca.fillna(confianca.median()).clip(0, 1)
    sessao = sessao.fillna(sessao.median()).clip(1, 240)

    anonimizada = pd.DataFrame(
        {
            "faixa_etaria": _faixa_etaria(trabalho["data_nascimento"]),
            "regiao_agregada": trabalho["cidade"]
            .map(REGIAO_POR_CIDADE)
            .fillna("Outra")
            .astype("string"),
            "especie_pet": trabalho["especie_pet"].astype("string").fillna("desconhecida"),
            "humor_predominante": trabalho["humor_predominante"]
            .astype("string")
            .fillna("indeterminado"),
            "nivel_estresse_faixa": pd.cut(
                estresse, bins=ESTRESSE_BINS, labels=ESTRESSE_LABELS
            ).astype("string"),
            "confianca_faixa": pd.cut(
                confianca, bins=CONFIANCA_BINS, labels=CONFIANCA_LABELS
            ).astype("string"),
            "sessao_minutos": sessao.astype(float),
            "data_evento_mes": trabalho["data_evento"].dt.to_period("M").astype("string"),
            "canal_captura": trabalho["canal_captura"].astype("string").fillna("outro"),
        }
    )
    # Identificadores diretos são deliberadamente descartados, nunca mascarados na saída.
    anonimizada = anonimizada.replace({pd.NA: None}).dropna(subset=["data_evento_mes"])
    if anonimizada.empty:
        raise ValueError("Nenhuma linha válida restou após o tratamento das datas.")
    return anonimizada.reset_index(drop=True)


def _amostrar_categoria(
    serie: pd.Series, tamanho: int, rng: np.random.Generator
) -> np.ndarray:
    valores = serie.dropna().astype(str).to_numpy()
    if len(valores) == 0:
        return np.repeat("indeterminado", tamanho)
    return rng.choice(valores, size=tamanho, replace=True)


def _meses_com_perturbacao(
    valores: pd.Series, tamanho: int, rng: np.random.Generator
) -> list[str]:
    meses = pd.PeriodIndex(valores.astype(str), freq="M")
    escolhidos = meses[rng.integers(0, len(meses), tamanho)]
    deslocamentos = rng.integers(-2, 3, tamanho)
    return [(mes + int(delta)).strftime("%Y-%m") for mes, delta in zip(escolhidos, deslocamentos)]


def _id_sintetico(fake: Faker, indice: int) -> str:
    """Cria um identificador técnico sem guardar o identificador da origem."""

    return f"SYN-{indice:06d}-{fake.uuid4()[:8].upper()}"


def gerar_base_sintetica(
    anonimizada: pd.DataFrame, quantidade: int, seed: int = 42
) -> pd.DataFrame:
    """Gera novas linhas por reamostragem, mutação e ruído bounded.

    A função retorna somente linhas sintéticas. ``quantidade`` pode ser maior ou
    menor que o volume original, permitindo tanto augmentation quanto amostras de
    teste controladas.
    """

    if quantidade < 1:
        raise ValueError("quantidade deve ser maior que zero.")
    if anonimizada.empty:
        raise ValueError("A base anonimizada está vazia.")

    rng = np.random.default_rng(seed)
    fake = Faker("pt_BR")
    fake.seed_instance(seed)
    indices = rng.integers(0, len(anonimizada), size=quantidade)
    escolhidas = anonimizada.iloc[indices].reset_index(drop=True)
    saida = pd.DataFrame(index=range(quantidade))

    saida["id_linha_sintetica"] = [_id_sintetico(fake, i + 1) for i in range(quantidade)]
    saida["faixa_etaria"] = escolhidas["faixa_etaria"].astype(str).to_numpy()
    saida["regiao_agregada"] = escolhidas["regiao_agregada"].astype(str).to_numpy()
    saida["especie_pet"] = escolhidas["especie_pet"].astype(str).to_numpy()
    saida["humor_predominante"] = escolhidas["humor_predominante"].astype(str).to_numpy()
    saida["nivel_estresse_faixa"] = escolhidas["nivel_estresse_faixa"].astype(str).to_numpy()
    saida["confianca_faixa"] = escolhidas["confianca_faixa"].astype(str).to_numpy()
    saida["canal_captura"] = escolhidas["canal_captura"].astype(str).to_numpy()

    # Pequena mutação categórica quebra cópias exatas e preserva distribuições globais.
    for coluna in TIPOS_MUTAVEIS:
        mascara = rng.random(quantidade) < 0.12
        saida.loc[mascara, coluna] = _amostrar_categoria(
            anonimizada[coluna], int(mascara.sum()), rng
        )

    duracoes = pd.to_numeric(anonimizada["sessao_minutos"], errors="coerce").dropna()
    desvio = max(float(duracoes.std(ddof=0) or 1.0) * 0.15, 1.0)
    base_duracao = pd.to_numeric(escolhidas["sessao_minutos"], errors="coerce").fillna(
        duracoes.median()
    )
    saida["sessao_minutos"] = np.rint(
        np.clip(base_duracao.to_numpy() + rng.normal(0, desvio, quantidade), 1, 240)
    ).astype(int)
    saida["data_evento_mes"] = _meses_com_perturbacao(
        escolhidas["data_evento_mes"], quantidade, rng
    )
    saida["origem_dado"] = "sintetico"
    return saida.loc[:, COLUNAS_SAIDA]


def _sha256_arquivo(caminho: Path) -> str:
    digest = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def montar_metadados(
    entrada: Path, quantidade_origem: int, quantidade_saida: int, seed: int
) -> pd.DataFrame:
    """Cria uma trilha mínima de execução sem expor conteúdo da base."""

    return pd.DataFrame(
        [
            ["pipeline", "algoritmo_anonimizacao", "Nome do pipeline"],
            ["entrada_arquivo", entrada.name, "Nome do arquivo de entrada"],
            ["sha256_entrada", _sha256_arquivo(entrada), "Hash para auditoria de integridade"],
            ["linhas_entrada", quantidade_origem, "Quantidade de linhas lidas"],
            ["linhas_saida", quantidade_saida, "Quantidade de linhas sintéticas"],
            ["seed", seed, "Semente de reprodutibilidade"],
            ["data_execucao_utc", pd.Timestamp.utcnow().isoformat(), "Momento da execução"],
            [
                "politica_saida",
                "somente_sintetico",
                "Linhas originais não são exportadas para a planilha",
            ],
        ],
        columns=["chave", "valor", "descricao"],
    )


def exportar_excel(
    dados: pd.DataFrame,
    dicionario: tuple = DICIONARIO_SAIDA,
    metadados: pd.DataFrame | None = None,
    destino: Path | str = "saida_anonimizada.xlsx",
) -> Path:
    """Exporta dados, dicionário e metadados com formatação legível no Excel."""

    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    dicionario_df = pd.DataFrame([campo.__dict__ for campo in dicionario])
    if metadados is None:
        metadados = pd.DataFrame(columns=["chave", "valor", "descricao"])

    with pd.ExcelWriter(destino, engine="xlsxwriter", datetime_format="yyyy-mm-dd") as writer:
        dados.to_excel(writer, sheet_name="dados_anonimizados", index=False)
        dicionario_df.to_excel(writer, sheet_name="dicionario_dados", index=False)
        metadados.to_excel(writer, sheet_name="metadados_execucao", index=False)
        workbook = writer.book
        cabecalho = workbook.add_format(
            {"bold": True, "font_color": "#FFFFFF", "bg_color": "#4A3550", "bottom": 1}
        )
        destaque = workbook.add_format({"bg_color": "#FFF2CC"})
        for nome_aba, frame in (
            ("dados_anonimizados", dados),
            ("dicionario_dados", dicionario_df),
            ("metadados_execucao", metadados),
        ):
            worksheet = writer.sheets[nome_aba]
            worksheet.freeze_panes(1, 0)
            worksheet.autofilter(0, 0, len(frame), max(len(frame.columns) - 1, 0))
            worksheet.set_row(0, 24, cabecalho)
            for indice, nome_coluna in enumerate(frame.columns):
                largura = min(max(len(str(nome_coluna)) + 2, 14), 34)
                if not frame.empty:
                    amostra = frame[nome_coluna].astype(str).head(100)
                    largura = min(max(largura, int(amostra.map(len).max()) + 2), 42)
                worksheet.set_column(indice, indice, largura)
            if nome_aba == "dados_anonimizados":
                worksheet.set_column(0, 0, 28, destaque)
                worksheet.conditional_format(
                    1,
                    dados.columns.get_loc("nivel_estresse_faixa"),
                    len(dados),
                    dados.columns.get_loc("nivel_estresse_faixa"),
                    {
                        "type": "text",
                        "criteria": "containing",
                        "value": "alto",
                        "format": workbook.add_format({"bg_color": "#F4CCCC"}),
                    },
                )
    return destino


def processar_csv(
    entrada: Path | str,
    destino: Path | str,
    quantidade: int,
    seed: int = 42,
) -> dict[str, Any]:
    """Executa o pipeline completo e retorna um resumo serializável."""

    entrada = Path(entrada)
    destino = Path(destino)
    base = pd.read_csv(entrada)
    anonimizada = anonimizar_base(base)
    dados = gerar_base_sintetica(anonimizada, quantidade, seed)
    metadados = montar_metadados(entrada, len(base), len(dados), seed)
    exportar_excel(dados, metadados=metadados, destino=destino)
    return {
        "entrada": str(entrada),
        "saida": str(destino),
        "linhas_entrada": len(base),
        "linhas_saida": len(dados),
        "colunas_saida": list(dados.columns),
        "seed": seed,
    }


def resumo_json(resumo: dict[str, Any]) -> str:
    """Formata o resumo para uso pela CLI."""

    return json.dumps(resumo, ensure_ascii=False, indent=2)
