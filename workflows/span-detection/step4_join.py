"""Step 4: join neighbouring kept spans that the cut separated only weakly (no API call).

Two kept spans next to each other (the second begins right after the first
ends) become one span when the probability, from step 1, that the second's
first sentence continues the unit before it is at least --threshold (the
code's join cutoff in common.CODES: Scholarship 0.6, Asceticism 0.55); a cut
between it and step 2's --cut (0.75) is a weak one. Spans not kept
are passed on unchanged. Output: step4.jsonl in the step3 format; main_monk is
the final decision.
"""

from common import CODES, arguments, parse, read_jsonl, write_jsonl


def join(records, p_continue, threshold):
    n = lambda sid: int(sid[1:])
    out = [r for r in records if not r["main_monk"]]
    cur = None
    for r in sorted((r for r in records if r["main_monk"]), key=lambda r: n(r["start"])):
        if cur and n(r["start"]) == n(cur["end"]) + 1 and p_continue.get(r["start"], 0) >= threshold:
            cur = dict(cur, end=r["end"], joined=True)
        else:
            if cur:
                out.append(cur)
            cur = dict(r)
    if cur:
        out.append(cur)
    return out


def main():
    p = arguments(__doc__.splitlines()[0], requests=False, code=True)
    p.add_argument("--threshold", type=float, help="minimum probability of continuing (default: the code's join cutoff)")
    args = parse(p)
    if args.threshold is None:
        args.threshold = CODES[args.code]["join"]
    step1 = read_jsonl(args.run_dir / "step1.jsonl")
    step3 = read_jsonl(args.run_dir / "step3.jsonl")
    records = []
    for bio in dict.fromkeys(r["bio"] for r in step3):
        if args.bio and bio not in args.bio:
            continue
        pc = {r["sentence"]: r["p_continue"] for r in step1 if r["bio"] == bio}
        records += join([r for r in step3 if r["bio"] == bio], pc, args.threshold)
    write_jsonl(args.run_dir / "step4.jsonl", records)
    print(sum(r["main_monk"] for r in records), "spans kept")


if __name__ == "__main__":
    main()
