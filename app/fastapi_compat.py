from __future__ import annotations

from dataclasses import asdict, is_dataclass
from inspect import signature
from typing import get_type_hints


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class BackgroundTasks:
    def __init__(self):
        self.tasks = []

    def add_task(self, fn, *args, **kwargs):
        self.tasks.append((fn, args, kwargs))


class FastAPI:
    def __init__(self, title: str = "", version: str = ""):
        self.title = title
        self.version = version
        self.routes: dict[tuple[str, str], tuple] = {}

    def get(self, path: str, response_model=None):
        return self._register("GET", path, response_model)

    def post(self, path: str, response_model=None):
        return self._register("POST", path, response_model)

    def _register(self, method: str, path: str, response_model=None):
        def decorator(fn):
            self.routes[(method.upper(), path)] = (fn, response_model)
            return fn

        return decorator


class _Response:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self):
        return self._payload

    @property
    def text(self) -> str:
        return str(self._payload)


def _to_payload(value):
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, list):
        return [_to_payload(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_payload(v) for k, v in value.items()}
    return value


def _call_route(fn, json_body=None):
    sig = signature(fn)
    hints = get_type_hints(fn)
    kwargs = {}
    for name, param in sig.parameters.items():
        ann = hints.get(name, param.annotation)
        if name in ("bg", "background_tasks"):
            kwargs[name] = BackgroundTasks()
            continue
        if json_body is not None and isinstance(json_body, dict):
            if ann is not param.empty and hasattr(ann, "from_dict"):
                kwargs[name] = ann.from_dict(json_body)
            elif ann is not param.empty and callable(ann):
                try:
                    kwargs[name] = ann(**json_body)
                except Exception:
                    kwargs[name] = json_body
            else:
                kwargs[name] = json_body
    result = fn(**kwargs)
    return _to_payload(result)


class TestClient:
    __test__ = False

    def __init__(self, app: FastAPI):
        self.app = app

    def get(self, path: str):
        return self._request("GET", path, None)

    def post(self, path: str, json=None):
        return self._request("POST", path, json)

    def _request(self, method: str, path: str, json):
        route = self.app.routes.get((method.upper(), path))
        if not route:
            return _Response(404, {"detail": "Not found"})
        fn, _ = route
        try:
            payload = _call_route(fn, json)
            return _Response(200, payload)
        except HTTPException as exc:
            return _Response(exc.status_code, {"detail": exc.detail})
