# Bad → better: ML, LLM and agent examples

Each example: short bad code, the shape of the fix, one line of why. Illustrative, not production code.

Contents (chapter in heading): complexity (2) · tactics (3, 16) · deep modules (4) · leakage (5) ·
general-purpose (6) · layers (7) · pull down (8) · together/apart (9) · errors (10) ·
design twice (11) · comments (12–16) · names (14) · consistency and obviousness (17–18) ·
inheritance (19) · performance (20).

## Complexity (2)

### Unknown unknown: normalization in several files

```python
# train.py
img = (img / 255.0 - 0.18) / 0.21
# serve.py, written six months later
img = (img / 255.0 - 0.18) / 0.21
# eval_external.py: someone recomputed stats on a new dataset
img = (img / 255.0 - 0.20) / 0.22      # silent train/serve skew
```

```python
# preprocessing.py — the only place the stats live
NORM = Normalization.from_file("stats/train_v3.json")
def to_model_input(raw: np.ndarray) -> torch.Tensor:
    return NORM(crop_to_fan(raw))
# train.py / serve.py / eval_external.py: x = to_model_input(raw)
```

"How a scan becomes model input" is one module's decision: skew becomes impossible, not unlikely.

### Cognitive load in short code

```python
def train_step(model, batch, optimizer):
    loss = model(**batch).loss
    loss.backward()
    optimizer.step()
    return loss.item()
```

Five lines, yet the caller must remember `model.train()`, `zero_grad()` outside, device, `labels` in
the batch. Forget `zero_grad` and gradients accumulate silently. Fix: a `Trainer.step(batch)` that
owns the whole step protocol (ch. 4).

### Hidden link: new tool → three places

```python
TOOLS = {"read": read, "edit": edit, "bash": bash, "grep": grep}   # tools.py
TOOL_SCHEMAS = [READ_SCHEMA, EDIT_SCHEMA, BASH_SCHEMA]             # schemas.py, grep forgotten
SYSTEM_PROMPT = "...You can use read, edit, bash..."               # prompt.py
```

Register once with `@tool(name, description, schema)` next to the function; API list and prompt are
generated from the registry. An explicit `REGISTRY = [Read(), Edit(), Bash()]` beats registration by
import side effect: deleting an "unused" import won't drop tools.

## Tactics (3, 16)

### Patches at the symptom

```python
def run_tool(name, args):
    if name == "edit" and args["path"].endswith(".ipynb"):    # patch 1
        args["new"] = args["new"].replace("\n", "\\n")
    if name == "bash" and "pytest" in args["cmd"]:             # patch 2
        args["cmd"] += " -q --tb=short"
    out = TOOLS[name](**args)
    if len(out) > 20000: out = out[:20000]                      # patch 3
    return out
```

Each `if` is a missing design decision. The edit tool understands notebooks; output size is one
policy `truncate_for_context(output, budget)` in the layer that builds `tool_result`.

### New data source as a special case

```python
def augment(img, mask, cfg):
    img, mask = random_flip(img, mask)
    if cfg.dataset == "thyroid_v2":            # new probe: images are mirrored
        img, mask = img[:, ::-1], mask[:, ::-1]
    return normalize(img), mask
```

```python
@dataclass(frozen=True)
class SourceSpec:
    name: str
    mirrored: bool                    # probe orientation; fixed at load time
    transforms: tuple[Transform, ...]

def load_frame(path: Path, spec: SourceSpec) -> np.ndarray:
    img = read_png(path)
    return img[:, ::-1] if spec.mirrored else img   # canonical orientation from here on
```

The code as if the second probe had been known from the start: `augment` knows no dataset names.

## Deep modules (4)

### Dataset

```python
ds = USDataset(root)
ds.load_index(); ds.filter_by_split("train")
ds.set_crop_mode("fan"); ds.set_target_spacing(0.3)
ds.enable_cache("/scratch/cache")        # forget it and an epoch takes 10x longer
img = ds.apply_crop(ds.resample(ds.read_dicom(case_id)))
```

