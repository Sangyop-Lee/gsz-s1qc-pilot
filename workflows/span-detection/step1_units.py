"""Step 1: where does each narrative unit begin?

For every sentence from the second on, one Noul question: does it continue the
narrative unit of the sentence before it? Its criteria say what continuing means:
belonging to that unit's core, setup or consequences, as `span_definition`
(in the state, with the biography) defines them. Output:
step1.jsonl, one record per sentence from the second on, with the probability
that it continues the unit before it, and usage_step1.jsonl. Step 2 cuts the
biography where that probability is low; step 4 uses it again to join spans.
"""

from typesafe_sdk import Noul, NoulCriteria

from common import arguments, ask, client, definition, parse, selected, sentence_id, sentences, write_jsonl, write_usage

CRITERIA = NoulCriteria(true=("It continues the narrative unit of the sentence before it: it belongs to that unit's core, "
                              "setup or consequences, as `span_definition` defines them."),
                        false="It begins a new narrative unit.")


def question(prev, sid):
    return Noul(instructions=f"Does sentence {sid} of `biography` continue the narrative unit of sentence {prev}?",
                criteria=CRITERIA)


def run(bio, ts, args):
    sents = sentences(bio)
    state = {"span_definition": definition("span")}
    ids = [sentence_id(i) for i in range(len(sents))]
    questions = {ids[i]: question(ids[i - 1], ids[i]) for i in range(1, len(ids))}
    items = [(ids[i], i - 1, i) for i in range(1, len(ids))]
    answers = ask(ts, bio, state, sents, items, questions, args) if items else {}
    return [{"bio": bio, "sentence": ids[i], "p_continue": answers[ids[i]].noul} for i in range(1, len(ids))]


def main():
    args = parse(arguments(__doc__.splitlines()[0]))
    records = []
    with client() as ts:
        for bio in selected(args):
            records += run(bio, ts, args)
            print(bio, len(sentences(bio)), "sentences")
    write_jsonl(args.run_dir / "step1.jsonl", records)
    write_usage(args.run_dir, "step1")


if __name__ == "__main__":
    main()
