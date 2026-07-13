"""Define safe application errors shared by credential and analysis boundaries."""


class AnalysisError(Exception):
    """Carry a stable public code and message without leaking internal exceptions."""

    def __init__(self, code: str, public_message: str):
        """Preserve only fields approved to cross the safe error boundary."""

        super().__init__(public_message)
        self.code = code
        self.public_message = public_message
