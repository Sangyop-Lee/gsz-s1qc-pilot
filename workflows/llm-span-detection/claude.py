"""LLM span detection with Claude: one request per biography and code; the model decides the spans.

Claude Sonnet 5.5 (claude-sonnet-5-5), adaptive thinking at effort "low", answer constrained to a JSON schema,
server-side fallbacks ("default") on a declined request. Output: spans.jsonl (one record per span; main_monk is the
model's about_main_monk), responses.jsonl (stop reason, token usage and seconds per biography) and timing_claude.jsonl.
A span with an unknown sentence id, an end before its start, or an overlap with the previous span is kept and listed
under problems.

  ANTHROPIC_API_KEY=... python claude.py ../../results/llm-span-detection/claude-low/dev/run-1/Scholarship --code Scholarship
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor

import anthropic

from common import SCHEMA, arguments, biography_message, check, instructions, parse, selected, write_jsonl, write_timing

MODEL = "claude-sonnet-5-5"
EFFORT = "low"


def ask(client, bio, code, model, effort):
    t0 = time.time()
    try:
        with client.beta.messages.stream(
            model=model,
            max_tokens=64000,
            thinking={"type": "adaptive"},
            output_config={"effort": effort, "format": {"type": "json_schema", "schema": SCHEMA}},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=[{"type": "text", "text": instructions(code), "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": biography_message(bio)}],
        ) as stream:
            message = stream.get_final_message()
    except anthropic.APIError as e:  # still failing after the client's retries
        return {"bio": bio, "model": model, "stop_reason": "error", "error": str(e)}, []
    response = {"bio": bio, "model": message.model, "stop_reason": message.stop_reason,
                "usage": message.usage.model_dump(mode="json"), "seconds": round(time.time() - t0, 1)}
    if message.stop_reason != "end_turn":
        return response, []
    spans = json.loads(next(b.text for b in message.content if b.type == "text"))["spans"]
    return response, [dict(s, bio=bio, code=code, main_monk=s["about_main_monk"], model=message.model) for s in check(bio, spans)]


def main():
    args = parse(arguments(__doc__.splitlines()[0], MODEL, EFFORT))
    client = anthropic.Anthropic(max_retries=5)
    bios = selected(args)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda bio: ask(client, bio, args.code, args.model, args.effort), bios))
    for bio, (response, recs) in zip(bios, results):
        print(bio, response["stop_reason"], len(recs), "spans")
    write_jsonl(args.run_dir / "responses.jsonl", [r for r, _ in results])
    write_jsonl(args.run_dir / "spans.jsonl", [s for _, recs in results for s in recs])
    write_timing(args.run_dir, "claude", model=args.model, effort=args.effort, workers=args.workers, biographies=len(bios))


if __name__ == "__main__":
    main()
