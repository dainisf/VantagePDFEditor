import pymupdf

from pdfscout.cli import main


def make(path, text="Mail me at bob@example.com"):
    d = pymupdf.open()
    d.new_page().insert_text((72, 72), text)
    d.new_page().insert_text((72, 72), "Page two")
    d.save(path)
    return str(path)


def test_redact_and_dry_run(tmp_path, capsys):
    src = make(tmp_path / "a.pdf")
    assert main(["redact", src, "--preset", "email", "--dry-run"]) == 0
    assert "bob@example.com" in capsys.readouterr().out
    out = tmp_path / "r.pdf"
    assert main(["redact", src, "--preset", "email", "-o", str(out)]) == 0
    assert "example" not in pymupdf.open(out)[0].get_text()
    assert main(["redact", src, "--preset", "email"]) == 2  # missing -o


def test_merge_protect_bates(tmp_path):
    a, b = make(tmp_path / "a.pdf"), make(tmp_path / "b.pdf")
    m = tmp_path / "m.pdf"
    assert main(["merge", a, b, "-o", str(m)]) == 0
    assert pymupdf.open(m).page_count == 4
    bt = tmp_path / "bt.pdf"
    assert main(["bates", str(m), "-o", str(bt), "--prefix", "X", "--digits", "3"]) == 0
    assert "X004" in pymupdf.open(bt)[3].get_text()
    p = tmp_path / "p.pdf"
    assert main(["protect", str(bt), "-o", str(p), "--new-password", "pw"]) == 0
    assert main(["info", str(p)]) == 1
    assert main(["info", str(p), "--password", "pw"]) == 0


def test_split_and_extract(tmp_path):
    a = make(tmp_path / "a.pdf")
    assert main(["split", a, "--every", "1", "-o", str(tmp_path / "s.zip")]) == 0
    assert main(["extract", a, "--pages", "2", "-o", str(tmp_path / "e.pdf")]) == 0
    assert pymupdf.open(tmp_path / "e.pdf")[0].get_text().strip() == "Page two"
