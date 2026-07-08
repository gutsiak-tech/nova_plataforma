-- Migration 002 (compatível com schema legado já presente no volume Docker).
-- Apenas ADD COLUMN / INDEX / VIEW idempotentes. Sem DROP/TRUNCATE.

BEGIN;

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS geo;
CREATE SCHEMA IF NOT EXISTS serving;

-- ---------------------------------------------------------------------------
-- Tabelas mínimas se a base for nova (CREATE IF NOT EXISTS)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS geo.municipios (
    cod_municipio VARCHAR(7) PRIMARY KEY,
    nome_municipio TEXT NOT NULL,
    uf CHAR(2) NOT NULL,
    nome_municipio_norm TEXT,
    uf_norm TEXT,
    geom geometry(MultiPolygon, 4326)
);

ALTER TABLE geo.municipios
    ADD COLUMN IF NOT EXISTS nome_municipio_norm TEXT,
    ADD COLUMN IF NOT EXISTS uf_norm TEXT;

-- Legado: municipios_rmc pode ser só (cod_municipio, nome_municipio_norm) com FK.
CREATE TABLE IF NOT EXISTS geo.municipios_rmc (
    cod_municipio VARCHAR(7) PRIMARY KEY,
    nome_municipio_norm TEXT
);

-- Legado: geo.ufs usa PK uf (sigla CHAR2)
CREATE TABLE IF NOT EXISTS geo.ufs (
    uf CHAR(2) PRIMARY KEY,
    nome_uf TEXT NOT NULL,
    cod_uf VARCHAR(2),
    nome_uf_norm TEXT,
    geom geometry(MultiPolygon, 4326)
);

ALTER TABLE geo.ufs
    ADD COLUMN IF NOT EXISTS cod_uf VARCHAR(2),
    ADD COLUMN IF NOT EXISTS nome_uf_norm TEXT;

CREATE TABLE IF NOT EXISTS serving.fact_emprego_municipio_mes (
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    uf CHAR(2) NOT NULL,
    municipio TEXT NOT NULL,
    cod_municipio VARCHAR(7),
    admissoes INTEGER,
    desligamentos INTEGER,
    saldo INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT pk_fact_emprego_municipio_mes PRIMARY KEY (ano, mes, uf, municipio)
);

ALTER TABLE serving.fact_emprego_municipio_mes
    ADD COLUMN IF NOT EXISTS cod_municipio VARCHAR(7),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();

CREATE UNIQUE INDEX IF NOT EXISTS uq_fact_emprego_municipio_mes_ano_mes_cod
ON serving.fact_emprego_municipio_mes (ano, mes, cod_municipio)
WHERE cod_municipio IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_fact_emprego_municipio_mes_cod
ON serving.fact_emprego_municipio_mes (cod_municipio);

-- Legado UF facts: coluna uf (sigla) como PK parcial
CREATE TABLE IF NOT EXISTS serving.fact_emprego_uf_mes (
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    uf CHAR(2) NOT NULL,
    admissoes INTEGER,
    desligamentos INTEGER,
    saldo INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT pk_fact_emprego_uf_mes PRIMARY KEY (ano, mes, uf)
);

ALTER TABLE serving.fact_emprego_uf_mes
    ADD COLUMN IF NOT EXISTS uf_nome TEXT,
    ADD COLUMN IF NOT EXISTS cod_uf VARCHAR(2),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_fact_emprego_uf_mes_competencia
ON serving.fact_emprego_uf_mes (ano, mes);

-- ICTT: schema legado amplo; garante cod_municipio + updated_at
CREATE TABLE IF NOT EXISTS serving.fact_ictt_municipio_pr_mes (
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    uf TEXT NOT NULL,
    municipio TEXT NOT NULL,
    municipio_norm TEXT,
    cod_municipio VARCHAR(7),
    status_calculo TEXT,
    "ICTT" DOUBLE PRECISION,
    ranking_ictt DOUBLE PRECISION,
    percentil_ictt DOUBLE PRECISION,
    classe_ictt TEXT,
    admissoes DOUBLE PRECISION,
    desligamentos DOUBLE PRECISION,
    saldo DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT pk_fact_ictt_municipio_pr_mes PRIMARY KEY (ano, mes, municipio)
);

ALTER TABLE serving.fact_ictt_municipio_pr_mes
    ADD COLUMN IF NOT EXISTS cod_municipio VARCHAR(7),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_fact_ictt_municipio_pr_mes_cod_municipio
ON serving.fact_ictt_municipio_pr_mes (cod_municipio);

CREATE UNIQUE INDEX IF NOT EXISTS uq_fact_ictt_municipio_pr_mes_ano_mes_cod
ON serving.fact_ictt_municipio_pr_mes (ano, mes, cod_municipio)
WHERE cod_municipio IS NOT NULL;

-- Views adaptadas ao schema legado
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

COMMIT;
