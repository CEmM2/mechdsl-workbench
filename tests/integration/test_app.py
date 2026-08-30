from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from mechdsl_workbench.app import create_app
from mechdsl_workbench.config import Settings

pytestmark = pytest.mark.integration


def make_client(fake_service, **settings_overrides):
    settings = Settings(**settings_overrides)
    return TestClient(create_app(settings=settings, compiler_service=fake_service))


def test_homepage_contains_dual_mode_workbench(fake_service) -> None:
    with make_client(fake_service) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "MechDSL Workbench" in response.text
    assert 'id="source-input"' in response.text
    assert 'id="mode-mechanics"' in response.text
    assert 'id="mode-algorithm"' in response.text
    assert "Generated Taichi" in response.text


def test_compile_route_forwards_public_request(fake_service) -> None:
    with make_client(fake_service) as client:
        response = client.post(
            "/api/compile",
            json={"problem_source": "% mechanics dim 3", "profile": "mvp"},
        )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert fake_service.last_compile_request.problem_source == "% mechanics dim 3"


def test_transpile_route_forwards_algorithm_request(fake_service) -> None:
    with make_client(fake_service) as client:
        response = client.post(
            "/api/transpile",
            json={"algorithm_source": "% algorithm axpy", "backend": "taichi"},
        )
    assert response.status_code == 200
    assert response.json()["entry_point"] == "axpy"
    assert fake_service.last_transpile_request.algorithm_source == "% algorithm axpy"


def test_transpile_failure_is_structured_and_keeps_http_200(fake_service) -> None:
    fake_service.transpile_result = {
        "ok": False,
        "diagnostic": {
            "severity": "error",
            "stage": "transpiler",
            "category": "ParseError",
            "message": "bad algorithm",
        },
    }
    with make_client(fake_service) as client:
        response = client.post("/api/transpile", json={"algorithm_source": "bad"})
    assert response.status_code == 200
    assert response.json()["diagnostic"]["stage"] == "transpiler"


def test_preview_route_escapes_html_for_algorithm(fake_service) -> None:
    with make_client(fake_service) as client:
        response = client.post(
            "/api/preview",
            json={"mode": "algorithm", "source": "<img src=x onerror=alert(1)>"},
        )
    assert response.status_code == 200
    assert "<img" not in response.json()["body_html"]
    assert "&lt;img" in response.json()["body_html"]


def test_preview_route_accepts_v01_problem_source_key(fake_service) -> None:
    with make_client(fake_service) as client:
        response = client.post(
            "/api/preview",
            json={"problem_source": "% mechanics dim 3"},
        )
    assert response.status_code == 200
    assert response.json()["mode"] == "mechanics"


def test_examples_can_be_filtered_by_mode(fake_service) -> None:
    with make_client(fake_service) as client:
        response = client.get("/api/examples?mode=algorithm")
    assert response.status_code == 200
    assert response.json()["examples"]
    assert all(item["mode"] == "algorithm" for item in response.json()["examples"])


def test_invalid_json_shape_returns_400(fake_service) -> None:
    with make_client(fake_service) as client:
        response = client.post("/api/compile", json=["not", "an", "object"])
    assert response.status_code == 400
    assert response.json()["ok"] is False


def test_readyz_requires_both_mechanics_and_algorithm_toolchains(fake_service) -> None:
    with make_client(fake_service) as client:
        response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json()["compiler"]["algorithm_ready"] is True


def test_missing_algo2code_reports_partial_readiness(fake_service) -> None:
    fake_service.capabilities_result["packages"]["algo2code"] = None
    with make_client(fake_service) as client:
        response = client.get("/readyz")
    assert response.status_code == 503
    compiler = response.json()["compiler"]
    assert compiler["mechanics_ready"] is True
    assert compiler["algorithm_ready"] is False


def test_security_headers_are_present(fake_service) -> None:
    with make_client(fake_service) as client:
        response = client.get("/")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "object-src 'none'" in response.headers["content-security-policy"]


def test_custom_mathjax_origin_is_added_to_csp(fake_service) -> None:
    with make_client(fake_service, mathjax_url="https://math.example.org/tex.js") as client:
        response = client.get("/")
    assert "https://math.example.org" in response.headers["content-security-policy"]
