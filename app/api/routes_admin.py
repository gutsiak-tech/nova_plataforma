from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import require_admin_bearer
from pipelines.gold.load_fact_tables import load_fact_emprego_municipio
from pipelines.gold.load_geo_tables import load_municipios_geometria

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_bearer)],
)


@router.post("/load/fact-municipio")
def admin_load_fact_municipio(
    ano: int = Query(..., ge=2000, le=2100),
    mes: int = Query(..., ge=1, le=12),
):
    """Dispara carga idempotente de fatos municipais (PostGIS) para uma competência."""
    try:
        load_fact_emprego_municipio(ano=ano, mes=mes)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gold partition not found for the requested competencia.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load fact table.",
        ) from exc

    return {"status": "ok", "operation": "load_fact_emprego_municipio", "ano": ano, "mes": mes}


@router.post("/load/geo-municipios")
def admin_load_geo_municipios(
    shapefile_path: str = Query(..., min_length=1),
    coluna_nome: str = Query(..., min_length=1),
    coluna_uf: str = Query(..., min_length=1),
    coluna_codigo: str | None = Query(None),
):
    """Dispara carga idempotente de geometrias municipais (UPSERT por cod_municipio)."""
    try:
        load_municipios_geometria(
            shapefile_path=shapefile_path,
            coluna_nome=coluna_nome,
            coluna_uf=coluna_uf,
            coluna_codigo=coluna_codigo,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load geo table.",
        ) from exc

    return {"status": "ok", "operation": "load_municipios_geometria"}