```python
ds = USDataset(root, split="train")      # index, cache, crop, resampling by default
img, mask = ds[i]                         # always target spacing, same shape
# rare case separately: USDataset(root, split="train", cache_dir=None)
```

The caller cares about an aligned pair; call order and cache are unimportant detail (Java buffering).

### Chat format

```python
fmt = ChatFormat(tokenizer)                         # all template knowledge inside
ex = fmt.encode(messages, train_on="assistant")      # input_ids, labels with mask
text = fmt.render_prompt(messages)                   # inference, generation prompt inside
reply = fmt.parse_completion(raw_text)               # inverse operation, same place
```

Three methods hide special tokens, BOS/EOS, masking, per-model templates. A new base model touches
one class.

### Classitis in a training loop

```python
class LossComputer:     def compute(self, out, b): return self.fn(out, b["y"])
class GradClipper:      def clip(self, m): clip_grad_norm_(m.parameters(), self.c)
class OptimizerStepper: def step(self): self.opt.step(); self.opt.zero_grad()
```

One `Trainer.step(batch)`: loss, AMP scaler, accumulation, unscale → clip → step → update →
zero_grad → scheduler. The order is knowledge that must live in one place.

### Informal interface of tensor code

```python
def attention(q, k, v, mask): ...
# (B,H,T,D) or (B,T,H,D)? mask: True = keep or masked? additive or boolean? causal inside?
```

Docstring with shapes and semantics, `key_padding_mask: BoolTensor  # True = pad`, assert on ndim.
Flipped mask polarity doesn't crash; it silently ruins training.

### Agent tools

```python
tools = [read_file, read_lines, list_dir, list_dir_recursive, grep, glob,
         write_file, append_file, insert_line, replace_line, delete_lines, bash]
```

`read(path, offset=None, limit=None)`, `list(path, pattern=None)`, `edit(path, old, new)`, `bash(cmd)`.
Fewer, deeper tools. The model reads the interface, so the cognitive load is the model's.

## Information hiding and leakage (5)

### Back-door leakage: a template in three files

```python
# build_sft.py
text = f"<|im_start|>user\n{q}<|im_end|>\n<|im_start|>assistant\n{a}<|im_end|>"
# collator.py
start = find_subseq(ids, tok.encode("<|im_start|>assistant\n"))
# serve.py
reply = out.split("<|im_start|>assistant\n")[-1].split("<|im_end|>")[0]
```

No file exposes the template; all depend on it. Cure: `ChatFormat` above.

### Temporal decomposition: pipeline scripts

```python
# 01_preprocess.py
np.savez(out, img=img.astype(np.float16), mask=mask, sp=spacing[::-1])
# 02_train.py
d = np.load(p); x = torch.from_numpy(d["img"]).float(); sp = d["sp"]
# 03_eval.py
d = np.load(p); sp = d["sp"][::-1]          # "fixed" the order again: mm bug
```

```python
# case_store.py — only this module knows the format
def save_case(path, case: Case) -> None: ...
def load_case(path) -> Case: ...   # Case(img: float32, mask, spacing_rc_mm)
```

Stage scripts stay; format knowledge leaves them.

### Overexposure: generate

```python
out = model.generate(ids, attention_mask=am, pad_token_id=tok.eos_token_id,
                     eos_token_id=tok.eos_token_id, max_new_tokens=512,
                     do_sample=False, use_cache=True)
```

`Generator(model, tok).complete(messages, max_new_tokens=512)`: mask, pad/eos, cache and template are
derived from tokenizer and model; sampling is an optional `SamplingParams`.

### Internal list exposed

```python
conv.messages.append({"role": "user", "content": [
    {"type": "tool_result", "tool_use_id": tu.id, "content": out}]})
if count_tokens(conv.messages) > LIMIT:
    conv.messages = conv.messages[:1] + [summarize(conv.messages[1:-6])] + conv.messages[-6:]
```

