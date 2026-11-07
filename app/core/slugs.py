from collections.abc import Iterator
from uuid import UUID

from slugify import slugify


def slug_candidates(
    name: str,
    *,
    fallback: str,
) -> Iterator[str]:
    base = slugify(name, max_length=120) or fallback
    # The organization resolver treats every UUID-parseable string as an ID.
    try:
        UUID(base)
    except ValueError:
        pass
    else:
        base = f"organization-{base}"

    yield base

    for suffix in range(2, 101):
        yield f"{base}-{suffix}"
