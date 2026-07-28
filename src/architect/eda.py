"""Cache-level EDA sub-tool (pure standard library).

Analyzes a CSV sample entirely in memory and returns it discarded afterwards:
nothing is written to disk or logged. It infers column types, detects
enumerator (categorical) columns and proposes an encoding, computes Pearson
correlations between numeric columns, and suggests signals for the wizard.

No third-party dependencies (no pandas/numpy) so it fits the deterministic,
dependency-free deployment.
"""

from __future__ import annotations

import csv
import datetime as _dt
import io
import math
from collections import Counter
from typing import Any, Dict, List, Optional

MAX_ROWS = 5000
MAX_COLS = 60
_SAMPLE_VALUES = 5
_MAX_MAP_CATEGORIES = 20
_HIGH_CORR = 0.7
_ENUM_MAX_CARDINALITY = 20
_HIGH_MISSING = 0.4
_NEAR_CONSTANT = 0.95
_DATE_FORMATS = (
    "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y",
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
)

_BOOL_TOKENS = {"true", "false", "yes", "no", "si", "sí", "0", "1", "t", "f"}


class EdaError(ValueError):
    """Raised for a safe, client-visible EDA validation error."""


def analyze_csv(
    text: str,
    has_header: bool = True,
    delimiter: Optional[str] = None,
) -> Dict[str, Any]:
    """Analyze a CSV string in memory and return an EDA report."""
    if not isinstance(text, str) or not text.strip():
        raise EdaError("el CSV está vacío")

    sample = text[:4096]
    if delimiter is None:
        delimiter = _sniff_delimiter(sample)

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    try:
        all_rows = [row for row in reader]
    except csv.Error as error:
        raise EdaError("CSV inválido: {}".format(error))
    if not all_rows:
        raise EdaError("el CSV no tiene filas")

    if has_header:
        header = [
            h.replace("\ufeff", "").strip() or "col_{}".format(i)
            for i, h in enumerate(all_rows[0])
        ]
        data_rows = all_rows[1:]
    else:
        width = len(all_rows[0])
        header = ["col_{}".format(i) for i in range(width)]
        data_rows = all_rows

    if not data_rows:
        raise EdaError("el CSV no tiene filas de datos")

    truncated_cols = len(header) > MAX_COLS
    header = header[:MAX_COLS]
    truncated_rows = len(data_rows) > MAX_ROWS
    data_rows = data_rows[:MAX_ROWS]

    n_cols = len(header)
    columns_raw: List[List[str]] = [[] for _ in range(n_cols)]
    for row in data_rows:
        for index in range(n_cols):
            value = row[index].strip() if index < len(row) else ""
            columns_raw[index].append(value)

    columns = [
        _analyze_column(header[index], columns_raw[index])
        for index in range(n_cols)
    ]

    numeric_aligned = {
        col["name"]: _aligned_numeric(columns_raw[index])
        for index, col in enumerate(columns)
        if col["type"] == "numeric"
    }
    correlations, high_correlations = _correlations(numeric_aligned)
    enumerators = [col for col in columns if col["type"] == "enumerator"]
    suggested = _suggested_context(columns, len(data_rows))
    target_correlations = _target_correlations(numeric_aligned, suggested)
    date_columns = [col["name"] for col in columns if col["type"] == "datetime"]
    recommendations = _recommendations(columns, high_correlations, date_columns)

    return {
        "privacy": "Los datos se analizaron en memoria y no se almacenaron.",
        "rows_analyzed": len(data_rows),
        "columns_analyzed": n_cols,
        "truncated_rows": truncated_rows,
        "truncated_columns": truncated_cols,
        "columns": columns,
        "enumerators": enumerators,
        "correlations": correlations,
        "high_correlations": high_correlations,
        "target_correlations": target_correlations,
        "date_columns": date_columns,
        "time_series_candidate": bool(date_columns),
        "recommendations": recommendations,
        "suggested_context": suggested,
    }


def _target_correlations(numeric_aligned, suggested) -> List[Dict[str, Any]]:
    """Rank numeric features by |Pearson r| against a numeric target column."""
    target = suggested.get("primary_target")
    if not target or target not in numeric_aligned:
        return []
    ranked = []
    for name, values in numeric_aligned.items():
        if name == target:
            continue
        r = _pearson_pairwise(values, numeric_aligned[target])
        if r is not None:
            ranked.append({"feature": name, "r": r})
    ranked.sort(key=lambda item: abs(item["r"]), reverse=True)
    return ranked


def _sniff_delimiter(sample: str) -> str:
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        return ","


def _numeric_values(values: List[str]) -> List[float]:
    result = []
    for value in values:
        if value == "":
            continue
        try:
            result.append(float(value))
        except ValueError:
            continue
    return result


