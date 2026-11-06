# PyInstaller spec of the early packaging test (see specs/packaging.md). Run by
# tools/check_packaging.py, not by hand. A folder, windowed (no console).
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH).parent  # noqa: F821 - SPECPATH is given by PyInstaller

# No hook exists for pywinpty: collect the whole package (conpty.dll, OpenConsole.exe, winpty.dll,
# winpty-agent.exe and the compiled module), but not its tests (they pull pytest in).
winpty_datas, winpty_binaries, winpty_hiddenimports = collect_all(
    "winpty", filter_submodules=lambda name: not name.startswith("winpty.tests")
)

analysis = Analysis(  # noqa: F821
    [str(root / "packaging" / "smoke.py")],
    pathex=[str(root / "src")],
    binaries=winpty_binaries,
    datas=winpty_datas,
    hiddenimports=winpty_hiddenimports,
    # pyte is LGPL v3: keep it as separate source files in the folder, replaceable by the user,
    # not inside the internal archive.
    module_collection_mode={"pyte": "py"},
)
archive = PYZ(analysis.pure)  # noqa: F821
executable = EXE(  # noqa: F821
    archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="n5terminal-smoke",
    console=False,
)
COLLECT(  # noqa: F821
    executable,
    analysis.binaries,
    analysis.datas,
    name="n5terminal-smoke",
)
