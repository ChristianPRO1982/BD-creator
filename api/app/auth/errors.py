class AuthError(Exception):
    pass


class InvalidCallbackError(AuthError):
    pass


class UnknownUserError(AuthError):
    pass


class DisabledUserError(AuthError):
    pass


class KeycloakAuthError(AuthError):
    pass
