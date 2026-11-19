---
name: software-design
description: >
  Design and review code the way John Ousterhout's "A Philosophy of Software Design" teaches,
  tuned for ML, LLM and coding-agent code (PyTorch, HuggingFace, data pipelines, train/eval loops,
  inference wrappers, tool-use agents on the Claude API). Use this skill whenever the user asks to
  review, design, refactor or split a module, class, function, interface or agent tool; asks why
  code feels complicated or hard to change; adds a feature to existing code; designs a Dataset,
  collator, metric, trainer or loader; or mentions deep modules, information leakage, complexity,
  "по Джону", "по Ousterhout", design review — even without naming the book. Not for throwaway
  notebooks.
---

# Software design after Ousterhout

The book makes one claim: the enemy is complexity, meaning anything in the structure of code that
makes it hard to understand or change. Every rule here exists only to reduce it. When a rule does
not reduce complexity in the case at hand, drop it and say why; Ousterhout himself warns that any
idea pushed to the extreme becomes a mistake.

Answer in the user's language and keep the book's terms in English (deep module, information
leakage, pass-through). Assume an engineer who knows ML; skip basics.

## How to think about complexity

Keep three questions in mind while reading any code.

1. **Who needs to know what, and when?** Each design decision (file format, chat template,
   normalization constant, axis order, mask polarity, embedding prefix) should be known by exactly
   one module. When two files must agree on it without a shared definition, a later change updates
   one and silently misses the other. That is the worst symptom, the unknown unknown: nothing tells
   you the second place exists. The opposite mistake is as real: hiding what the caller needs (a
   loader that silently resamples, a tool that silently edits the first of several matches) is a
   false abstraction.
2. **What does the caller pay?** A module is deep when its interface is much simpler than what it
   does. The caller pays for every argument, call-order rule, exception and "remember to also...".
   Pay it once inside the module rather than at every call site: a module has more users than
   authors, so a simple interface beats a simple implementation.
3. **How often is this touched?** Complexity is weighted by time spent on it: $C=\sum_p c_p t_p$.
   Ugly code behind a narrow interface that nobody edits costs almost nothing. Training loops,
   collators, agent loops and data formats are touched constantly; spend attention there.

The three symptoms: change amplification (one change, many edits), cognitive load (how much you must
know), unknown unknowns (not obvious what to change). The two causes: dependencies and obscurity.
Replacing a hidden dependency with a visible one (a shared import instead of the same string in two
files) is already a win even if the count stays the same. Lines of code are not the measure: longer
explicit code is often simpler than short magic. Complexity is incremental, so small things matter.

## Principles and their limits

Each line: the rule, then where it stops working. Chapter numbers point into
[references/principles.md](references/principles.md).

1. Working code isn't enough; invest ~10–20% continuously (3). Not big up-front design, not
   features "for later".
2. Modules should be deep (4). Length is not a criterion either way; some shallow modules are
   unavoidable; one class for everything is also a failure.
3. Make the common case simple (4–5): defaults that do the right thing, rare options separate.
4. Information hiding (5). Hide only what callers don't need; flush rules, resampling, spacing must
   stay visible. Extracting knowledge into a new class helps only if its interface is simple.
5. No temporal decomposition (5): build modules around knowledge, not around load → process → save.
6. Somewhat general-purpose (6): general interface, functionality for today. Flags are not
   generality; a too-general API (per-character insert) is inconvenient today.
7. Different layer, different abstraction (7). Dispatchers and multiple implementations of one
   interface are fine; pass-through is not. Doubt decorators: first try base class, merging with the
   use case or another wrapper, or a separate object. Context objects: immutable, stored in
   constructors, each module gets its sub-config.
8. Pull complexity downward (8). Expose a parameter only if the caller knows a better value;
   otherwise compute it, ideally dynamically. Only pull down what belongs to the module.
9. Together or apart (9). Join on shared information, simpler interface, removed duplication;
   "used together" counts only if two-way. Separate general mechanism from special use. Split a
   method only if child and parent are each understandable alone. DRY is not mechanical: 1–2 lines
   or a fragment with a messy signature stay.
10. Define errors and special cases out of existence (10): change semantics, mask low, aggregate
    high, crash on bugs. Hide an error only if nobody above needs to know; in medical data they
    almost always do.
11. Design it twice (11): 2–3 genuinely different rough sketches; the second one diagnoses the first.
12. Comments describe what code can't (12–13, 15–16): interface comment first; precision (units,
    shapes, bounds, None, ownership) or intuition, never a retelling. The reason for an odd line
    lives in code, not in commits or chat. Document each decision once, link elsewhere.
13. Precise, consistent names (14): one name per purpose, one purpose per name. Hard to name means
    the thing mixes two concepts. Paper notation (`q, k, v`) is fine in short scopes.
14. Consistency (17): do it the way the repo already does. Change a convention only fully, never
    half. Don't force different things into one template.
15. Design for reading, not writing (18): event handlers documented with when they fire; named
    structures instead of tuples; queries without hidden side effects.
16. Increments are abstractions, not features (19). Tests exist to make refactoring safe; TDD is
    not a way to get a design; test-first only for bug fixes. Test through the interface: a test
    that must change when the implementation changes is testing past it. Prefer composition to
    implementation inheritance. Patterns only when the problem fits. Getters/setters don't fix exposed state.
17. Performance through simplicity (20): pick naturally efficient options when they are no more
    complex; tune only after measuring; revert changes without measurable gain unless they
    simplified code; one check for all special cases on the critical path.

## Reviewing code

