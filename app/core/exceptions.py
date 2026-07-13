class InvalidTokenError(Exception):
    pass

class StorageError(Exception):
    """Базовое исключение для StorageService."""
    pass


class WorkerError(Exception):
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


class SubmissionNotFoundError(WorkerError):
    pass


class TaskNotFoundError(WorkerError):
    def __init__(self, task_id: int):
        self.task_id = task_id
        super().__init__(f"Task {task_id} not found")


class TestsNotFound(WorkerError):
    def __init__(self, task_id: int):
        self.task_id = task_id
        super().__init__(f"Tests not found for task {task_id}")