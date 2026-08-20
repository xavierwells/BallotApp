import ast
from pathlib import Path


def test_alembic_revision_ids_fit_the_default_version_column() -> None:
    versions_directory = Path(__file__).resolve().parents[1] / "migrations" / "versions"

    for migration_path in versions_directory.glob("*.py"):
        if migration_path.name == "__init__.py":
            continue
        module = ast.parse(migration_path.read_text(encoding="utf-8"))
        revision = next(
            node.value.value
            for node in module.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "revision" for target in node.targets)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        )
        assert len(revision) <= 32, f"{migration_path.name} revision exceeds Alembic's default 32-character limit"