def _is_sequential_index(numeric: List[float]) -> bool:
    """True if values are a contiguous integer index like 0,1,2,... or 1,2,3,..."""
    if len(numeric) < 2:
        return False
    ints = sorted(int(v) for v in numeric)
    if len(set(ints)) != len(ints):
        return False
    return ints == list(range(ints[0], ints[0] + len(ints)))


def _looks_like_date(values: List[str]) -> bool:
    """True if a strong majority of a sample parses as dates (needs separators)."""
    sample = values[:50]
    if len(sample) < 2:
        return False
    matched = 0
    for value in sample:
        if "-" not in value and "/" not in value:
            continue
        for fmt in _DATE_FORMATS:
            try:
                _dt.datetime.strptime(value, fmt)
                matched += 1
                break
            except ValueError:
                continue
    return matched >= max(2, int(0.9 * len(sample)))


def _is_near_constant(non_empty: List[str], n_unique: int) -> bool:
    """True if one value dominates (>=95%) while there is more than one value."""
    if n_unique <= 1 or not non_empty:
        return False
    dominant = Counter(non_empty).most_common(1)[0][1]
    return dominant / len(non_empty) >= _NEAR_CONSTANT


def _analyze_column(name: str, values: List[str]) -> Dict[str, Any]:
    total = len(values)
    non_empty = [v for v in values if v != ""]
    missing = total - len(non_empty)
    distinct = sorted(set(non_empty))
    n_unique = len(distinct)

    numeric = _numeric_values(non_empty)
    is_numeric = bool(non_empty) and len(numeric) >= 0.95 * len(non_empty)

    report: Dict[str, Any] = {
        "name": name,
        "n_missing": missing,
        "missing_pct": round(missing / total, 3) if total else 0.0,
        "n_unique": n_unique,
        "sample": distinct[:_SAMPLE_VALUES],
        "high_missing": bool(total) and (missing / total) >= _HIGH_MISSING,
        "near_constant": _is_near_constant(non_empty, n_unique),
    }

    lowered = {v.lower() for v in distinct}
    name_lower = name.lower()
    name_is_id = name_lower in {"id", "index", "idx", "uuid", "key"} or name_lower.endswith("_id")
    all_unique = n_unique == len(non_empty) and n_unique == total
    if n_unique <= 1:
        report["type"] = "constant"
        report["note"] = "Valor constante; candidata a eliminar."
        return report
    if lowered <= _BOOL_TOKENS and n_unique <= 3:
        report["type"] = "boolean"
        report["note"] = "Binaria; codifícala como 0/1."
        return report
    if _looks_like_date(non_empty):
        report["type"] = "datetime"
        report["note"] = "Columna de fecha; útil para un problema de forecasting."
        return report
    if is_numeric:
        report.update(_numeric_stats(numeric))
        is_int = all(float(v).is_integer() for v in numeric)
        if all_unique and is_int and (name_is_id or _is_sequential_index(numeric)):
            report["type"] = "id"
            report["note"] = "Parece un índice/identificador; no la uses como feature."
        elif n_unique <= 10 and is_int:
            report["type"] = "numeric"
            report["note"] = "Numérica de baja cardinalidad: podría ser categórica ordinal."
        else:
            report["type"] = "numeric"
        return report

    # Non-numeric.
    if all_unique and (name_is_id or total > 20):
        report["type"] = "id"
        report["note"] = "Texto único por fila; probablemente un identificador."
        return report
    if n_unique <= _ENUM_MAX_CARDINALITY:
        report["type"] = "enumerator"
        report["cardinality"] = n_unique
        report["encoding"] = _encoding_for(n_unique)
        report["encoding_map"] = _label_map(distinct)
        return report
    report["type"] = "high_cardinality_text"
    report["cardinality"] = n_unique
    report["note"] = "Texto de alta cardinalidad: hashing/target encoding o embeddings."
    return report


def _numeric_stats(values: List[float]) -> Dict[str, Any]:
    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n if n else 0.0
    std = math.sqrt(variance)
    return {
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "mean": round(mean, 4),
        "std": round(std, 4),
        "normalization": {
            "zscore": {"mean": round(mean, 4), "std": round(std, 4)},
            "minmax": {"min": round(min(values), 4), "max": round(max(values), 4)},
            "recommended": "zscore" if std > 0 else "none",
        },
    }


def _encoding_for(cardinality: int) -> str:
    if cardinality <= 10:
        return "one-hot"
    if cardinality <= 50:
        return "ordinal/label o target encoding"
    return "hashing/target encoding"


def _label_map(distinct: List[str]) -> Dict[str, int]:
    """Deterministic label-encoding preview (sorted categories -> integer code)."""
    return {value: code for code, value in enumerate(distinct[:_MAX_MAP_CATEGORIES])}


