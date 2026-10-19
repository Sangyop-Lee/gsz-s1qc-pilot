"""LLM span detection with GPT: one request per biography and code; the model decides the spans.

GPT-6.1 Sol (gpt-6.1-sol) through the Responses API, reasoning effort "low", strict structured output. Output:
spans.jsonl (one record per span; main_monk is the model's about_main_monk), responses.jsonl (status, token usage and
seconds per biography) and timing_gpt.jsonl. A span with an unknown sentence id, an end before its start, or an overlap
with the previous span is kept and listed under problems.

  OPENAI_API_KEY=... python gpt.py ../../results/llm-span-detection/gpt-low/dev/run-1/Scholarship --code Scholarship
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor

import openai
from openai import OpenAI

from common import SCHEMA, arguments, biography_message, check, instructions, parse, selected, write_jsonl, write_timing

MODEL = "gpt-6.1-sol"
EFFORT = "low"


def ask(client, bio, code, model, effort):
    t0 = time.time()
    try:
        # streamed: long biographies can be cut off on the way when not streamed
        with client.responses.stream(
            model=model,
            max_output_tokens=64000,
            reasoning={"effort": effort},
            text={"format": {"type": "json_schema", "name": "spans", "schema": SCHEMA, "strict": True}},
            instructions=instructions(code),
            input=biography_message(bio),
        ) as stream:
            response = stream.get_final_response()
    except (openai.APIError, RuntimeError) as e:  # still failing after the client's retries, or a stream cut off
        return {"bio": bio, "model": model, "status": "error", "error": str(e)}, []
    refused = any(c.type == "refusal" for o in response.output if o.type == "message" for c in o.content)
    status = "refusal" if refused else response.status
    record = {"bio": bio, "model": response.model, "status": status,
              "usage": response.usage.model_dump(mode="json") if response.usage else None,
              "seconds": round(time.time() - t0, 1)}
    if status != "completed":
        return record, []
    spans = json.loads(response.output_text)["spans"]
    return record, [dict(s, bio=bio, code=code, main_monk=s["about_main_monk"], model=response.model) for s in check(bio, spans)]


def main():
    args = parse(arguments(__doc__.splitlines()[0], MODEL, EFFORT))
    client = OpenAI(max_retries=5)
    bios = selected(args)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda bio: ask(client, bio, args.code, args.model, args.effort), bios))
    for bio, (response, recs) in zip(bios, results):
        print(bio, response["status"], len(recs), "spans")
    write_jsonl(args.run_dir / "responses.jsonl", [r for r, _ in results])
    write_jsonl(args.run_dir / "spans.jsonl", [s for _, recs in results for s in recs])
    write_timing(args.run_dir, "gpt", model=args.model, effort=args.effort, workers=args.workers, biographies=len(bios))


if __name__ == "__main__":
    main()
