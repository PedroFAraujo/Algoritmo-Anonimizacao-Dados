from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree

import pandas as pd
import pytest

from algoritmo_anonimizacao.pipeline import (
    anonimizar_base,
    gerar_base_sintetica,
    processar_csv,
)


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "base_amostra.csv"


def test_anonimizacao_descarta_identificadores_e_generaliza_datas():
    base = pd.read_csv(BASE)
    resultado = anonimizar_base(base)

    assert "nome" not in resultado.columns
    assert "email" not in resultado.columns
    assert "registro_id" not in resultado.columns
    assert resultado["regiao_agregada"].isin(
        ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul", "Outra"]
    ).all()
    assert resultado["data_evento_mes"].str.fullmatch(r"\d{4}-\d{2}").all()


def test_geracao_tem_quantidade_e_origem_sintetica():
    anonimizada = anonimizar_base(pd.read_csv(BASE))
    resultado = gerar_base_sintetica(anonimizada, quantidade=50, seed=7)

    assert len(resultado) == 50
    assert resultado["id_linha_sintetica"].is_unique
    assert (resultado["origem_dado"] == "sintetico").all()
    assert resultado["sessao_minutos"].between(1, 240).all()


def test_quantidade_invalida():
    anonimizada = anonimizar_base(pd.read_csv(BASE))
    with pytest.raises(ValueError, match="maior que zero"):
        gerar_base_sintetica(anonimizada, quantidade=0)


def test_processamento_cria_planilha_com_tres_abas(tmp_path):
    destino = tmp_path / "resultado.xlsx"
    resumo = processar_csv(BASE, destino, quantidade=15, seed=11)

    assert destino.exists()
    assert resumo["linhas_saida"] == 15
    with ZipFile(destino) as arquivo_xlsx:
        workbook_xml = ElementTree.fromstring(arquivo_xlsx.read("xl/workbook.xml"))
    namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    abas = [
        aba.attrib["name"]
        for aba in workbook_xml.findall("main:sheets/main:sheet", namespace)
    ]
    assert abas == ["dados_anonimizados", "dicionario_dados", "metadados_execucao"]
