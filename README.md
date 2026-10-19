# gsz-s1qc-pilot

A **pilot study of automated qualitative coding** of Buddhist biographies. Four workflows find two codes, **Scholarship** and **Asceticism**, in the biographies of Huijiao's *Gaoseng zhuan* (GSZ, 高僧傳; T 2059), using the same definitions, and are scored against a manual coding of the same biographies. The study prepares the coding of later collections, starting with the *Xu gaoseng zhuan* (XGSZ, 續高僧傳; T 2060), whose biographies are included without manual coding.

The manual coding here is an excerpt from a larger, exhaustive manual coding of the 227 GSZ biographies of Chinese monks with 54 codes and 70 subcodes: it gives only the Scholarship and Asceticism spans, without subcodes. Sangyop Lee carried out the original coding; the full dataset is being prepared for publication with 김지현, 유용식, 안은혜 and 이애리.

## Contents

| Folder | What it holds |
| --- | --- |
| `gsz/plaintext/` | the 227 GSZ biographies, one text file each |
| `gsz/gold/` | the same biographies in TEI, with the manual Scholarship and Asceticism coding |
| `gsz/splits/` | `dev.txt` (144 biographies) and `test.txt` (83) |
| `xgsz/plaintext/` | 472 XGSZ biographies, uncoded |
| `sources/` | the CBETA files the texts and the GSZ punctuation come from, with their headers |
| `definitions/` | the definitions every workflow reads |
| `workflows/sentence-detection/` | Jev: the sentences that describe a code, for a reviewer who draws the spans |
| `workflows/span-detection/` | Jev: the biography cut into narrative units, then each unit classified |
| `workflows/llm-sentence-detection/` | Claude and GPT: the sentences that describe a code |
| `workflows/llm-span-detection/` | Claude and GPT: the spans of a code |
| `results/` | the outputs of the runs, with their scores and costs in `results/README.md` |

## Data

A biography's sentences are the stretches of its text that end in 。, the only punctuation mark in the texts, numbered S001, S002, … in text order. Every workflow and every result refers to sentences by these ids, so all of them read `plaintext/` and split it the same way. File names give the fascicle, the number of the biography in it and the monk's name (`07_23_釋道溫`); the name is the main monk the codes are about.

`gsz/gold/` marks each coded passage with `<seg ana="#Scholarship">`, `<seg ana="#Asceticism">` or both; the pointers resolve to the categories declared in each file's header. Span ids follow `s1qc-12_27-s001`, numbered within each biography. The coding records explicit evidence about the main monk outside long quoted documents; subcodes and inferred codes are not included. Where a span boundary falls inside a sentence, `<anchor type="division" resp="#SLee"/>` marks it; the text of every gold file, with each anchor written as 。, is the text of its plaintext file.

The two splits divide the GSZ biographies: **dev** is the set on which the workflows' wording and cutoffs were chosen; **test** is kept back for a final check of the chosen workflows on biographies they were not tuned on.

Both texts are the Taishō reading as CBETA encodes it, with CBETA's own emendations reverted, and with characters in their normalized form where one exists, else as the Unicode character, else in CBETA's composition notation. The GSZ text is from CBETA T50n2059.xml (2026-07-08); its punctuation is the Taishō's 。, as in CBETA's releases before its new punctuation (2020), the last of which is included as `sources/T50n2059_2019Q3.xml`. The XGSZ text, punctuation included, is from CBETA T50n2060.xml (2025-06-03). Both files are in `sources/` (see Source and terms). An XGSZ file holds one biography, named and numbered as in the GSZ: fascicle, position in the fascicle, and the name as the Taishō text gives it. In both collections, biographies of foreign monks are left out but keep their numbers, so some numbers are missing (in the GSZ, all of fascicle 2).

## Definitions

| File | What it defines | Read by |
| --- | --- | --- |
| `scholarship.txt`, `asceticism.txt` | the two codes | every workflow |
| `span.txt` | where a span begins and ends | span detection, LLM span detection |
| `main_monk.txt` | what counts as being about the main monk (`{name}` and `{last}` are filled in per biography) | sentence detection, LLM sentence detection |
| `quotation.txt` | what counts as a long quoted document | sentence detection, LLM sentence detection |

Span detection asks about the main monk and quotations in its own wording, about passages rather than sentences; the LLM span workflows have the main monk and quotations in their task (`workflows/llm-span-detection/task.txt`) and in `span.txt`.

## Workflows

All four run on the GSZ (`--corpus gsz`, the default; `--split dev`, the default, `test` or `all`) or the XGSZ (`--corpus xgsz`, all biographies). Their code questions ask about one code at a time.

| Workflow | Model | Returns |
| --- | --- | --- |
| sentence detection | Jev (`jev-1.14.0`) | a probability per sentence for the code, the main monk and quotations; `flags.py` lists the flagged sentences |
| span detection | Jev (`jev-1.14.0`) | spans |
| LLM sentence detection | Claude Sonnet 5.5 (`claude-sonnet-5-5`) or GPT-6.1 Sol (`gpt-6.1-sol`), effort `low` | the sentences that describe the code |
| LLM span detection | Claude Sonnet 5.5 or GPT-6.1 Sol, effort `low` | spans |

