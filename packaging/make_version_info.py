"""Write a PyInstaller version resource for the app .exe.

Windows shows FileDescription as the app's name in "Open with", Task Manager,
the taskbar and security prompts; without it, it shows the bare file name.

    python packaging/make_version_info.py <version> <out-file>
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pdfscout import brand  # noqa: E402

version = sys.argv[1]
out = Path(sys.argv[2])
nums = [int(p) for p in (version.split("-")[0].split(".") + ["0", "0", "0"])[:4]]
t = tuple(nums)

out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(filevers={t}, prodvers={t}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('CompanyName', '{brand.PUBLISHER}'),
        StringStruct('FileDescription', '{brand.PRODUCT_NAME}'),
        StringStruct('FileVersion', '{version}'),
        StringStruct('InternalName', '{brand.EXE_NAME}'),
        StringStruct('LegalCopyright', '(C) {brand.PUBLISHER} AGPL-3.0-or-later'),
        StringStruct('OriginalFilename', '{brand.EXE_NAME}.exe'),
        StringStruct('ProductName', '{brand.PRODUCT_NAME}'),
        StringStruct('ProductVersion', '{version}')])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""",
    encoding="utf-8",
)
print(f"wrote {out}")
