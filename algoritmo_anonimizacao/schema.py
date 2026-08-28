"""Esquema, regras de generalização e dicionário de dados do pipeline."""

from __future__ import annotations

from dataclasses import dataclass


COLUNAS_OBRIGATORIAS = (
    "registro_id",
    "nome",
    "email",
    "data_nascimento",
    "cidade",
    "especie_pet",
    "humor_predominante",
    "nivel_estresse",
    "confianca_analise",
    "sessao_minutos",
    "data_evento",
    "canal_captura",
)

COLUNAS_IDENTIFICADOR_DIRETO = ("registro_id", "nome", "email")

COLUNAS_SAIDA = (
    "id_linha_sintetica",
    "faixa_etaria",
    "regiao_agregada",
    "especie_pet",
    "humor_predominante",
    "nivel_estresse_faixa",
    "confianca_faixa",
    "sessao_minutos",
    "data_evento_mes",
    "canal_captura",
    "origem_dado",
)

REGIAO_POR_CIDADE = {
    "São Paulo": "Sudeste",
    "Campinas": "Sudeste",
    "Rio de Janeiro": "Sudeste",
    "Belo Horizonte": "Sudeste",
    "Curitiba": "Sul",
    "Porto Alegre": "Sul",
    "Salvador": "Nordeste",
    "Recife": "Nordeste",
    "Brasília": "Centro-Oeste",
    "Goiânia": "Centro-Oeste",
    "Manaus": "Norte",
    "Belém": "Norte",
}

FAIXAS_ETARIAS = ("18-24", "25-34", "35-44", "45-54", "55-64", "65+")


@dataclass(frozen=True)
class CampoSaida:
    """Metadados exibidos na aba de dicionário de dados."""

    nome: str
    tipo: str
    classificacao: str
    descricao: str
    regra: str


DICIONARIO_SAIDA = (
    CampoSaida(
        "id_linha_sintetica",
        "string",
        "identificador técnico",
        "UUID gerado para a linha de saída; não possui correspondência reversível com a origem.",
        "Gerado com Faker.uuid4().",
    ),
    CampoSaida(
        "faixa_etaria",
        "categoria",
        "quase-identificador generalizado",
        "Faixa etária ampla, sem data de nascimento.",
        "Calculada a partir da data de nascimento e agregada em seis faixas.",
    ),
    CampoSaida(
        "regiao_agregada",
        "categoria",
        "quase-identificador generalizado",
        "Região do Brasil, sem a cidade original.",
        "Mapeamento cidade → região; cidades não reconhecidas viram 'Outra'.",
    ),
    CampoSaida(
        "especie_pet",
        "categoria",
        "atributo analítico",
        "Espécie do pet associada ao evento.",
        "Amostragem com reposição e mutação categórica controlada.",
    ),
    CampoSaida(
        "humor_predominante",
        "categoria",
        "atributo sensível generalizado",
        "Categoria de humor detectada na sessão.",
        "Amostragem com reposição; permanece apenas como categoria, sem imagem ou texto livre.",
    ),
    CampoSaida(
        "nivel_estresse_faixa",
        "categoria ordinal",
        "atributo sensível generalizado",
        "Faixa ordinal de estresse: baixo, moderado ou alto.",
        "Valor numérico é convertido em faixa; não é publicado o escore original.",
    ),
    CampoSaida(
        "confianca_faixa",
        "categoria ordinal",
        "atributo sensível generalizado",
        "Faixa de confiança da análise: baixa, moderada, alta ou muito alta.",
        "Valor contínuo é convertido em faixa; não é publicado o valor original.",
    ),
    CampoSaida(
        "sessao_minutos",
        "inteiro",
        "atributo analítico perturbado",
        "Duração aproximada da sessão em minutos.",
        "Ruído aleatório controlado, arredondamento e limites de 1 a 240 minutos.",
    ),
    CampoSaida(
        "data_evento_mes",
        "string YYYY-MM",
        "quase-identificador generalizado",
        "Mês do evento, sem dia ou horário.",
        "Mês deslocado aleatoriamente em uma janela de até dois meses.",
    ),
    CampoSaida(
        "canal_captura",
        "categoria",
        "atributo analítico",
        "Canal agregado de coleta: app ou dispositivo IoT.",
        "Amostragem com reposição e mutação categórica controlada.",
    ),
    CampoSaida(
        "origem_dado",
        "categoria",
        "controle de proveniência",
        "Indica que a linha foi sintetizada e não deve ser tratada como observação real.",
        "Valor constante 'sintetico'.",
    ),
)
