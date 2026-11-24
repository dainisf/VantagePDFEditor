# PDFScout

A self-hosted PDF editor covering the core of what Acrobat Pro does: edit text, **true redaction**, comments and markup, page organization, forms, signatures, stamps, protection and compression. It comes as a browser UI and a command-line tool for batch jobs.

It runs on your own machine. Files go to the local PDFScout server only and are never sent to a third party.

Built on [PyMuPDF](https://pymupdf.readthedocs.io/) (MuPDF) + FastAPI, with a build-free vanilla-JS front end.

## Quick start

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e .
pdfscout serve            # → http://127.0.0.1:8000
```

Optional: install [Tesseract](https://github.com/tesseract-ocr/tesseract) (`apt install tesseract-ocr` / `brew install tesseract`) to enable OCR.

## Windows desktop app

PDFScout can run as a normal Windows program, without a browser. It opens its own window and uses the standard Windows Open/Save dialogs. The title bar shows `•` when there are unsaved changes, and you're asked before closing with unsaved work.

**Get `PDFScout.exe`:** every push builds it on Windows via GitHub Actions. Open the **Actions** tab, then the latest **Windows app** run, and download the **PDFScout-windows** artifact. Tagging a release (`v0.1.0`) also attaches the .exe to the GitHub release. It's a single file with nothing to install. You can double-click it, drag a PDF onto it, or use *Open with → PDFScout*.

**Build it yourself** (Windows, Python 3.10+):

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
```

This produces `dist\PDFScout.exe` and runs a packaging self-test.

**Run from source without building:** `pip install -e ".[desktop]"`, then `pdfscout-app [file.pdf]`.

Requirements: Windows 10 or 11 with the Microsoft Edge WebView2 runtime, which is preinstalled on current Windows. The window is rendered by WebView2, and the PDF engine runs inside the same process on a private localhost port, so no data leaves the PC. The .exe isn't code-signed, so SmartScreen may warn on first launch (*More info → Run anyway*).

## Features

| Area | What you can do |
|---|---|
| **Edit** | Edit existing text lines in place (keeps baseline, size, color, closest standard font) · add text boxes · add images · undo/redo history |
| **Redact** | Mark areas by dragging · find & redact words, phrases, regex or presets (email, phone, SSN, credit card, IBAN, IP, URL, dates) · removes the underlying text, image pixels and graphics, not just a black box on top · optional overlay text · removes comments/links over redacted areas · “remove hidden information” sanitize |
| **Comment** | Highlight, underline, strikethrough, sticky notes, text comments, freehand ink, rectangles, ellipses, arrows · list, jump to, delete · flatten |
| **Organize** | Thumbnails with drag-to-reorder · rotate, delete, duplicate, insert blank, extract pages · crop · combine files (PDF, images, XPS, EPUB) · split by every N pages or ranges |
| **Forms** | Fill existing forms · create text, checkbox, dropdown, signature fields · flatten |
| **Sign** | Draw a signature (remembered on your device) and place it |
| **Stamp** | Text watermark (opacity, angle, behind/over content) · headers & footers with `{page}`, `{total}`, `{date}`, `{filename}` · Bates numbering |
| **Protect** | AES-256 password encryption with print/copy/edit/annotate permissions · open password-protected files |
| **Optimize** | Downsample images, subset fonts, compact the file · sanitize metadata, JavaScript, attachments, hidden text |
| **Convert** | Export pages to PNG/JPEG, text, HTML · create a PDF from images · OCR scanned pages (invisible text layer) |
| **Compare** | Text diff of two PDFs |
| **Other** | Find text, bookmarks editor, document properties, keyboard shortcuts, drag-and-drop open |

### Keyboard shortcuts

`Ctrl+O` open · `Ctrl+S` download · `Ctrl+Z` / `Ctrl+Shift+Z` undo/redo · `Ctrl+F` find · `Ctrl +/-` zoom · `Esc` back to Select · `Delete` removes the selected comment · `PgUp/PgDn` change page

## Command line

```bash
pdfscout redact in.pdf -o out.pdf --preset email --preset ssn --term "Jane Doe"
pdfscout redact in.pdf --regex "INV-\d{6}" --dry-run      # list matches only
pdfscout merge a.pdf b.pdf c.pdf -o merged.pdf
pdfscout split big.pdf --ranges "1-3; 4-10" -o parts.zip
pdfscout extract in.pdf --pages 2,5-7 -o subset.pdf
pdfscout protect in.pdf -o locked.pdf --new-password s3cret --allow print
pdfscout unlock locked.pdf --password s3cret -o open.pdf
pdfscout watermark in.pdf -o draft.pdf --text DRAFT
pdfscout number in.pdf -o numbered.pdf --footer "Page {page} of {total}"
pdfscout bates in.pdf -o bates.pdf --prefix ACME --digits 6
pdfscout compress in.pdf -o small.pdf --dpi 120
pdfscout fill form.pdf -o filled.pdf --values '{"name": "Ann"}' --flatten
pdfscout sanitize in.pdf -o clean.pdf
pdfscout ocr scan.pdf -o searchable.pdf --lang eng
pdfscout images *.jpg -o photos.pdf --page-size a4
pdfscout compare v1.pdf v2.pdf
```

Run `pdfscout <command> --help` for all options.

## How redaction works

Redaction follows Acrobat's mark-then-apply model. Marks are only proposals until you click **Apply**. Applying runs MuPDF's redaction engine, which:

1. deletes the glyphs under each mark from the page's content stream,
2. blanks the covered image pixels (or removes whole images if you choose),
3. removes vector graphics that sit entirely inside the mark,
4. draws the fill box (black by default), with optional overlay text.

PDFScout also deletes comments and links that overlap a redacted area. By default it then runs *Remove hidden information*, which strips metadata, XMP, JavaScript, attachments and hidden text. The saved file is fully rewritten, so the old content does not survive in the file's revision history.

Always open the result and use Find to confirm nothing remains, especially for scanned pages. On a scan the "text" is part of an image, so text search can't find it; mark those areas by hand.

## Architecture

```
pdfscout/
  core.py     all PDF operations (pure functions on pymupdf.Document)
  store.py    in-memory document sessions with an undo/redo version stack
  server.py   FastAPI JSON API + static UI
  cli.py      command-line interface
  desktop.py  native-window desktop app (pywebview) + packaging self-test
  static/     index.html, app.js, styles.css (no build step)
tests/        pytest suites for core, API and CLI
```

- Coordinates: the API takes PDF points relative to the page **as displayed** (after `/Rotate`). Before writing to a rotated page, `normalize_page` bakes the rotation into the content, so every edit tool works the same on rotated pages.
- Every edit is a new immutable version in `store.py`, so undo and redo are exact. The history is capped (40 steps by default), and idle sessions expire after 6 hours.
- `PDFSCOUT_MAX_MB` sets the upload size limit (default 200).

### API sketch

```
POST /api/documents                      upload (multipart: file, password?)
GET  /api/documents/{id}                 state + page sizes, metadata, toc
GET  /api/documents/{id}/pages/{n}/image?scale=1.5
GET  /api/documents/{id}/pages/{n}/text  editable lines with style + bbox
POST /api/documents/{id}/ops/{op}        edit_text, add_text, annotate, redact_areas,
                                         redact_search, rotate, delete_pages, reorder,
                                         crop, watermark, header_footer, fill_form,
                                         add_field, flatten, sanitize, optimize, ocr, …
POST /api/documents/{id}/undo | /redo
POST /api/documents/{id}/insert          merge another file (multipart)
POST /api/documents/{id}/download        {user_password, owner_password, permissions, compress}
POST /api/documents/{id}/export/{kind}   images | text | html | extract | split
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Known limitations

- Text editing works one line at a time and substitutes the closest standard font (Helvetica, Times or Courier family). Embedded custom fonts are not reused, so a heavily styled line can look slightly different after an edit.
- Redaction doesn't reach text inside images unless you mark that area; OCR helps you find it.
- There is no conversion to Word, Excel or PowerPoint, and no certificate-based digital signatures. The signature tool places a drawn image.

## License

PyMuPDF is licensed under AGPL-3.0 (commercial licenses are available from Artifex), so this project is AGPL-3.0-or-later as well.
