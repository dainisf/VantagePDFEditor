import sys
import pymupdf

out = sys.argv[1]
d = pymupdf.open()
p = d.new_page()
p.insert_text((72, 90), "Quarterly Report", fontsize=24, fontname="hebo")
y = 130
for t in [
    "Prepared by Jane Smith (jane.smith@example.com)",
    "Phone: 555-867-5309   SSN: 123-45-6789",
    "Revenue grew 14% compared with last quarter.",
    "Next review meeting: 12/05/2026",
]:
    p.insert_text((72, y), t, fontsize=12)
    y += 22
p.draw_rect(pymupdf.Rect(72, 250, 520, 400), color=(0.2, 0.3, 0.7), fill=(0.9, 0.93, 1))
p.insert_text((90, 280), "Chart placeholder", fontsize=14)
for i in range(2):
    q = d.new_page()
    q.insert_text((72, 90), f"Appendix {i + 1}", fontsize=18)
d.save(out)
