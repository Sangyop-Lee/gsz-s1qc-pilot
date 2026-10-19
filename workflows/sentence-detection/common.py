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

ROOT = Path(__file__).resolve().parents[2]
DEFINITIONS = ROOT / "definitions"
SPLITS = ROOT / "gsz" / "splits"
COLLECTIONS = {"gsz": "the Gaoseng zhuan (高僧傳)", "xgsz": "the Xu gaoseng zhuan (續高僧傳)"}
CORPUS = {"name": "gsz"}  # set from --corpus by parse()
START = time.time()

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


def main_monk_definition(name):
    # 香闍梨, 猷禪師: the text calls him by the character before the title
    short = name.removesuffix("闍梨").removesuffix("禪師")
    return definition("main_monk").format(name=name, last=short[-1])


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


MARGIN = 40  # a stretch of a biography too long for one request is sent with this many sentences on each side


class TextTooLong(Exception):
    """Jev rejects a request with a single question: the biography itself is over its token limit."""


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


def halves(lo, hi):
    """The sentence range lo..hi cut in two."""
    mid = (lo + hi) // 2
    return [(lo, mid), (mid + 1, hi)]


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
