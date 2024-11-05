from uuid import (
    uuid5,
    NAMESPACE_URL,
)

from eventsourcing.application import (
    ProcessingEvent,
    AggregateNotFoundError,
)
from eventsourcing.dispatch import singledispatchmethod
from eventsourcing.domain import (
    Aggregate,
    event,
    DomainEventProtocol,
)
from eventsourcing.system import ProcessApplication

from school.domainmodel import DogAggregate


class Counters(ProcessApplication):
    @singledispatchmethod
    def policy(self, domain_event, process_event):
        """Default policy"""
        ...

    @policy.register
    def _(self, domain_event: DogAggregate.Registered, process_event):
        name = domain_event.name
        try:
            counter_id = Counter.create_id(name)
            counter = self.repository.get(counter_id)
        except AggregateNotFoundError:
            counter = Counter(name)
        counter.increment()
        process_event.collect_events(counter)

    @policy.register
    def _(self, domain_event: DogAggregate.TrickAdded, process_event):
        trick = domain_event.trick_name
        try:
            counter_id = Counter.create_id(trick)
            counter = self.repository.get(counter_id)
        except AggregateNotFoundError:
            counter = Counter(trick)
        counter.increment()
        process_event.collect_events(counter)

    def get_count(self, trick):
        counter_id = Counter.create_id(trick)
        try:
            counter = self.repository.get(counter_id)
        except AggregateNotFoundError:
            return 0
        return counter.count

class Counter(Aggregate):
    def __init__(self, name):
        self.name = name
        self.count = 0

    @classmethod
    def create_id(cls, name):
        return uuid5(NAMESPACE_URL, f'/counters/{name}')

    @event('Incremented')
    def increment(self):
        self.count += 1


class Printers(ProcessApplication):

    def policy(self, domain_event: DomainEventProtocol, processing_event: ProcessingEvent) -> None:
        print(f'Process! {domain_event}')
