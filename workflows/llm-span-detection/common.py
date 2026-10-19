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


# The task: one request per biography and code; the model returns every span of the code.
CODES = ("Scholarship", "Asceticism")

# The answer: every span of the code, by first and last sentence id.
SCHEMA = {
    "type": "object",
    "properties": {
        "spans": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "start": {"type": "string", "description": "id of the span's first sentence, e.g. S004"},
                    "end": {"type": "string", "description": "id of the span's last sentence, e.g. S005"},
                    "about_main_monk": {"type": "boolean"},
                },
                "required": ["start", "end", "about_main_monk"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["spans"],
    "additionalProperties": False,
}


def instructions(code):
    """The fixed part of the prompt: the task, the code's definition and the span definition."""
    task = (Path(__file__).parent / "task.txt").read_text(encoding="utf-8").strip()
    return "\n\n".join([task.format(code=code, collection=collection()), definition(code.lower()), definition("span")])


def biography_message(bio):
    """The part that changes per biography."""
    name = main_monk(bio)
    return (f"Main monk: {name} (usually {name[-1]} after the first sentence)\n\n"
            f"Biography:\n{tagged(sentences(bio))}")


def check(bio, spans):
    """Spans in text order, each with the problems found: unknown ids, end before start,
    overlap with the previous span. A span with a problem is kept and flagged."""
    known = {sentence_id(i) for i in range(len(sentences(bio)))}
    out, last_end = [], 0
    for s in sorted(spans, key=lambda s: s["start"]):
        problems = [f"unknown id {i}" for i in dict.fromkeys((s["start"], s["end"])) if i not in known]
        if not problems:
            start, end = int(s["start"][1:]), int(s["end"][1:])
            if end < start:
                problems.append("end before start")
            elif start <= last_end:
                problems.append("overlaps the previous span")
            last_end = max(last_end, end)
        out.append(dict(s, problems=problems) if problems else dict(s))
    return out


def arguments(description, model, effort):
    p = parser(description)
    p.add_argument("run_dir", type=Path)
    p.add_argument("--code", choices=CODES, required=True)
    p.add_argument("--model", default=model)
    p.add_argument("--effort", default=effort)
    p.add_argument("--workers", type=int, default=6, help="biographies sent at once (default 6)")
    return p
