"""Step 2: cut the biography into units, and is each one the code (Scholarship by default) about the main monk?

The biography is cut before every sentence whose probability of continuing the
unit before it (step 1) is below --cut (default 0.75). Each unit gets two Noul
questions, against the whole biography (or the stretch of it the request is
about): does it describe the code (--code; threshold in common.CODES:
Scholarship 0.8, Asceticism 0.75), and is it about the main monk, named in the
file name (threshold 0.5)? A unit is kept only if it passes both. Output:
step2.jsonl, one record per unit with p_<code> and p_main_monk (main_monk is the
decision: true only for a unit that passes both), and usage_step2.jsonl.
"""

from typesafe_sdk import Noul, NoulCriteria

from common import (CODES, arguments, ask, client, definition, main_monk, parse, read_jsonl, sentence_id, sentences,
                    short_name, write_jsonl, write_usage)

CUT = 0.75
MAIN_THRESHOLD = 0.5


def where(start, end):
    return f"sentence {start}" if start == end else f"sentences {start} to {end}"


def code_question(start, end, code):
    return Noul(
        instructions=(
            f"Read the passage in {where(start, end)} of `biography` in the context of the whole biography. "
            f"Does the passage describe {code} as defined in `{code.lower()}_definition`?"
        ),
        criteria=NoulCriteria(
            true=f"The passage describes {code} as defined",
            false=f"The passage does not describe {code}",
        ),
    )


def main_monk_question(start, end, name):
    return Noul(
        instructions=(
            f"In the passage in {where(start, end)} of `biography`, is `main_monk` the person the passage is about? "
            f"`main_monk` is the subject of the biography, named in full in its first sentence; after that, the text "
            f"usually calls him by the last character of his name alone ({short_name(name)} for {name}). "
            f"A passage that tells what others said of him or how they responded to him is about him. A passage that "
            f"tells what someone else did or was (a disciple, a teacher, a layman, a ruler, another monk), mentioning "
            f"him only in passing, is about that other person. A passage that introduces another person (a disciple, "
            f"a contemporary monk, a layman) and goes on to tell that person's learning, character or career is that "
            f"person's own account, even when it says he studied under `main_monk` or followed his work."
        ),
        criteria=NoulCriteria(
            true="The passage is about `main_monk`: what he did or was, or how others saw him or responded to him",
            false="The passage is about someone else",
        ),
    )


def units(n, p_continue, cut):
    """0-based (first, last) of each unit: a unit begins at the first sentence and wherever the
    probability of continuing the unit before falls below cut."""
    out, start = [], 0
    for i in range(1, n):
        if p_continue[i] < cut:
            out.append((start, i - 1))
            start = i
    out.append((start, n - 1))
    return out


def check(ts, bio, spans, args):
    """Step 2's two questions for spans given as (start id, end id); returns {(start, end): (p_code, p_main_monk)}."""
    sents, name, key = sentences(bio), main_monk(bio), args.code.lower() + "_definition"
    state = {key: definition(args.code.lower()), "main_monk": name}
    questions, items = {}, []
    for a, b in spans:
        k, lo, hi = f"{a}-{b}", int(a[1:]) - 1, int(b[1:]) - 1
        questions[k + "-s"] = code_question(a, b, args.code)
        questions[k + "-m"] = main_monk_question(a, b, name)
        items += [(k + "-s", lo, hi), (k + "-m", lo, hi)]
    got = ask(ts, bio, state, sents, items, questions, args)
    return {(a, b): (got[f"{a}-{b}-s"].noul, got[f"{a}-{b}-m"].noul) for a, b in spans}


def main():
    p = arguments(__doc__.splitlines()[0], code=True)
    p.add_argument("--threshold", type=float, help="minimum probability of the code (default: its cutoff in common.CODES)")
    p.add_argument("--main-threshold", type=float, default=MAIN_THRESHOLD,
                   help=f"minimum probability that a unit is about the main monk (default {MAIN_THRESHOLD})")
    p.add_argument("--cut", type=float, default=CUT,
                   help=f"a unit begins where the probability of continuing is below this (default {CUT})")
    args = parse(p)
    if args.threshold is None:
        args.threshold = CODES[args.code]["threshold"]
    step1 = read_jsonl(args.run_dir / "step1.jsonl")
    records = []
    with client() as ts:
        for bio in dict.fromkeys(r["bio"] for r in step1):
            if args.bio and bio not in args.bio:
                continue
            n = len(sentences(bio))
            pc = [None] + [r["p_continue"] for r in step1 if r["bio"] == bio]
            spans = [(sentence_id(a), sentence_id(b)) for a, b in units(n, pc, args.cut)]
            p = check(ts, bio, spans, args)
            for a, b in spans:
                ps, pm = p[(a, b)]
                records.append({"bio": bio, "start": a, "end": b, f"p_{args.code.lower()}": ps, "p_main_monk": pm,
                                "main_monk": ps >= args.threshold and pm >= args.main_threshold})
            print(bio, len(spans), "units,", sum(r["main_monk"] for r in records if r["bio"] == bio), "kept")
    write_jsonl(args.run_dir / "step2.jsonl", records)
    write_usage(args.run_dir, "step2")


if __name__ == "__main__":
    main()
