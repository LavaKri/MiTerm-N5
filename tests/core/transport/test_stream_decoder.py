import pytest

from n5terminal.core.transport.stream_decoder import StreamDecoder

pytestmark = pytest.mark.unit


def test_utf8_is_decoded() -> None:
    decoder = StreamDecoder()
    assert decoder.decode("café ✓".encode()) == "café ✓"
    assert not decoder.uses_fallback


def test_a_character_split_between_two_blocks_is_not_corrupted() -> None:
    decoder = StreamDecoder()
    data = "café".encode()
    assert decoder.decode(data[:4]) + decoder.decode(data[4:]) == "café"


def test_bytes_that_are_not_utf8_switch_to_the_fallback_code_page() -> None:
    decoder = StreamDecoder("cp850")
    assert decoder.decode("café".encode("cp850")) == "café"
    assert decoder.uses_fallback


def test_the_switch_keeps_the_text_before_and_decodes_the_rest_with_the_fallback() -> None:
    decoder = StreamDecoder("cp850")
    first = decoder.decode(b"abc ")
    second = decoder.decode("été".encode("cp850"))
    third = decoder.decode(b" \x82")
    assert (first, second, third) == ("abc ", "été", " é")


def test_a_cut_character_held_back_is_decoded_with_the_fallback_after_the_switch() -> None:
    decoder = StreamDecoder("cp850")
    assert decoder.decode(b"a\xc3") == "a"  # may be the start of a UTF-8 character
    assert decoder.decode(b"(") == "├("  # it was not: cp850 reads \xc3 as a box drawing
    assert decoder.uses_fallback


def test_finish_with_nothing_held_gives_nothing() -> None:
    decoder = StreamDecoder()
    decoder.decode(b"abc")
    assert decoder.finish() == ""


def test_finish_decodes_a_character_cut_at_the_end_of_the_stream() -> None:
    decoder = StreamDecoder("cp850")
    decoder.decode(b"a\xc3")
    assert decoder.finish() == "├"
    assert decoder.uses_fallback