```python
class Conversation:
    """Message history of one agent run. Keeps tool_use/tool_result pairs intact."""
    def add_user_text(self, text: str) -> None: ...
    def add_tool_results(self, results: list[ToolResult]) -> None: ...  # merged into one user turn
    def compact(self, token_budget: int) -> None: ...  # never splits pairs, keeps system verbatim
    def to_api(self) -> list[dict]: ...
```

One class knows the Messages API format and history invariants. A getter/setter on `messages` would
not have helped.

### Taking it too far (5.9)

- Bad: `train(model, data)` hides lr, batch size, epochs. They are the experiment; expose them.
- Good: expose lr, schedule, epochs; derive num_workers, pin_memory, grad accumulation from target
  batch and memory.
- False abstraction: `standardize(raw)` silently resamples to 0.3 mm while downstream computes area
  in original geometry. Return an object with `image`, `spacing_mm`, `to_original(mask)`.

## General-purpose (6)

### Metrics for one case

```python
def dice_liver_val(preds, batch):
    p = preds.argmax(1) == 3; t = batch["seg"] == 3
    return 2 * (p & t).sum() / (p.sum() + t.sum())
def dice_kidney_val(preds, batch): ...   # copy with another class id
```

```python
def dice(pred: Tensor, target: Tensor, num_classes: int,
         ignore_index: int | None = None, eps: float = 1e-6) -> Tensor:
    """Per-class Dice, shape (num_classes,). Class absent in both pred and target scores 1."""
# caller: dice(logits.argmax(1), batch["seg"], num_classes=4)[LIVER]
```

Batch keys, class ids and split stay with the caller; 0/0 handling is hidden inside.

### "Generality" via flags

```python
def run_model(x, train=False, use_tta=False, export=False, fp16=False, return_feats=False): ...
```

Five special cases in one signature, combinations untested. One `forward(x) -> Output` plus
upper-level functions: `predict_with_tta(model, x)`, `export_onnx(model)`.

### Too specific vs too general tools

- Too specific: `add_import`, `rename_symbol`, `fix_indentation`: every edit type is a new tool.
- Too general: only `bash`, edits via sed and heredocs: escaping breaks, the model writes glue
  (the per-character API of agents).
- About right: `edit(path, old, new, replace_all=False)`.

## Layers (7)

### Pass-through model client

```python
class Agent:
    def send(self, messages, tools): return self.client.send(messages, tools)
class LLMClient:
    def send(self, messages, tools): return self.api.send(messages, tools)
```

One `ModelClient.turn(conv) -> AssistantTurn`: retries on 429/529, token accounting, prompt caching,
parsing content blocks into `text` and `tool_calls`. The agent loop works in "conversation turns".

### Wrappers leaked into the checkpoint

```python
model = DDP(EMAWrapper(CompileWrapper(Net())))
torch.save(model.state_dict(), "ckpt.pt")      # keys "module._orig_mod.net.conv1..."
net.load_state_dict({k.replace("module.", "").replace("_orig_mod.", ""): v ...})
```

`save_checkpoint(path, unwrap(model), ema=ema.state_dict(), meta=...)` with a symmetric load; EMA is a
separate object beside the model, not a `forward` wrapper.

### Pass-through variable

```python
def run(cfg, tok, device, logger): train_epoch(model, dl, cfg, tok, device, logger)
def train_epoch(model, dl, cfg, tok, device, logger):
    for b in dl: step(model, b, cfg, tok, device, logger)   # cfg needed only for cfg.optim.clip
```

```python
@dataclass(frozen=True)
class RunContext: device: torch.device; logger: Logger; run_dir: Path
class Trainer:
    def __init__(self, model, optim_cfg: OptimConfig, ctx: RunContext): ...
    def fit(self, dl): ...
```

Each module gets its sub-config; only `main` sees the full `cfg`.

### Legitimate duplication: dispatcher

```python
def dispatch(call: ToolCall, ctx: RunContext) -> ToolResult:
    tool = REGISTRY.get(call.name)
    if tool is None: return ToolResult.error(f"unknown tool {call.name}")
    return tool.run(validate(call.args, tool.schema), ctx)
```

