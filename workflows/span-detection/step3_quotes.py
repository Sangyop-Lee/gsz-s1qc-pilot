"""Step 3: take long quoted documents out of the kept units.

For every sentence of a unit kept by step 2, one Noul question: is it inside a
long quoted document? Its criteria say what counts (a letter, memorial, edict,
inscription, eulogy or treatise quoted at length, as `span_definition`
describes). Sentences at or above --threshold (default
0.5) are removed and the unit splits around them; the sentence that introduces
a quotation stays. A piece that a split or trim creates is a new span, so it is
asked step 2's two questions again, with step 2's thresholds. Output:
step3.jsonl in the step2 format (main_monk is the final decision),
quotes_step3.jsonl with every probability, and usage_step3.jsonl.
"""

from typesafe_sdk import Noul, NoulCriteria

import step2_classify as s2
from common import (CODES, arguments, ask, client, definition, parse, read_jsonl, sentence_id, sentences, write_jsonl,
                    write_usage)

CRITERIA = NoulCriteria(true=("Inside the quoted text of a long document: a letter, memorial, edict, inscription, eulogy or "
                              "treatise quoted at length, as `span_definition` describes."),
                        false="The narrator's own text, a short quoted remark or dialogue, or the sentence that introduces a quotation.")


def question(sid):
    return Noul(instructions=f"Is sentence {sid} of `biography` inside a long quoted document?", criteria=CRITERIA)


def pieces(start, end, quoted):
    """(start id, end id) of the runs of unquoted sentences in start..end."""
    out, run = [], []
    for i in range(int(start[1:]), int(end[1:]) + 1):
        if i in quoted:
            if run:
                out.append((run[0], run[-1]))
            run = []
        else:
            run.append(i)
    if run:
        out.append((run[0], run[-1]))
    return [(sentence_id(a - 1), sentence_id(b - 1)) for a, b in out]


def main():
    p = arguments(__doc__.splitlines()[0], threshold=0.5, code=True)
    p.add_argument("--code-threshold", type=float, help="step 2's code cutoff for a new piece (default: the code's in common.CODES)")
    p.add_argument("--main-threshold", type=float, default=s2.MAIN_THRESHOLD)
    args = parse(p)
    if args.code_threshold is None:
        args.code_threshold = CODES[args.code]["threshold"]
    step2 = read_jsonl(args.run_dir / "step2.jsonl")
    records, quotes = [], []
    with client() as ts:
        for bio in dict.fromkeys(r["bio"] for r in step2):
            if args.bio and bio not in args.bio:
                continue
            sents = sentences(bio)
            units = [r for r in step2 if r["bio"] == bio]
            kept = [r for r in units if r["main_monk"]]
            idx = sorted({i for r in kept for i in range(int(r["start"][1:]) - 1, int(r["end"][1:]))})
            p_quote = {}
            if idx:
                state = {"span_definition": definition("span")}
                got = ask(ts, bio, state, sents, [(sentence_id(i), i, i) for i in idx],
                          {sentence_id(i): question(sentence_id(i)) for i in idx}, args)
                p_quote = {i + 1: got[sentence_id(i)].noul for i in idx}
            quotes += [{"bio": bio, "sentence": sentence_id(i - 1), "p_quote": p} for i, p in p_quote.items()]
            quoted = {i for i, p in p_quote.items() if p >= args.threshold}
            new = []
            for r in units:
                if not r["main_monk"]:
                    records.append(r)
                    continue
                for a, b in pieces(r["start"], r["end"], quoted):
                    piece = dict(r, start=a, end=b)
                    if (a, b) != (r["start"], r["end"]):
                        piece["split_from"] = f"{r['start']}-{r['end']}"
                        new.append(piece)
                    records.append(piece)
            if new:
                p = s2.check(ts, bio, [(r["start"], r["end"]) for r in new], args)
                for r in new:
                    ps, pm = p[(r["start"], r["end"])]
                    r.update({f"p_{args.code.lower()}": ps, "p_main_monk": pm, "rechecked": True,
                              "main_monk": ps >= args.code_threshold and pm >= args.main_threshold})
            print(bio, len(idx), "sentences asked,", len(quoted), "quoted")
    write_jsonl(args.run_dir / "step3.jsonl", records)
    write_jsonl(args.run_dir / "quotes_step3.jsonl", quotes)
    write_usage(args.run_dir, "step3")


if __name__ == "__main__":
    main()
