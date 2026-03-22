from typing import Any

from fastapi import Request
from starlette import status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

_MSG_PREFIXES = (
    "Value error, ",
    "Assertion failed, ",
)


def _normalize_message(msg: str) -> str:
    for prefix in _MSG_PREFIXES:
        if msg.startswith(prefix):
            return msg[len(prefix) :].strip()
    return msg


def _issue_from_error(err: dict[str, Any]) -> dict[str, Any]:
    loc = err.get("loc") or ()
    path = ".".join(str(part) for part in loc)
    return {
        "path": path,
        "code": err.get("type", "validation_error"),
        "message": _normalize_message(err.get("msg") or ""),
        "input": err.get("input"),
    }


async def request_validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    issues = [_issue_from_error(e) for e in exc.errors()]
    payload = {"error": "validation_error", "issues": issues}
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=jsonable_encoder(payload),
    )
