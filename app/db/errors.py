from sqlalchemy.exc import IntegrityError


def get_constraint_name(exc: IntegrityError) -> str | None:
    diag = getattr(exc.orig, "diag", None)

    if diag is None:
        return None

    return getattr(diag, "constraint_name", None)