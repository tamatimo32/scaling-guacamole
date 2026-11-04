import pymupdf, glob, os, re, json
src="/tmp/arena-coding-uploads"; out="/home/user/scaling-guacamole/work/chunks"; os.makedirs(out,exist_ok=True)
labels={"I":"LI","II":"LII","III":"LIII"}
for f in sorted(glob.glob(src+"/*.pdf")):
    key = "III" if "III" in f else ("II" if "II" in f and "III" not in f else "I")
    lab=labels[key]
    doc=pymupdf.open(f)
    pages=[]
    for i,p in enumerate(doc):
        t=p.get_text(sort=True)
        lines=[l.strip() for l in t.split("\n")]
        lines=[l for l in lines if l and not re.match(r'^Version\s*2\.7', l) and not re.fullmatch(r'[A-G]\s*[≤<>]?\s*[\d\s\-]+', l)]
        # drop pure page numbers
        lines=[l for l in lines if not re.fullmatch(r'\d{1,3}',l)]
        pages.append((i+1,"\n".join(lines)))
    # group into chunks by char budget ~22000, at page boundaries
    chunks=[]; cur=[]; curchars=0
    for pg,txt in pages:
        if curchars+len(txt)>22000 and cur:
            chunks.append(cur); cur=[]; curchars=0
        cur.append((pg,txt)); curchars+=len(txt)
    if cur: chunks.append(cur)
    print(lab,"pages",len(pages),"chunks",len(chunks))
    for ci,ch in enumerate(chunks,1):
        path=f"{out}/{lab}_c{ci:02d}.txt"
        with open(path,"w",encoding="utf-8") as fh:
            fh.write(f"## {lab} CHUNK {ci} | pages {ch[0][0]}-{ch[-1][0]}\n")
            for pg,txt in ch:
                fh.write(f"\n--- p.{pg} ---\n{txt}\n")
        print("  ",os.path.basename(path), sum(len(t) for _,t in ch), "chars", f"p{ch[0][0]}-{ch[-1][0]}")
    doc.close()
