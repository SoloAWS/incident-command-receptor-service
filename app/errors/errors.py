class ApiError(Exception):
    code = 422
    description = "N/A"

class InvalidToken(ApiError):
    code = 401

class EmptyToken(ApiError):
    code = 403