"""Serving ICTT v2.0 a partir do Gold Parquet canônico.

V1 permanece em ``/api/ict/v1`` e no Gold ``tabela_ictt_municipio``.
Esta camada não recalcula o índice, não lê CSV/microdados e não usa PostGIS.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from app.core.config import GOLD_CAGED_DIR
from pipelines.gold.ictt_v2.spec import frozen_spec

ICTT_V2_SUBDIR = "ictt_v2"
ICTT_V2_PARQUET_STEM = "tabela_ictt_v2_municipio_pr"
COMPETENCIA_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
MUNICIPIO_CODE_PATTERN = re.compile(r"^\d{7}$")
_ANO_DIR_PATTERN = re.compile(r"^ano=(\d{4})$")
_MES_DIR_PATTERN = re.compile(r"^mes=(0[1-9]|1[0-2])$")

RankingUniverse = Literal["n10", "n20"]
ReliabilityFilter = Literal["reduced", "higher"]

REQUIRED_COLUMNS: tuple[str, ...] = (
    "competencia",
    "cod_municipio",
    "municipio",
    "calculavel",
    "reliability_class",
    "admissoes",
    "desligamentos",
    "saldo",
    "absorcao",
    "remuneracao",
    "qualidade_contratual",
    "diversificacao",
    "ictt_v2",
    "rank_n10",
    "rank_n20",
    "methodology_version",
    "normalization_version",
)


class IcttV2RepositoryError(Exception):
    """Erro de serving ICTT v2."""


class IcttV2InvalidCompetenciaError(IcttV2RepositoryError):
    """Competência com formato inválido ou path inseguro."""


class IcttV2InvalidMunicipalityCodeError(IcttV2RepositoryError):
    """Identificador municipal inválido."""


class IcttV2PartitionNotFoundError(IcttV2RepositoryError):
    """Parquet canônico v2 ausente para a competência."""


class IcttV2ArtifactError(IcttV2RepositoryError):
    """Artefato Parquet ilegível ou com schema/metodologia incompatível."""


class IcttV2MunicipalityNotFoundError(IcttV2RepositoryError):
    """Município ausente na partição Gold v2."""


def parse_competencia(value: str) -> tuple[int, int, str]:
    """Valida YYYY-MM e bloqueia path traversal antes de montar o filesystem."""
    raw = (value or "").strip()
    if not raw or ".." in raw or "/" in raw or "\\" in raw or "\x00" in raw:
        raise IcttV2InvalidCompetenciaError(
            "competencia inválida. Use YYYY-MM (ex.: 2026-04)."
        )
    if not COMPETENCIA_PATTERN.fullmatch(raw):
        raise IcttV2InvalidCompetenciaError(
            "competencia inválida. Use YYYY-MM (ex.: 2026-04)."
        )
    year_s, month_s = raw.split("-", 1)
    return int(year_s), int(month_s), raw


def parse_municipality_code(value: str) -> str:
    raw = (value or "").strip()
    if not raw or ".." in raw or "/" in raw or "\\" in raw or "\x00" in raw:
        raise IcttV2InvalidMunicipalityCodeError(
            "codigo_municipio inválido. Use o código IBGE de 7 dígitos."
        )
    if not MUNICIPIO_CODE_PATTERN.fullmatch(raw):
        raise IcttV2InvalidMunicipalityCodeError(
            "codigo_municipio inválido. Use o código IBGE de 7 dígitos."
        )
    return raw


def json_safe_value(value: Any) -> Any:
    """Converte NaN/NA/NaT em None. Nunca emite NaN JSON."""
    if value is None:
        return None
    if isinstance(value, (str, bytes)):
        text = value.decode("utf-8") if isinstance(value, bytes) else value
        if text.lower() == "nan":
            return None
        return text
    if isinstance(value, bool):
        return value
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item") and not isinstance(value, (bytes, str, pd.Timestamp)):
        try:
            return json_safe_value(value.item())
        except (ValueError, AttributeError, RecursionError):
            pass
    if isinstance(value, (float, int)) and not isinstance(value, bool):
        number = float(value)
        if not math.isfinite(number):
            return None
        if isinstance(value, int) or float(value).is_integer():
            return int(value)
        return float(value)
    return value


def _optional_float(value: Any) -> float | None:
    safe = json_safe_value(value)
    if safe is None:
        return None
    number = float(safe)
    if not math.isfinite(number):
        return None
    return number


def _optional_int(value: Any) -> int | None:
    safe = json_safe_value(value)
    if safe is None:
        return None
    return int(safe)


def _count_int(value: Any) -> int:
    safe = _optional_int(value)
    return 0 if safe is None else safe


def _required_bool(value: Any) -> bool:
    safe = json_safe_value(value)
    if safe is None:
        return False
    return bool(safe)


class IcttV2Repository:
    """Localiza a partição v2, abre o Parquet canônico e devolve dados sem recálculo."""

    def __init__(self, gold_root: Path | None = None) -> None:
        self._gold_root = gold_root

    @property
    def gold_root(self) -> Path:
        return self._gold_root if self._gold_root is not None else GOLD_CAGED_DIR

    def parquet_path(self, ano: int, mes: int) -> Path:
        path = (
            self.gold_root
            / f"ano={ano}"
            / f"mes={mes:02d}"
            / ICTT_V2_SUBDIR
            / f"{ICTT_V2_PARQUET_STEM}.parquet"
        )
        self._assert_path_under_gold(path)
        return path

    def list_competencias(self) -> list[str]:
        """Descobre competências apenas em subdiretórios ``ictt_v2`` com Parquet."""
        root = self.gold_root
        if not root.is_dir():
            return []
        found: list[str] = []
        for ano_dir in root.iterdir():
            if not ano_dir.is_dir():
                continue
            ano_match = _ANO_DIR_PATTERN.fullmatch(ano_dir.name)
            if ano_match is None:
                continue
            for mes_dir in ano_dir.iterdir():
                if not mes_dir.is_dir():
                    continue
                mes_match = _MES_DIR_PATTERN.fullmatch(mes_dir.name)
                if mes_match is None:
                    continue
                parquet = (
                    mes_dir / ICTT_V2_SUBDIR / f"{ICTT_V2_PARQUET_STEM}.parquet"
                )
                if parquet.is_file():
                    found.append(f"{ano_match.group(1)}-{mes_match.group(1)}")
        return sorted(found)

    def load_partition(self, competencia: str) -> pd.DataFrame:
        ano, mes, competencia_key = parse_competencia(competencia)
        path = self.parquet_path(ano, mes)
        if not path.is_file():
            raise IcttV2PartitionNotFoundError(
                f"Gold ICTT v2 não encontrado para {competencia_key}."
            )
        try:
            frame = pd.read_parquet(path)
        except Exception as exc:
            raise IcttV2ArtifactError(
                f"Gold ICTT v2 ilegível para {competencia_key}."
            ) from exc
        self._validate_schema(frame, competencia_key)
        self._validate_methodology(frame, competencia_key)
        return frame

    def partition_meta(self, frame: pd.DataFrame, competencia: str) -> dict[str, Any]:
        calculavel = frame["calculavel"].fillna(False).astype(bool)
        first = frame.iloc[0]
        return {
            "competencia": competencia,
            "methodology_version": str(first["methodology_version"]),
            "normalization_version": str(first["normalization_version"]),
            "n_municipalities": int(len(frame)),
            "n_calculable": int(calculavel.sum()),
        }

    def list_municipalities(
        self,
        competencia: str,
        *,
        reliability: ReliabilityFilter | None = None,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        frame = self.load_partition(competencia)
        meta = self.partition_meta(frame, competencia)
        if reliability is not None:
            frame = frame[frame["reliability_class"].astype("string") == reliability]
        records = [self._public_record(row) for row in frame.itertuples(index=False)]
        records.sort(key=lambda item: (item["codigo_municipio"], item["municipio"]))
        return meta, records

    def get_municipality(
        self,
        competencia: str,
        codigo_municipio: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        code = parse_municipality_code(codigo_municipio)
        frame = self.load_partition(competencia)
        meta = self.partition_meta(frame, competencia)
        codes = frame["cod_municipio"].astype(str).str.strip()
        matched = frame[codes == code]
        if matched.empty:
            raise IcttV2MunicipalityNotFoundError(
                f"Município {code} não encontrado na competência {competencia}."
            )
        return meta, self._detail_record(matched.iloc[0])

    def ranking(
        self,
        competencia: str,
        universe: RankingUniverse,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        frame = self.load_partition(competencia)
        meta = self.partition_meta(frame, competencia)
        rank_col = "rank_n10" if universe == "n10" else "rank_n20"
        threshold = 10 if universe == "n10" else 20
        admissoes = pd.to_numeric(frame["admissoes"], errors="coerce")
        ranked = frame[(admissoes >= threshold) & frame[rank_col].notna()].copy()
        ranked = ranked.sort_values(
            [rank_col, "cod_municipio"],
            ascending=[True, True],
            kind="mergesort",
        )
        records = [self._public_record(row) for row in ranked.itertuples(index=False)]
        meta = {
            **meta,
            "universe": universe,
            "n_ranked": int(len(records)),
        }
        return meta, records

    def _assert_path_under_gold(self, path: Path) -> None:
        root = self.gold_root.resolve()
        resolved = path.resolve()
        if not resolved.is_relative_to(root):
            raise IcttV2InvalidCompetenciaError(
                "competencia inválida. Use YYYY-MM (ex.: 2026-04)."
            )

    def _validate_schema(self, frame: pd.DataFrame, competencia: str) -> None:
        missing = [col for col in REQUIRED_COLUMNS if col not in frame.columns]
        if missing:
            raise IcttV2ArtifactError(
                "Gold ICTT v2 com schema mínimo incompatível "
                f"para {competencia}: ausentes {', '.join(missing)}."
            )

    def _validate_methodology(self, frame: pd.DataFrame, competencia: str) -> None:
        spec = frozen_spec()
        versions = {
            str(value)
            for value in frame["methodology_version"].dropna().unique().tolist()
        }
        if versions != {spec.methodology_version}:
            raise IcttV2ArtifactError(
                "Gold ICTT v2 com methodology_version incompatível "
                f"para {competencia}."
            )
        norms = {
            str(value)
            for value in frame["normalization_version"].dropna().unique().tolist()
        }
        if spec.normalization_version not in norms or len(norms) != 1:
            raise IcttV2ArtifactError(
                "Gold ICTT v2 com normalization_version incompatível "
                f"para {competencia}."
            )

    def _row_mapping(self, row: Any) -> dict[str, Any]:
        if isinstance(row, pd.Series):
            return row.to_dict()
        if hasattr(row, "_asdict"):
            return row._asdict()
        return dict(row)

    def _public_record(self, row: Any) -> dict[str, Any]:
        mapping = self._row_mapping(row)
        codigo = str(mapping.get("cod_municipio", "")).strip()
        reliability = json_safe_value(mapping.get("reliability_class"))
        reliability_text = None if reliability is None else str(reliability)
        calculavel = _required_bool(mapping.get("calculavel"))
        ictt = None if not calculavel else _optional_float(mapping.get("ictt_v2"))
        rank_n10 = None if not calculavel else _optional_int(mapping.get("rank_n10"))
        rank_n20 = _optional_int(mapping.get("rank_n20")) if calculavel else None
        return {
            "competencia": str(mapping.get("competencia")),
            "codigo_municipio": codigo,
            "municipio": str(mapping.get("municipio")),
            "calculavel": calculavel,
            "reliability_class": reliability_text,
            "admissoes": _count_int(mapping.get("admissoes")),
            "desligamentos": _count_int(mapping.get("desligamentos")),
            "saldo": _count_int(mapping.get("saldo")),
            "absorcao": _optional_float(mapping.get("absorcao")),
            "remuneracao": _optional_float(mapping.get("remuneracao")),
            "qualidade_contratual": _optional_float(mapping.get("qualidade_contratual")),
            "diversificacao": _optional_float(mapping.get("diversificacao")),
            "ictt_v2": ictt,
            "rank_n10": rank_n10,
            "rank_n20": rank_n20,
        }

    def _detail_record(self, row: pd.Series) -> dict[str, Any]:
        mapping = row.to_dict()
        public = self._public_record(mapping)
        diagnostic = {
            "a_volume_score": _optional_float(mapping.get("a_volume_score")),
            "a_saldo": _optional_float(mapping.get("a_saldo")),
            "n_salarios_r4": _optional_int(mapping.get("n_salarios_r4")),
            "salario_mediano_r4_municipio": _optional_float(
                mapping.get("salario_mediano_r4_municipio")
            ),
            "salario_mediano_r4_pr": _optional_float(mapping.get("salario_mediano_r4_pr")),
            "salario_relativo_r4": _optional_float(mapping.get("salario_relativo_r4")),
            "perc_parcial_admissao": _optional_float(mapping.get("perc_parcial_admissao")),
            "perc_intermitente_admissao": _optional_float(
                mapping.get("perc_intermitente_admissao")
            ),
            "q_parcial": _optional_float(mapping.get("q_parcial")),
            "q_intermitente": _optional_float(mapping.get("q_intermitente")),
            "shannon_cbo": _optional_float(mapping.get("shannon_cbo")),
            "shannon_subclasse": _optional_float(mapping.get("shannon_subclasse")),
            "shannon_secao": _optional_float(mapping.get("shannon_secao")),
            "d_cbo": _optional_float(mapping.get("d_cbo")),
            "d_subclasse": _optional_float(mapping.get("d_subclasse")),
            "d_secao": _optional_float(mapping.get("d_secao")),
        }
        return {**public, **diagnostic}


def get_ictt_v2_repository() -> IcttV2Repository:
    return IcttV2Repository()
