import pymupdf, glob, os, re, json
out = "/home/user/scaling-guacamole/work"
# Livre II outline from font
f = "/tmp/arena-coding-uploads/Protocole_Certification_PEB_Residentiel_Livre_II_1.pdf"
doc = pymupdf.open(f)
print("=== LIVRE II HEADINGS ===")
for i,p in enumerate(doc):
    d=p.get_text("dict")
    for b in d["blocks"]:
        if b["type"]!=0: continue
        for l in b["lines"]:
            txt = "".join(s["text"] for s in l["spans"]).strip()
            if not txt: continue
            fonts = [s["font"] for s in l["spans"]]
            sizes = [s["size"] for s in l["spans"]]
            if any("TrebuchetMS-Bold" in fo and sz>=10.5 for fo,sz in zip(fonts,sizes)) or any(sz>=13 and "Bold" in fo for fo,sz in zip(fonts,sizes)):
                print(f"[{i+1}] ({max(sizes):.0f}) {txt}")
# Tables from all books
alltabs=[]
for f in sorted(glob.glob("/tmp/arena-coding-uploads/*.pdf")):
    doc=pymupdf.open(f); name=os.path.basename(f)[:6]
    for i,p in enumerate(doc):
        try: tabs=p.find_tables().tables
        except Exception: continue
        for j,t in enumerate(tabs):
            data=t.extract()
            alltabs.append({"book":os.path.basename(f),"page":i+1,"idx":j,"data":data})
    doc.close()
with open(out+"/tables.json","w",encoding="utf-8") as fh: json.dump(alltabs,fh,ensure_ascii=False,indent=1)
print("TABLES:",len(alltabs))
