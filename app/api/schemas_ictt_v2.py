"""Contratos públicos da API ICTT methodology version 2.0.

Schemas próprios da V2: não reutilizam o contexto analítico da V1 (PCA).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class ReliabilityClass(str, Enum):
    reduced = "reduced"
    higher = "higher"


class RankingUniverse(str, Enum):
    n10 = "n10"
    n20 = "n20"


class IcttV2Dimension(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    weight: float


class IcttV2Eligibility(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_admissions: int
    higher_reliability_from: int


class IcttV2ReferencePeriod(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: str
    end: str


class IcttV2MethodologyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    methodology_version: str
    normalization_version: str
    reference_scope: str
    reference_period: IcttV2ReferencePeriod
    eligibility: IcttV2Eligibility
    dimensions: list[IcttV2Dimension]


class IcttV2CompetenciasResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    methodology_version: str
    competencias: list[str]


class IcttV2MunicipalityPublic(BaseModel):
    """Campos públicos do município (lista e ranking)."""

    model_config = ConfigDict(extra="forbid")

    competencia: str
    codigo_municipio: str
    municipio: str
    calculavel: bool
    reliability_class: ReliabilityClass | None = None
    admissoes: int
    desligamentos: int
    saldo: int
    absorcao: float | None = None
    remuneracao: float | None = None
    qualidade_contratual: float | None = None
    diversificacao: float | None = None
    ictt_v2: float | None = None
    rank_n10: int | None = None
    rank_n20: int | None = None


class IcttV2MunicipalityDetail(IcttV2MunicipalityPublic):
    """Campos públicos + diagnósticos auditáveis (detalhe)."""

    a_volume_score: float | None = None
    a_saldo: float | None = None
    n_salarios_r4: int | None = None
    salario_mediano_r4_municipio: float | None = None
    salario_mediano_r4_pr: float | None = None
    salario_relativo_r4: float | None = None
    perc_parcial_admissao: float | None = None
    perc_intermitente_admissao: float | None = None
    q_parcial: float | None = None
    q_intermitente: float | None = None
    shannon_cbo: float | None = None
    shannon_subclasse: float | None = None
    shannon_secao: float | None = None
    d_cbo: float | None = None
    d_subclasse: float | None = None
    d_secao: float | None = None


class IcttV2ListMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    competencia: str
    methodology_version: str
    normalization_version: str
    n_municipalities: int
    n_calculable: int
    reliability: ReliabilityClass | None = None


class IcttV2RankingMeta(IcttV2ListMeta):
    universe: RankingUniverse
    n_ranked: int


class IcttV2MunicipalityListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meta: IcttV2ListMeta
    data: list[IcttV2MunicipalityPublic]


class IcttV2MunicipalityDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meta: IcttV2ListMeta
    data: IcttV2MunicipalityDetail


class IcttV2RankingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meta: IcttV2RankingMeta
    data: list[IcttV2MunicipalityPublic]


V2_ENDPOINT_DESCRIPTION = (
    "ICTT methodology version 2.0. Endpoint versionado em paralelo à V1 "
    "(PCA em /api/ict/v1). Fonte canônica: Gold Parquet ictt_v2. "
    "A API não recalcula o índice."
)
