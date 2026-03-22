from fastapi import Request
from starlette import status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def request_validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    issues = [
        {
            "path": ".".join(str(part) for part in (err.get("loc") or ())),
            "code": err.get("type", "validation_error"),
            "message": (err.get("msg") or "")
            .removeprefix("Value error, ")
            .removeprefix("Assertion failed, "),
            "input": err.get("input"),
        }
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"error": "validation_error", "issues": issues},
    )