It selects an implementation and validates arguments: added value. `Read`, `Edit`, `Bash` sharing a
signature are implementations of one interface.

## Pull complexity down (8)

```python
enc = tok(texts, truncation=True, max_length=512, padding="max_length", return_tensors="pt")
labels = enc["input_ids"].clone()
labels[enc["attention_mask"] == 0] = -100
labels[:, :prompt_len] = -100              # and prompt_len must be computed somewhere
```

```python
class SFTCollator:
    """(prompt, answer) pairs -> padded batch; loss only on answer tokens; pads to longest."""
    def __init__(self, tok, max_tokens: int | None = None): ...
    def __call__(self, pairs) -> dict[str, Tensor]: ...
```

Knobs vs computed values:

```python
warmup = int(0.03 * total_steps)                               # a fraction doesn't go stale
max_len = min(tok.model_max_length, int(np.percentile(lengths, 99)))
limit = context_window(model) - max_output_tokens - margin     # instead of compact_at=150_000
log.info("derived: warmup=%d max_len=%d", warmup, max_len)     # log what was derived
```

## Together / apart (9)

- Special-General Mixture: `if task == "us_seg": ...` inside `train_epoch` → `train_epoch(model,
  loader, opt, step_fn)`, specifics in the task module's `step_fn`.
- Conjoined: `_forward`, `_loss`, `_backward`, `_maybe_step` passing `aux` and `n_tokens` around →
  one 50-line `train_step` with block-header comments. A legitimate extraction is `dice(...)`,
  understandable without its parent.
- Logging wrapper `log_val_epoch(epoch, dice)` whose body is `wandb.log(...)`, called once → inline.
- Repetition: four eval scripts with the same `eval(); no_grad(); cat; threshold` → missing
  `predict(model, loader) -> Predictions`.
- Agent loop like undo: mechanism (model → tool_use → dispatch → tool_result) knows nothing about
  tools; specifics in tool objects; policy (stop, compaction, step limit) on top.

## Errors (10)

### Define away

```python
Path(ckpt_tmp).unlink(missing_ok=True)       # instead of try/except FileNotFoundError: pass
metrics.pop("aux_loss", None)
os.makedirs(run_dir, exist_ok=True)

def read_file(path, offset=0, limit=2000) -> str:
    """Lines [offset, offset+limit) that exist; empty string if offset is past EOF. 0-based."""
```

`F.cross_entropy(..., ignore_index=-100)`: padding stops being a special case.

### Where defining away is wrong

```python
def edit(path, old, new, replace_all=False):
    text = Path(path).read_text(); n = text.count(old)
    if n == 0: raise ToolError(f"old_string not found in {path}")
    if n > 1 and not replace_all:
        lines = [i + 1 for i, l in enumerate(text.splitlines()) if old in l]
        raise ToolError(f"old_string matches {n} places (lines {lines}); "
                        "add surrounding context or set replace_all")
```

Replacing the first match would "remove the error" and edit the wrong place. The ambiguity is
information the model needs; return it actionably.

### Masking in medical data

```python
df["label"] = df["label"].fillna(0)                  # unknown -> "healthy"
spacing = getattr(ds, "PixelSpacing", [1.0, 1.0])    # invented millimetres
try: img = load(p)
except Exception: continue                            # frames of one scanner silently dropped
```

```python
missing = df["label"].isna()
log.warning("dropping %d/%d studies with unknown label", missing.sum(), len(df))
df = df[~missing]
if not hasattr(ds, "PixelSpacing"):
    raise DataError(f"{p}: no PixelSpacing, mm metrics impossible")
```

The information changes what results mean (prevalence, mm metrics), so it is exposed.

### Aggregation in a tool-use loop

```python
class ToolError(Exception): """Aborts this tool call; message goes to the model."""

for block in tool_uses:
    try:
        out, is_err = TOOLS[block.name].run(block.input), False
    except (ToolError, OSError, subprocess.TimeoutExpired) as e:
        out, is_err = f"{type(e).__name__}: {e}", True
    results.append(ToolResult(block.id, out, is_err))
# AuthenticationError and bugs in the loop are not caught: they are fatal
```

