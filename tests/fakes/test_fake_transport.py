import pytest

from fakes.fake_transport import FakeTransport
from fakes.recording_listener import RecordingListener
from n5terminal.core.errors import TransportClosedError
from n5terminal.core.transport.transport import Stream, Transport, TransportState

pytestmark = pytest.mark.unit


def test_fake_transport_plays_a_whole_session() -> None:
    fake = FakeTransport()
    transport: Transport = fake
    listener = RecordingListener()
    transport.start(listener)
    fake.set_state(TransportState.AUTHENTICATING)
    fake.set_state(TransportState.CONNECTED)
    transport.write(b"input\n")
    fake.receive(b"output")
    fake.receive(b"error", Stream.ERROR)
    fake.exit(0)
    assert fake.written == [b"input\n"]
    assert listener.received(Stream.OUTPUT) == b"output"
    assert listener.received(Stream.ERROR) == b"error"
    assert listener.exit_codes == [0]
    assert listener.states[-1] is TransportState.CLOSED
    with pytest.raises(TransportClosedError):
        transport.write(b"late")
