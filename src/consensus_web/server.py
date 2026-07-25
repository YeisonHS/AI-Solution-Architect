"""Same-origin HTTP product for the deterministic consensus engine."""

from __future__ import annotations

import argparse
import io
import json
import logging
import os
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

from orchestrator import (
    AgentVerdict,
    ConsensusResult,
    confidence,
    decide,
    review_board,
    run_consensus,
)
from orchestrator.agents import (
    ATTR_AUTH,
    ATTR_BACKUPS,
    ATTR_COST,
    ATTR_ENCRYPTION,
    ATTR_PUBLIC,
    CONTEXT_BUDGET,
)
from architect import Constraints, HardwareProfile, ProblemContext
from architect.models import PRIVACY_LEVELS
from architect.catalog import FAMILY_LABELS
from architect.decision import run_review, serialize_adr
from architect.artifacts import generate_files

MAX_BODY_BYTES = 1_048_576
VERSION = "0.1.0"
STATIC_DIR = Path(__file__).with_name("static")
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
}
_VERDICT_KEYS = {
    "agent",
    "verdict",
    "severity",
    "risk",
    "hard_rules_passed",
    "hard_rules_total",
}
_ROUND_KEYS = {"candidate", "verdicts"}


class RequestValidationError(ValueError):
    """Raised for a safe, client-visible request validation failure."""


class ConsensusHTTPServer(ThreadingHTTPServer):
    """Threaded server with bounded request handling."""

    allow_reuse_address = True
    daemon_threads = True


