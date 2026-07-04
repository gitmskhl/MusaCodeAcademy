from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    STUDENT = "student"


class FileType(str, Enum):
    IMAGE = "image"
    DOCUMENT = "document"
    VIDEO = "video"
    ARCHIVE = "archive"