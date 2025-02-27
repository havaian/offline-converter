# src/core/exceptions.py
class ConverterError(Exception):
    """Base exception for converter errors"""
    pass

class UnsupportedFormatError(ConverterError):
    """Raised when format is not supported"""
    pass

class DependencyError(ConverterError):
    """Raised when required dependency is missing"""
    pass