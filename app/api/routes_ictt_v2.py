"""Endpoints versionados do ICTT methodology version 2.0.

V1 continua ativa em ``/api/ict/v1`` (não depreciada; PCA).
V2 é paralelo e explícito em ``/api/ict/v2``.
Fonte canônica: Gold Parquet ``.../ictt_v2/tabela_ictt_v2_municipio_pr.parquet``.
A API é somente serving: não recalcula o índice, não lê CSV nem microdados,
não usa PostGIS.
"""

from __future__ import annotations

from typing import NoReturn

from fastapi import APIRouter, Query

from app.api.errors import GoldAPIError
from app.api.schemas_ictt_v2 import (
    V2_ENDPOINT_DESCRIPTION,
    IcttV2CompetenciasResponse,
    IcttV2Dimension,
    IcttV2Eligibility,
    IcttV2ListMeta,
    IcttV2MethodologyResponse,
    IcttV2MunicipalityDetail,
    IcttV2MunicipalityDetailResponse,
    IcttV2MunicipalityListResponse,
    IcttV2MunicipalityPublic,
    IcttV2RankingMeta,
    IcttV2RankingResponse,
    IcttV2ReferencePeriod,
    RankingUniverse,
    ReliabilityClass,
)
from app.core.config import API_LOG_FILE
from app.core.logging import setup_logger
from app.repositories.ictt_v2_repository import (
    IcttV2ArtifactError,
    IcttV2InvalidCompetenciaError,
    IcttV2InvalidMunicipalityCodeError,
    IcttV2MunicipalityNotFoundError,
    IcttV2PartitionNotFoundError,
    IcttV2Repository,
    IcttV2RepositoryError,
    parse_competencia,
)
from pipelines.gold.ictt_v2.spec import frozen_spec

router = APIRouter(prefix="/api/ict/v2", tags=["ict-v2"])
logger = setup_logger("api.ict.v2", API_LOG_FILE)
_repository = IcttV2Repository()


def _raise_repo_error(exc: Exception) -> NoReturn:
    if isinstance(exc, IcttV2InvalidCompetenciaError):
        raise GoldAPIError(
            "INVALID_COMPETENCIA",
            str(exc),
            status_code=400,
        ) from exc
    if isinstance(exc, IcttV2InvalidMunicipalityCodeError):
        raise GoldAPIError(
            "INVALID_MUNICIPALITY_CODE",
            str(exc),
            status_code=400,
        ) from exc
    if isinstance(exc, IcttV2PartitionNotFoundError):
        raise GoldAPIError(
            "ICTT_V2_NOT_FOUND",
            str(exc),
            status_code=404,
        ) from exc
    if isinstance(exc, IcttV2MunicipalityNotFoundError):
        raise GoldAPIError(
            "ICTT_V2_MUNICIPALITY_NOT_FOUND",
            str(exc),
            status_code=404,
        ) from exc
    if isinstance(exc, IcttV2ArtifactError):
        raise GoldAPIError(
            "ICTT_V2_ARTIFACT_INVALID",
            str(exc),
            status_code=500,
        ) from exc
    raise exc


def _validated_competencia(raw: str) -> str:
    try:
        _ano, _mes, competencia = parse_competencia(raw)
    except IcttV2InvalidCompetenciaError as exc:
        _raise_repo_error(exc)
    return competencia


def _parse_reliability(raw: str | None) -> ReliabilityClass | None:
    if raw is None or raw.strip() == "":
        return None
    value = raw.strip().lower()
    if value in ("reduced", "higher"):
        return ReliabilityClass(value)
    raise GoldAPIError(
        "INVALID_RELIABILITY",
        "reliability inválido. Use: reduced | higher.",
        {"reliability": raw},
        status_code=400,
    )


def _parse_universe(raw: str) -> RankingUniverse:
    value = (raw or "").strip().lower()
    if value in ("n10", "n20"):
        return RankingUniverse(value)
    raise GoldAPIError(
        "INVALID_UNIVERSE",
        "universe inválido. Use: n10 | n20.",
        {"universe": raw},
        status_code=400,
    )


def _methodology_payload() -> IcttV2MethodologyResponse:
    spec = frozen_spec()
    return IcttV2MethodologyResponse(
        methodology_version=spec.methodology_version,
        normalization_version=spec.normalization_version,
        reference_scope=spec.reference_scope,
        reference_period=IcttV2ReferencePeriod(
            start=spec.reference_start,
            end=spec.reference_end,
        ),
        eligibility=IcttV2Eligibility(
            min_admissions=spec.min_admissions_calculable,
            higher_reliability_from=spec.robust_admissions_threshold,
        ),
        dimensions=[
            IcttV2Dimension(key="absorcao", weight=spec.weight_absorption),
            IcttV2Dimension(key="remuneracao", weight=spec.weight_remuneration),
            IcttV2Dimension(
                key="qualidade_contratual",
                weight=spec.weight_contract_quality,
            ),
            IcttV2Dimension(
                key="diversificacao",
                weight=spec.weight_diversification,
            ),
        ],
    )


