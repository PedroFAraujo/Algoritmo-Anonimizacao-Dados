Endrigo Gustavo Brandao de Oliveira
Gabriel Messias da Silva
Pedro Fernandes Araujo

# Algoritmo de Anonimização de Dados

Pipeline em Python para transformar registros de análise emocional do domínio do
[MellowPet](https://github.com/Endrigogustavo/MellowPet) em uma base sintética,
generalizada e pronta para análise no Excel.

## Visão geral e área analisada

O MellowPet é uma plataforma de bem-estar emocional que registra eventos de
análise associados à interação de uma pessoa com um pet virtual ou dispositivo de
captura. Este repositório isola o caso de uso de dados: gerar uma amostra
analítica para prototipação, testes, demonstrações e treinamento de relatórios,
sem expor imagens, textos livres, nomes, e-mails ou identificadores de usuários.

O fluxo é:

```text
CSV de entrada
    ↓ validação e normalização
generalização de PII/quase-identificadores
    ↓ amostragem com reposição + mutações + ruído bounded
base 100% sintética
    ↓ exportação
Excel (.xlsx): dados + dicionário + metadados de execução
```

As linhas originais não são concatenadas à saída. A função de geração aprende
categorias e distribuições da versão generalizada, reamostra perfis e perturba
campos analíticos. O identificador de saída é técnico e novo, gerado com
`Faker.uuid4()`; ele não é um hash reversível nem uma chave de ligação com a
origem.

## Estrutura do projeto

```text
.
├── algoritmo_anonimizacao/
│   ├── cli.py              # interface de linha de comando
│   ├── pipeline.py         # anonimização, síntese e Excel
│   └── schema.py           # esquema e dicionário de dados
├── data/
│   └── base_amostra.csv    # dados fictícios para demonstração
├── exemplos/
│   └── saida_anonimizada.xlsx
├── tests/
│   └── test_pipeline.py
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Dicionário de dados

### Entrada esperada

| Coluna | Tipo | Classificação | Uso |
|---|---|---|---|
| `registro_id` | string | identificador direto | Validado e descartado. |
| `nome` | string | identificador direto | Validado e descartado. |
| `email` | string | identificador direto | Validado e descartado. |
| `data_nascimento` | data `YYYY-MM-DD` | quase-identificador | Convertida em faixa etária. |
| `cidade` | string | quase-identificador | Convertida em região agregada. |
| `especie_pet` | categoria | analítico | Reamostrada e mutada. |
| `humor_predominante` | categoria | sensível/analítico | Mantida somente como categoria e reamostrada. |
| `nivel_estresse` | número de 0 a 10 | sensível/analítico | Convertido em faixa ordinal. |
| `confianca_analise` | decimal de 0 a 1 | sensível/analítico | Convertida em faixa ordinal. |
| `sessao_minutos` | número | analítico | Perturbado com ruído e limitado entre 1 e 240. |
| `data_evento` | data/hora | quase-identificador | Reduzida ao mês e deslocada em até dois meses. |
| `canal_captura` | categoria | analítico | Reamostrada e mutada. |

### Saída publicada no Excel

| Coluna | Tipo | Classificação | Regra aplicada |
|---|---|---|---|
| `id_linha_sintetica` | string | identificador técnico | Novo UUID do Faker; não corresponde ao `registro_id`. |
| `faixa_etaria` | categoria | quase-identificador generalizado | `18-24`, `25-34`, `35-44`, `45-54`, `55-64` ou `65+`. |
| `regiao_agregada` | categoria | quase-identificador generalizado | `Norte`, `Nordeste`, `Centro-Oeste`, `Sudeste`, `Sul` ou `Outra`. |
| `especie_pet` | categoria | analítico | Amostragem com reposição e mutação de 12%. |
| `humor_predominante` | categoria | sensível generalizado | Categoria sem imagem, texto livre ou score individual. |
| `nivel_estresse_faixa` | categoria ordinal | sensível generalizado | `baixo`, `moderado` ou `alto`. |
| `confianca_faixa` | categoria ordinal | sensível generalizado | `baixa`, `moderada`, `alta` ou `muito alta`. |
| `sessao_minutos` | inteiro | analítico perturbado | Ruído, arredondamento e limite de 1–240. |
| `data_evento_mes` | string `YYYY-MM` | quase-identificador generalizado | Sem dia/hora e com deslocamento aleatório de -2 a +2 meses. |
| `canal_captura` | categoria | analítico | Amostragem com reposição e mutação de 12%. |
| `origem_dado` | categoria | proveniência | Sempre `sintetico`, para evitar uso indevido como dado observado. |

O dicionário também é exportado para a aba `dicionario_dados`, com descrição e
regra de transformação. A aba `metadados_execucao` registra a quantidade de
linhas, a seed, o momento de execução e o SHA-256 do arquivo de entrada, sem
gravar o conteúdo da base original.

## Objetivo da geração sintética

O objetivo é disponibilizar volume suficiente para:

- testar dashboards, consultas e integrações sem carregar dados pessoais;
- aumentar a amostra para protótipos e testes de carga;
- preservar tipos, categorias e relações aproximadas da base analítica;
- impedir a cópia direta de uma observação original para a planilha final;
- deixar explícita a proveniência sintética para evitar interpretações indevidas.

O pipeline não deve ser usado para decisões individuais, diagnóstico, medição
clínica ou para afirmar que uma pessoa não pode ser identificada em qualquer
contexto. Se a saída for usada com uma base externa, recomenda-se testar
unicidade, ataques de ligação, classes raras e métricas de utilidade/risco antes
da liberação.

## Como executar

### 1. Preparar o ambiente

Requer Python 3.10 ou superior.

```bash
git clone https://github.com/SEU_USUARIO/Algoritmo-Anonimizacao-Dados.git
cd Algoritmo-Anonimizacao-Dados

python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Gerar a planilha de exemplo

```bash
python -m algoritmo_anonimizacao.cli \
  --input data/base_amostra.csv \
  --output exemplos/saida_anonimizada.xlsx \
  --rows 100 \
  --seed 42
```

No Windows PowerShell, o comando também pode ser executado em uma única linha:

```powershell
python -m algoritmo_anonimizacao.cli --input data/base_amostra.csv --output exemplos/saida_anonimizada.xlsx --rows 100 --seed 42
```

O comando imprime um resumo JSON e cria as três abas descritas acima. Para usar
uma base própria, forneça um CSV com as colunas da tabela de entrada. Não
commite a base real: use `.gitignore`, armazenamento seguro e controle de acesso.

### 3. Executar os testes

```bash
pip install pytest
pytest
```

## Decisões de privacidade

1. **Identificadores diretos:** `registro_id`, `nome` e `email` não aparecem na
   saída; não são mascarados para posterior reidentificação.
2. **Generalização:** cidade vira região, datas viram mês e idade vira faixa.
3. **Redução de precisão:** scores sensíveis viram classes ordinais.
4. **Perturbação:** duração de sessão recebe ruído bounded e categorias podem
   sofrer mutação controlada.
5. **Síntese:** a planilha final contém somente linhas novas; a semente torna a
   execução reproduzível para testes, não sendo um segredo criptográfico.
6. **Governança:** dados reais, chaves, tokens e arquivos exportados com PII não
   devem entrar no Git. Faça revisão de privacidade antes de qualquer publicação.

