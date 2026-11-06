# PyInstaller spec of MiTerm-N5 (see specs/packaging.md). Run by Built.bat, not by hand.
# A folder (onedir), windowed (no console): MiTerm-N5.exe and its libraries.
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH).parent  # noqa: F821 - SPECPATH is given by PyInstaller

# No hook exists for pywinpty: collect the whole package (conpty.dll, OpenConsole.exe, winpty.dll,
# winpty-agent.exe and the compiled module), but not its tests (they pull pytest in).
winpty_datas, winpty_binaries, winpty_hiddenimports = collect_all(
    "winpty", filter_submodules=lambda name: not name.startswith("winpty.tests")
)

# The compiled translations, where i18n looks for them (n5terminal/locale next to the package).
translations = [
    (str(path), "n5terminal/locale/" + path.parent.relative_to(root / "src" / "n5terminal" / "locale").as_posix())
    for path in (root / "src" / "n5terminal" / "locale").rglob("*.mo")
]

# The starter profiles, in _internal/StartProfil (where core/config/starter_profiles.py looks).
starter_profiles = [
    (str(path), "StartProfil") for path in sorted((root / "starter_profiles").glob("*.json"))
]

analysis = Analysis(  # noqa: F821
    [str(root / "src" / "n5terminal" / "__main__.py")],
    pathex=[str(root / "src")],
    binaries=winpty_binaries,
    datas=[*winpty_datas, *translations, *starter_profiles],
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
    name="MiTerm-N5",
    console=False,
)
# The program ssh runs to ask the user (SSH_ASKPASS, see specs/architecture/connection.md): a
# console program, standard library only. It shares _internal with the application, so it adds
# very little. Built.bat moves it into _internal: contents_directory="." makes it look for its
# libraries in its own folder, and not in a _internal beside it.
askpass_analysis = Analysis(  # noqa: F821
    [str(root / "src" / "n5terminal" / "askpass.py")],
    pathex=[str(root / "src")],
)
askpass_archive = PYZ(askpass_analysis.pure)  # noqa: F821
askpass_executable = EXE(  # noqa: F821
    askpass_archive,
    askpass_analysis.scripts,
    [],
    exclude_binaries=True,
    name="MiTerm-N5-askpass",
    console=True,
    contents_directory=".",
)
COLLECT(  # noqa: F821
    executable,
    analysis.binaries,
    analysis.datas,
    askpass_executable,
    askpass_analysis.binaries,
    askpass_analysis.datas,
    name="MiTerm-N5",
)
