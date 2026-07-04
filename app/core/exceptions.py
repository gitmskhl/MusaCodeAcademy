class InvalidTokenError(Exception):
    pass

class StorageError(Exception):
    """Базовое исключение для StorageService."""
    pass


class InvalidFileExtensionError(StorageError):
    pass


class InvalidMimeTypeError(StorageError):
    pass


class EmptyFilenameError(StorageError):
    pass


class FileTooLargeError(StorageError):
    pass


class EmptyFileError(StorageError):
    pass


class InvalidImageContentError(StorageError):
    pass