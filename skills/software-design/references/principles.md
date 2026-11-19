# APOSD by chapter: nuances, author caveats, anchors

Paraphrase of the book (1st ed., 2018). [ML] marks a transfer to ML/agent code.

Contents: 1 Intro · 2 Complexity · 3 Strategic · 4 Deep modules · 5 Hiding · 6 General-purpose ·
7 Layers · 8 Pull down · 9 Together/apart · 10 Errors · 11 Design twice · 12 Why comments ·
13 What to comment · 14 Names · 15 Comments first · 16 Modifying code · 17 Consistency ·
18 Obvious code · 19 Trends · 20 Performance · 21 Conclusion

## 1. Introduction

- Two weapons: eliminate complexity (fewer special cases, uniformity) and encapsulate it (modules).
- Design is continuous; the first design is rarely best. Waterfall fails: consequences are invisible
  until implementation, then problems get patched over.
- Best use of the book is code review: others' problems are easier to see. A red flag means stop and
  look for an alternative; try several.
- Moderation: any idea taken to the extreme is bad. Respect the "Taking it too far" sections.
- Module = anything with interface and implementation. [ML] `Dataset`, `nn.Module`, CLI script,
  checkpoint format, tool JSON schema.

## 2. The Nature of Complexity

- Complexity depends on the task: the same code is simple for a frequent task, awful for a rare one.
- bannerBg: a shared variable didn't reduce the number of dependencies but made them visible and
  checkable. The highlight color set by hand as "darker than banner" stayed an unknown unknown.
- Cognitive load sources: big APIs, globals, inconsistency, duties pushed to callers (malloc/free).
- Obscurity: generic names (`time`), missing units, unstated links (a new error status needs a row
  in a message table), one name for two meanings.
- Needing extensive documentation is a design red flag; the cure for obscurity is simpler design,
  comments come second.

## 3. Working Code Isn't Enough

- Tactical path: each compromise is reasonable alone; patches breed patches; once code is a mess,
  cleanup takes months, so tactics continue. Hard to leave this path.
- Tactical tornado: ships features fastest and leaves wreckage; the real heroes clean up after them
  and look slower.
