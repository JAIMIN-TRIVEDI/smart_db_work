class DatabaseError(Exception):
    """Base class for all database exceptions."""

    pass


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""

    pass


class AuthenticationError(DatabaseConnectionError):
    """Raised for invalid credentials."""

    pass


class UnsupportedDatabaseError(DatabaseError):
    """Raised when an unsupported DB type is requested."""

    pass


class DatabaseNotConnectedError(DatabaseError):
    """Raised when trying to use a disconnected database."""

    pass
