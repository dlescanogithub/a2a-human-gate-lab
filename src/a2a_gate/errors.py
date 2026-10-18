"""Errors the lab raises. ``reason_code`` is safe to log; it is not free text."""


class GateLabError(Exception):
    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


class ValidationError(GateLabError):
    pass


class AuthError(GateLabError):
    pass


class ConfigError(GateLabError):
    pass


class PermanentError(GateLabError):
    pass


class TransientError(GateLabError):
    pass