class ConsensusRequestHandler(BaseHTTPRequestHandler):
    """Serve only known static assets and the documented JSON API."""

    server_version = "ConsensusEngine/0.1"
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.query:
            self._write_error(404, "route not found")
            return
        if parsed.path == "/api/health":
            self._write_json(200, {"status": "ok", "version": VERSION})
            return
        static_asset = STATIC_FILES.get(parsed.path)
        if static_asset is None:
            self._write_error(404, "route not found")
            return
        self._write_static(*static_asset)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.query or parsed.path not in (
            "/api/consensus",
            "/api/evaluate",
            "/api/architect",
            "/api/artifacts",
            "/api/artifacts.zip",
        ):
            self._write_error(404, "route not found")
            return
        if self.headers.get_content_type() != "application/json":
            self._write_error(415, "Content-Type must be application/json")
            return

        content_length = self.headers.get("Content-Length")
        if content_length is None:
            self._write_error(411, "Content-Length is required")
            return
        try:
            length = int(content_length)
        except ValueError:
            self._write_error(400, "Content-Length must be an integer")
            return
        if length < 0:
            self._write_error(400, "Content-Length must not be negative")
            return
        if length > MAX_BODY_BYTES:
            self._write_error(413, "request body exceeds 1 MiB")
            return

        body = self.rfile.read(length)
        if len(body) != length:
            self._write_error(400, "incomplete request body")
            return
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._write_error(400, "request body must be valid UTF-8 JSON")
            return

        try:
            if parsed.path == "/api/consensus":
                response = {"result": serialize_result(evaluate_request(payload))}
            elif parsed.path == "/api/evaluate":
                response = evaluate_options(payload)
            elif parsed.path == "/api/architect":
                response = evaluate_architecture(payload)
            elif parsed.path == "/api/artifacts":
                response = build_artifacts(payload)
            else:
                zip_bytes = artifacts_zip_bytes(payload)
                self._write_download(
                    zip_bytes, "application/zip", "ai-architecture-artifacts.zip"
                )
                return
        except RequestValidationError as error:
            self._write_error(400, str(error))
        except Exception:
            logging.exception("Unexpected request failure")
            self._write_error(500, "internal server error")
        else:
            self._write_json(200, response)

    def do_OPTIONS(self) -> None:
        self._write_error(405, "method not allowed")

    def do_PUT(self) -> None:
        self._write_error(405, "method not allowed")

    def do_PATCH(self) -> None:
        self._write_error(405, "method not allowed")

    def do_DELETE(self) -> None:
        self._write_error(405, "method not allowed")

    def do_HEAD(self) -> None:
        self._write_error(405, "method not allowed")

    def log_message(self, format: str, *args: object) -> None:
        """Avoid logging paths or request data by default."""

    def _write_static(self, filename: str, content_type: str) -> None:
        try:
            body = (STATIC_DIR / filename).read_bytes()
        except OSError:
            logging.exception("Static asset unavailable")
            self._write_error(500, "static asset unavailable")
            return
        self._write_response(200, body, content_type)

    def _write_json(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
        self._write_response(status, body, "application/json; charset=utf-8")

    def _write_error(self, status: int, message: str) -> None:
        self._write_json(status, {"error": message})

    def _write_download(self, body: bytes, content_type: str, filename: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header(
            "Content-Disposition", 'attachment; filename="{}"'.format(filename)
        )
        self.send_header("Cache-Control", "no-store")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
        )
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def _write_response(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
        )
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True


def evaluate_request(payload: Any) -> ConsensusResult:
    """Validate an API payload and execute its complete scripted round sequence."""
    if not isinstance(payload, dict):
        raise RequestValidationError("request body must be an object")
    _require_exact_keys("request", payload, {"rounds"}, optional={"context"})
    context = payload.get("context", {})
    if not isinstance(context, dict):
        raise RequestValidationError("context must be an object")
    rounds = _parse_rounds(payload.get("rounds"))
    _validate_round_sequence(rounds)

    review_index = 0

    def architect(_: Dict[str, Any], rejected: Tuple[Dict[str, Any], ...]) -> Dict[str, Any]:
        return rounds[len(rejected)]["candidate"]

    def review_board(_: Dict[str, Any], __: Dict[str, Any]) -> List[AgentVerdict]:
        nonlocal review_index
        verdicts = rounds[review_index]["verdicts"]
        review_index += 1
        return verdicts

    return run_consensus(context, architect, review_board, lambda _: None)


def _parse_rounds(raw_rounds: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_rounds, list) or not 1 <= len(raw_rounds) <= 3:
        raise RequestValidationError("rounds must be a list containing 1 to 3 rounds")
    parsed: List[Dict[str, Any]] = []
    for index, raw_round in enumerate(raw_rounds):
        if not isinstance(raw_round, dict):
            raise RequestValidationError("round {} must be an object".format(index))
        _require_exact_keys("round {}".format(index), raw_round, _ROUND_KEYS)
        candidate = raw_round["candidate"]
        if not isinstance(candidate, dict):
            raise RequestValidationError("round {} candidate must be an object".format(index))
        verdicts_raw = raw_round["verdicts"]
        if not isinstance(verdicts_raw, list) or not verdicts_raw:
            raise RequestValidationError(
                "round {} verdicts must be a non-empty list".format(index)
            )
        parsed.append(
            {
                "candidate": candidate,
                "verdicts": [
                    _parse_verdict(verdict, index, verdict_index)
                    for verdict_index, verdict in enumerate(verdicts_raw)
                ],
            }
        )
    return parsed


def _parse_verdict(raw_verdict: Any, round_index: int, verdict_index: int) -> AgentVerdict:
    if not isinstance(raw_verdict, dict):
        raise RequestValidationError(
            "round {} verdict {} must be an object".format(round_index, verdict_index)
        )
    _require_exact_keys(
        "round {} verdict {}".format(round_index, verdict_index),
        raw_verdict,
        _VERDICT_KEYS,
    )
    try:
        return AgentVerdict(
            agent=raw_verdict["agent"],
            verdict=raw_verdict["verdict"],
            severity=raw_verdict["severity"],
            risk=raw_verdict["risk"],
            hard_rules_passed=raw_verdict["hard_rules_passed"],
            hard_rules_total=raw_verdict["hard_rules_total"],
        )
    except (TypeError, ValueError) as error:
        raise RequestValidationError(str(error)) from error


def _validate_round_sequence(rounds: List[Dict[str, Any]]) -> None:
    for index, round_data in enumerate(rounds):
        action = decide(round_data["verdicts"], index)
        is_last = index == len(rounds) - 1
        if action == "re_propose":
            if is_last:
                raise RequestValidationError(
                    "a blocker in round {} requires the next round".format(index)
                )
            continue
        if not is_last:
            raise RequestValidationError(
                "round {} already reaches a final decision; remove unused rounds".format(
                    index
                )
            )
        return
    raise RequestValidationError("round sequence does not reach a final decision")


def _require_exact_keys(
    name: str,
    value: Dict[str, Any],
    required: Set[str],
    optional: Optional[Set[str]] = None,
) -> None:
    actual = set(value.keys())
    allowed = required | (optional or set())
    missing = required - actual
    unknown = actual - allowed
    if missing or unknown:
        raise RequestValidationError("{} has an invalid field set".format(name))


def serialize_result(result: ConsensusResult) -> Dict[str, Any]:
    """Convert validated domain output into JSON-only response data."""
    return {
        "architecture": result.architecture,
        "verdicts": [_serialize_verdict(verdict) for verdict in result.verdicts],
        "accepted_risks": result.accepted_risks,
        "unresolved_risks": result.unresolved_risks,
        "rejected": result.rejected,
        "round_reached": result.round_reached,
        "confidence": result.confidence,
        "forced": result.forced,
    }


def _serialize_verdict(verdict: AgentVerdict) -> Dict[str, Any]:
    return {
        "agent": verdict.agent,
        "verdict": verdict.verdict,
        "severity": verdict.severity,
        "risk": verdict.risk,
        "hard_rules_passed": verdict.hard_rules_passed,
        "hard_rules_total": verdict.hard_rules_total,
    }


_OPTION_KEYS = {
    "name",
    "description",
    ATTR_ENCRYPTION,
    ATTR_AUTH,
    ATTR_PUBLIC,
    ATTR_BACKUPS,
    ATTR_COST,
}
_EVALUATE_KEYS = {"budget_usd", "options", "project"}


def evaluate_options(payload: Any) -> Dict[str, Any]:
    """Score each described option with the board and recommend the best fit."""
    if not isinstance(payload, dict):
        raise RequestValidationError("request body must be an object")
    _require_exact_keys(
        "request", payload, {"options"}, optional={"budget_usd", "project"}
    )

    context: Dict[str, Any] = {}
    if payload.get("budget_usd") is not None:
        context[CONTEXT_BUDGET] = _parse_budget(payload["budget_usd"])
    project = payload.get("project")
    if project is not None and not isinstance(project, str):
        raise RequestValidationError("project must be a string")

    raw_options = payload.get("options")
    if not isinstance(raw_options, list) or not 1 <= len(raw_options) <= 5:
        raise RequestValidationError("options must be a list of 1 to 5 items")

    evaluations: List[Dict[str, Any]] = []
    for index, raw_option in enumerate(raw_options):
        candidate = _parse_option(raw_option, index)
        try:
            verdicts = review_board(context, candidate)
        except ValueError as error:
            raise RequestValidationError(
                "option {}: {}".format(index, error)
            ) from error
        blocked = any(verdict.is_blocker for verdict in verdicts)
        evaluations.append(
            {
                "option": candidate,
                "verdicts": [_serialize_verdict(verdict) for verdict in verdicts],
                "confidence": confidence(verdicts),
                "blocked": blocked,
                "strengths": [
                    verdict.agent for verdict in verdicts if verdict.verdict == "PASS"
                ],
                "warnings": [
                    verdict.risk
                    for verdict in verdicts
                    if verdict.verdict == "WARN" and verdict.risk
                ],
                "blockers": [
                    verdict.risk for verdict in verdicts if verdict.is_blocker
                ],
                "_index": index,
            }
        )

    ranked = sorted(
        evaluations,
        key=lambda item: (not item["blocked"], item["confidence"], -item["_index"]),
        reverse=True,
    )
    acceptable = [item for item in ranked if not item["blocked"]]
    winner = acceptable[0] if acceptable else ranked[0]
    forced = not acceptable

    comparison = []
    for position, item in enumerate(ranked, start=1):
        comparison.append(
            {
                "rank": position,
                "name": item["option"].get("name"),
                "description": item["option"].get("description"),
                "confidence": item["confidence"],
                "blocked": item["blocked"],
                "recommended": item is winner,
                "strengths": item["strengths"],
                "warnings": item["warnings"],
                "blockers": item["blockers"],
                "verdicts": item["verdicts"],
            }
        )

    return {
        "recommendation": {
            "name": winner["option"].get("name"),
            "description": winner["option"].get("description"),
            "confidence": winner["confidence"],
            "forced": forced,
            "strengths": winner["strengths"],
            "warnings": winner["warnings"],
            "blockers": winner["blockers"],
        },
        "comparison": comparison,
    }


def _parse_option(raw_option: Any, index: int) -> Dict[str, Any]:
    if not isinstance(raw_option, dict):
        raise RequestValidationError("option {} must be an object".format(index))
    _require_exact_keys(
        "option {}".format(index),
        raw_option,
        {"name", ATTR_ENCRYPTION, ATTR_AUTH},
        optional={"description", ATTR_PUBLIC, ATTR_BACKUPS, ATTR_COST},
    )
    name = raw_option.get("name")
    if not isinstance(name, str) or not name.strip():
        raise RequestValidationError(
            "option {} needs a non-empty name".format(index)
        )
    description = raw_option.get("description")
    if description is not None and not isinstance(description, str):
        raise RequestValidationError(
            "option {} description must be a string".format(index)
        )
    candidate: Dict[str, Any] = {"name": name.strip()}
    if description is not None and description.strip():
        candidate["description"] = description.strip()
    for key in (ATTR_ENCRYPTION, ATTR_AUTH, ATTR_PUBLIC, ATTR_BACKUPS):
        if key in raw_option and raw_option[key] is not None:
            if not isinstance(raw_option[key], bool):
                raise RequestValidationError(
                    "option {} field {} must be a boolean".format(index, key)
                )
            candidate[key] = raw_option[key]
    if raw_option.get(ATTR_COST) is not None:
        candidate[ATTR_COST] = _parse_budget(raw_option[ATTR_COST], field=ATTR_COST)
    # Security requires both flags to be present and boolean.
    for required in (ATTR_ENCRYPTION, ATTR_AUTH):
        if required not in candidate:
            raise RequestValidationError(
                "option {} requires {} as a boolean".format(index, required)
            )
    return candidate


def _parse_budget(value: Any, field: str = "budget_usd") -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RequestValidationError("{} must be a number".format(field))
    if value < 0:
        raise RequestValidationError("{} must not be negative".format(field))
    return float(value)


_ARCHITECT_KEYS = {"description", "hardware", "constraints", "knowledge_base_docs"}
_HARDWARE_KEYS = {"cpu_cores", "ram_gb", "has_gpu", "vram_gb", "unified_memory", "storage_gb"}
_CONSTRAINT_KEYS = {
    "monthly_budget_usd",
    "max_latency_ms",
    "privacy",
    "expected_requests_per_day",
    "data_changes_frequently",
}


def evaluate_architecture(payload: Any) -> Dict[str, Any]:
    """Validate the wizard input and run the Architect -> Board -> ADR review."""
    context = _context_from_payload(payload)
    try:
        adr = run_review(context)
    except ValueError as error:
        raise RequestValidationError(str(error)) from error
    return serialize_adr(context, adr)


def build_artifacts(payload: Any) -> Dict[str, Any]:
    """Generate starter artifacts (files) from the reviewed decision."""
    context = _context_from_payload(payload)
    try:
        adr = run_review(context)
    except ValueError as error:
        raise RequestValidationError(str(error)) from error
    return {"files": generate_files(context, adr)}


def artifacts_zip_bytes(payload: Any) -> bytes:
    """Return the generated artifacts packaged as a ZIP archive."""
    files = build_artifacts(payload)["files"]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for entry in files:
            archive.writestr(entry["path"], entry["content"])
    return buffer.getvalue()


def _context_from_payload(payload: Any) -> ProblemContext:
    if not isinstance(payload, dict):
        raise RequestValidationError("request body must be an object")
    _require_exact_keys(
        "request",
        payload,
        {"description", "hardware"},
        optional={
            "constraints",
            "knowledge_base_docs",
            "task",
            "dataset_labeled",
            "dataset_rows",
        },
    )
    description = payload.get("description")
    if not isinstance(description, str) or not description.strip():
        raise RequestValidationError("description must be a non-empty string")

    hardware = _parse_hardware(payload["hardware"])
    constraints = _parse_constraints(payload.get("constraints"))
    docs = payload.get("knowledge_base_docs")
    if docs is not None and (isinstance(docs, bool) or not isinstance(docs, int) or docs < 0):
        raise RequestValidationError("knowledge_base_docs must be a non-negative integer")

    task = payload.get("task")
    if task is not None and (not isinstance(task, str) or task not in FAMILY_LABELS):
        raise RequestValidationError("task is not a recognised problem family")
    dataset_labeled = payload.get("dataset_labeled")
    if dataset_labeled is not None and not isinstance(dataset_labeled, bool):
        raise RequestValidationError("dataset_labeled must be a boolean")
    dataset_rows = payload.get("dataset_rows")
    if dataset_rows is not None and (
        isinstance(dataset_rows, bool) or not isinstance(dataset_rows, int) or dataset_rows < 0
    ):
        raise RequestValidationError("dataset_rows must be a non-negative integer")

    try:
        return ProblemContext(
            description=description.strip(),
            hardware=hardware,
            constraints=constraints,
            knowledge_base_docs=docs,
            task=task,
            dataset_labeled=dataset_labeled,
            dataset_rows=dataset_rows,
        )
    except ValueError as error:
        raise RequestValidationError(str(error)) from error


def _parse_hardware(raw: Any) -> HardwareProfile:
    if not isinstance(raw, dict):
        raise RequestValidationError("hardware must be an object")
    _require_exact_keys(
        "hardware",
        raw,
        {"cpu_cores", "ram_gb"},
        optional={"has_gpu", "vram_gb", "unified_memory", "storage_gb"},
    )
    cpu = _positive_number("cpu_cores", raw.get("cpu_cores"))
    ram = _positive_number("ram_gb", raw.get("ram_gb"))
    vram = _optional_nonneg("vram_gb", raw.get("vram_gb"))
    storage = _optional_nonneg("storage_gb", raw.get("storage_gb"))
    try:
        return HardwareProfile(
            cpu_cores=int(cpu),
            ram_gb=float(ram),
            has_gpu=_optional_flag("has_gpu", raw.get("has_gpu")),
            vram_gb=float(vram),
            unified_memory=_optional_flag("unified_memory", raw.get("unified_memory")),
            storage_gb=float(storage),
        )
    except ValueError as error:
        raise RequestValidationError(str(error)) from error


def _parse_constraints(raw: Any) -> Constraints:
    if raw is None:
        return Constraints()
    if not isinstance(raw, dict):
        raise RequestValidationError("constraints must be an object")
    _require_exact_keys("constraints", raw, set(), optional=set(_CONSTRAINT_KEYS))
    privacy = raw.get("privacy", "public")
    if privacy not in PRIVACY_LEVELS:
        raise RequestValidationError(
            "privacy must be one of {}".format(", ".join(PRIVACY_LEVELS))
        )
    try:
        return Constraints(
            monthly_budget_usd=_optional_nonneg_or_none(
                "monthly_budget_usd", raw.get("monthly_budget_usd")
            ),
            max_latency_ms=_optional_int_or_none("max_latency_ms", raw.get("max_latency_ms")),
            privacy=privacy,
            expected_requests_per_day=_optional_int_or_none(
                "expected_requests_per_day", raw.get("expected_requests_per_day")
            ),
            data_changes_frequently=_optional_flag(
                "data_changes_frequently", raw.get("data_changes_frequently")
            ),
        )
    except ValueError as error:
        raise RequestValidationError(str(error)) from error


def _positive_number(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise RequestValidationError("{} must be a positive number".format(name))
    return float(value)


def _optional_nonneg(name: str, value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise RequestValidationError("{} must be a non-negative number".format(name))
    return float(value)


def _optional_nonneg_or_none(name: str, value: Any):
    if value is None:
        return None
    return _optional_nonneg(name, value)


def _optional_int_or_none(name: str, value: Any):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RequestValidationError("{} must be a non-negative integer".format(name))
    return value


def _optional_flag(name: str, value: Any) -> bool:
    if value is None:
        return False
    if not isinstance(value, bool):
        raise RequestValidationError("{} must be a boolean".format(name))
    return value


def create_server(host: str = "127.0.0.1", port: int = 8080) -> ConsensusHTTPServer:
    """Create, but do not start, the HTTP server for tests and embedding."""
    return ConsensusHTTPServer((host, port), ConsensusRequestHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the consensus-engine web product.")
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST", "127.0.0.1"),
        help="Interface to bind (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "8080")),
        help="TCP port to bind (default: 8080).",
    )
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")

    server = create_server(args.host, args.port)
    print("Consensus Engine listening on http://{}:{}".format(args.host, args.port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
