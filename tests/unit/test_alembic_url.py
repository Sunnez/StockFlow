"""Extract only the configuration statement; NEVER execute Alembic env.py."""

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic.config import Config
from sqlalchemy.engine import make_url


@pytest.mark.parametrize("password", ["p%40ss", "p%25ss", "p%2F%3A%23%3Fss", "plain"])
def test_alembic_config_preserves_encoded_url(password):
    url = f"postgresql+psycopg://synthetic:{password}@127.0.0.1/unit"
    tree = ast.parse(Path("alembic/env.py").read_text(encoding="utf-8"))
    statement = next(
        node
        for node in tree.body
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and node.value.func.attr == "set_main_option"
    )
    config = Config()
    exec(  # noqa: S102 -- only this trusted config AST, never execute env.py
        compile(
            ast.Module(body=[statement], type_ignores=[]), "<url-config-only>", "exec"
        ),
        {"config": config, "settings": SimpleNamespace(database_url=url)},
    )
    assert config.get_main_option("sqlalchemy.url") == url
    assert config.get_section(config.config_ini_section)["sqlalchemy.url"] == url
    assert (
        make_url(config.get_main_option("sqlalchemy.url")).password
        == make_url(url).password
    )
