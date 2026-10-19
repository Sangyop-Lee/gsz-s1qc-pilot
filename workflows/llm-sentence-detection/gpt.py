"""LLM sentence detection with GPT: one request per biography and code; the model lists the code's sentences.

GPT-6.1 Sol (gpt-6.1-sol) through the Responses API, reasoning effort "low", strict structured output. Output:
sentences.jsonl (one record per sentence), responses.jsonl (status, token usage and seconds per biography) and
timing_gpt.jsonl.

  OPENAI_API_KEY=... python gpt.py ../../results/llm-sentence-detection/gpt-low/dev/run-1/Scholarship --code Scholarship
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor

import openai
from openai import OpenAI

from common import arguments, biography_message, instructions, parse, records, schema, selected, write_jsonl, write_timing

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
            text={"format": {"type": "json_schema", "name": "trait_sentences", "schema": schema(code), "strict": True}},
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
    recs, unknown = records(bio, json.loads(response.output_text), response.model, code)
    if unknown:
        record["unknown_ids"] = unknown
    return record, recs


def main():
    args = parse(arguments(__doc__.splitlines()[0], MODEL, EFFORT))
    client = OpenAI(max_retries=5)
    bios = selected(args)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda bio: ask(client, bio, args.code, args.model, args.effort), bios))
    for bio, (response, recs) in zip(bios, results):
        print(bio, response["status"], sum(r[f"listed_{args.code.lower()}"] for r in recs), args.code)
    write_jsonl(args.run_dir / "responses.jsonl", [r for r, _ in results])
    write_jsonl(args.run_dir / "sentences.jsonl", [s for _, recs in results for s in recs])
    write_timing(args.run_dir, "gpt", model=args.model, effort=args.effort, workers=args.workers, biographies=len(bios))


if __name__ == "__main__":
    main()
