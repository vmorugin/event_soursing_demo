from eventsourcing.persistence import Transcoding

from school.domainmodel import Trick

class DataclassTranscoder(Transcoding):
    def encode(self, obj: Trick) -> dict:
        return obj.__dict__

    def decode(self, data: dict) -> Trick:
        assert isinstance(data, dict)
        return Trick(**data)


class TrickAsDict(DataclassTranscoder):
    type = Trick
    name = "Trick"
