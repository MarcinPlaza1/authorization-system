from fastapi import Request, status, HTTPException
from fastapi.responses import JSONResponse
from app.models.errors import ErrorResponse, ErrorDetail, ErrorTypes, ErrorMessages
from pydantic import ValidationError

async def error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Globalny handler błędów."""
    if isinstance(exc, HTTPException):
        error_type = ErrorTypes.VALIDATION_ERROR if exc.status_code == 400 else ErrorTypes.SERVER_ERROR
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=ErrorDetail(
                    code=exc.status_code,
                    message=str(exc.detail),
                    type=error_type
                )
            ).dict()
        )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error=ErrorDetail(
                code=500,
                message=ErrorMessages.SERVER_ERROR,
                type=ErrorTypes.SERVER_ERROR,
                details=str(exc)
            )
        ).dict()
    )

async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handler dla błędów walidacji."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error=ErrorDetail(
                code=422,
                message=ErrorMessages.VALIDATION_ERROR,
                type=ErrorTypes.VALIDATION_ERROR,
                details=exc.errors()
            )
        ).dict()
    ) 