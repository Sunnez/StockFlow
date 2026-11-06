from collections.abc import Iterator

from slugify import slugify


def slug_candidates(
    name: str,
    *,
    fallback: str,
) -> Iterator[str]:
    base = slugify(name, max_length=120) or fallback

    yield base

    for suffix in range(2, 101):
        yield f"{base}-{suffix}"