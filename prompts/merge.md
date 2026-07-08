# Merge pass — combine chunked extractions

The document was too large for one pass, so it was split into chunks and each
chunk was extracted separately. Below is a JSON array of those per-chunk
extractions. Merge them into ONE extraction with exactly the same shape as the
individual entries (title, thesis, audience, concepts, narrative_order,
open_questions).

Rules:
- Deduplicate concepts that appear in multiple chunks; merge their
  explanations, keeping the best supporting_detail.
- Choose the strongest overall thesis; chunks from the middle of a document
  often mistake a section's point for the whole document's.
- Rebuild narrative_order across the merged concept list — do not just
  concatenate the per-chunk orders.
- Keep 4–10 concepts total. Prefer fewer, deeper.
- Never invent facts not present in the extractions.

Return only the merged JSON object.

Per-chunk extractions follow:

{extractions}