- Proactive investment: a couple of alternatives per new class; imagine future changes and check they
  would be easy (don't implement them); documentation. Reactive: fix design problems, don't patch
  around them.
- 10–20%: first projects that much slower, within months at least that much faster. Fig. 3.1 is
  qualitative; nobody measured the curves.
- Startups: "we'll get rich and hire people to clean up" fails; payback comes fast; bad code repels
  strong engineers. Facebook ("Move fast and break things" → "Move fast with solid infrastructure")
  vs Google and VMware. Mild conclusion: success is possible either way.
- Slippery slope: "clean up after the deadline" — another deadline follows.
- [ML] Tactical inside a throwaway experiment, strategic at its boundaries. Before refactoring code
  that produced paper numbers: tag the run, add a golden test on the metrics.

## 4. Modules Should Be Deep

- Formal interface (signatures, types) vs informal (behavior, call order, side effects). The informal
  part is usually bigger and lives only in comments. If you must know X to use the module, X is part
  of its interface.
- Abstraction omits unimportant detail. Two errors: extra detail (load), omitted important detail
  (false abstraction, obscurity).
- Shallow test: correct documentation longer than the code.
- Garbage collector: depth with no interface; the feature shrinks the system interface (no free).
- File system hides block allocation, but flush rules must be visible: databases need them.
- Java streams: buffering is opt-in. "Choice is good," but optimize the interface for the common case
  and offer choice through a separate mechanism.
- Against "classes should be small" and "split methods over N lines".
- Anchors: Unix I/O (5 calls), balanced tree, `addNullValueForAttribute`.

## 5. Information Hiding (and Leakage)

- Hide data structures and algorithms, low-level parameters, high-level assumptions.
- Partial hiding: a feature few need, behind separate methods, is almost hidden.
- private ≠ hiding: a field with getter and setter is exposed. [ML] `_x` + `@property` + setter hide
  nothing. Test: can the module change representation without touching callers?
- Leakage cure: merge small tightly linked classes; or extract the knowledge into a new class only if
  it gets a simple interface, otherwise back-door leakage becomes leakage through the interface.
- HTTP: students hid parameter source and URL decoding well but exposed the internal Map
  (`getParams`). One module can be good on one decision and leak another: check each decision.
- `getIntParameter(name)`: the module owns conversion and the error; deeper than returning a string.
- Defaults: a caller supplying a value the module can derive (HTTP version) is leakage.
- Inside a class: minimize the places each field is used.
- Temporal decomposition is fine when stages use entirely different knowledge.

## 6. General-Purpose Modules are Deeper

- Text class: `backspace(Cursor)`, `deleteSelection(Selection)` → `insert(Position, String)`,
  `delete(Position, Position)`, `changePosition(Position, int)`.
- UI calls got slightly longer but clearer: you see which characters are deleted.
- Backspace was a false abstraction: hid what the UI developer needed to know.
- A method for one use, called from one place: caller knowledge leaked into the callee.
- Upper-layer types in a lower module (`Cursor` instead of `Position`) are a sign.

## 7. Different Layer, Different Abstraction

- TextDocument with 13 of 15 pass-through methods; fixed by redistributing responsibility.
- Pass-through method cures: expose the lower class, redistribute functionality, merge classes.
- Interface ≠ representation: line storage is fine, a line API forced the UI to split and join lines.
- Pass-through variable (`cert` through main → m1 → m2 → m3): shared object, global (two instances in
  one process impossible, tests suffer), context object (author's pick, with caveats: global-like
  drawbacks, grab-bag risk, prefer immutability).
- Every design element must remove more complexity than it adds.

## 8. Pull Complexity Downwards

- Retry interval computed from measured response time beats a parameter.
- Legitimate parameter: low-level infrastructure lacks domain policy (request priority), the user has it.
- Too far: pull down only when all three hold: close to the module's functionality, simplifies many
  callers, simplifies the interface. Backspace in the text class fails them.
- [ML] Log computed defaults, or the run is not reproducible.

## 9. Better Together or Better Apart?

- Cost of splitting: more components and interfaces, management code, separation (related code in
  different files), duplication.
- Block cache uses hash table but not vice versa: one-way link, keep apart.
- goto to shared cleanup is fine. [ML] try/finally, context manager, ExitStack.
- Cursor and selection: intuitively linked, merging was worse; the answer was a shared Position type.
- NetworkErrorLogger: one-line methods each called once → log in place.
- Undo: History (mechanism) + Actions in modules that understand them (specifics) + fences in UI
  (policy). Special code of one mechanism may live inside the general code of another.
- Splitting into two caller-visible methods pays off if most callers need one of them and both are
  more general; bad if callers call all of them in order passing state.

## 10. Define Errors Out of Existence

- Exception = any unusual condition changing flow, including `None`, `-1`.
- Why hard: continue or roll back; secondary exceptions; rarely executed code doesn't work. Yuan et
  al., OSDI 2014: most catastrophic failures in distributed systems come from bad error handling.
- "Errors catch bugs": an error-ful API adds complexity and hence other bugs. About balance, not a ban
  on checks.
- Tcl `unset` throwing on a missing variable: the author calls it one of his biggest design mistakes.
- Deleting an open file: Unix removes two errors (deleter's and readers').
- NFS hang-and-retry: controversial, alternatives worse when upper levels have no sensible reaction.
- Aggregation pattern: an exception aborts the current request, the loop continues; fatal ones apart.
- Error promotion (RAMCloud): corrupted object → server crash → common recovery, which then runs
  often and therefore works. Only for rare errors.
- Catching OOM is pointless: the handler needs memory too.
- A network module swallowing all errors made robust apps impossible. Expose what matters.

## 11. Design It Twice

- Variants radically different and rough: a few key methods.
- Interface criteria: ease for code above, simplicity, generality, efficient implementation. For
  implementation: simplicity and performance.
- Smart-people trap: first ideas used to suffice; problems grow and they stop working.
- An hour or two per class against days of implementation.

## 12. Why Write Comments? The Four Excuses

- "Self-documenting code" is a myth: code expresses only the signature. A read-the-code culture
  pushes toward shallow methods.
- "No time": typing code is ≤ ~10% of dev time; comments add about as much.
- "They go stale": keep near code, don't duplicate, catch in review.
- "All comments I've seen are useless": the most justified excuse; fixed by skill.
- Docs fix cognitive load and unknown unknowns, not change amplification.

## 13. Comments Should Describe Things that Aren't Obvious from the Code

- Repetition test: could someone write the comment from the adjacent line alone?
- Precision: units, inclusive bounds, meaning of null, who frees a resource, invariants, meaning of a
  missing entry. For variables use nouns: what it represents, not who changes it.
- Intuition: what the code tries to do; "how we get here".
- Class interface comment: the abstraction, what an instance represents, limits (threads). May show
  how methods are used together.
- IndexLookup: message format not in the interface; key comparison function yes; server crashes
  invisible to users, so not.
- Cross-module: where developers will surely look (at the Status enum, at the end of the list);
  otherwise designNotes plus links. The author calls designNotes an experiment.
- Commenting nearly every interface and field is easier than deciding each time.

## 14. Choosing Names

- Sprite: `block` meant a disk block in one place and a file block in another; the bug took six
  months. "Almost right" names are dangerous. Fix: `fileBlock` / `diskBlock`.
- Too specific is bad too: `delete(Range selection)` → `range`.
- Booleans are predicates (`cursorVisible`); sentinels named by meaning (`NOT_YET_VOTED`).
- The farther use is from declaration, the longer the name.
- Versus Go style: readers decide readability; short `n` is fine if it always means count. Reusing a
  short name for different things is not.

## 15. Write the Comments First

- Order: class comment → method signatures and interface comments → iterate → fields → bodies and
  implementation comments; a new method mid-way gets its comment first.
- Comments are a design tool and a canary: a long complete interface comment means a complex
  interface; one that lists the implementation means shallow.
- Hard to Describe works only on a complete comment: a short incomplete docstring fakes simplicity.
  Check completeness first, then judge depth.
- The time savings are the author's hypothesis from experience.

## 16. Modifying Existing Code

- Goal: the structure the system would have if the change had been known from the start. If the
  design isn't getting better, it is probably getting worse.
- Limits: 3 months of refactoring vs 2 hours under a hard deadline; breaking many teams. Still look
  for a nearly-as-clean option in days; agree to come back.
- Comments by the code (interface comment at the method body, not in .h); implementation comment in
  the narrowest scope; the farther from code, the more abstract.
- The reason for a change goes in code, not the commit log, or someone reverts it and the bug returns.
- Document each decision once; link elsewhere. A broken link is visible, a stale copy isn't. Link to
  external docs instead of copying.
- Check the diffs before committing.
- Fear of strategic changes is cured by unit tests (ch. 19).

## 17. Consistency

- Levels: names, style, interfaces with several implementations, patterns, invariants.
- Document; Enforce (checker that blocks commits; the CRLF script taught newcomers by itself); review
  (the author endorses picky reviews); When in Rome; don't change conventions.
- Before changing one: is there significant new information? is the gain worth updating every place?
  Only on two yeses, and completely.

## 18. Code Should Be Obvious

- Whitespace in parameter docs and between method blocks; first line of a block is its comment.
- Event-driven: the handler's interface comment says when and on which thread it runs.
- Generic containers: `Pair<Integer, Boolean>` → named structure.
- `List` declared, `ArrayList` allocated: the author prefers the reader to see the real type.
- `RaftClient` at the end of `main` starts threads: for strongly surprising behavior, duplicate the
  note at the point of use.

## 19. Software Trends

- Interface inheritance is leverage (more implementations, deeper interface). Implementation
  inheritance cuts duplication but creates parent–child dependencies; if unavoidable, the parent owns
  the state and children only read it.
- Agile matches incrementalism but risks tactics. "Minimal special mechanism now, generalize later"
  is only partly reasonable.
- Unit tests: Tcl rewritten to a byte-code compiler; the suite caught almost everything.
- TDD: focus on the next feature, no moment for design. Test first only for bug fixes, otherwise the
  test may not reproduce the bug.
- Getters/setters: lesser evil for exposed state; better not to expose.
- Judge any new paradigm by whether it reduces complexity in large systems.

## 20. Designing for Performance

- Middle ground between optimizing every statement and ignoring speed (death by a thousand cuts,
  5–10× too slow).
- Fundamental costs (2018): datacenter network 10–50 µs, WAN 10–100 ms, disk 5–10 ms, flash
  10–100 µs, allocation, cache misses. Learn them with micro-benchmarks.
- Hash table vs ordered map: if order isn't needed, take the faster one; it isn't more complex.
- Complexity for speed: small and hidden — OK; large or in the interface — start simple; clear
  evidence (RAMCloud kernel bypass) — do it up front.
- Simple code is usually faster: fewer special-case checks, deep classes do more per call.
- RAMCloud Buffer: one variable `extraAppendBytes`, zero in three special cases, gave one check on the
  critical path; ~20% less code, append twice as fast. Several critical paths: `totalLength` is kept
  for another frequent operation.
- [ML] Fundamental costs on an ML box: host–device sync (`.item()`, `bool(cuda_tensor)`), H2D/D2H
  copies, Python overhead per sample and per tiny kernel launch, cluster network storage, cross-node
  collectives, KV-cache bandwidth when decoding. For an agent: API round trips, tokens per request,
  stability of the cached prefix.

## 21. Conclusion

- The price is extra early work and a slowdown while learning. For throwaway code, skipping the
  advice is an honest choice.
- With experience good design costs little more than quick-and-dirty.
- [ML] With agents writing is nearly free while reading and review stay expensive: "design for
  reading" gets stronger, and strategic refactoring gets cheap when tests exist.
