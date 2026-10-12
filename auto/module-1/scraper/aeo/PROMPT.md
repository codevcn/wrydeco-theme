# Product Overview and FAQ authoring contract — version 1

Write AEO alongside the six existing SEO fields for this one assigned product. Use only the scraper MCP.
Read get_content_context again after writing visual analysis: its `aeo.input` contains the current compiler-issued facts and IDs.
Do not browse/search, access arbitrary files, claim another product, infer other products' specifications or mutate Shopify.

Priority: factual accuracy and evidence, precise product identity, meaningful pre-purchase intent, direct answers,
semantic coverage, natural language. Search intent here means likely buying questions inferred from the product;
never claim measured search popularity or external research.

Analyze the evidence, define the product entity, select answerable buying intents, write Overview and FAQs,
check facts and duplication, then save, validate, correct and finalize through the normal MCP lifecycle.
Do not expose private reasoning. Citations are evidence IDs only, not chain-of-thought.

## Evidence

Use source title/bullets/A+ text for factual claims, verified options for sizes/finishes and explicit choices,
and approved visual facts ONLY for shape, silhouette, geometric form and visible structure.
Only permitted gallery images may be inspected. Never infer color, finish, material/species, dimensions, scale,
capacity, manufacture, durability or performance from pixels. Styling props do not prove capacity or included accessories.
Color/finish options describe available finishes; they do not prove solid wood species or construction.
Preserve every supplied measurement and its axis/unit exactly. Do not estimate, convert, round or combine dimensions
from different variants. For variable products, describe available choices rather than presenting one choice as universal.
Do not invent handmade production, installation/hardware, care instructions, sustainability or warranty.
No trusted store policy is supplied in this version: omit shipping, lead time, returns and warranty topics.
Unknown claims must be omitted, even if they would make an interesting FAQ.
Do not turn a robust/stable base into a weighted foundation, or an organic shape into a single-tier
configuration. Cite approved visual facts for visible configuration; omit tier counts when none are supplied.
When listing available finishes or sizes, include all explicit verified choices or clearly say the list gives examples.
Keep answers informative and neutral; remove sales phrases such as "captivating modern art" or "elevating interiors".

## AEO draft

Add an `aeo` object to the complete content object passed to write_content_draft. Follow `aeo.schema` exactly:
- overview: `{text, evidence_ids}`. English, 80–140 words. First sentence identifies the product type,
  distinctive supported design/configuration and function. Explain the actual item concisely, not an advertisement.
- summary: `[{label, value, evidence_ids}]`, at most seven supported-only attributes. Allowed labels:
  Product type, Design, Configuration, Primary use, Placement, Dimensions, Visual style. Omit unknown attributes.
- faq: 3–8 items, each `{question, answer, evidence_ids}`. Question 3–30 words; answer 30–80 words.
  Aim for 5–6 useful questions if supported; 3–4 are valid. Never add filler to reach a count.
  Each answer starts with the direct answer, followed by useful context, and must make sense independently.

Every overview, summary value and FAQ answer must cite one or more relevant IDs from `aeo.input.facts`.
IDs are exact identifiers; never invent or cite an unread/other product's fact. A visual ID supports only an approved
visual phrase. A size/finish answer must cite the corresponding verified option IDs.
All draft strings are plain text, without HTML/Markdown/URLs; Python renders customer-facing HTML.
Do not supply `aeo_html` yourself. It is a derived output, not another editable source of truth.

Prefer product identity, size/fit, supported primary function, configuration and product differentiation.
Do not repeat one intent across several questions. Do not mechanically turn every Overview sentence into a question.
Avoid emotional filler, exaggerated adjectives, keyword stuffing, unsupported comparisons and vague pronouns.
Common questions can occur across products; do not invent differences between genuinely identical specifications.

After writing the complete SEO + AEO object, call validate_content_draft. Correct all field/evidence/uniqueness errors,
then finalize_content. Fewer than three supported FAQs requires releasing the task with a clear insufficient-evidence
reason; never silently omit required AEO. Finish with the existing WRYDECO_CONTENT_DONE marker and ASIN.
