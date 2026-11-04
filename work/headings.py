import pymupdf, glob, os, collections, json
for f in sorted(glob.glob("/tmp/arena-coding-uploads/*.pdf")):
    doc = pymupdf.open(f)
    print("="*70, os.path.basename(f))
    sizes = collections.Counter()
    for p in doc:
        d = p.get_text("dict")
        for b in d["blocks"]:
            if b["type"]!=0: continue
            for l in b["lines"]:
                for s in l["spans"]:
                    sizes[(round(s["size"],1), "bold" in s["font"].lower() or "bold" in s["flags"].__str__(), s["font"])] += len(s["text"])
    print("Top font signatures:", sizes.most_common(15))
    # tables count
    nt=0
    for p in doc:
        try:
            tabs = p.find_tables()
            nt += len(tabs.tables)
        except Exception as e:
            pass
    print("tables found:", nt)
    doc.close()
