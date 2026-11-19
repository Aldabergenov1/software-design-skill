---
type: llm
focus: trace
weight: 1
---

The response notices that 30 fps is also hard-coded in TemporalHead's time embedding (t / 30.0), not only in ClipDataset, and changes it.
