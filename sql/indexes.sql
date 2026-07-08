CREATE INDEX IF NOT EXISTS idx_geo_municipios_geom
ON geo.municipios
USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_geo_municipios_uf
ON geo.municipios (uf);

CREATE INDEX IF NOT EXISTS idx_geo_ufs_geom
ON geo.ufs
USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_fact_emprego_municipio_mes_competencia
ON serving.fact_emprego_municipio_mes (ano, mes);

CREATE INDEX IF NOT EXISTS idx_fact_emprego_municipio_mes_uf
ON serving.fact_emprego_municipio_mes (uf);

CREATE INDEX IF NOT EXISTS idx_fact_emprego_municipio_mes_cod
ON serving.fact_emprego_municipio_mes (cod_municipio);

CREATE UNIQUE INDEX IF NOT EXISTS uq_fact_emprego_municipio_mes_ano_mes_cod
ON serving.fact_emprego_municipio_mes (ano, mes, cod_municipio)
WHERE cod_municipio IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_fact_emprego_uf_mes_competencia
ON serving.fact_emprego_uf_mes (ano, mes);

CREATE INDEX IF NOT EXISTS idx_fact_ictt_municipio_pr_mes_competencia
ON serving.fact_ictt_municipio_pr_mes (ano, mes);

CREATE INDEX IF NOT EXISTS idx_fact_ictt_municipio_pr_mes_cod_municipio
ON serving.fact_ictt_municipio_pr_mes (cod_municipio);

CREATE UNIQUE INDEX IF NOT EXISTS uq_fact_ictt_municipio_pr_mes_ano_mes_cod
ON serving.fact_ictt_municipio_pr_mes (ano, mes, cod_municipio)
WHERE cod_municipio IS NOT NULL;
