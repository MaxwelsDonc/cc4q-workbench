"""Deterministic id generation for extracted records."""

from typing import Iterator

__all__ = ["id_generator"]


def id_generator(start: int = 1) -> Iterator[str]:
    """Yield incrementing string ids, starting at ``start``.

    Args:
        start: First integer in the sequence.

    Yields:
        ``"1"``, ``"2"``, ... as strings, matching the id type used by
        :class:`~cc4q.pipeline.types.CommentRecord`.
    """
    i = start
    while True:
        yield str(i)
        i += 1
