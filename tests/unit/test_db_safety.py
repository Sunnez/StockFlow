import pytest

from tests.db_safety import UnsafeTestDatabase, validate_test_database_url

MAIN = "postgresql+psycopg://stockflow:synthetic@127.0.0.1:5433/stockflow"
TEST = "postgresql+psycopg://stockflow_test:synthetic@127.0.0.1:5434/stockflow_test"


def test_accepts_only_explicit_disposable_target():
    target = validate_test_database_url(TEST, MAIN, reset_confirmation="stockflow_test")
    assert target.database == "stockflow_test"


@pytest.mark.parametrize("confirmation", [None, "", "1", "true", "stockflow"])
def test_requires_exact_reset_opt_in(confirmation):
    with pytest.raises(UnsafeTestDatabase):
        validate_test_database_url(TEST, MAIN, reset_confirmation=confirmation)


@pytest.mark.parametrize(
    "target",
    [
        None,
        "",
        "invalid",
        MAIN,
        TEST.replace("5434/stockflow_test", "5433/stockflow"),
        TEST.replace("/stockflow_test", "/production_test"),
        TEST.replace("stockflow_test:", "stockflow:"),
        TEST.replace("stockflow_test:", "postgres:"),
        TEST.replace("127.0.0.1", "production.example.com"),
        TEST.replace(":5434", ""),
        TEST.replace("postgresql+psycopg", "sqlite"),
        TEST + "?host=production.example.com",
        TEST + "?dbname=stockflow",
        TEST + "?options=-csearch_path%3Dproduction",
    ],
)
def test_rejects_unsafe_target(target):
    with pytest.raises(UnsafeTestDatabase):
        validate_test_database_url(target, MAIN, reset_confirmation="stockflow_test")


def test_same_database_name_is_rejected_even_for_host_alias_and_other_role():
    with pytest.raises(UnsafeTestDatabase):
        validate_test_database_url(
            TEST.replace("127.0.0.1", "localhost"),
            MAIN.replace("/stockflow", "/stockflow_test"),
            reset_confirmation="stockflow_test",
        )


def test_errors_do_not_include_url_or_password():
    with pytest.raises(UnsafeTestDatabase) as error:
        validate_test_database_url(
            "postgresql+psycopg://bad:private-password@host:bad/db",
            MAIN,
            reset_confirmation="stockflow_test",
        )
    assert "private-password" not in str(error.value)
    assert "postgresql" not in str(error.value)


@pytest.mark.parametrize(
    "main",
    [
        MAIN + "?dbname=stockflow_test",
        "postgresql+psycopg:///stockflow",
        "postgresql+psycopg://127.0.0.1/stockflow",
    ],
)
def test_rejects_ambiguous_main_database_identity(main):
    with pytest.raises(UnsafeTestDatabase):
        validate_test_database_url(TEST, main, reset_confirmation="stockflow_test")


def test_rejects_shared_role_even_when_both_role_names_have_test_suffix():
    with pytest.raises(UnsafeTestDatabase):
        validate_test_database_url(
            TEST,
            MAIN.replace("stockflow:", "stockflow_test:"),
            reset_confirmation="stockflow_test",
        )
