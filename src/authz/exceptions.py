from src.authz.models import Reason


class AuthorizationError(Exception):
    def __init__(self, reason: Reason) -> None:
        self.reason = reason
        super().__init__(reason)
