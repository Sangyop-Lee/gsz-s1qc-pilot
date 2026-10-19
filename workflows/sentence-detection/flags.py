"""Sentence detection (Jev): the sentences flagged for a reviewer, from a shared pass and the code passes of sentences.py.

Usage: flags.py <shared run dir> <code>=<code run dir> [...] <output.jsonl>
e.g. flags.py R/shared Scholarship=R/Scholarship Asceticism=R/Asceticism R/flags.jsonl, where R is one run folder
Applies the cutoffs in sentences.py. Output: one record per sentence flagged for a code, with its three scores.
"""

import json
import sys
from pathlib import Path

from sentences import CUTOFFS, MAIN_CUTOFF, QUOTE_CUTOFF


def read(path):
    with open(path, encoding="utf-8") as f:
        return {(r["bio"], r["sentence"]): r for r in map(json.loads, f)}


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    shared_dir, *pairs, out = sys.argv[1:]
    shared = read(Path(shared_dir) / "sentences_shared.jsonl")
    flagged = []
    for pair in pairs:
        code, run_dir = pair.split("=", 1)
        for key, r in read(Path(run_dir) / f"sentences_{code.lower()}.jsonl").items():
            s = shared[key]
            if r[f"p_{code.lower()}"] >= CUTOFFS[code] and s["p_main_monk"] >= MAIN_CUTOFF and s["p_quote"] < QUOTE_CUTOFF:
                flagged.append({"bio": key[0], "sentence": key[1], "code": code, "text": r["text"],
                                "p_code": r[f"p_{code.lower()}"], "p_main_monk": s["p_main_monk"], "p_quote": s["p_quote"]})
    flagged.sort(key=lambda r: (r["bio"], r["sentence"], r["code"]))
    with open(out, "w", encoding="utf-8") as f:
        for r in flagged:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(len(flagged), "flagged sentences")


if __name__ == "__main__":
    main()
