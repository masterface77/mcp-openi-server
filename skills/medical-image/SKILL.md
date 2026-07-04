---
name: medical-image
description: Find a medical, clinical, dental or radiological illustrative image from Open-i (NLM) and return it as a Markdown image link, ready to paste or embed into a note. Use whenever the user asks for a medical/dental picture, figure, diagram, X-ray, histology slide or clinical photo — e.g. "acha uma imagem de cárie", "preciso de uma foto de incisão oral pro resumo", "embed an X-ray of a mandible fracture", "ilustra esse tópico com uma figura". Also use proactively when writing exam-study notes that would benefit from an illustrative figure.
---

# Find & embed a medical image (Open-i)

You have the `search_openi_images` MCP tool available (from the `openi` plugin). Use it to fetch a real, citable biomedical image and hand it back in a form the user can paste or embed immediately.

## Steps

1. **Translate the topic to English.** Open-i is English-only. Translate any Portuguese term before searching:
   - "cárie" → `dental caries` · "incisão oral" → `oral incision` · "radiografia panorâmica" → `panoramic radiograph` · "gengivite" → `gingivitis` · "anatomia do periodonto" → `periodontal anatomy` · "odontolegista" → `forensic dentistry`.

2. **Pick the right image-type filter (`it`)** based on what the user wants:
   - Diagram / chart / illustration → `it="g"`
   - Clinical or gross photo → `it="ph"`
   - X-ray → `it="x"` · CT → `it="c"` · MRI → `it="m"` · ultrasound → `it="u"` · histology/microscopy → `it="mc"`
   - If unsure, omit `it` and let Open-i return everything, then choose the most relevant result yourself.
   - For dentistry topics you may add `sp="d"`.

3. **Call `search_openi_images`** with a small window first (`m=1, n=6`). Read the `title` and `summary` of each result and choose the one that genuinely matches the topic — don't just grab the first hit. Prefer results whose caption clearly depicts the concept.

4. **Return it as Markdown**, always with attribution:
   ```markdown
   ![<short description>](<image_url>)
   *<caption / summary>* — [Fonte](<article_url>)
   ```
   If the user asked for several, return 2–3 options and say which you'd pick and why.

5. **If no good match:** broaden the query (drop adjectives, use the core anatomical/clinical term), remove the `it`/`sp` filters, and try once more before telling the user nothing fit.

## When working inside a notes vault (e.g. Obsidian)

If the user is building study notes and asks you to *place* the image in the note (not just show it):

- Insert the Markdown image at the most relevant point in the note — typically right under the heading of the section it illustrates, or inside the relevant callout — not dumped at the top or bottom.
- Keep the caption + `[Fonte](...)` link so the note stays citable.
- If the vault is used **offline** (synced to a phone/tablet) and the user wants images to work without internet, offer to **download** the image into the vault's assets folder and embed it locally instead of hot-linking. Ask before downloading many files.
- One well-chosen figure per concept beats several — don't clutter the note.

## Reminder

Every image comes from a real PubMed Central / NLM article. Always keep the `[Fonte]` link so the user can verify and cite it. Never invent an image URL — only use URLs returned by the tool.
