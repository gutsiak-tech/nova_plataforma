from pathlib import Path
import logging
import os
from dotenv import load_dotenv

load_dotenv()

_config_logger = logging.getLogger("app.core.config")

# =========================
# Raiz do projeto
# =========================
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# =========================
# Diretórios principais
# =========================
DATA_LAKE_DIR = PROJECT_ROOT / "data-lake"
BRONZE_DIR = DATA_LAKE_DIR / "bronze"
SILVER_DIR = DATA_LAKE_DIR / "silver"
GOLD_DIR = DATA_LAKE_DIR / "gold"

APP_DIR = PROJECT_ROOT / "app"
PIPELINES_DIR = PROJECT_ROOT / "pipelines"
SQL_DIR = PROJECT_ROOT / "sql"
INFRA_DIR = PROJECT_ROOT / "infra"
LOGS_DIR = PROJECT_ROOT / "logs"
TESTS_DIR = PROJECT_ROOT / "tests"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
SRC_LEGACY_DIR = PROJECT_ROOT / "src"

# =========================
# Subárvores de dados
# =========================
BRONZE_CAGED_DIR = BRONZE_DIR / "caged"
SILVER_CAGED_DIR = SILVER_DIR / "caged"
GOLD_CAGED_DIR = GOLD_DIR / "caged"

# =========================
# Configurações gerais
# =========================
DEFAULT_ANO = int(os.getenv("DEFAULT_ANO", "2026"))
DEFAULT_MES = int(os.getenv("DEFAULT_MES", "4"))
DEFAULT_UF = os.getenv("DEFAULT_UF", "PR")

# =========================
# Gold data backend
# =========================
_ALLOWED_GOLD_BACKENDS = frozenset({"filesystem", "postgis"})


def resolve_gold_backend(raw: str | None = None) -> str:
    """Resolve GOLD_BACKEND. Default e valores inválidos → filesystem."""
    value = (raw if raw is not None else os.getenv("GOLD_BACKEND", "filesystem")).strip().lower()
    if not value:
        return "filesystem"
    if value not in _ALLOWED_GOLD_BACKENDS:
        _config_logger.warning(
            "GOLD_BACKEND inválido=%r; usando filesystem. Valores aceitos: filesystem | postgis",
            value,
        )
        return "filesystem"
    return value


GOLD_BACKEND = resolve_gold_backend()

# =========================
# Bronze — validação de ingestão
# =========================
BRONZE_MIN_FILE_SIZE_WARNING_BYTES = int(
    os.getenv("BRONZE_MIN_FILE_SIZE_WARNING_BYTES", "50000")
)
BRONZE_SAMPLE_ROWS = int(os.getenv("BRONZE_SAMPLE_ROWS", "100"))

# =========================
# Banco de dados
# =========================
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "plataforma")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

# =========================
# Segurança / CORS / debug
# =========================
APP_ENV = os.getenv("APP_ENV", "local").strip().lower()
ADMIN_BEARER_TOKEN = os.getenv("ADMIN_BEARER_TOKEN", "").strip()


def is_production_env() -> bool:
    return APP_ENV in ("production", "prod")


ENABLE_DEBUG_ROUTES = os.getenv("ENABLE_DEBUG_ROUTES", "false").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)


def _env_bool(name: str, *, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return default


def resolve_enable_admin_routes() -> bool:
    """Em produção desabilitado por padrão; em dev/local habilitado por padrão."""
    return _env_bool("ENABLE_ADMIN_ROUTES", default=not is_production_env())


ENABLE_ADMIN_ROUTES = resolve_enable_admin_routes()


def resolve_rate_limit_enabled() -> bool:
    """Habilitado por padrão em produção; desabilitado em dev/local."""
    return _env_bool("RATE_LIMIT_ENABLED", default=is_production_env())


RATE_LIMIT_ENABLED = resolve_rate_limit_enabled()
RATE_LIMIT_PER_MINUTE = max(1, min(int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")), 10_000))

_DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
)


def parse_cors_allowed_origins(raw: str | None = None) -> list[str]:
    value = raw if raw is not None else os.getenv("CORS_ALLOWED_ORIGINS", "")
    if not value.strip():
        return list(_DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in value.split(",") if origin.strip()]


CORS_ALLOWED_ORIGINS = parse_cors_allowed_origins()

# =========================
# Logs
# =========================
PIPELINE_LOG_FILE = LOGS_DIR / "pipeline.log"
API_LOG_FILE = LOGS_DIR / "api.log"