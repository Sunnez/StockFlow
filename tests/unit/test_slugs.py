from uuid import UUID

import pytest

from app.core.slugs import slug_candidates


@pytest.mark.parametrize(
    "name",
    [
        "12345678-1234-1234-1234-123456789abc",
        "12345678123412341234123456789abc",
        "{12345678-1234-1234-1234-123456789ABC}",
        "urn:uuid:12345678-1234-1234-1234-123456789abc",
    ],
)
def test_uuid_like_name_never_generates_uuid_parseable_slug(name):
    candidates = list(slug_candidates(name, fallback="organization"))
    assert len(candidates) == 100
    assert len(set(candidates)) == 100
    for slug in candidates:
        with pytest.raises(ValueError):
            UUID(slug)


def test_normal_slug_collision_suffixes_and_empty_fallback():
    assert list(slug_candidates("Acme Ltd", fallback="organization"))[:3] == [
        "acme-ltd",
        "acme-ltd-2",
        "acme-ltd-3",
    ]
    assert next(slug_candidates("!!!", fallback="organization")) == "organization"