**Sentence detection.** Two kinds of pass over every sentence. The shared pass asks whether it is about the main monk and whether it is inside a long quoted document; a code pass asks whether it describes the code. Each pass's state holds only what its questions are judged by. `flags.py` flags a sentence for a code when it reaches the code's cutoff (Scholarship 0.45, Asceticism 0.7), is about the main monk (0.5 or above) and is not inside a quoted document (below 0.5). The cutoffs are set for a reviewer: few places to visit that hold no span, and almost no span without a flagged sentence. A biography goes whole into one request, which is halved while it is over Jev's token limit; a biography whose text alone is over the limit (in the XGSZ, 04_01 釋玄奘) is asked in halves, each with its stretch of the text, 40 sentences on each side and the first sentence.

**Span detection.** Jev first asks, for every sentence, whether it continues the narrative unit of the sentence before it, and the biography is cut where the answer is weak (below 0.75). Each unit is then asked whether it describes the code (Scholarship 0.8, Asceticism 0.75) and whether it is about the main monk (0.5); long quoted documents are taken out of the kept units, and neighbouring kept units that the cut separated only weakly are joined (Scholarship 0.6, Asceticism 0.55). A request covers at most 200 sentences of a biography, with 40 more on each side and the first sentence, so that long biographies fit.

**LLM workflows.** One request per biography and code, with the task, the definitions, the main monk's name and the biography, one sentence per line with its id. The answer is constrained to a JSON schema.

## Running

```sh
pip install -r requirements.txt
export TYPESAFE_API_KEY=...    # Jev
export ANTHROPIC_API_KEY=...   # Claude
export OPENAI_API_KEY=...      # GPT
R=../../results/sentence-detection/jev/dev/run-1

cd workflows/sentence-detection
for pass in shared Scholarship Asceticism; do python sentences.py $R/$pass --pass $pass; done
python flags.py $R/shared Scholarship=$R/Scholarship Asceticism=$R/Asceticism $R/flags.jsonl

cd ../span-detection
S=../../results/span-detection/jev/dev/run-1
python step1_units.py $S/units
for code in Scholarship Asceticism; do
  mkdir -p $S/$code && cp $S/units/step1.jsonl $S/$code/
  python step2_classify.py $S/$code --code $code
  python step3_quotes.py $S/$code --code $code
  python step4_join.py $S/$code --code $code
done

cd ../llm-sentence-detection   # or ../llm-span-detection
python claude.py ../../results/llm-sentence-detection/claude-low/dev/run-1/Scholarship --code Scholarship
python gpt.py ../../results/llm-sentence-detection/gpt-low/dev/run-1/Scholarship --code Scholarship
```

Add `--corpus xgsz` (and `xgsz` in place of `dev` in the folder) to run on the XGSZ. Every script writes its token usage (`usage_*.jsonl`, or `responses.jsonl` for the LLMs) and its wall-clock time (`timing_*.jsonl`) next to its output.

## Results

`results/<workflow>/<model>/<set>/<run>/`, e.g. `results/span-detection/jev/all/run-1/` (all GSZ) or `results/span-detection/jev/xgsz/run-1/` (all XGSZ). Each run folder holds what the scripts write: per-sentence scores or spans in JSON Lines, the usage of every request, and the run's timing. `results/README.md` gives the runs' scores against the manual coding and their costs.

## Source and terms

The GSZ and XGSZ texts come from the CBETA Chinese Electronic Tripitaka Collection (財團法人佛教電子佛典基金會), CBETA XML P5 (https://github.com/cbeta-org/xml-p5):

- T50n2059 高僧傳, version 2026-07-08 14:32:21 +0800: `sources/T50n2059.xml`
- T50n2060 續高僧傳, version 2025-06-03 13:27:15 +0800: `sources/T50n2060.xml`
- T50n2059 高僧傳, CBETA 2019 Q3, version 2019-09-12 02:11:51 +0800, the last release with the Taishō punctuation: `sources/T50n2059_2019Q3.xml`

The files are included unchanged, with their headers intact, which state: "Available for non-commercial use when distributed with this header intact." As CBETA's terms (https://www.cbeta.org/copyright) require, their statement is reproduced here unchanged:

> 一、 CBETA 電子佛典資料庫（以下簡稱本資料庫）使用說明
> 非營利使用：本資料庫之使用限定於個人或團體非營利性用途。
> 再傳播規範：將本資料庫以網路、光碟或其它媒體再傳播、節錄引用及再加工發行時，以不改變實質內容為原則，並需於成品附上本說明及版本資訊，以利使用者查詢相關修訂資訊。
> 錯誤回報：若發現本資料庫中任何錯誤之處，請與本會聯絡。
> 免責聲明：若因使用本資料庫所產生之任何損害，本會一概不負任何責任。
> 核心授權：除下方「二、底本來源與授權分類」中特別註明不適用之文獻外，本資料庫未特別說明處皆採用「Creative Commons 姓名標示-非商業性-相同方式分享 4.0 國際授權條款」釋出。

## Acknowledgements

The workflow scripts, the preparation of the texts from CBETA and the documentation were written with Claude Code (Anthropic), under the direction of Sangyop Lee.

## Licence

Everything in this release, the code included, is under CC BY-NC-SA 4.0 (`LICENSE`). The texts come from CBETA and are used under CBETA's terms for non-commercial use (see Source and terms).
