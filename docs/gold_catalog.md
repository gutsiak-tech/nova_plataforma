# Catálogo da camada Gold

_Gerado em: 2026-06-25T14:42:27.413276+00:00_

## O que é a camada Gold

A camada Gold é a camada analítica do projeto CAGED, produzida pelo pipeline `pipelines/gold/aggregate_indicators.py` a partir da Silver. Seus artefatos são consumidos pela API FastAPI e pelo dashboard React.

## Competência

Os dados são particionados por competência no padrão Hive:

```
data-lake/gold/caged/ano=YYYY/mes=MM/
```

Cada competência válida contém tabelas analíticas em CSV e Parquet, além de um Excel consolidado opcional.

## Escopos territoriais

| Escopo no catálogo | Significado | Sufixo de arquivo |
|---|---|---|
| `brasil` | Brasil (sem recorte estadual/metropolitano) | sem sufixo |
| `parana` | Paraná | `_pr` |
| `rmc` | Região Metropolitana de Curitiba | `_rmc` |

## Sufixos de tabelas

- Sem sufixo: escopo Brasil.
- `_pr`: recorte Paraná.
- `_rmc`: recorte RMC.

## Formatos

- **CSV**: formato primário lido pela API.
- **Parquet**: formato colunar espelhado, gerado pelo pipeline.
- **Excel consolidado**: `tabelas_caged_YYYY_MM.xlsx` (não é tabela analítica unitária).

## Granularidades

| Granularidade | Descrição |
|---|---|
| `resumo` | Indicadores agregados da competência |
| `uf` | Agregação por UF |
| `municipio` | Agregação por município |
| `setor` | Agregação por seção/setor |
| `ocupacao` | Agregação por ocupação (CBO) |
| `salario` | Indicadores de salário por recorte |
| `perfil` | Perfil demográfico genérico |
| `perfil_sexo` | Perfil por sexo |
| `perfil_faixa_etaria` | Perfil por faixa etária |
| `perfil_instrucao` | Perfil por grau de instrução |
| `desconhecida` | Não classificada automaticamente |

## Resumo por competência

| Competência | CSV | Parquet | Excel | Suspeitos | Observações |
|---|---:|---:|---:|---|---|
| 2026-01 | 57 | 57 | 1 | — | CSV/Parquet alinhados com pipeline atual (59 tabelas). |
| 2026-02 | 57 | 57 | 1 | — | CSV/Parquet alinhados com pipeline atual (59 tabelas). |
| 2026-03 | 57 | 57 | 1 | — | CSV/Parquet alinhados com pipeline atual (59 tabelas). |
| 2026-04 | 57 | 57 | 1 | — | CSV/Parquet alinhados com pipeline atual (59 tabelas). |

## Tabelas encontradas

