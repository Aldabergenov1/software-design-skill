---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

we need a module for loading ultrasound DICOMs that training, the inference service and our labeling tool will all use. the data has frames without PixelSpacing, different photometric interpretations, sometimes a cine loop instead of a single frame. design the interface, no implementation yet
