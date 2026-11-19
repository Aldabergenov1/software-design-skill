---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

built a RAG over clinical guidelines, rag.py is three files glued together (index_build, retriever, answer). look at the design: what will hurt to change when we swap the embedding model or the chunk size, and what to fix first

Input files: rag.py
