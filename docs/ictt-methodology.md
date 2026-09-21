# ICTT v2.0 — methodology

Índice de Competitividade Territorial do Trabalho, versão **2.0**. Spec congelada em `pipelines/gold/ictt_v2/methodology_v2.json` (`methodology_version: "2.0"`, `normalization_version: NORM_B.2026-01_2026-04.N233`).

Esta página descreve a especificação publicada. Não é um diário de experimentação.

## 1. Objetivo

Sintetizar, em escala 0–100, a posição relativa dos municípios paranaenses na absorção, remuneração, qualidade contratual e diversificação das movimentações formais de trabalhadores migrantes.

## 2. Unidade de análise

Município (código IBGE de 7 dígitos), competência mensal `YYYY-MM`.

## 3. Universo

Malha municipal do Paraná usada pelo pipeline Gold. Registros com município `IGNORADO` não entram na malha.

## 4. Critério mínimo de cálculo

| Admissões elegíveis (N) | Situação |
|---|---|
| N < 10 | ICTT não calculável (`null`) |
| 10 ≤ N < 20 | Calculável, confiabilidade reduzida |
| N ≥ 20 | Calculável, maior robustez |

`higher` descreve robustez amostral relativa. Não equivale a certeza estatística.

## 5. Dimensões

Pesos do índice:

```
ICTT = 0.25 A + 0.25 R + 0.25 Q + 0.25 D
```

Os pesos são **normativos**, não estimados.

### 5.1 Absorção (A)

Combina volume e saldo suavizado:

- volume: `log1p(admissões)`, normalizado por NORM_B
- saldo: `100 × (admissões + c) / (admissões + desligamentos + λ)`, com `c = 5` e `λ = 10`

Pesos internos: 50% / 50%.

### 5.2 Remuneração (R)

Mediana salarial municipal na regra R4, relativa à mediana estadual da competência. R4 exclui vínculos intermitentes e aplica faixa `[0,3 ; 150]` salários mínimos do ano. Salários mínimos versionados: 2025 = 1518; 2026 = 1621.

### 5.3 Qualidade contratual (Q)

Menor incidência relativa de vínculos parciais e intermitentes nas admissões:

```
Q_parcial = 100 − min(100, k × %parcial)
Q_intermitente = 100 − min(100, k × %intermitente)
```

`k = 10`. Pesos internos: 50% / 50%.

### 5.4 Diversificação (D)

Média de Shannon em CBO, subclasse e seção, estimada sobre todas as movimentações (admissões + desligamentos). Pesos internos iguais (~1/3).

## 6. Normalização

`NORM_B` usa P05/P95 congelados:

```
score = 100 × clip((x − P05) / (P95 − P05), 0, 1)
```

Referência:

- recorte: Paraná
- janela: 2026-01 a 2026-04
- elegibilidade: N ≥ 10
- N pooled: 233 observações município-mês

Os percentis **não** são recalculados em produção nem no backfill.

### P05 / P95 (NORM_B)

| Variável | P05 | P95 |
|---|---:|---:|
| `a_volume_raw` (`log1p` admissões) | 2.4501 | 6.1425 |
| `salario_relativo_r4` | 0.9171 | 1.1088 |
| Shannon CBO | 0.1646 | 3.8805 |
| Shannon subclasse | 0.2524 | 4.0103 |
| Shannon seção | 0.0000 | 1.9144 |

## 7. Agregação

Após as quatro dimensões na escala 0–100:

```
ICTT = 0.25 A + 0.25 R + 0.25 Q + 0.25 D
```

Municípios com N < 10 recebem `ictt_v2 = null` e dimensões nulas. Zero não é usado como sentença.

## 8. Confiabilidade

Campo `reliability_class`:

- `reduced` — 10–19 admissões
- `higher` — 20 ou mais admissões
- `null` — não calculável

A UI usa “Confiabilidade reduzida” e “Maior robustez”.

## 9. Ranking N10 / N20

Há dois universos de ordenação, ambos derivados do mesmo score:

| Universo | Critério | Uso na UI |
|---|---|---|
| `n10` | N ≥ 10 | opcional |
| `n20` | N ≥ 20 | padrão |

A API não escolhe ranking oficial. O frontend começa em N ≥ 20; a troca é visual.

## 10. Validação

Holdout 2025, 12 meses, parâmetros congelados, sem retuning.

A avaliação apoia:

- transportabilidade da spec para outro ano
- clipping baixo na normalização congelada
- concordância elevada entre scores frozen e rebased (Spearman ≈ 0,997)
- cobertura de admissões do universo N10 em torno de 97%
- maior incerteza em N10–19 do que em N20+
- correlação ICTT × volume de admissões bem menor que na V1
- zero violações de monotonicidade nos testes da spec

Isso não prova que o índice seja uma medida “científica absoluta” do mercado de trabalho. Indica que a especificação congelada se comporta de forma estável nas checagens aplicadas.

## 11. Limitações

- Q concentra massa elevada em 100 (muitos municípios com baixa incidência de parcial/intermitente).
- Pesos são normativos.
- D permanece altamente correlacionado ao índice agregado.
- R4 é empiricamente próximo de um recorte salarial sem o filtro intermitente (R0) nesta base.
- Município `IGNORADO` fica fora da malha.
- NORM_B é estadual e de janela definida (jan–abr/2026).
- A competência é mensal: sazonalidade exige leitura contextual.

## 12. Versionamento

| Versão | Papel |
|---|---|
| ICTT v1 | PCA sobre a Gold municipal; API `/api/ict/v1`; UI `/ict-v1` |
| ICTT v2.0 | Quatro dimensões iguais + NORM_B; API `/api/ict/v2`; UI `/ict` |

A V1 não é recalculada pelo job v2. Os artefatos Gold são paralelos.
