CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS geo;
CREATE SCHEMA IF NOT EXISTS serving;

-- Schema alinhado ao volume legado + extensões aditivas (cod_municipio).
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

CREATE TABLE IF NOT EXISTS serving.fact_emprego_uf_mes (
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    uf CHAR(2) NOT NULL,
    uf_nome TEXT,
    cod_uf VARCHAR(2),
    admissoes INTEGER,
    desligamentos INTEGER,
    saldo INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT pk_fact_emprego_uf_mes PRIMARY KEY (ano, mes, uf)
);

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

CREATE TABLE IF NOT EXISTS geo.municipios (
    cod_municipio VARCHAR(7) PRIMARY KEY,
    nome_municipio TEXT NOT NULL,
    uf CHAR(2) NOT NULL,
    nome_municipio_norm TEXT,
    uf_norm TEXT,
    geom geometry(MultiPolygon, 4326)
);

CREATE TABLE IF NOT EXISTS geo.municipios_rmc (
    cod_municipio VARCHAR(7) PRIMARY KEY,
    nome_municipio_norm TEXT
);

CREATE TABLE IF NOT EXISTS geo.ufs (
    uf CHAR(2) PRIMARY KEY,
    nome_uf TEXT NOT NULL,
    cod_uf VARCHAR(2),
    nome_uf_norm TEXT,
    geom geometry(MultiPolygon, 4326)
);
