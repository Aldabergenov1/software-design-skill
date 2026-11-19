# Red flags

Fourteen from the book (chapter in brackets) and six derived ones, then syndromes: flags that
usually fire together. Each: what it is, what you see
in a diff, the usual fix. A flag is a prompt to look for a better alternative, not a verdict.

| Flag | Sign in code | Usual fix |
|---|---|---|
| Shallow Module (4) | 1–2 line method that renames an operation; docstring longer than body; calling it is longer than inlining it | inline it, or merge with neighbours into one deeper module |
| Information Leakage (5) | same format, key, template string, constant or axis order in 2+ files without one definition; save/load pair in different modules; files that change in the same commits without importing each other | one module owns the decision (`ChatFormat`, `case_store`, `Normalization`) |
| Temporal Decomposition (5) | `read_*` / `process_*` / `write_*` modules or `01_`, `02_` scripts that all know one format | build modules around knowledge; stage scripts stay but call the owner |
| Overexposure (5) | common case needs knowledge of rare features: many required args identical for every caller; must enable a cache to simply read | defaults, rare options behind separate methods or an optional params object |
| Pass-Through Method (7) | body is a call with the same arguments; `Agent.send → Client.send → Wrapper.send` | give callers the lower object, or redistribute so each layer adds an abstraction |
| Repetition (9) | same nontrivial block in 3+ places (eval loops, batch preparation) | extract the missing abstraction (`predict(model, loader)`); not for 1–2 lines |
| Special-General Mixture (9) | `if task == ...`, `if dataset == ...`, `if tool.name == ...` inside a general mechanism | mechanism stays generic; specifics move to the user (`step_fn`, `SourceSpec`) |
| Conjoined Methods (9) | `_forward/_loss/_backward` passing state to each other; one is unreadable without the other | join into one method with block comments |
| Comment Repeats Code (13) | `# divide loss by grad_accum` over `loss / grad_accum` | say why, units, invariants — what the line can't |
| Implementation Contaminates Interface (13) | public docstring explains cache layout, DICOM library, internal structures | interface comment = what the caller needs; move the rest inside |
| Vague Name (14) | `x`, `data`, `out`, `res`, `idx`, `mask` (which polarity?), `len` (tokens or chars?) | precise noun: `pred_mask`, `max_prompt_tokens`, `is_pad` |
| Hard to Pick Name (14) | `state`, `manager`, `ctx` holding three different things | split the thing the name tries to cover |
| Hard to Describe (15) | a complete docstring can't be short: modes, flags, "except when" | split or redesign the interface |
| Nonobvious Code (18) | need 3+ files to understand one line; tuple unpacking of 4+; side effects in `get_`/`compute_`/`evaluate` | named dataclass, restore state, document event handlers |
| Pass-through variable (7) | `cfg`, `device`, `tokenizer`, `logger` in 4+ signatures where it's only forwarded | immutable context in constructors; each module gets its sub-config |
| Masked important error (10) | `except Exception: continue`; `fillna(0)` on labels; invented default for PixelSpacing | expose: drop with a logged count, or raise with an actionable message |
| Config knob nobody can set (8) | "tune for your task" parameter; absolute number that goes stale with data or model; every caller passes the same value | compute it (fraction of steps, from context window), log the derived value; a constant if nobody varies it |
| Conflicting parameters (8) | two knobs that encode one decision: `warmup_steps` and `warmup_ratio`, `batch_size` and `lr` with no scaling rule, `fp16` + `bf16` + `amp` flags | one choice: a single parameter, a preset (`precision="bf16-mixed"`) or a computed value |
| Internal mutable leaks out (5, 19) | `return self._messages`; caller does `conv.messages.append(...)` | methods that keep invariants (`add_tool_results`, `compact`) |
| Tactical special case (3, 16) | a diff adds a branch for one feature or one test instead of changing structure | ask what the design would be with this known from the start |

## Syndromes

Flags that fire together usually share one cause. Fixing them one by one moves the problem around;
name the syndrome as a single finding and fix the cause.

| Syndrome | Flags together | Typical ML/agent shape | Cause and fix |
|---|---|---|---|
| Read/process/write split | Temporal Decomposition + Information Leakage + Repetition | `01_preprocess.py`, `02_train.py`, `03_eval.py` each parse the same manifest or label format | modules follow pipeline steps, not knowledge; one module owns the format, stage scripts call it |
| Shallow wrapper stack | Shallow Module + Pass-Through Method + Conjoined Methods | `Agent → Client → Wrapper → SDK`, each layer forwarding `send`; `Trainer` split into `_forward/_loss/_backward` | one deep module sliced into layers; merge, re-split only along knowledge |
| Leaky general module | Information Leakage + Overexposure + Special-General Mixture | a "generic" loader whose callers pass `is_dicom`, `vendor` and must know its cache layout | absorb the leaked knowledge, defaults instead of knobs, specifics to the caller |
| Naming spiral | Vague Name + Hard to Pick Name + Hard to Describe | `ctx`/`state`/`batch_info` dicts whose docstring keeps growing | the thing holds two concepts; split it, renaming won't help |
| Error avalanche | Masked important error + Overexposure + Shallow Module | interface raises more than callers can handle, so they `except: continue` and drop samples silently | define errors out below the interface, expose only what callers act on, with a logged count |
