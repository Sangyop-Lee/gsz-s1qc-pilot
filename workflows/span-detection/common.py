"""Shared helpers (each workflow folder keeps its own copy).

A biography is a file in <corpus>/plaintext/ (gsz or xgsz). Its sentences are the stretches that end in 。,
numbered S001, S002, ... in text order; every workflow refers to them by these ids. The definitions the models read are
in definitions/.
"""

import argparse
import json
import re
import time
from pathlib import Path

from typesafe_sdk import TypeSafeBadRequestError, TypeSafeClient

ROOT = Path(__file__).resolve().parents[2]
DEFINITIONS = ROOT / "definitions"
SPLITS = ROOT / "gsz" / "splits"
COLLECTIONS = {"gsz": "the Gaoseng zhuan (高僧傳)", "xgsz": "the Xu gaoseng zhuan (續高僧傳)"}
CORPUS = {"name": "gsz"}  # set from --corpus by parse()
START = time.time()

# Jev
MODEL = "jev-1.14.0"  # pinned: the jev-latest alias moves with new releases
MAX_OPTIONS = 255  # Jev's limit on the options of one Choice question

# The codes the workflow can find, each read against definitions/<code>.txt, with its cutoffs for jev-1.14.0:
# the code question in steps 2 and 3, and the join in step 4.
CODES = {"Scholarship": {"threshold": 0.8, "join": 0.6},
         "Asceticism": {"threshold": 0.75, "join": 0.55}}

WINDOW = 200  # a request asks about at most this many sentences of the biography...
MARGIN = 40  # ...and carries this many more on each side, plus the first sentence
MAX_QUESTIONS = 200


SENTENCE_END = re.compile(r"(?<=。)")


def definition(name):
    return (DEFINITIONS / f"{name}.txt").read_text(encoding="utf-8").strip()


def collection():
    """The collection's name as the models read it."""
    return COLLECTIONS[CORPUS["name"]]


def plaintext():
    return ROOT / CORPUS["name"] / "plaintext"


def biographies(split):
    """Biography names (file names without extension): all of the corpus, a split of the GSZ (dev, test), or the
    biographies listed in a file, one per line."""
    if split == "all":
        return sorted(p.stem for p in plaintext().glob("*.txt"))
    path = Path(split) if Path(split).is_file() else SPLITS / f"{split}.txt"
    return path.read_text(encoding="utf-8").split()


def main_monk(bio):
    """The main monk's name, from the file name: 07_23_釋道溫 -> 釋道溫."""
    return bio.split("_", 2)[2]


def short_name(name):
    """What the text calls him after the first sentence: 釋道溫 -> 溫, 香闍梨 -> 香."""
    return name.removesuffix("闍梨").removesuffix("禪師")[-1]


def main_monk_definition(name):
    return definition("main_monk").format(name=name, last=short_name(name))


def sentence_id(i):
    """Sentence id for the 0-based index i: 0 -> S001."""
    return f"S{i + 1:03d}"


def sentences(bio):
    """The biography's sentences, in order."""
    text = (plaintext() / f"{bio}.txt").read_text(encoding="utf-8").strip()
    return [s for s in SENTENCE_END.split(text) if s]


def tagged(sents):
    """The biography as the model reads it: one sentence per line, with its id."""
    return "\n".join(f"{sentence_id(i)}| {s}" for i, s in enumerate(sents))


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def parser(description):
    """An argument parser with --corpus, --split and --bio, shared by every script."""
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--corpus", choices=COLLECTIONS, default="gsz", help="gsz (default) or xgsz")
    p.add_argument("--split", help="gsz: dev (default), test or all; xgsz: all (default); or a file listing biographies")
    p.add_argument("--bio", action="append", help="only this biography (repeatable)")
    return p


def parse(p):
    """Parses the arguments and sets the corpus."""
    args = p.parse_args()
    CORPUS["name"] = args.corpus
    if args.split is None:
        args.split = "dev" if args.corpus == "gsz" else "all"
    return args


def selected(args):
    return args.bio or biographies(args.split)


def write_timing(run_dir, step, **extra):
    """Wall-clock seconds since the script started, written to timing_<step>.jsonl."""
    write_jsonl(run_dir / f"timing_{step}.jsonl", [{"seconds": round(time.time() - START, 1), **extra}])