The throw site writes the message; the handler only knows the `tool_result` format.

### Error promotion and just crash

- A rank failure (NCCL timeout, one OOM on a long batch) → job dies and resumes from checkpoint via
  the same path as preemption. Resume runs often, so it works. Broken samples are not handled this
  way: filter them when building the dataset.
- Shape mismatch, label outside `range(num_classes)`, a patient_id in both train and test are bugs:
  assert at run start. Catching `OutOfMemoryError` mid-training and continuing is pointless.

### Remove the special case

`attend(q, k, v, mask=None)` with two branches → the collator always returns a mask. In an agent,
`history` is always a list and `system` always a string, possibly empty.

## Design it twice (11)

Eval harness:
- A: one script per dataset. Fast; metrics drift apart.
- B: `evaluate(predict_fn, dataset, metrics) -> dict`. One metric codebase; a new metric = GPU again.
- C: `predict(model, split) -> predictions.parquet`, then `score(predictions, labels, metrics)`.
  Metrics without GPU, predictions as an artifact for bootstrap and the paper; the file format
  becomes a contract.

Agent context compaction: drop old turns / summarize with the model / clear old tool_result bodies.
Compare information loss, cost, pair integrity; often a hybrid wins.

## Comments (12–16)

```python
# boxes: float32 [N, 4], (x1, y1, x2, y2) in pixels of the resized 512x512 input; N may be 0.
# mask: bool [B, H, W], True = lesion. Unannotated frames are filtered in UltrasoundDataset.
```

```python
class UltrasoundFrames(Dataset):
    """B-mode thyroid ultrasound, one item per annotated frame.

    Item: image float32 [1, H, W] in [0, 1], letterbox to 512; mask uint8 [H, W], 1 = nodule;
    spacing_mm (row_mm, col_mm) of the resized image; patient_id — all frames of a patient
    are in one split. Frames without PixelSpacing raise DataError at construction.
    """
```

Leave out cache layout and the DICOM library (implementation contaminates interface).

```python
# Gradients are summed over grad_accum micro-batches; dividing keeps the effective lr
# independent of grad_accum.
loss = loss / grad_accum
```

```python
# Left padding: batched generate() on a decoder-only model appends tokens after the last
# position; with right padding they follow pad tokens. Training pads right on purpose.
tok.padding_side = "left"
```

Contract first for a metric:

```python
def dice_score(probs: Tensor, mask: Tensor, threshold: float = 0.5) -> Tensor:
    """Binary Dice per image, averaged over the batch.

    probs: (B, 1, H, W) sigmoid outputs; mask: (B, 1, H, W) in {0, 1}, 1 = lesion.
    Empty mask and empty prediction score 1.0. Returns a 0-dim tensor, no .item().
    """
```

Writing the contract forces decisions on positive class, averaging and 0/0. If the docstring grows
(multi-class, micro/macro, weights), that is Hard to Describe: split.

Cross-module: at `LABELS = [...]` list the places to update (head num_classes, loss weights,
metrics, paper table).

A tool description is an interface comment:

```python
{"name": "read_file",
 "description": "Read a UTF-8 text file. Returns up to `limit` lines from 0-based line "
                "`offset`, each prefixed with its 1-based line number. Offset past EOF "
                "returns an empty string. Binary files return an error."}
```

## Names (14)

- Tokens vs characters (the `block` bug): `if len(prompt) > max_len: prompt = prompt[-max_len:]` →
  `max_prompt_tokens`, `truncate_tokens(prompt, n, side="left")`.
- `idx`: dataset index, `frame_idx` within a clip, `patient_id` — three names, never one.
- Mask polarity: HF `attention_mask` 1 = attend; `nn.MultiheadAttention` `key_padding_mask` True =
  ignore; boolean `attn_mask` in `F.scaled_dot_product_attention` True = participates. Use
  predicates `is_pad`, `keep`, `is_lesion`; convert to PyTorch APIs in one place.
