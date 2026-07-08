"""Carga idempotente de geometrias → PostGIS (geo.municipios / municipios_rmc / ufs).

Datasets CLI:
  municipios-pr | municipios-rmc | ufs

Fontes padrão: dashboard/public/geo/*.geojson (já com cod_municipio / uf_sigla).
Não altera frontend, Tegola nem API Gold filesystem.
"""

from __future__ import annotations

import argparse
import json
import unicodedata
from pathlib import Path
from typing import Any

from app.core.config import PIPELINE_LOG_FILE, PROJECT_ROOT
from app.core.logging import setup_logger
from app.db.connection import get_connection

logger = setup_logger("load_geo", PIPELINE_LOG_FILE)

DEFAULT_GEO_PR = PROJECT_ROOT / "dashboard" / "public" / "geo" / "municipios_pr.geojson"
DEFAULT_GEO_RMC = PROJECT_ROOT / "dashboard" / "public" / "geo" / "municipios_rmc.geojson"
DEFAULT_GEO_UFS = PROJECT_ROOT / "dashboard" / "public" / "geo" / "ufs.geojson"

# Shapefile opcional (legado / admin)
DEFAULT_SHP_PR = (
    PROJECT_ROOT
    / "data-lake"
    / "geodata"
    / "municipios"
    / "uf=PR"
    / "ano=2024"
    / "PR_Municipios_2024.shp"
)
DEFAULT_SHP_UFS = PROJECT_ROOT / "data-lake" / "geodata" / "ufs" / "BR_UF_2024.shp"

UPSERT_MUNICIPIO_SQL = """
    INSERT INTO geo.municipios
        (cod_municipio, nome_municipio, uf, nome_municipio_norm, uf_norm, geom)
    VALUES (%s, %s, %s, %s, %s, ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)))
    ON CONFLICT (cod_municipio) DO UPDATE SET
        nome_municipio = EXCLUDED.nome_municipio,
        uf = EXCLUDED.uf,
        nome_municipio_norm = EXCLUDED.nome_municipio_norm,
        uf_norm = EXCLUDED.uf_norm,
        geom = EXCLUDED.geom;
"""

# Schema legado: municipios_rmc é subconjunto (cod + nome_norm) com FK para geo.municipios.
UPSERT_MUNICIPIO_RMC_SQL = """
    INSERT INTO geo.municipios_rmc
        (cod_municipio, nome_municipio_norm)
    VALUES (%s, %s)
    ON CONFLICT (cod_municipio) DO UPDATE SET
        nome_municipio_norm = EXCLUDED.nome_municipio_norm;
"""

# Schema legado: PK = uf (sigla CHAR2)
UPSERT_UF_SQL = """
    INSERT INTO geo.ufs
        (uf, nome_uf, cod_uf, nome_uf_norm, geom)
    VALUES (%s, %s, %s, %s, ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)))
    ON CONFLICT (uf) DO UPDATE SET
        nome_uf = EXCLUDED.nome_uf,
        cod_uf = EXCLUDED.cod_uf,
        nome_uf_norm = EXCLUDED.nome_uf_norm,
        geom = EXCLUDED.geom;
"""


def normalizar_texto(txt: object) -> str | None:
    if txt is None:
        return None
    try:
        import pandas as pd

        if pd.isna(txt):
            return None
    except Exception:
        pass
    text = str(txt).strip().upper()
    if not text or text.lower() == "nan":
        return None
    text = "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )
    return " ".join(text.split())


def load_municipios_geometria(
    shapefile_path: str,
    coluna_nome: str,
    coluna_uf: str,
    coluna_codigo: str | None = None,
):
    """API legada (admin): carga shapefile → geo.municipios via GeoPandas/WKT."""
    import geopandas as gpd

    logger.info(f"[GEO] Lendo arquivo geográfico: {shapefile_path}")
    gdf = gpd.read_file(shapefile_path)
    if gdf.crs is None:
        raise ValueError("A malha geográfica está sem CRS definido.")
    gdf = gdf.to_crs(epsg=4326)
    gdf["nome_municipio"] = gdf[coluna_nome].astype(str).str.strip()
    gdf["uf"] = gdf[coluna_uf].astype(str).str.strip().str.upper()
    gdf["nome_municipio_norm"] = gdf["nome_municipio"].apply(normalizar_texto)
    gdf["uf_norm"] = gdf["uf"].apply(normalizar_texto)
    code_col = coluna_codigo if coluna_codigo and coluna_codigo in gdf.columns else None
    if code_col:
        gdf["cod_municipio"] = gdf[code_col].astype(str).str.strip()
    else:
        gdf["cod_municipio"] = None

    upsert_sql = """
        INSERT INTO geo.municipios
            (cod_municipio, nome_municipio, uf, nome_municipio_norm, uf_norm, geom)
        VALUES (%s, %s, %s, %s, %s, ST_SetSRID(ST_GeomFromText(%s), 4326))
        ON CONFLICT (cod_municipio) DO UPDATE SET
            nome_municipio = EXCLUDED.nome_municipio,
            uf = EXCLUDED.uf,
            nome_municipio_norm = EXCLUDED.nome_municipio_norm,
            uf_norm = EXCLUDED.uf_norm,
            geom = EXCLUDED.geom;
    """

    conn = get_connection()
    cur = conn.cursor()
    inserted = 0
    skipped = 0
    try:
        for _, row in gdf.iterrows():
            cod = row["cod_municipio"]
            if cod is None or not str(cod).strip():
                skipped += 1
                continue
            geom_wkt = row.geometry.wkt if row.geometry is not None else None
            if not geom_wkt:
                skipped += 1
                continue
            uf_val = str(row["uf"]).strip().upper()
            if len(uf_val) > 2:
                # Shapefile pode trazer nome; tenta manter 2 letras se for SIGLA
                uf_val = uf_val[:2] if len(uf_val) == 2 else "PR"
            cur.execute(
                upsert_sql,
                (
                    str(cod).strip(),
                    row["nome_municipio"],
                    uf_val if len(uf_val) == 2 else "PR",
                    row["nome_municipio_norm"],
                    row["uf_norm"],
                    geom_wkt,
                ),
            )
            inserted += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    logger.info(
        f"[GEO] Carga idempotente concluída | upsert={inserted} | ignoradas={skipped}"
    )
    return {"upserted": inserted, "skipped": skipped}


