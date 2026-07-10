-- Exemplo: usuário PostgreSQL read-only para a API em produção
-- NÃO executar automaticamente. Ajuste nomes de banco/objetos conforme o ambiente.
-- Substitua 'change-me-strong-password' antes de aplicar.
--
-- IMPORTANTE: tabelas e views analíticas ficam nos schemas geo e serving (não public).
-- A API em produção deve usar POSTGRES_USER=caged_readonly.

-- Conectar como superuser (ex.: postgres) no cluster:
--   psql -U postgres -d postgres -f sql/create_readonly_user.example.sql

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'caged_readonly') THEN
        CREATE ROLE caged_readonly LOGIN PASSWORD 'change-me-strong-password';
    END IF;
END
$$;

-- Ajuste o nome do banco (ex.: plataforma ou caged)
GRANT CONNECT ON DATABASE plataforma TO caged_readonly;

\c plataforma

GRANT USAGE ON SCHEMA geo TO caged_readonly;
GRANT USAGE ON SCHEMA serving TO caged_readonly;

GRANT SELECT ON ALL TABLES IN SCHEMA geo TO caged_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA serving TO caged_readonly;

GRANT SELECT ON ALL SEQUENCES IN SCHEMA geo TO caged_readonly;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA serving TO caged_readonly;

-- Objetos futuros (opcional; revisar política institucional)
ALTER DEFAULT PRIVILEGES IN SCHEMA geo
    GRANT SELECT ON TABLES TO caged_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA serving
    GRANT SELECT ON TABLES TO caged_readonly;

-- Defesa em profundidade: revogar escrita explícita
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA geo FROM caged_readonly;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA serving FROM caged_readonly;

-- Não conceder CREATE, DROP, ou superuser.
-- Loaders/migrations devem usar outro usuário (ex.: postgres ou caged_loader).
