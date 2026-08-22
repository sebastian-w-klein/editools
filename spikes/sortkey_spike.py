import re, unicodedata
def sort_key(entry: str) -> str:
    s = entry.split('(')[0].split(',')[0].split(':')[0]      # drop after ( , :
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[ \-‐-―'‘’\"“”.]", '', s)  # letter-by-letter
    return s.lower()

tests = ["Adams, John, 15", "Ada, Countess of Lovelace, 3", "Adam-Smith, Jane, 9",
         "Adams, Abigail, 22", "Chicago (city), 40", "Chicago Tribune, 41",
         "New York: a history, 7", "Newark, 8", "O'Brien, Pat, 12", "Obama, Barack, 5",
         "post-World War II era, 88", "postal service, 90"]
keys = [(sort_key(t), t) for t in tests]
print(f"{'SORT KEY':<22} ENTRY")
for k, t in keys: print(f"{k:<22} {t}")

print("\nOut-of-order check against a correctly sorted list:")
given = [t for _, t in keys]
for a, b in zip(given, given[1:]):
    ka, kb = sort_key(a), sort_key(b)
    flag = "OK " if ka <= kb else "OUT OF ORDER ->"
    if ka == kb: flag = "TIE (unresolvable) ->"
    print(f"  {flag:<24}{a!r} vs {b!r}")
