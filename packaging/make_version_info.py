"""Write a PyInstaller version resource for PDFScout.exe.

Windows shows FileDescription as the app's name in "Open with", Task Manager,
the taskbar and security prompts; without it, it shows "PDFScout.exe".

    python packaging/make_version_info.py <version> <out-file>
"""

import sys
from pathlib import Path

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
        StringStruct('CompanyName', 'PDFScout'),
        StringStruct('FileDescription', 'PDFScout'),
        StringStruct('FileVersion', '{version}'),
        StringStruct('InternalName', 'PDFScout'),
        StringStruct('LegalCopyright', 'PDFScout contributors. AGPL-3.0-or-later'),
        StringStruct('OriginalFilename', 'PDFScout.exe'),
        StringStruct('ProductName', 'PDFScout'),
        StringStruct('ProductVersion', '{version}')])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""",
    encoding="utf-8",
)
print(f"wrote {out}")
