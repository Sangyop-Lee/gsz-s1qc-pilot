"""Sentence detection (Jev): scores every sentence of a biography for a reviewer who draws the spans.

Two kinds of pass, each with a state that holds only what its questions are judged by:
--pass shared asks whether the sentence is about the main monk and whether it is inside a long quoted document;
--pass Scholarship or --pass Asceticism asks whether it describes that code. Each question names the sentence and
the part of the state it is judged by. A biography goes in one request, halved until each request fits Jev's token
limit. flags.py turns the scores into the list a reviewer reads. Output: sentences_<pass>.jsonl (one record per
sentence), usage_sentences_<pass>.jsonl and timing_sentences_<pass>.jsonl.

  python sentences.py ../../results/sentence-detection/jev/dev/run-1/shared --pass shared
  python sentences.py ../../results/sentence-detection/jev/dev/run-1/Scholarship --pass Scholarship
"""

from pathlib import Path

from typesafe_sdk import Noul, TypeSafeBadRequestError, TypeSafeClient

from common import (MARGIN, TextTooLong, definition, excerpt, halves, log_usage, main_monk, main_monk_definition, parse,
                    parser, selected, sentence_id, sentences, tagged, write_jsonl, write_usage)

CODES = ("Scholarship", "Asceticism")
MODEL = "jev-1.14.0"  # pinned: jev-preview and jev-latest move with new releases
# Cutoffs for jev-1.14.0, set for a reviewer: few places to visit that hold no span, almost no span without a flag.
CUTOFFS = {"Scholarship": 0.45, "Asceticism": 0.7}
MAIN_CUTOFF = 0.5
QUOTE_CUTOFF = 0.5


def setup(bio, which):
    """(sentences, state, questions for one sentence id) for a pass."""
    sents, name = sentences(bio), main_monk(bio)
    if which == "shared":
        state = {"main_monk": name, "main_monk_definition": main_monk_definition(name),
                 "quotation_definition": definition("quotation"), "biography": tagged(sents)}

        def questions(sid):
            return {"p_main_monk": Noul(instructions=f"Is sentence {sid} of `biography` about `main_monk`, "
                                                     "as `main_monk_definition` describes?"),
                    "p_quote": Noul(instructions=f"Is sentence {sid} of `biography` inside a long quoted document, "
                                                 "as `quotation_definition` describes?")}
    else:
        key = which.lower() + "_definition"
        state = {key: definition(which.lower()), "biography": tagged(sents)}

        def questions(sid):
            return {f"p_{which.lower()}": Noul(instructions=f"Does sentence {sid} of `biography` describe {which} "
                                                            f"as defined in `{key}`?")}
    return sents, state, questions


def ask(ts, bio, state, questions, batch):
    """Answers for the sentences in batch, in one request; halved until each request fits Jev's token limit."""
    qs = {f"{sid}|{k}": q for sid in batch for k, q in questions(sid).items()}
    try:
        response = ts.system_one(state=state, questions=qs)
    except TypeSafeBadRequestError as e:
        if "max_tokens_exceeded" not in str(e):
            raise
        if len(batch) < 2:
            raise TextTooLong(bio) from e
        half = len(batch) // 2
        return {**ask(ts, bio, state, questions, batch[:half]), **ask(ts, bio, state, questions, batch[half:])}
    log_usage(bio, response)
    out = {}
    for name, answer in response.nouls.items():
        sid, k = name.split("|")
        out.setdefault(sid, {"model": response.model})[k] = answer.noul
    return out


def ask_text(ts, bio, sents, state, questions, lo, hi):
    """Answers for sentences lo..hi (0-based). A biography over Jev's limit is asked in halves, each with
    only its stretch of the text, MARGIN sentences on each side and the first sentence."""
    if (lo, hi) != (0, len(sents) - 1):
        state = dict(state, biography=excerpt(sents, max(0, lo - MARGIN), min(len(sents) - 1, hi + MARGIN)))
    try:
        return ask(ts, bio, state, questions, [sentence_id(i) for i in range(lo, hi + 1)])
    except TextTooLong:
        if lo == hi:
            raise
        return {sid: a for x, y in halves(lo, hi) for sid, a in ask_text(ts, bio, sents, state, questions, x, y).items()}


def main():
    p = parser(__doc__.splitlines()[0])
    p.add_argument("run_dir", type=Path)
    p.add_argument("--pass", dest="which", choices=("shared",) + CODES, required=True)
    p.add_argument("--model", default=MODEL)
    args = parse(p)
    records = []
    with TypeSafeClient(model=args.model) as ts:
        for bio in selected(args):
            sents, state, questions = setup(bio, args.which)
            ids = [sentence_id(i) for i in range(len(sents))]
            for sid, answers in ask_text(ts, bio, sents, state, questions, 0, len(sents) - 1).items():
                records.append({"bio": bio, "sentence": sid, "text": sents[int(sid[1:]) - 1], **answers})
            print(bio, len(ids), "sentences")
    write_jsonl(args.run_dir / f"sentences_{args.which.lower()}.jsonl", records)
    write_usage(args.run_dir, f"sentences_{args.which.lower()}")


if __name__ == "__main__":
    main()
