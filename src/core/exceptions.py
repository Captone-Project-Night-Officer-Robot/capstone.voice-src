from __future__ import annotations


class NightOfficerError(Exception):
    """Base for all domain exceptions."""


class AgentSessionError(NightOfficerError):
    """LiveKit agent session could not be started."""


class LiveKitTokenError(NightOfficerError):
    """Room token generation failed."""


class ConfigurationError(NightOfficerError):
    """Missing or invalid configuration."""