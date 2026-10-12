"""
Service layer base class.

Services orchestrate business logic and are the only layer that talks to
both repositories AND the nlp/ subsystem. API endpoints stay thin — they
parse the request, call a service method, and serialize the response.
"""

from abc import ABC


class BaseService(ABC):
    """Marker base class. Currently just documents intent; extend with
    shared cross-cutting behavior (e.g. audit logging) as real services
    accumulate common needs."""
    pass
