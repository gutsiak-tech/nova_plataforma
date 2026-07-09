-- Exemplo: usuário PostgreSQL read-only para a API em produção
-- NÃO executar automaticamente. Ajuste nomes de tabelas/views conforme o schema real.
-- Substitua 'change-me-strong-password' antes de aplicar.

-- Conectar como superuser (ex.: postgres) no banco alvo:
--   psql -U postgres -d caged -f sql/create_readonly_user.example.sql

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'caged_readonly') THEN
        CREATE ROLE caged_readonly LOGIN PASSWORD 'change-me-strong-password';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE caged TO caged_readonly;

\c caged

GRANT USAGE ON SCHEMA public TO caged_readonly;

-- Tabelas/views Gold analíticas (ajuste a lista após \dt no schema public)
GRANT SELECT ON ALL TABLES IN SCHEMA public TO caged_readonly;

-- Garantir SELECT em objetos criados no futuro (opcional; revisar política institucional)
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO caged_readonly;

-- Revogar escrita explícita (defesa em profundidade se o role herdou permissões)
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA public FROM caged_readonly;

-- PostGIS: leitura de geometrias
GRANT USAGE ON SCHEMA public TO caged_readonly;

-- Sequências (somente leitura, se necessário para algumas views)
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO caged_readonly;

-- Não conceder CREATE, DROP, ou superuser.
-- A API deve usar POSTGRES_USER=caged_readonly em produção.
