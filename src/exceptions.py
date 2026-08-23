class Unauthenticated(Exception):
    """Bearer token missing in a required sense, or verification failed."""


class NotFound(Exception):
    """The path id is not a known resource."""


class Conflict(Exception):
    """The write collides with an existing row."""
