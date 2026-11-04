import pymupdf, os, json, glob
src = "/tmp/arena-coding-uploads"
out = "/home/user/scaling-guacamole/work"
files = sorted(glob.glob(src + "/*.pdf"))
for f in files:
    doc = pymupdf.open(f)
    name = os.path.basename(f).replace(" ", "_").replace("(", "").replace(")", "").replace(".pdf", "")
    print("="*80)
    print(name, "pages:", len(doc), "meta:", doc.metadata.get("title"), doc.metadata.get("creator"))
    toc = doc.get_toc()
    print("TOC entries:", len(toc))
    for t in toc[:40]:
        print("   ", t)
    # text sample
    txt = doc[0].get_text()
    print("PAGE0 TEXT:", repr(txt[:800]))
    # total chars
    total = sum(len(p.get_text()) for p in doc)
    print("TOTAL TEXT CHARS:", total, "avg/page:", total//max(1,len(doc)))
    # save full text
    with open(os.path.join(out, name + ".txt"), "w", encoding="utf-8") as fh:
        for i, page in enumerate(doc):
            fh.write(f"\n\n===== PAGE {i+1} =====\n")
            fh.write(page.get_text(sort=True))
    with open(os.path.join(out, name + ".toc.json"), "w", encoding="utf-8") as fh:
        json.dump(toc, fh, ensure_ascii=False, indent=1)
    doc.close()
