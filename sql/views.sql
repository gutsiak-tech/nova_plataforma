-- Views stateless alinhadas ao schema legado (+ colunas aditivas).

CREATE OR REPLACE VIEW serving.vw_emprego_municipio_mes AS
SELECT
    f.cod_municipio,
    f.municipio,
    g.nome_municipio,
    f.uf,
    f.ano,
    f.mes,
    f.admissoes,
    f.desligamentos,
    f.saldo
FROM serving.fact_emprego_municipio_mes f
LEFT JOIN geo.municipios g
    ON f.cod_municipio IS NOT NULL
   AND f.cod_municipio = g.cod_municipio;

CREATE OR REPLACE VIEW serving.vw_emprego_uf_mes AS
SELECT
    f.ano,
    f.mes,
    f.uf AS uf_sigla,
    f.uf_nome,
    f.cod_uf,
    u.nome_uf,
    f.admissoes,
    f.desligamentos,
    f.saldo
FROM serving.fact_emprego_uf_mes f
LEFT JOIN geo.ufs u
    ON f.uf = u.uf;

CREATE OR REPLACE VIEW serving.vw_mapa_ictt_municipios_pr_mes AS
SELECT
    f.ano,
    f.mes,
    f.cod_municipio,
    f.municipio,
    f.municipio_norm,
    f.uf,
    f.status_calculo,
    f."ICTT" AS ictt,
    f.ranking_ictt,
    f.percentil_ictt,
    f.classe_ictt,
    f.admissoes,
    f.desligamentos,
    f.saldo,
    g.nome_municipio,
    g.geom
FROM serving.fact_ictt_municipio_pr_mes f
LEFT JOIN geo.municipios g
    ON f.cod_municipio = g.cod_municipio;
