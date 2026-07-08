from fastapi import APIRouter, Query

from app.services.map_service import get_map_municipios

router = APIRouter(prefix="/api/map", tags=["map"])


@router.get(
    "/municipios",
    summary="Métricas municipais para mapa (PostGIS, stateless)",
    description=(
        "Consulta parametrizada por ano/mês/UF. Não altera estado global no banco; "
        "cada request é independente (multiusuário)."
    ),
)
def municipios(
    ano: int = Query(..., ge=2000, le=2100),
    mes: int = Query(..., ge=1, le=12),
    uf: str = Query(..., min_length=2, max_length=2),
):
    return get_map_municipios(ano=ano, mes=mes, uf=uf)
