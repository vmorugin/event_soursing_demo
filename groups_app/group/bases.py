from __future__ import annotations
from typing import (
    Generic,
    Iterable,
)

from d3m.core import (
    AbstractEvent,
    Version,
    DomainName,
    IRootEntity,
    MessageName,
)

from d3m.core.abstractions import (
    AbstractEventMeta,
    _ReferenceType,
    IRootEntityMeta,
)
from d3m.domain import (
    Entity,
    get_event_class,
)
from d3m.domain.bases import (
    BaseDomainMessageMeta,
    BaseDomainMessage,
    get_domain_name,
)
from d3m.domain.entities import (
    _EntityMeta,
    increment_version,
)
from pydantic._internal._model_construction import ModelMetaclass


class _DomainEventMeta(BaseDomainMessageMeta, AbstractEventMeta):
    def __init__(cls, name, bases, namespace, *, domain: str | None = None):
        super().__init__(name, bases, namespace, domain=domain)
        if domain is None and cls.__module__ != __name__:
            try:
                _ = cls.__domain_name__
            except AttributeError:
                raise ValueError(
                    f"required set domain name for event '{cls.__module__}.{cls.__name__}'"
                )


def set_version(entity: RootEntity, version: int):
    """
    Set the version of the root entity

    Attributes:
        entity (RootEntity): The root entity object whose version needs to be set.

    """
    if isinstance(entity.__pydantic_private__, dict):
        if old_version := entity.__pydantic_private__.get("_RootEntity__version"):
            assert version > old_version, "New version must be not less then current"
        entity.__pydantic_private__["_RootEntity__version"] = version


class DomainEvent(BaseDomainMessage, AbstractEvent, metaclass=_DomainEventMeta):
    reference: _ReferenceType
    version: Version

    def mutate(self, aggregate: RootEntity | None) -> RootEntity | None:
        assert aggregate is not None

        # Check this event belongs to this aggregate.
        assert aggregate.__reference__ == self.reference

        # Check this event is the next in its sequence.
        next_version = aggregate.__version__ + 1
        assert self.version == next_version

        # Call apply() before mutating values, in case exception is raised.
        self.apply(aggregate)

        # Update the aggregate's 'version' number.
        set_version(aggregate, self.version)

        # Update the aggregate's 'modified on' time.
        # aggregate.modified_on = self.timestamp

        # Return the mutated aggregate.
        return aggregate

    def apply(self, aggregate: RootEntity) -> None:
        ...


class _RootEntityMeta(_EntityMeta, IRootEntityMeta, ModelMetaclass):
    def __init__(cls, name, bases, namespace, *, domain: str | None = None, **kwargs):
        super().__init__(name, bases, namespace, **kwargs)
        domain = get_domain_name(cls, bases, domain)
        if domain is not None:
            cls.__domain_name = domain
        elif domain is None and cls.__module__ != __name__:
            raise ValueError(
                f"required set domain name for root entity '{cls.__module__}.{cls.__name__}'"
            )

    def __call__(cls, __version__=Version(1), **data):
        obj = super().__call__(**data)
        obj.__pydantic_private__["_RootEntity__version"] = __version__
        return obj

    @property
    def __domain_name__(cls) -> DomainName:
        return cls.__domain_name


class RootEntity(
    Entity,
    IRootEntity,
    Generic[_ReferenceType],
    metaclass=_RootEntityMeta,
):
    __version: Version = Version(1)

    def __init_subclass__(cls, *, domain: str | None = None, **kwargs):
        super().__init_subclass__()

    def __init__(self, **data):
        super().__init__(**data)
        self._events: list[AbstractEvent] = list()

    @property
    def __domain_name__(self) -> DomainName:
        """
        Get the domain name associated with the current class.

        Returns:
            DomainName: The domain name associated with the class.

        """
        return self.__class__.__domain_name__  # type: ignore

    @property
    def __version__(self) -> Version:
        """
        Get the current version of the root entity.

        Returns:
             Version: The current version of the root entity.
        """
        return self.__version

    def create_event(self, __name: MessageName | str, /, **payload):
        increment_version(self)
        event_class = get_event_class(self.__domain_name__, __name)
        event = event_class(
            reference=self.__reference__,
            version=self.__version__,
            **payload,
        )
        event.apply(self)
        self._events.append(event)

    def collect_events(self) -> Iterable[DomainEvent]:
        events = self._events
        self._events = []
        yield from events
