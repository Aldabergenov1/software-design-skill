# software-design

A Claude Code skill for designing and reviewing code by John Ousterhout's *A Philosophy of Software
Design*, adapted to ML, LLM and coding-agent code: PyTorch and HuggingFace, data pipelines,
train/eval loops, inference wrappers, tool-use agents.

Install it, then ask for a design review or a new module. The skill triggers on its own.

## Why another APOSD skill

Most APOSD skills retell the book chapter by chapter. This one is narrower and tries to be usable
on real ML code:

- Every principle comes with the point where it stops working. The book insists on moderation, and
  a review that applies every rule to the limit is worse than no review.
- Reviews follow a fixed shape: red flag, place, symptom (change amplification, cognitive load,
  unknown unknowns), fix, cost. A finding with no symptom gets dropped as taste.
- `references/ml-examples.md` has bad → better pairs from ML and agent code for each chapter: a chat
  template copied into three files, a pass-through model client, classitis in a training loop,
  `except Exception: continue` that silently drops one scanner's frames.
- A section on where ML code legitimately bends the rules (notebooks, `nn.Module` structure,
  framework wrappers, experiment configs).
- Syndromes: groups of red flags that share one cause, so a review fixes the cause once.
- An eval suite for `claude plugin eval`.

## Install

As a plugin:

```
/plugin marketplace add Aldabergenov1/software-design-skill
/plugin install software-design@software-design-skill
```

Or copy `skills/software-design/` into `~/.claude/skills/`.

## Use

It triggers on requests like these:

- "review this module's design", "why is this so hard to change?"
- "design a Dataset / collator / loader / trainer for ..."
- "add support for X to this code" (it checks whether the change should be a refactor first)
- "split this class", "is this a deep module?", "where does information leak here?"

It answers in the language of the request and keeps the book's terms in English.

## Layout

```
skills/software-design/
  SKILL.md                  how to think, principles with limits, review / design / change workflows
  references/red-flags.md   flags, what they look like in a diff, usual fixes, syndromes
  references/principles.md  chapter-by-chapter notes and caveats (paraphrase, 1st ed.)
  references/ml-examples.md bad → better pairs from ML, LLM and agent code
evals/                      three cases with LLM graders
```

## Evals

Three cases: reviewing a small RAG pipeline, adding a 25 fps vendor to a clip extractor, designing
a DICOM ultrasound loader. Each run starts a full Claude Code session on your account, so they
cost usage limits.

```
claude plugin eval . --scaffold --allow-tools Bash Write Edit --runs 1 --no-publish
```

`--scaffold` copies each case's input files into the sandbox. Without it there is nothing to review.

## Credits

Built on *A Philosophy of Software Design* by John Ousterhout. The references are a paraphrase, not
the book; read the book. This project is not affiliated with or endorsed by the author or the
publisher.

MIT license.