| table_name | competências | scope | granularity | row_count | column_count | has_csv | has_parquet | suspected_legacy |
|---|---|---|---|---:|---:|---|---|---|
| tabela_continente | 2026-01, 2026-02, 2026-03, 2026-04 | brasil | continente | 8 | 4 | sim | sim | não |
| tabela_continente_pr | 2026-01, 2026-02, 2026-03, 2026-04 | parana | continente | 7 | 4 | sim | sim | não |
| tabela_continente_rmc | 2026-01, 2026-02, 2026-03, 2026-04 | rmc | continente | 6 | 4 | sim | sim | não |
| tabela_ictt_municipio_pr | 2026-01, 2026-02, 2026-03, 2026-04 | parana | ictt | 399 | 34 | sim | sim | não |
| tabela_municipio | 2026-01, 2026-02, 2026-03, 2026-04 | brasil | municipio | 729 | 5 | sim | sim | não |
| tabela_municipio_pr | 2026-01, 2026-02, 2026-03, 2026-04 | parana | municipio | 104 | 5 | sim | sim | não |
| tabela_municipio_rmc | 2026-01, 2026-02, 2026-03, 2026-04 | rmc | municipio | 18 | 5 | sim | sim | não |
| tabela_ocupacao | 2026-01, 2026-02, 2026-03, 2026-04 | brasil | ocupacao | 1309 | 4 | sim | sim | não |
| tabela_ocupacao_pr | 2026-01, 2026-02, 2026-03, 2026-04 | parana | ocupacao | 640 | 4 | sim | sim | não |
| tabela_ocupacao_rmc | 2026-01, 2026-02, 2026-03, 2026-04 | rmc | ocupacao | 419 | 4 | sim | sim | não |
| tabela_pais | 2026-01, 2026-02, 2026-03, 2026-04 | brasil | pais | 150 | 4 | sim | sim | não |
| tabela_pais_pr | 2026-01, 2026-02, 2026-03, 2026-04 | parana | pais | 99 | 4 | sim | sim | não |
| tabela_pais_rmc | 2026-01, 2026-02, 2026-03, 2026-04 | rmc | pais | 33 | 4 | sim | sim | não |
| tabela_perfil_faixa_etaria | 2026-01, 2026-02, 2026-03, 2026-04 | brasil | perfil_faixa_etaria | 8 | 4 | sim | sim | não |
| tabela_perfil_faixa_etaria_instrucao | 2026-01, 2026-02, 2026-03, 2026-04 | brasil | perfil_faixa_etaria | 49 | 5 | sim | sim | não |
| tabela_perfil_faixa_etaria_instrucao_pr | 2026-01, 2026-02, 2026-03, 2026-04 | parana | perfil_faixa_etaria | 45 | 5 | sim | sim | não |
| tabela_perfil_faixa_etaria_instrucao_rmc | 2026-01, 2026-02, 2026-03, 2026-04 | rmc | perfil_faixa_etaria | 43 | 5 | sim | sim | não |
| tabela_perfil_faixa_etaria_instrucao_salario | 2026-01, 2026-02, 2026-03, 2026-04 | brasil | salario | 49 | 12 | sim | sim | não |
| tabela_perfil_faixa_etaria_instrucao_salario_pr | 2026-01, 2026-02, 2026-03, 2026-04 | parana | salario | 45 | 12 | sim | sim | não |
| tabela_perfil_faixa_etaria_instrucao_salario_rmc | 2026-01, 2026-02, 2026-03, 2026-04 | rmc | salario | 43 | 12 | sim | sim | não |
| tabela_perfil_faixa_etaria_pr | 2026-01, 2026-02, 2026-03, 2026-04 | parana | perfil_faixa_etaria | 7 | 4 | sim | sim | não |
| tabela_perfil_faixa_etaria_rmc | 2026-01, 2026-02, 2026-03, 2026-04 | rmc | perfil_faixa_etaria | 7 | 4 | sim | sim | não |
| tabela_perfil_faixa_etaria_salario | 2026-01, 2026-02, 2026-03, 2026-04 | brasil | salario | 8 | 11 | sim | sim | não |
| tabela_perfil_faixa_etaria_salario_pr | 2026-01, 2026-02, 2026-03, 2026-04 | parana | salario | 7 | 11 | sim | sim | não |
| tabela_perfil_faixa_etaria_salario_rmc | 2026-01, 2026-02, 2026-03, 2026-04 | rmc | salario | 7 | 11 | sim | sim | não |
| tabela_perfil_graudeinstrucao | 2026-01, 2026-02, 2026-03, 2026-04 | brasil | perfil_instrucao | 7 | 4 | sim | sim | não |
| tabela_perfil_graudeinstrucao_pr | 2026-01, 2026-02, 2026-03, 2026-04 | parana | perfil_instrucao | 7 | 4 | sim | sim | não |
| tabela_perfil_graudeinstrucao_rmc | 2026-01, 2026-02, 2026-03, 2026-04 | rmc | perfil_instrucao | 7 | 4 | sim | sim | não |
| tabela_perfil_graudeinstrucao_salario | 2026-01, 2026-02, 2026-03, 2026-04 | brasil | salario | 7 | 11 | sim | sim | não |
| tabela_perfil_graudeinstrucao_salario_pr | 2026-01, 2026-02, 2026-03, 2026-04 | parana | salario | 7 | 11 | sim | sim | não |
| tabela_perfil_graudeinstrucao_salario_rmc | 2026-01, 2026-02, 2026-03, 2026-04 | rmc | salario | 7 | 11 | sim | sim | não |
| tabela_perfil_racacor | 2026-01, 2026-02, 2026-03, 2026-04 | brasil | perfil_racacor | 6 | 4 | sim | sim | não |
| tabela_perfil_racacor_pr | 2026-01, 2026-02, 2026-03, 2026-04 | parana | perfil_racacor | 6 | 4 | sim | sim | não |
| tabela_perfil_racacor_rmc | 2026-01, 2026-02, 2026-03, 2026-04 | rmc | perfil_racacor | 6 | 4 | sim | sim | não |
| tabela_perfil_sexo | 2026-01, 2026-02, 2026-03, 2026-04 | brasil | perfil_sexo | 2 | 4 | sim | sim | não |
| tabela_perfil_sexo_faixa_etaria | 2026-01, 2026-02, 2026-03, 2026-04 | brasil | perfil_sexo | 15 | 5 | sim | sim | não |
| tabela_perfil_sexo_faixa_etaria_pr | 2026-01, 2026-02, 2026-03, 2026-04 | parana | perfil_sexo | 14 | 5 | sim | sim | não |
| tabela_perfil_sexo_faixa_etaria_rmc | 2026-01, 2026-02, 2026-03, 2026-04 | rmc | perfil_sexo | 14 | 5 | sim | sim | não |
| tabela_perfil_sexo_faixa_etaria_salario | 2026-01, 2026-02, 2026-03, 2026-04 | brasil | salario | 15 | 12 | sim | sim | não |
| tabela_perfil_sexo_faixa_etaria_salario_pr | 2026-01, 2026-02, 2026-03, 2026-04 | parana | salario | 14 | 12 | sim | sim | não |
| tabela_perfil_sexo_faixa_etaria_salario_rmc | 2026-01, 2026-02, 2026-03, 2026-04 | rmc | salario | 14 | 12 | sim | sim | não |
| tabela_perfil_sexo_instrucao | 2026-01, 2026-02, 2026-03, 2026-04 | brasil | perfil_sexo | 14 | 5 | sim | sim | não |
| tabela_perfil_sexo_instrucao_pr | 2026-01, 2026-02, 2026-03, 2026-04 | parana | perfil_sexo | 14 | 5 | sim | sim | não |
| tabela_perfil_sexo_instrucao_rmc | 2026-01, 2026-02, 2026-03, 2026-04 | rmc | perfil_sexo | 14 | 5 | sim | sim | não |
| tabela_perfil_sexo_instrucao_salario | 2026-01, 2026-02, 2026-03, 2026-04 | brasil | salario | 14 | 12 | sim | sim | não |
| tabela_perfil_sexo_instrucao_salario_pr | 2026-01, 2026-02, 2026-03, 2026-04 | parana | salario | 14 | 12 | sim | sim | não |
| tabela_perfil_sexo_instrucao_salario_rmc | 2026-01, 2026-02, 2026-03, 2026-04 | rmc | salario | 14 | 12 | sim | sim | não |
| tabela_perfil_sexo_pr | 2026-01, 2026-02, 2026-03, 2026-04 | parana | perfil_sexo | 2 | 4 | sim | sim | não |
| tabela_perfil_sexo_rmc | 2026-01, 2026-02, 2026-03, 2026-04 | rmc | perfil_sexo | 2 | 4 | sim | sim | não |
| tabela_perfil_sexo_salario | 2026-01, 2026-02, 2026-03, 2026-04 | brasil | salario | 2 | 11 | sim | sim | não |
| tabela_perfil_sexo_salario_pr | 2026-01, 2026-02, 2026-03, 2026-04 | parana | salario | 2 | 11 | sim | sim | não |
| tabela_perfil_sexo_salario_rmc | 2026-01, 2026-02, 2026-03, 2026-04 | rmc | salario | 2 | 11 | sim | sim | não |
| tabela_resumo | 2026-01, 2026-02, 2026-03, 2026-04 | brasil | resumo | 1 | 4 | sim | sim | não |
| tabela_setor | 2026-01, 2026-02, 2026-03, 2026-04 | brasil | setor | 21 | 4 | sim | sim | não |
| tabela_setor_pr | 2026-01, 2026-02, 2026-03, 2026-04 | parana | setor | 19 | 4 | sim | sim | não |
| tabela_setor_rmc | 2026-01, 2026-02, 2026-03, 2026-04 | rmc | setor | 19 | 4 | sim | sim | não |
| tabela_uf | 2026-01, 2026-02, 2026-03, 2026-04 | brasil | uf | 28 | 4 | sim | sim | não |

## Artefatos suspeitos

Nenhum artefato suspeito identificado nas competências atuais.

## Observações

- Regenerar o catálogo após cada processamento mensal com `python -m pipelines.jobs.build_gold_catalog`.
- O catálogo não altera arquivos Gold; apenas documenta metadados.
- Tabelas legadas `tabela_perfil`, `tabela_perfil_pr` e `tabela_perfil_rmc` devem ser marcadas como suspeitas caso reapareçam.
- Integração futura recomendada: executar o job de catálogo ao final do pipeline mensal.
