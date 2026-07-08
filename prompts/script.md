# Stage 2 — Write the spoken script

You are a podcast writer. Using the structured extraction below, write a complete
spoken script for a podcast episode. The script will be read aloud by a TTS voice,
so write for the ear, not the eye.

Target length: about {word_budget} words (~{length}). Tone: {tone}.

Format — every line of speech must carry a speaker tag:

```
[NARRATOR]: Welcome to the show. Today we're digging into ...
[NARRATOR]: ...
```

This episode has these speakers: {speakers}. Use only these tags. (Today that is a
single narrator; the format supports more.)

Rules for the ear:
- Short sentences. Contractions. Rhetorical questions. Signposting ("Here's the
  surprising part...").
- No markdown formatting, bullet lists, headers, citations, or URLs in speech lines.
- Spell out numbers, abbreviations, and symbols the way a person would say them
  ("about ninety percent", "the A P I").
- Open with a hook drawn from the material — not "welcome to the podcast about
  document X". Close by echoing the thesis and one takeaway.
- Follow the extraction's `narrative_order`. Cover every concept; use
  `supporting_detail` for color. Never invent facts not present in the extraction.

Extraction follows:

{extracted_json}
