import zipfile
from lxml import etree
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
def V(el,tag):
    if el is None: return False
    e=el.find(W+tag)
    return e is not None and e.get(W+'val') not in ('0','false','off')

root = etree.fromstring(zipfile.ZipFile("checked2.docx").read("word/document.xml"))
print("XML parses OK\n")

def resolve(p, mode):
    out=[]
    for r in p.iter(W+'r'):
        anc={a.tag for a in r.iterancestors()}
        deleted, inserted = W+'del' in anc, W+'ins' in anc
        if mode=='accept' and deleted: continue
        if mode=='reject' and inserted: continue
        t = r.find(W+'delText') if deleted else r.find(W+'t')
        if t is not None and t.text: out.append(t.text)
    return ''.join(out)

def marked(p):
    out=[]
    for r in p.iter(W+'r'):
        if any(a.tag==W+'del' for a in r.iterancestors()): continue
        t=r.find(W+'t')
        if t is None or not t.text: continue
        rPr=r.find(W+'rPr'); s=t.text
        if V(rPr,'i'): s=f"*{s}*"
        hl=rPr.find(W+'highlight') if rPr is not None else None
        if hl is not None: s=f"[{hl.get(W+'val')}]{s}[/]"
        out.append(s)
    return ''.join(out)

ok=True
for n,p in enumerate(root.findall('.//'+W+'p')):
    if not resolve(p,'reject').strip(): continue
    print(f"--- paragraph {n} ---")
    print(" before (reject all):", resolve(p,'reject'))
    print(" after  (accept all):", resolve(p,'accept'))
    print(" marked             :", marked(p))
    print(f" tracked: {len(p.findall('.//'+W+'ins'))} ins, {len(p.findall('.//'+W+'del'))} del, "
          f"{len(p.findall('.//'+W+'rPrChange'))} fmt, {len(p.findall('.//'+W+'highlight'))} hl\n")
