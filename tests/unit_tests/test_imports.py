"""Test importing files."""


def test_imports() -> None:
    """Test importing deepagents modules."""
    from coda_cli import (
        agent,  # noqa: F401
        integrations,  # noqa: F401
    )
    from coda_cli.main import cli_main  # noqa: F401


def test_langchain_deepseek_import() -> None:
    """Test importing langchain-deepseek package."""
    # This should not raise ImportError after dependency is added
    import langchain_deepseek  # noqa: F401
