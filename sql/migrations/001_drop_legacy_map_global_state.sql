-- Migração: remove artefatos legados de estado global do mapa e alinha schema idempotente.
-- Execute uma vez em bases PostGIS existentes (psql -f sql/migrations/001_drop_legacy_map_global_state.sql).

BEGIN;

-- Materialized view legada (substituída por view parametrizada + filtros por request).
DROP MATERIALIZED VIEW IF EXISTS serving.mv_saldo_municipio CASCADE;

-- Schema reservado para estado global legado (nunca populado neste repositório).
DROP SCHEMA IF EXISTS internal CASCADE;

-- Ajuste de tabela de fatos: adiciona colunas territoriais se vier de schema antigo.
ALTER TABLE serving.fact_emprego_municipio_mes
    ADD COLUMN IF NOT EXISTS uf CHAR(2),
    ADD COLUMN IF NOT EXISTS municipio TEXT,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

-- Remove surrogate key legado se existir (permite PK natural).
ALTER TABLE serving.fact_emprego_municipio_mes
    DROP CONSTRAINT IF EXISTS fact_emprego_municipio_mes_pkey;

ALTER TABLE serving.fact_emprego_municipio_mes
    DROP COLUMN IF EXISTS id;

-- Deduplica antes de criar PK (mantém linha com maior saldo absoluto).
DELETE FROM serving.fact_emprego_municipio_mes a
USING serving.fact_emprego_municipio_mes b
WHERE a.ctid < b.ctid
  AND a.ano = b.ano
  AND a.mes = b.mes
  AND COALESCE(a.uf, '') = COALESCE(b.uf, '')
  AND COALESCE(a.municipio, '') = COALESCE(b.municipio, '');

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'pk_fact_emprego_municipio_mes'
    ) THEN
        ALTER TABLE serving.fact_emprego_municipio_mes
            ADD CONSTRAINT pk_fact_emprego_municipio_mes
            PRIMARY KEY (ano, mes, uf, municipio);
    END IF;
END $$;

-- Geo: colunas de normalização usadas pelo loader.
ALTER TABLE geo.municipios
    ADD COLUMN IF NOT EXISTS nome_municipio_norm TEXT,
    ADD COLUMN IF NOT EXISTS uf_norm TEXT;

COMMIT;

-- Recrie a view parametrizada após migração:
--   psql -f sql/views.sql
