"""The layers only depend downwards (see the layout in CLAUDE.md).

- ``core/`` and ``presenters/`` never import ``wx``.
- ``core/`` imports neither ``presenters/`` nor ``ui/``; ``presenters/`` does not import ``ui/``.
- Inside ``core/`` each subpackage only imports the ones before it: ``config``, ``transport``,
  ``screen``, ``session``. ``errors.py`` at the root imports none of them.
"""

import ast
from pathlib import Path

import pytest

import n5terminal

pytestmark = pytest.mark.unit

PACKAGE = Path(n5terminal.__file__).parent
WX_FREE_LAYERS = ("core", "presenters")
LAYERS = ("core", "presenters", "ui")  # each one may import the ones before it
CORE_ORDER = ("config", "transport", "screen", "session")


def source_files() -> list[Path]:
    return sorted(PACKAGE.rglob("*.py"))


def wx_free_files() -> list[Path]:
    return sorted(path for layer in WX_FREE_LAYERS for path in (PACKAGE / layer).rglob("*.py"))


def imported_modules(path: Path) -> set[str]:
    """The modules a file imports (absolute imports; the names of a ``from`` import included)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
            modules.update(f"{node.module}.{alias.name}" for alias in node.names)
    return modules


def relative_imports(path: Path) -> list[int]:
    """The lines of the relative imports of a file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node.lineno for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.level
    ]


def module_name(path: Path) -> str:
    parts = list(path.relative_to(PACKAGE.parent).with_suffix("").parts)
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def layer_of(module: str) -> int | None:
    """The rank of the layer of ``module`` (``None``: not in a layer)."""
    parts = module.split(".")
    if len(parts) > 1 and parts[0] == "n5terminal" and parts[1] in LAYERS:
        return LAYERS.index(parts[1])
    return None


def core_rank(module: str) -> int | None:
    """The rank of a subpackage of ``core/``; -1 for the modules at its root (``errors``)."""
    parts = module.split(".")
    if layer_of(module) != 0:
        return None
    if len(parts) > 2 and parts[2] in CORE_ORDER:
        return CORE_ORDER.index(parts[2])
    return -1


def is_higher(own: int | None, other: int | None) -> bool:
    """Is ``other`` above ``own``? (``None``: not in a ranking, so never.)"""
    return own is not None and other is not None and other > own


def layer_violations(module: str, imported: set[str]) -> list[str]:
    """The imports of ``module`` that go against the layers."""
    return [
        name
        for name in sorted(imported)
        if is_higher(layer_of(module), layer_of(name))
        or is_higher(core_rank(module), core_rank(name))
    ]


def file_id(path: Path) -> str:
    return path.relative_to(PACKAGE).as_posix()


def test_the_wx_free_layers_have_files() -> None:
    assert wx_free_files()


@pytest.mark.parametrize("path", wx_free_files(), ids=file_id)
def test_layer_never_imports_wx(path: Path) -> None:
    wx_imports = {name for name in imported_modules(path) if name == "wx" or name.startswith("wx.")}
    assert not wx_imports


@pytest.mark.parametrize("path", source_files(), ids=file_id)
def test_layers_only_import_downwards(path: Path) -> None:
    assert not layer_violations(module_name(path), imported_modules(path))


@pytest.mark.parametrize("path", source_files(), ids=file_id)
def test_imports_are_absolute(path: Path) -> None:
    """A relative import would escape the checks above."""
    assert not relative_imports(path)


@pytest.mark.parametrize(
    ("module", "imported"),
    [
        ("n5terminal.core.config.settings", {"n5terminal.core.session.shell"}),
        ("n5terminal.core.transport.pipe_transport", {"n5terminal.core.screen.titles"}),
        ("n5terminal.core.screen.titles", {"n5terminal.core.session.session_state"}),
        ("n5terminal.core.errors", {"n5terminal.core.config.settings"}),
        ("n5terminal.core.session.shell", {"n5terminal.presenters.session_view"}),
        ("n5terminal.core.session.shell", {"n5terminal.ui.actions"}),
        ("n5terminal.presenters.session_presenter", {"n5terminal.ui.actions"}),
        ("n5terminal.core.config.settings", {"n5terminal.core.session"}),
    ],
)
def test_a_violation_is_found(module: str, imported: set[str]) -> None:
    assert layer_violations(module, imported) == sorted(imported)


@pytest.mark.parametrize(
    ("module", "imported"),
    [
        ("n5terminal.core.session.session_state", {"n5terminal.core.config.announcements"}),
        ("n5terminal.core.screen.display_exchange", {"n5terminal.core.screen.screen_model"}),
        ("n5terminal.core.config.settings", {"n5terminal.core.errors", "n5terminal.i18n"}),
        ("n5terminal.presenters.session_presenter", {"n5terminal.core.session.shell"}),
        ("n5terminal.ui.actions", {"n5terminal.presenters.session_presenter", "wx"}),
        ("n5terminal.__main__", {"n5terminal.ui.main_window"}),
    ],
)
def test_a_downward_import_is_allowed(module: str, imported: set[str]) -> None:
    assert not layer_violations(module, imported)