- `logits` before activation, `probs` after, `pred_*` after threshold/argmax — always.
- `state` holding history, token count and a compaction flag → `messages`, `input_tokens_used`,
  `needs_compaction()`.
- `compact = True` → `compaction_enabled`.
- `crop(img, thyroid_bbox)` in shared transforms → `bbox`.

## Consistency and obviousness (17–18)

Layout:

```python
# data/__init__.py — the one place for the convention
# Every tensor leaving a Dataset: float32, (C, H, W), values in [0, 1]. Batches are NCHW.
# Models and eval never permute. Horizontal flip is dims=[-1] everywhere.
def assert_nchw(x: Tensor, channels: int) -> None:
    assert x.ndim == 4 and x.shape[1] == channels, f"expected NCHW, got {tuple(x.shape)}"
```

Otherwise `torch.flip(x, dims=[2])` in TTA flips H or W depending on where the tensor came from.

Generic container from collate:

```python
for a, b, c, d, e in loader: ...          # bad

@dataclass
class Batch:
    images: Tensor          # (B, 1, H, W) float32
    masks: Tensor           # (B, 1, H, W) {0, 1}, 1 = lesion
    patient_ids: list[str]  # for patient-level metrics, never fed to the model
    spacing_mm: Tensor      # (B, 2) row/col
    def to(self, device) -> "Batch": ...
    def pin_memory(self) -> "Batch": ...  # DataLoader(pin_memory=True) calls it
```

Callback as event handler: `FreezeEncoderUntil(500)` with a docstring saying when it fires and what it
changes, plus a comment where it is registered. Several interacting callbacks: write an explicit loop.

Broken expectations: `evaluate()` leaves the model in `eval()`; the next epoch runs without dropout.
Meet the expectation: save `model.training` and restore it in `finally`.

Split names `train`/`val`/`test` everywhere; never `dev`, or nobody knows whether it is val or test.

## Inheritance (19)

```python
class DistillTrainer(BaseTrainer):
    def train_step(self, batch):                 # copied the parent's step, forgot scaler.update()
        ...
```

`Trainer(opt, loss_fn)` owns the AMP step protocol; variants differ only in the loss function
(`distill_loss(student, teacher, w)`). A new variant can't break the step.

Pattern over-application: Registry + Factory + `build_from_cfg` for a model with one implementation.

Bug fix via a failing test:

```python
def test_dice_empty_mask_and_empty_pred_is_one():
    z = torch.zeros(1, 1, 8, 8)
    assert dice_score(z, z).item() == 1.0     # must fail before the fix
```

## Performance (20)

Host–device sync:

```python
running = torch.zeros((), device=dev)
for step, batch in enumerate(loader, 1):
    loss = model(**batch).loss
    loss.backward(); opt.step(); opt.zero_grad(set_to_none=True)
    running += loss.detach()                   # instead of loss.item() every step
    if step % log_every == 0:
        avg = (running / log_every).item(); running.zero_()
        if not math.isfinite(avg): raise RuntimeError(f"non-finite loss by step {step}")
```

No more complex than the original, so naturally efficient. Cost: NaN detected up to `log_every` steps
late. Verify the gain with a profiler.

Measure first: time `next(it)` separately from the step with `torch.cuda.synchronize()`; if data isn't
the bottleneck, leave the loader alone; then `torch.profiler`, and the same measurement after the
change as baseline.

Fundamental fix: tokenize and apply the chat template once in `ds.map(..., batched=True)` with cache
key `{tokenizer}_{template_ver}_{max_len}`; `__getitem__` becomes a lookup.

Critical path with one check:

```python
class KVCache:
    def append(self, k: Tensor, v: Tensor) -> None:
        """Hot path: once per layer per decoded token; k, v are (B, H, 1, D)."""
        if self._free == 0:          # one check: unallocated, full, window shift
            self._slow_path()
        p = self._pos
        self.k[:, :, p:p + 1] = k; self.v[:, :, p:p + 1] = v
        self._pos += 1; self._free -= 1
```

Agent: every turn resends the history; keep the stable prefix (system, tools) unchanged between
turns so prompt caching works.
