"""CLI subcommand and hosted-API client tests (client runs against a local stub server)."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from chempath_demo.cli import main
from chempath_demo.client import ChemPathAPIError, ChemPathClient


def test_cli_batch_library_explain(tmp_path, capsys):
    assert main(["batch", "examples/mixed_batch.json", "--out", str(tmp_path / "b.json")]) == 0
    assert json.loads((tmp_path / "b.json").read_text())["items_submitted"] == 4
    assert main(["library"]) == 0
    assert "VBGLYOIFKLUMQG-UHFFFAOYSA-N" in capsys.readouterr().out
    assert main(["explain", "--samples", "800"]) == 0
    assert "recovered as top features: True" in capsys.readouterr().out


def test_cli_pdf_and_failed(tmp_path, capsys):
    pytest.importorskip("reportlab")
    pdf = tmp_path / "p.pdf"
    assert main(["analyze", "examples/partial_formulation.json", "--pdf", str(pdf)]) == 0
    assert pdf.read_bytes().startswith(b"%PDF")
    failed = tmp_path / "failed.json"
    failed.write_text(json.dumps({"entries": [{"name": "unknown"}]}))
    assert main(["analyze", str(failed), "--pdf", str(tmp_path / "f.pdf")]) == 2
    assert not (tmp_path / "f.pdf").exists()


class _Stub(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _reply(self, status, body, ctype="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.headers.get("X-API-Key") != "test-key":
            return self._reply(401, b'{"error":"unauthorized"}')
        if self.path.endswith("/report"):
            return self._reply(200, b"%PDF-1.4 stub", "application/pdf")
        self._reply(200, json.dumps({"path": self.path}).encode())

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self._reply(200, json.dumps({"path": self.path, "echo": body}).encode())


@pytest.fixture
def server():
    httpd = HTTPServer(("127.0.0.1", 0), _Stub)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


def test_client_routes(server):
    c = ChemPathClient(server, "test-key")
    assert c.formulation({"entries": [{"name": "CBN"}]})["path"] == "/api/v1/chempath/formulation"
    assert c.batch([{"kind": "compound"}])["echo"] == {"items": [{"kind": "compound"}]}
    assert c.report_json("a1")["path"] == "/api/v1/chempath/a1/report?format=json"
    assert c.report_pdf("a1").startswith(b"%PDF")
    assert c.history(limit=5)["path"] == "/api/v1/chempath/history?limit=5&offset=0"
    assert c.status()["path"] == "/api/lab/status"


def test_client_errors(server, monkeypatch):
    with pytest.raises(ChemPathAPIError) as exc:
        ChemPathClient(server, "wrong").status()
    assert exc.value.status == 401
    monkeypatch.delenv("CHEMPATH_BASE_URL", raising=False)
    monkeypatch.delenv("CHEMPATH_API_KEY", raising=False)
    with pytest.raises(ValueError):
        ChemPathClient()
