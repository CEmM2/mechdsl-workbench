"""Starlette application factory for the external MechDSL workbench."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version
from starlette.applications import Starlette
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from . import __version__
from .compiler.diagnostics import normalize_exception
from .compiler.models import CompileRequest, TranspileRequest
from .compiler.service import CompilerService, SubprocessCompilerService
from .config import Settings
from .examples import get_example, list_examples
from .middleware import ContentLengthLimitMiddleware, SecurityHeadersMiddleware
from .services.preview import render_preview


def create_app(
    settings: Settings | None = None,
    compiler_service: CompilerService | None = None,
) -> Starlette:
    settings = settings or Settings.from_env()
    service = compiler_service or SubprocessCompilerService(settings)
    templates = Jinja2Templates(directory=str(settings.templates_dir))
    example_metadata = list_examples()
    mechanics_examples = [item for item in example_metadata if item["mode"] == "mechanics"]
    default_example = get_example(mechanics_examples[0]["id"])

    @asynccontextmanager
    async def lifespan(app: Starlette):
        try:
            raw_probe = await service.capabilities()
        except Exception as exc:  # defensive boundary around an injected service
            raw_probe = {
                "ok": False,
                "diagnostic": normalize_exception(exc).to_dict(),
            }
        app.state.compiler_probe = _probe_status(raw_probe, settings.supported_mechdsl)
        yield

    async def index(request: Request):
        probe = getattr(
            request.app.state,
            "compiler_probe",
            {
                "available": False,
                "compatible": False,
                "mechanics_ready": False,
                "algorithm_ready": False,
                "message": "Compiler probe has not run",
                "version": None,
            },
        )
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "app_version": __version__,
                "examples": example_metadata,
                "default_example": default_example,
                "compiler_probe": probe,
                "mathjax_url": settings.mathjax_url,
                "max_source_bytes": settings.max_source_bytes,
            },
        )

    async def compile_api(request: Request) -> JSONResponse:
        payload, error = await _json_object(request)
        if error is not None:
            return error
        try:
            compile_request = CompileRequest.from_mapping(payload)
        except (TypeError, ValueError) as exc:
            return _http_error(str(exc), category=type(exc).__name__, status_code=400)

        if not compile_request.problem_source.strip():
            return _http_error(
                "problem_source must not be empty",
                category="EmptySource",
                status_code=400,
            )

        result = await service.compile(compile_request)
        return JSONResponse(result, status_code=200)

    async def transpile_api(request: Request) -> JSONResponse:
        payload, error = await _json_object(request)
        if error is not None:
            return error
        try:
            transpile_request = TranspileRequest.from_mapping(payload)
        except (TypeError, ValueError) as exc:
            return _http_error(str(exc), category=type(exc).__name__, status_code=400)

        if not transpile_request.algorithm_source.strip():
            return _http_error(
                "algorithm_source must not be empty",
                category="EmptySource",
                status_code=400,
            )

        result = await service.transpile(transpile_request)
        return JSONResponse(result, status_code=200)

    async def preview_api(request: Request) -> JSONResponse:
        payload, error = await _json_object(request)
        if error is not None:
            return error

        # v0.2 uses generic ``source`` while accepting v0.1's mechanics key.
        source = payload.get("source", payload.get("problem_source"))
        mode = payload.get("mode", "mechanics")
        if not isinstance(source, str):
            return _http_error(
                "source must be a string",
                category="TypeError",
                status_code=400,
            )
        if mode not in {"mechanics", "algorithm"}:
            return _http_error(
                "mode must be 'mechanics' or 'algorithm'",
                category="ValueError",
                status_code=400,
            )
        size = len(source.encode("utf-8"))
        if size > settings.max_source_bytes:
            return _http_error(
                f"source is {size} bytes; limit is {settings.max_source_bytes}",
                category="SourceTooLarge",
                status_code=413,
            )
        return JSONResponse({"ok": True, **render_preview(source, mode=mode)})

    async def examples_api(request: Request) -> JSONResponse:
        mode = request.query_params.get("mode")
        if mode is not None and mode not in {"mechanics", "algorithm"}:
            return _http_error(
                "mode must be 'mechanics' or 'algorithm'",
                category="ValueError",
                status_code=400,
            )
        examples = list_examples(mode=mode) if mode else example_metadata
        return JSONResponse({"ok": True, "examples": examples})

    async def example_api(request: Request) -> JSONResponse:
        example_id = request.path_params["example_id"]
        try:
            example = get_example(example_id)
        except KeyError:
            return _http_error(
                f"unknown example: {example_id}",
                category="ExampleNotFound",
                status_code=404,
            )
        return JSONResponse({"ok": True, "example": example})

    async def capabilities_api(request: Request) -> JSONResponse:
        result = await service.capabilities()
        status = _probe_status(result, settings.supported_mechdsl)
        request.app.state.compiler_probe = status
        return JSONResponse(
            {"ok": result.get("ok") is True, "result": result, "status": status},
            status_code=200 if result.get("ok") is True else 503,
        )

    async def models_api(_: Request) -> JSONResponse:
        result = await service.models()
        return JSONResponse(result, status_code=200 if result.get("ok") is True else 503)

    async def healthz(_: Request) -> JSONResponse:
        return JSONResponse(
            {
                "ok": True,
                "service": "mechdsl-workbench",
                "version": __version__,
                "modes": ["mechanics", "algorithm"],
            }
        )

    async def readyz(request: Request) -> JSONResponse:
        probe = getattr(request.app.state, "compiler_probe", None)
        if probe is None or not probe.get("available"):
            try:
                result = await service.capabilities()
            except Exception as exc:
                result = {"ok": False, "diagnostic": normalize_exception(exc).to_dict()}
            probe = _probe_status(result, settings.supported_mechdsl)
            request.app.state.compiler_probe = probe

        ready = bool(probe.get("compatible"))
        return JSONResponse(
            {"ok": ready, "compiler": probe},
            status_code=200 if ready else 503,
        )

    routes = [
        Route("/", index, methods=["GET"], name="index"),
        Route("/api/compile", compile_api, methods=["POST"]),
        Route("/api/transpile", transpile_api, methods=["POST"]),
        Route("/api/preview", preview_api, methods=["POST"]),
        Route("/api/examples", examples_api, methods=["GET"]),
        Route("/api/examples/{example_id:str}", example_api, methods=["GET"]),
        Route("/api/capabilities", capabilities_api, methods=["GET"]),
        Route("/api/models", models_api, methods=["GET"]),
        Route("/healthz", healthz, methods=["GET"]),
        Route("/readyz", readyz, methods=["GET"]),
        Mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static"),
    ]

    app = Starlette(debug=settings.debug, routes=routes, lifespan=lifespan)
    app.state.settings = settings
    app.state.compiler_service = service
    app.add_middleware(
        SecurityHeadersMiddleware,
        mathjax_url=settings.mathjax_url,
    )
    app.add_middleware(
        ContentLengthLimitMiddleware,
        max_bytes=settings.max_request_bytes,
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    return app


def _probe_status(result: dict[str, Any], supported_spec: str) -> dict[str, Any]:
    if result.get("ok") is not True:
        diagnostic = result.get("diagnostic") or {}
        return {
            "available": False,
            "compatible": False,
            "mechanics_ready": False,
            "algorithm_ready": False,
            "version": None,
            "algo2code_version": None,
            "message": diagnostic.get("message", "MechDSL compiler is unavailable"),
            "capabilities": None,
        }

    capabilities = result.get("capabilities")
    if not isinstance(capabilities, dict):
        return {
            "available": False,
            "compatible": False,
            "mechanics_ready": False,
            "algorithm_ready": False,
            "version": None,
            "algo2code_version": None,
            "message": "MechDSL capability response was malformed",
            "capabilities": None,
        }

    packages = result.get("packages")
    if not isinstance(packages, dict):
        packages = {}

    version_text = str(capabilities.get("version", "unknown"))
    version_ok = _version_matches(version_text, supported_spec)
    profiles = capabilities.get("profiles", [])
    backends = capabilities.get("backends", [])
    actions = capabilities.get("actions", [])
    common_contract = version_ok and "taichi" in backends
    mechanics_ready = common_contract and "mvp" in profiles and "emit" in actions

    algo2code_version = packages.get("algo2code")
    algorithm_ready = common_contract and "transpile" in actions and bool(algo2code_version)
    compatible = mechanics_ready and algorithm_ready

    if compatible:
        message = f"MechDSL {version_text} + algo2code {algo2code_version} ready"
    elif not version_ok:
        message = f"MechDSL {version_text} is outside supported range {supported_spec}"
    elif not mechanics_ready:
        message = "MechDSL is installed but lacks the required mvp/Taichi emit contract"
    elif "transpile" not in actions:
        message = "MechDSL integration does not expose the required transpile action"
    else:
        message = "Mechanics mode is ready; install the pinned algo2code package for Algorithm mode"

    return {
        "available": True,
        "compatible": compatible,
        "mechanics_ready": mechanics_ready,
        "algorithm_ready": algorithm_ready,
        "version": version_text,
        "algo2code_version": algo2code_version,
        "message": message,
        "capabilities": capabilities,
        "packages": packages,
    }


def _version_matches(version_text: str, supported_spec: str) -> bool:
    try:
        return Version(version_text) in SpecifierSet(supported_spec)
    except (InvalidVersion, InvalidSpecifier):
        return False


async def _json_object(request: Request) -> tuple[dict[str, Any], JSONResponse | None]:
    try:
        payload = await request.json()
    except Exception:
        return {}, _http_error(
            "Request body must be valid JSON",
            category="InvalidJSON",
            status_code=400,
        )
    if not isinstance(payload, dict):
        return {}, _http_error(
            "Request JSON must be an object",
            category="InvalidJSONShape",
            status_code=400,
        )
    return payload, None


def _http_error(message: str, *, category: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        {
            "ok": False,
            "diagnostic": {
                "severity": "error",
                "stage": "http",
                "category": category,
                "message": message,
                "code": "WORKBENCH-HTTP",
            },
        },
        status_code=status_code,
    )
