---
type: llm
focus: trace
weight: 1
---

The review identifies that the embedding model name and/or the e5 'passage:'/'query:' prefixes are known separately by index building and retrieval (and answer.py strips the prefix), and proposes a single owner for the encoding convention stored with the index.