def _load_geojson_features(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"GeoJSON não encontrado: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload.get("features") or [])


def load_geo_municipios_from_geojson(
    path: Path,
    *,
    target: str = "municipios",
) -> dict[str, Any]:
    """Carrega municipios_pr/rmc GeoJSON → geo.municipios (e subset RMC se pedido)."""
    features = _load_geojson_features(path)
    conn = get_connection()
    cur = conn.cursor()
    upserted = 0
    skipped = 0
    try:
        for feat in features:
            props = feat.get("properties") or {}
            geom = feat.get("geometry")
            cod = props.get("cod_municipio")
            if cod is None or not str(cod).strip() or geom is None:
                skipped += 1
                continue
            nome = str(props.get("municipio") or props.get("nome_municipio") or "").strip()
            uf_sigla = str(props.get("uf_sigla") or "PR").strip().upper()[:2]
            nome_norm = normalizar_texto(props.get("municipio_norm") or nome)
            uf_norm = normalizar_texto(props.get("uf_norm") or props.get("uf") or uf_sigla)
            geom_json = json.dumps(geom, ensure_ascii=False)
            cod_s = str(cod).strip()
            # Sempre mantém geometria em geo.municipios (necessário para FK RMC).
            cur.execute(
                UPSERT_MUNICIPIO_SQL,
                (cod_s, nome or cod_s, uf_sigla, nome_norm, uf_norm, geom_json),
            )
            if target == "municipios_rmc":
                cur.execute(UPSERT_MUNICIPIO_RMC_SQL, (cod_s, nome_norm or nome or cod_s))
            upserted += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    report = {
        "dataset": f"geo-{target}",
        "file": str(path),
        "features": len(features),
        "upserted": upserted,
        "skipped": skipped,
    }
    _print_geo_report(report)
    return report


def load_geo_ufs_from_geojson(path: Path) -> dict[str, Any]:
    features = _load_geojson_features(path)
    conn = get_connection()
    cur = conn.cursor()
    upserted = 0
    skipped = 0
    try:
        for feat in features:
            props = feat.get("properties") or {}
            geom = feat.get("geometry")
            cod = props.get("cod_uf")
            sigla = props.get("uf_sigla")
            if cod is None or sigla is None or geom is None:
                skipped += 1
                continue
            nome = str(props.get("uf") or sigla).strip()
            nome_norm = normalizar_texto(props.get("uf_norm") or nome)
            geom_json = json.dumps(geom, ensure_ascii=False)
            cur.execute(
                UPSERT_UF_SQL,
                (
                    str(sigla).strip().upper()[:2],
                    nome,
                    str(cod).strip().zfill(2) if str(cod).strip().isdigit() else str(cod).strip(),
                    nome_norm,
                    geom_json,
                ),
            )
            upserted += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    report = {
        "dataset": "geo-ufs",
        "file": str(path),
        "features": len(features),
        "upserted": upserted,
        "skipped": skipped,
    }
    _print_geo_report(report)
    return report


def _print_geo_report(report: dict[str, Any]) -> None:
    print(f"--- load_geo_tables [{report['dataset']}] ---")
    print(f"  file={report['file']}")
    print(f"  features={report['features']}")
    print(f"  upserted={report['upserted']}")
    print(f"  skipped={report['skipped']}")
    print("")
    logger.info(
        "[GEO] dataset=%s upserted=%s skipped=%s file=%s",
        report["dataset"],
        report["upserted"],
        report["skipped"],
        report["file"],
    )


def load_dataset(dataset: str, *, path: Path | None = None) -> dict[str, Any]:
    if dataset == "municipios-pr":
        return load_geo_municipios_from_geojson(
            path or DEFAULT_GEO_PR, target="municipios"
        )
    if dataset == "municipios-rmc":
        # Upsert em geo.municipios + subset geo.municipios_rmc (FK).
        return load_geo_municipios_from_geojson(
            path or DEFAULT_GEO_RMC, target="municipios_rmc"
        )
    if dataset == "ufs":
        return load_geo_ufs_from_geojson(path or DEFAULT_GEO_UFS)
    raise ValueError(
        f"Dataset geo desconhecido: {dataset}. Use: municipios-pr, municipios-rmc, ufs"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Carga idempotente de geometrias → PostGIS."
    )
    parser.add_argument(
        "--dataset",
        required=True,
        choices=["municipios-pr", "municipios-rmc", "ufs"],
    )
    parser.add_argument(
        "--path",
        default=None,
        help="Caminho opcional do GeoJSON (default: dashboard/public/geo/).",
    )
    args = parser.parse_args(argv)
    try:
        load_dataset(args.dataset, path=Path(args.path) if args.path else None)
    except Exception as exc:
        print(f"ERRO: {exc}")
        logger.exception("[GEO] falha dataset=%s", args.dataset)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