def _aligned_numeric(values: List[str]) -> List[Optional[float]]:
    """Row-aligned numeric values; None where empty or non-numeric."""
    aligned: List[Optional[float]] = []
    for value in values:
        if value == "":
            aligned.append(None)
            continue
        try:
            aligned.append(float(value))
        except ValueError:
            aligned.append(None)
    return aligned


def _correlations(
    numeric_aligned: Dict[str, List[Optional[float]]],
) -> Any:
    names = list(numeric_aligned.keys())[:30]
    matrix: Dict[str, Dict[str, Optional[float]]] = {}
    high: List[Dict[str, Any]] = []
    for a in names:
        matrix[a] = {}
        for b in names:
            if a == b:
                matrix[a][b] = 1.0
                continue
            r = _pearson_pairwise(numeric_aligned[a], numeric_aligned[b])
            matrix[a][b] = r
            if b > a and r is not None and abs(r) >= _HIGH_CORR:
                high.append({"a": a, "b": b, "r": r})
    high.sort(key=lambda item: abs(item["r"]), reverse=True)
    return matrix, high


def _pearson_pairwise(
    xs: List[Optional[float]], ys: List[Optional[float]]
) -> Optional[float]:
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    n = len(pairs)
    if n < 3:
        return None
    mx = sum(p[0] for p in pairs) / n
    my = sum(p[1] for p in pairs) / n
    sxx = sum((p[0] - mx) ** 2 for p in pairs)
    syy = sum((p[1] - my) ** 2 for p in pairs)
    if sxx == 0 or syy == 0:
        return None
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pairs)
    return round(sxy / math.sqrt(sxx * syy), 3)


def _recommendations(
    columns: List[Dict[str, Any]],
    high_correlations: List[Dict[str, Any]],
    date_columns: Optional[List[str]] = None,
) -> List[str]:
    recs: List[str] = []
    constants = [c["name"] for c in columns if c["type"] == "constant"]
    ids = [c["name"] for c in columns if c["type"] == "id"]
    enums = [c["name"] for c in columns if c["type"] == "enumerator"]
    missing = [c["name"] for c in columns if c["n_missing"] > 0]
    numerics = [c["name"] for c in columns if c["type"] == "numeric"]
    high_missing = [
        "{} ({:.0%})".format(c["name"], c["missing_pct"])
        for c in columns if c.get("high_missing")
    ]
    near_constant = [
        c["name"] for c in columns
        if c.get("near_constant") and c["type"] != "constant"
    ]

    if constants:
        recs.append("Eliminar columnas constantes: {}.".format(", ".join(constants)))
    if high_missing:
        recs.append(
            "Considera descartar (o imputar con cuidado) por muchos faltantes: {}.".format(
                ", ".join(high_missing)
            )
        )
    if near_constant:
        recs.append(
            "Casi constantes (poca varianza, aportan poco): {}.".format(
                ", ".join(near_constant)
            )
        )
    if ids:
        recs.append("Excluir identificadores del modelo: {}.".format(", ".join(ids)))
    if missing:
        recs.append("Imputar/tratar valores faltantes en: {}.".format(", ".join(missing)))
    if enums:
        recs.append("Codificar enumeradores: {}.".format(", ".join(enums)))
    if numerics:
        recs.append("Escalar variables numéricas (z-score o min-max) antes de entrenar.")
    if date_columns:
        recs.append(
            "Detectada(s) columna(s) de fecha ({}): si predices a lo largo del tiempo, "
            "considera un problema de forecasting (serie temporal).".format(
                ", ".join(date_columns)
            )
        )
    for pair in high_correlations[:5]:
        recs.append(
            "Alta correlación entre {} y {} (r={}); revisa multicolinealidad.".format(
                pair["a"], pair["b"], pair["r"]
            )
        )
    if not recs:
        recs.append("No se detectaron problemas evidentes en la muestra.")
    return recs


def _suggested_context(columns: List[Dict[str, Any]], n_rows: int) -> Dict[str, Any]:
    usable = [c for c in columns if c["type"] not in ("id", "constant")]
    candidates: List[Dict[str, str]] = []
    for col in usable:
        if col["type"] in ("enumerator", "boolean"):
            task = "classification"
        elif col["type"] == "numeric":
            task = "regression"
        else:
            continue
        candidates.append({"column": col["name"], "suggested_task": task})
    # The last usable column is the most common convention for the target.
    primary = candidates[-1] if candidates else None
    return {
        "dataset_rows": n_rows,
        "n_features": max(0, len(usable) - 1),
        "dataset_labeled": None,
        "target_candidates": candidates,
        "primary_target": primary["column"] if primary else None,
        "suggested_task": primary["suggested_task"] if primary else None,
        "note": "Elige la columna objetivo: numérica sugiere regresión; "
        "categórica, clasificación. Sin objetivo, considera clustering.",
    }