# Token usage, one record per request, written by each step to usage_<step>.jsonl, with the step's timing.
USAGE = []


def log_usage(bio, response):
    USAGE.append({"bio": bio, "model": response.model, "usage": response.usage.model_dump(mode="json")})


def write_usage(run_dir, step):
    write_jsonl(run_dir / f"usage_{step}.jsonl", USAGE)
    write_timing(run_dir, step, requests=len(USAGE))
    USAGE.clear()


def client():
    return TypeSafeClient(model=MODEL)


def arguments(description, threshold=None, requests=True, code=False):
    """Command-line arguments shared by the steps: the run folder, --corpus, --split, --bio and the request settings."""
    p = parser(description)
    p.add_argument("run_dir", type=Path, help="folder for this run's outputs")
    if code:
        p.add_argument("--code", choices=CODES, default="Scholarship", help="the code to find (default Scholarship)")
    if threshold is not None:
        p.add_argument("--threshold", type=float, default=threshold,
                       help=f"minimum probability of yes (default {threshold})")
    if requests:
        p.add_argument("--window", type=int, default=WINDOW,
                       help=f"longest stretch of the biography one request asks about (default {WINDOW}; 0: whole biography)")
        p.add_argument("--margin", type=int, default=MARGIN,
                       help=f"sentences sent on each side of that stretch (default {MARGIN})")
        p.add_argument("--max-questions", type=int, default=MAX_QUESTIONS,
                       help=f"most questions per request (default {MAX_QUESTIONS})")
    return p


def excerpt(sents, lo, hi):
    """Sentences lo..hi (0-based, inclusive) as the model reads them; the first sentence, where the
    main monk is named, is always included, and a line "…" marks the sentences left out."""
    lines = []
    if lo > 0:
        lines.append(f"{sentence_id(0)}| {sents[0]}")
        if lo > 1:
            lines.append("…")
    lines += [f"{sentence_id(i)}| {sents[i]}" for i in range(lo, hi + 1)]
    if hi < len(sents) - 1:
        lines.append("…")
    return "\n".join(lines)


def batches(items, nsent, args):
    """Groups questions into requests. items: (key, first, last), the 0-based stretch of sentences a
    question is about. A request takes at most --max-questions questions about a stretch of at most
    --window sentences, and carries that stretch plus --margin sentences on each side.
    Returns (lo, hi, keys); a biography no longer than the window is always sent whole."""
    if not args.window or nsent <= args.window:
        keys = [k for k, _, _ in items]
        return [(0, nsent - 1, keys[i:i + args.max_questions]) for i in range(0, len(keys), args.max_questions)]
    groups, cur, lo, hi = [], [], None, None
    for k, a, b in sorted(items, key=lambda x: (x[1], x[2])):
        if cur and (max(hi, b) - min(lo, a) + 1 > args.window or len(cur) >= args.max_questions):
            groups.append((lo, hi, cur))
            cur = []
        if not cur:
            lo, hi = a, b
        cur.append(k)
        lo, hi = min(lo, a), max(hi, b)
    if cur:
        groups.append((lo, hi, cur))
    return [(max(0, a - args.margin), min(nsent - 1, b + args.margin), ks) for a, b, ks in groups]


def ask(ts, bio, state, sents, items, questions, args):
    """Asks every question in items against the biography (or the stretch of it the request is about),
    with the rest of the state; returns {key: answer}. A request over Jev's token limit is halved."""
    out = {}
    pending = batches(items, len(sents), args)
    while pending:
        lo, hi, keys = pending.pop(0)
        st = dict(state, biography=tagged(sents) if (lo, hi) == (0, len(sents) - 1) else excerpt(sents, lo, hi))
        try:
            response = ts.system_one(state=st, questions={k: questions[k] for k in keys})
        except TypeSafeBadRequestError as err:
            if "max_tokens_exceeded" not in str(err) or len(keys) == 1:
                raise
            pending[:0] = [(lo, hi, keys[:len(keys) // 2]), (lo, hi, keys[len(keys) // 2:])]
            continue
        log_usage(bio, response)
        out.update({k: response.answers[k] for k in keys})
    return out
