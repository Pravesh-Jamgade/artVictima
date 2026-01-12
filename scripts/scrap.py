#!/usr/bin/env python3
import csv
import re
from pathlib import Path

'''
^ start of line, $ end of line
(\d) digit 0-9
(+) one or more time
\s any whitespace char
'''
PSC_RE = re.compile(
    r"^proposed PSC level (\d+) hits (\d+), misses (\d+)\s*$"
)

def path_tag(stats_path: str) -> str:
    return "_".join(stats_path.parent.parts)


def main(root_dir="", out_csv="temp.csv"):
    root = Path(root_dir).resolve()
    stats_files = root.rglob("proposed.stats")
    rows = []
    for f in stats_files:
        tag = path_tag(f)
        with f.open("r", encoding="utf-8", errors="ignore") as fp:
            for line in fp:
                line = line.strip()
                m = PSC_RE.match(line)
                if not m:
                    continue

                level, hits, misses = m.groups()
                rows.append(tag + ","+ str( int(level)) + ","+ str( int(hits)) + ","+ str( int(misses)) + '\n' )
        
    with open(out_csv, "w", encoding="utf-8") as out:
        writer = "folder_tag,"+"level, "+ "hits, " + "misses\n"

        out.write(writer)
        for row in rows:
            out.write(row)
    
    print(f"Write {len(rows)} rows to {out_csv}")

if __name__ == "__main__":
    main(".", "temp.csv")

        