# PRISM Prompt Versioning

Prompts are stored as plain text files with `{variable}` placeholders.

## v1/ — Initial Prompts

- `stage1_extraction.txt` — Per-item content extraction (semantic, pragmatic, tonal, structural layers)
- `stage2_synthesis.txt` — Cross-corpus synthesis (trajectory, absences, pain coherence, stress, sophistication)
- `stage3_person.txt` — Person-level analysis (buying readiness, messaging resonance, influence mapping)
- `stage4_scoring.txt` — Final synthesis & scoring (why-now, confidence, play recommendation)
- `activation_angle.txt` — Per-contact outreach angle generation

## Versioning Rules

- Never edit v1 prompts in place after initial release
- Create v2/ directory for iterations
- Analysis records store the prompt version used
- Compare outputs across versions during iteration
