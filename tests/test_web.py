"""HTTP integration tests for the consensus web product."""

import http.client
import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from consensus_web.server import create_server


class ConsensusWebTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = create_server("127.0.0.1", 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = "http://{}:{}".format(host, port)

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, path, method="GET", payload=None, content_type=None):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {} if content_type is None else {"Content-Type": content_type}
        request = Request(self.base_url + path, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=2) as response:
                return response.status, response.headers, response.read()
        except HTTPError as error:
            return error.code, error.headers, error.read()

    def pass_verdict(self):
        return {
            "agent": "security",
            "verdict": "PASS",
            "severity": "info",
            "risk": None,
            "hard_rules_passed": 1,
            "hard_rules_total": 1,
        }

    def blocker(self, risk):
        return {
            "agent": "security",
            "verdict": "FAIL",
            "severity": "blocker",
            "risk": risk,
            "hard_rules_passed": 0,
            "hard_rules_total": 1,
        }

    def test_health_and_frontend_have_security_headers(self) -> None:
        status, headers, body = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"AI Solution Architect", body)
        self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["X-Frame-Options"], "DENY")

        status, _, body = self.request("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"status": "ok", "version": "0.1.0"})

    def test_api_converges_and_serializes_result(self) -> None:
        payload = {
            "rounds": [
                {
                    "candidate": {"name": "managed storage"},
                    "verdicts": [
                        self.pass_verdict(),
                        {
                            "agent": "reliability",
                            "verdict": "WARN",
                            "severity": "warning",
                            "risk": "Exercise recovery before release.",
                            "hard_rules_passed": 1,
                            "hard_rules_total": 1,
                        },
                    ],
                }
            ]
        }
        status, _, body = self.request(
            "/api/consensus", "POST", payload, "application/json"
        )
        self.assertEqual(status, 200)
        result = json.loads(body)["result"]
        self.assertEqual(result["architecture"], {"name": "managed storage"})
        self.assertEqual(result["confidence"], 75)
        self.assertEqual(result["accepted_risks"], ["Exercise recovery before release."])
        self.assertFalse(result["forced"])

    def test_api_forces_delivery_after_two_reproposals(self) -> None:
        payload = {
            "context": {"project": "payments"},
            "rounds": [
                {
                    "candidate": {"version": 1},
                    "verdicts": [self.blocker("Missing encryption 1.")],
                },
                {
                    "candidate": {"version": 2},
                    "verdicts": [self.blocker("Missing encryption 2.")],
                },
                {
                    "candidate": {"version": 3},
                    "verdicts": [self.blocker("Missing encryption 3.")],
                },
            ],
        }
        status, _, body = self.request(
            "/api/consensus", "POST", payload, "application/json"
        )
        self.assertEqual(status, 200)
        result = json.loads(body)["result"]
        self.assertTrue(result["forced"])
        self.assertEqual(result["round_reached"], 2)
        self.assertEqual(result["architecture"], {"version": 3})
        self.assertEqual(result["unresolved_risks"], ["Missing encryption 3."])
        self.assertEqual(
            [entry["rejected_round"] for entry in result["rejected"]], [0, 1]
        )

    def test_api_rejects_invalid_media_type_and_incomplete_blocker_sequence(self) -> None:
        status, _, body = self.request("/api/consensus", "POST", {"rounds": []})
        self.assertEqual(status, 415)
        self.assertEqual(json.loads(body)["error"], "Content-Type must be application/json")

        payload = {
            "rounds": [
                {"candidate": {"version": 1}, "verdicts": [self.blocker("Missing encryption.")]}
            ]
        }
        status, _, body = self.request(
            "/api/consensus", "POST", payload, "application/json"
        )
        self.assertEqual(status, 400)
        self.assertIn("requires the next round", json.loads(body)["error"])

    def test_api_rejects_unknown_fields_and_unused_rounds(self) -> None:
        payload = {
            "rounds": [
                {"candidate": {"version": 1}, "verdicts": [self.pass_verdict()]}
            ],
            "unexpected": True,
        }
        status, _, body = self.request(
            "/api/consensus", "POST", payload, "application/json"
        )
        self.assertEqual(status, 400)
        self.assertIn("invalid field set", json.loads(body)["error"])

        payload = {
            "rounds": [
                {"candidate": {"version": 1}, "verdicts": [self.pass_verdict()]},
                {"candidate": {"version": 2}, "verdicts": [self.pass_verdict()]},
            ]
        }
        status, _, body = self.request(
            "/api/consensus", "POST", payload, "application/json"
        )
        self.assertEqual(status, 400)
        self.assertIn("remove unused rounds", json.loads(body)["error"])
    def test_api_rejects_body_larger_than_one_mebibyte(self) -> None:
        host, port = self.server.server_address
        connection = http.client.HTTPConnection(host, port, timeout=2)
        connection.putrequest("POST", "/api/consensus")
        connection.putheader("Content-Type", "application/json")
        connection.putheader("Content-Length", str(1_048_577))
        connection.endheaders()
        response = connection.getresponse()
        body = response.read()
        connection.close()
        self.assertEqual(response.status, 413)
        self.assertEqual(json.loads(body)["error"], "request body exceeds 1 MiB")


    def test_evaluate_recommends_best_unblocked_option(self) -> None:
        payload = {
            "budget_usd": 200,
            "options": [
                {
                    "name": "Postgres administrado",
                    "encryption_at_rest": True,
                    "authentication": True,
                    "public_network": False,
                    "has_backups": True,
                    "monthly_cost_usd": 120,
                },
                {
                    "name": "Cache sin cifrado",
                    "encryption_at_rest": False,
                    "authentication": True,
                    "monthly_cost_usd": 50,
                },
            ],
        }
        status, _, body = self.request(
            "/api/evaluate", "POST", payload, "application/json"
        )
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data["recommendation"]["name"], "Postgres administrado")
        self.assertFalse(data["recommendation"]["forced"])
        self.assertEqual(data["comparison"][0]["rank"], 1)
        self.assertTrue(data["comparison"][0]["recommended"])
        blocked = next(c for c in data["comparison"] if c["name"] == "Cache sin cifrado")
        self.assertTrue(blocked["blocked"])
        self.assertTrue(blocked["blockers"])

    def test_evaluate_forces_when_all_options_blocked(self) -> None:
        payload = {
            "budget_usd": 100,
            "options": [
                {
                    "name": "Opcion cara",
                    "encryption_at_rest": True,
                    "authentication": True,
                    "monthly_cost_usd": 500,
                },
                {
                    "name": "Opcion insegura",
                    "encryption_at_rest": False,
                    "authentication": False,
                    "monthly_cost_usd": 10,
                },
            ],
        }
        status, _, body = self.request(
            "/api/evaluate", "POST", payload, "application/json"
        )
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertTrue(data["recommendation"]["forced"])
        self.assertTrue(all(item["blocked"] for item in data["comparison"]))

    def test_evaluate_rejects_missing_security_attributes(self) -> None:
        payload = {"options": [{"name": "Incompleta", "monthly_cost_usd": 10}]}
        status, _, body = self.request(
            "/api/evaluate", "POST", payload, "application/json"
        )
        self.assertEqual(status, 400)
        self.assertIn("invalid field set", json.loads(body)["error"])

    def test_evaluate_rejects_empty_option_list(self) -> None:
        status, _, body = self.request(
            "/api/evaluate", "POST", {"options": []}, "application/json"
        )
        self.assertEqual(status, 400)
        self.assertIn("1 to 5", json.loads(body)["error"])

    def test_architect_scripted_scenario_converges_on_rag(self) -> None:
        payload = {
            "description": "Chatbot sobre 5.000 PDFs que cambian cada semana.",
            "hardware": {"cpu_cores": 10, "ram_gb": 16, "unified_memory": True},
            "constraints": {
                "monthly_budget_usd": 200,
                "privacy": "private_cloud",
                "data_changes_frequently": True,
            },
            "knowledge_base_docs": 5000,
        }
        status, _, body = self.request(
            "/api/architect", "POST", payload, "application/json"
        )
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data["recommendation"]["strategy"], "rag")
        self.assertGreaterEqual(data["confidence"], 80)
        techniques = {row["technique"] for row in data["capability_matrix"]}
        self.assertEqual(techniques, {"rag", "agents", "lora", "fine_tuning"})
        rejected = [alt["strategy"] for alt in data["rejected_alternatives"]]
        self.assertIn("fine_tuning", rejected)

    def test_architect_rejects_missing_hardware(self) -> None:
        status, _, body = self.request(
            "/api/architect", "POST", {"description": "algo"}, "application/json"
        )
        self.assertEqual(status, 400)
        self.assertIn("invalid field set", json.loads(body)["error"])

    def test_architect_rejects_invalid_privacy(self) -> None:
        payload = {
            "description": "algo",
            "hardware": {"cpu_cores": 4, "ram_gb": 8},
            "constraints": {"privacy": "martian"},
        }
        status, _, body = self.request(
            "/api/architect", "POST", payload, "application/json"
        )
        self.assertEqual(status, 400)
        self.assertIn("privacy", json.loads(body)["error"])

    def test_artifacts_json_lists_expected_files(self) -> None:
        payload = {
            "description": "predecir precio con datos etiquetados",
            "task": "regression",
            "hardware": {"cpu_cores": 8, "ram_gb": 16, "unified_memory": True},
            "constraints": {"monthly_budget_usd": 100, "privacy": "private_cloud"},
        }
        status, _, body = self.request(
            "/api/artifacts", "POST", payload, "application/json"
        )
        self.assertEqual(status, 200)
        paths = {f["path"] for f in json.loads(body)["files"]}
        for expected in (
            "README.md",
            "docs/ADR.md",
            "Dockerfile",
            "infra/main.tf",
            ".github/workflows/ci.yml",
            "src/train.py",
        ):
            self.assertIn(expected, paths)

    def test_artifacts_zip_downloads_valid_archive(self) -> None:
        import io
        import zipfile

        payload = {
            "description": "clasificar churn",
            "task": "classification",
            "hardware": {"cpu_cores": 8, "ram_gb": 16, "unified_memory": True},
            "constraints": {"privacy": "private_cloud"},
        }
        status, headers, body = self.request(
            "/api/artifacts.zip", "POST", payload, "application/json"
        )
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "application/zip")
        self.assertIn("attachment", headers["Content-Disposition"])
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            names = archive.namelist()
            self.assertIn("README.md", names)
            self.assertIn("infra/main.tf", names)


if __name__ == "__main__":
    unittest.main()