Unless the user named the area, start where $t_p$ is high: `git log --name-only` over the last few
weeks shows which files keep changing; their problems cost the most. Work through the decisions the
code encodes rather than through files. For each finding name the red flag, the place, the symptom
and the fix. A finding that can't be tied to a symptom is probably taste; drop it. Three real
findings beat ten nitpicks. Read [references/red-flags.md](references/red-flags.md) on every review;
it is a short table of flags, signs in a diff and usual fixes. When several flags fire on one area,
look them up in its syndrome table and fix the shared cause as one finding. For a suspected shallow module use the deletion test: imagine
deleting it; if complexity vanishes it was a pass-through, if it reappears in every caller it earns
its keep.

Use this structure, with headings translated into the user's language:

```
## Summary
2–3 lines: the main problem and the main action.

## Findings (most important first)
1. <Red flag> — `file.py:line`
   Symptom: amplification / cognitive load / unknown unknown — what exactly breaks or slows down.
   Fix: the shape of the solution, 3–10 lines of code if needed.
   Cost: how many edits, what could break.

## Leave as is
Non-obvious good decisions and places where a principle is deliberately not applied.
```

## Designing something new

1. Name the decisions the module hides and what the caller must know.
2. For a big decision sketch two or three genuinely different interfaces (signatures plus one call
   site each), compare them by how easy they make the code above, pick one or a hybrid. Keep this to
   a few lines in the answer. If every variant forces the same extra work on callers, the module
   doesn't solve its whole problem. The first sketch anchors the rest, so get the second by
   pre-mortem: assume the first shipped and failed, name the assumption it rests on (who owns the
   data, which way the dependency points, where the boundary sits), design from its negation. For a
   high-stakes decision, and only if the user asks, a subagent that never sees the first design can
   produce the alternative.
3. Write signatures and interface comments before bodies. A complete docstring that stays short
   means a simple interface; one that keeps growing ("if X..., unless Y...") means go back to step 2.
4. Defaults for the common case. Research hyperparameters (lr, schedule, loss weights) are real
   parameters; num_workers, warmup in absolute steps, a compaction threshold for one model usually
   are not. Log derived values or the run isn't reproducible.
5. Errors: first try to define them away (`unlink(missing_ok=True)`, slicing past the end,
   `ignore_index=-100`). If the caller needs the information, expose it with an actionable message.

## Changing existing code

Agents and people under deadline default to the smallest diff that works; each adds a special case
and the cases pile up. Before editing, ask what the design would be if this requirement had been
known from the start. If it differs, propose the refactor explicitly as its own step with its
payoff; don't silently add the special case, and don't silently rewrite beyond the task. If the
refactor is out of scope, keep the special case in one place with a comment giving the reason.

- Find how the repo already does it (config, logging, seeding, paths, tensor layout) and match it.
- Look for the second place: a constant or convention you are changing often lives elsewhere too.
  Grep for the literal, the key or the field name; if the change needs a grep, the knowledge has
  leaked. `git log` shows files that keep changing in the same commits without importing each
  other: that is hidden shared knowledge. So are matching `if dataset == ...` branches in two
  modules. Fix it with one owner; a "keep in sync with X" comment only documents the leak.
- Re-read the diff for comments and docstrings it made false; remove debug leftovers.
- No tests around the code? A small golden test first, on the public output (what a `Dataset` or
  collator returns), not on private helpers. Fix bugs with a test that fails before the fix.
- After merging shallow modules into a deep one, replace their unit tests with tests on the new
  interface instead of keeping both layers.
- An edit-until-green loop recreates the TDD trap: look for branches that exist only for a test.
- Asked to "add docstrings" to finished code: derive the contract from callers and tests, don't
  retell the body.

## Where ML code legitimately bends

- Notebooks and one-day ablations have $t_p \approx 0$: let them be tactical. Be strategic at the
  boundaries that outlive experiments: data loading, splits, metrics, eval harness, checkpoint and
  prediction formats.
- `nn.Module` split into `Attention`, `MLP`, `Block` mirrors the math and is fine. `LossComputer`,
  `GradClipper`, `OptimizerStepper` is classitis: the step protocol then lives nowhere.
- Framework-imposed pass-through and wrappers (`LightningModule.forward`, `DDP`, `torch.compile`)
  are tolerable while their traces stay in one module (unwrap on save and load).
- Experiment configs legitimately expose many parameters; get depth from defaults, grouping and
  computed values. Hydra/OmegaConf is a context object: read-only, sub-configs per module.
- Saving hidden state (normalization stats, tokenizer version, seed) next to a checkpoint is not
  leakage while one module writes and reads it.
- Expensive runs justify naturally efficient choices up front (no per-step `.item()`, batched
  tokenization) when they are no more complex.
- For an LLM agent, a tool's description and `input_schema` are its interface comment: the model
  can't read the implementation.

## Don't

- Split a function only because it is long, or add a class for "cleanliness".
- Demand comments on obvious code or every local variable.
- Add Registry/Factory/Strategy with a single implementation.
- Rewrite isolated working code nobody touches.
- Report findings without the symptom they cause.

## References

- [references/red-flags.md](references/red-flags.md): flags, signs in a diff, fixes, syndromes.
  Every review.
- [references/principles.md](references/principles.md): per-chapter nuances, author caveats, book
  anchors. Read the chapter when a finding hinges on a nuance or the user asks what the book says.
- [references/ml-examples.md](references/ml-examples.md): bad → better pairs from ML, LLM and agent
  code by chapter. Use them to shape fixes; adapt instead of pasting.
