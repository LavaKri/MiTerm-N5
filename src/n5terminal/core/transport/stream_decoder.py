"""Decoding of the bytes of a program: UTF-8, with a fallback code page for old programs.

See "Launching programs" in ``specs/architecture/transport.md``. The decoder is incremental (a
character split between two blocks is not corrupted). It reads UTF-8; the first bytes that are not
UTF-8 make it switch, for the rest of the stream, to the fallback code page (the Windows console
one, ``cp850`` by default; a per-profile setting later).
"""

import codecs

DEFAULT_FALLBACK = "cp850"


class StreamDecoder:
    """Turns the bytes of one stream into text."""

    def __init__(self, fallback: str = DEFAULT_FALLBACK) -> None:
        self._utf8 = codecs.getincrementaldecoder("utf-8")(errors="strict")
        self._fallback = codecs.getincrementaldecoder(fallback)(errors="replace")
        self._use_fallback = False

    @property
    def uses_fallback(self) -> bool:
        """Did the stream turn out not to be UTF-8?"""
        return self._use_fallback

    def decode(self, data: bytes) -> str:
        """Text of ``data``; the end of an unfinished character waits for the next call."""
        if self._use_fallback:
            return self._fallback.decode(data)
        held, _flag = self._utf8.getstate()
        try:
            return self._utf8.decode(data)
        except UnicodeDecodeError:
            self._use_fallback = True
            return self._fallback.decode(held + data)

    def finish(self) -> str:
        """Text of what is still held back at the end of the stream (a cut character)."""
        if self._use_fallback:
            return self._fallback.decode(b"", final=True)
        try:
            return self._utf8.decode(b"", final=True)
        except UnicodeDecodeError:
            self._use_fallback = True
            held, _flag = self._utf8.getstate()
            return self._fallback.decode(held, final=True)