def _list_meta(raw_meta: dict, reliability: ReliabilityClass | None = None) -> IcttV2ListMeta:
    return IcttV2ListMeta(
        competencia=raw_meta["competencia"],
        methodology_version=raw_meta["methodology_version"],
        normalization_version=raw_meta["normalization_version"],
        n_municipalities=raw_meta["n_municipalities"],
        n_calculable=raw_meta["n_calculable"],
        reliability=reliability,
    )


@router.get(
    "/competencias",
    response_model=IcttV2CompetenciasResponse,
    summary="Competências Gold do ICTT v2.0",
    description=V2_ENDPOINT_DESCRIPTION,
)
def list_competencias() -> IcttV2CompetenciasResponse:
    spec = frozen_spec()
    competencias = _repository.list_competencias()
    logger.info("ICTT v2 competencias | n=%s", len(competencias))
    return IcttV2CompetenciasResponse(
        methodology_version=spec.methodology_version,
        competencias=competencias,
    )


@router.get(
    "/methodology",
    response_model=IcttV2MethodologyResponse,
    summary="Metodologia pública do ICTT v2.0",
    description=V2_ENDPOINT_DESCRIPTION,
)
def methodology() -> IcttV2MethodologyResponse:
    return _methodology_payload()


@router.get(
    "/municipalities",
    response_model=IcttV2MunicipalityListResponse,
    summary="Lista municipal do ICTT v2.0",
    description=V2_ENDPOINT_DESCRIPTION,
)
def list_municipalities(
    competencia: str = Query(
        ...,
        description="Competência YYYY-MM da partição Gold v2.",
        examples=["2026-04"],
    ),
    reliability: str | None = Query(
        None,
        description="Filtro opcional de confiabilidade: reduced | higher. "
        "Municípios N10–19 (reduced) possuem ICTT v2 válido.",
    ),
) -> IcttV2MunicipalityListResponse:
    competencia_key = _validated_competencia(competencia)
    reliability_filter = _parse_reliability(reliability)
    try:
        meta, rows = _repository.list_municipalities(
            competencia_key,
            reliability=None if reliability_filter is None else reliability_filter.value,
        )
    except IcttV2RepositoryError as exc:
        _raise_repo_error(exc)
    logger.info(
        "ICTT v2 municipalities | competencia=%s | n=%s | reliability=%s",
        competencia_key,
        len(rows),
        reliability_filter,
    )
    return IcttV2MunicipalityListResponse(
        meta=_list_meta(meta, reliability_filter),
        data=[IcttV2MunicipalityPublic.model_validate(row) for row in rows],
    )


@router.get(
    "/municipalities/{codigo_municipio}",
    response_model=IcttV2MunicipalityDetailResponse,
    summary="Detalhe municipal do ICTT v2.0",
    description=V2_ENDPOINT_DESCRIPTION,
)
def get_municipality(
    codigo_municipio: str,
    competencia: str = Query(
        ...,
        description="Competência YYYY-MM da partição Gold v2.",
        examples=["2026-04"],
    ),
) -> IcttV2MunicipalityDetailResponse:
    competencia_key = _validated_competencia(competencia)
    try:
        meta, row = _repository.get_municipality(competencia_key, codigo_municipio)
    except IcttV2RepositoryError as exc:
        _raise_repo_error(exc)
    logger.info(
        "ICTT v2 municipality | competencia=%s | codigo=%s",
        competencia_key,
        codigo_municipio,
    )
    return IcttV2MunicipalityDetailResponse(
        meta=_list_meta(meta),
        data=IcttV2MunicipalityDetail.model_validate(row),
    )


@router.get(
    "/ranking",
    response_model=IcttV2RankingResponse,
    summary="Ranking municipal do ICTT v2.0 (universos N10 e N20)",
    description=V2_ENDPOINT_DESCRIPTION,
)
def ranking(
    competencia: str = Query(
        ...,
        description="Competência YYYY-MM da partição Gold v2.",
        examples=["2026-04"],
    ),
    universe: str = Query(
        ...,
        description="Universo de ranking: n10 (admissões >= 10) ou n20 (admissões >= 20). "
        "A API não escolhe ranking oficial.",
    ),
) -> IcttV2RankingResponse:
    competencia_key = _validated_competencia(competencia)
    universe_key = _parse_universe(universe)
    try:
        meta, rows = _repository.ranking(competencia_key, universe_key.value)
    except IcttV2RepositoryError as exc:
        _raise_repo_error(exc)
    logger.info(
        "ICTT v2 ranking | competencia=%s | universe=%s | n=%s",
        competencia_key,
        universe_key.value,
        len(rows),
    )
    list_meta = _list_meta(meta)
    return IcttV2RankingResponse(
        meta=IcttV2RankingMeta(
            **list_meta.model_dump(),
            universe=universe_key,
            n_ranked=int(meta["n_ranked"]),
        ),
        data=[IcttV2MunicipalityPublic.model_validate(row) for row in rows],
    )
