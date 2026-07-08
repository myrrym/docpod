# Stage 1 — Extract & structure

You are preparing source material for a podcast episode. Read the document below and
extract its substance into structured JSON. Do not write the episode — that is a later
stage. Your job is fidelity and structure.

Return JSON with this shape:

```json
{
  "title": "the document's own title, or a faithful one you infer",
  "thesis": "the single central claim or purpose, one sentence",
  "audience": "who this document is written for",
  "concepts": [
    {
      "name": "short concept name",
      "explanation": "2-4 sentence faithful explanation in plain language",
      "why_it_matters": "one sentence connecting it to the thesis",
      "supporting_detail": "the most compelling example, number, or quote from the text"
    }
  ],
  "narrative_order": ["concept names in the order a listener should hear them"],
  "open_questions": ["genuine tensions or unknowns the document raises, if any"]
}
```

Rules:
- Extract 4–10 concepts depending on the document's density. Prefer fewer, deeper.
- Stay faithful: never invent facts, numbers, or quotes not present in the document.
- Plain language, but do not dumb down — preserve precise terms and define them.
- `narrative_order` may differ from document order if a different sequence explains better.

Document follows:

{document}
