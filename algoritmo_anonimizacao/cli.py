"""Interface de linha de comando do gerador de planilhas."""

from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import processar_csv, resumo_json


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Anonimiza uma base MellowPet e gera uma planilha Excel sintética."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/base_amostra.csv"),
        help="CSV de entrada (padrão: data/base_amostra.csv).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("exemplos/saida_anonimizada.xlsx"),
        help="Caminho do XLSX de saída.",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=100,
        help="Quantidade de linhas sintéticas a gerar (padrão: 100).",
    )
    parser.add_argument("--seed", type=int, default=42, help="Semente de reprodutibilidade.")
    return parser


def main() -> None:
    args = criar_parser().parse_args()
    resumo = processar_csv(args.input, args.output, args.rows, args.seed)
    print(resumo_json(resumo))


if __name__ == "__main__":
    main()
