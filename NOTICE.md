# Notices and attribution

## Project code, manual, scenarios and fixtures

The source code, the house manual, the evaluation scenarios and the reservation
fixtures in this repository are released under the MIT licence in `LICENSE`.

Lahore Heights Apartments is a fictional property. Every property, guest,
host, reservation, price, phone number and other number in the house manual,
scenarios and fixtures is fictional. The house manual and the fictional
content were written with Claude (Anthropic).

## City guide: English Wikivoyage "Lahore"

`data/local_guide/wikivoyage_lahore.txt` is a plain-text snapshot of the English
Wikivoyage article **"Lahore"**:

- Page: https://en.wikivoyage.org/wiki/Lahore
- Permanent link: https://en.wikivoyage.org/w/index.php?title=Lahore&oldid=5410746
- Revision id: **5410746**
- Revision timestamp: **2026-10-30T16:54:26Z**
- Retrieved: **2026-11-10** (2026-11-10T08:19:02Z)
- Licence: **Creative Commons Attribution-ShareAlike 4.0 International**
  (CC BY-SA 4.0), https://creativecommons.org/licenses/by-sa/4.0/

The text is attributed to the Wikivoyage contributors, whose names are listed
in the page history at https://en.wikivoyage.org/w/index.php?title=Lahore&action=history.
Changes made for this project: the API extract was saved as plain text and
split into chunks for retrieval.

**This file keeps its own CC BY-SA 4.0 licence and is not covered by the MIT
licence.** Adaptations of it must stay under CC BY-SA 4.0. The snapshot is used
only as a public city guide for the fictional property and is not affiliated
with or endorsed by Wikivoyage or the Wikimedia Foundation.

## Third-party models

- **BAAI/bge-small-en-v1.5** (embedding model) — MIT licence.
- **Qwen2.5-3B** (chat model, run through Ollama) — the licence file on the
  Ollama model page is titled **"Qwen RESEARCH LICENSE AGREEMENT"**; the model
  card notes that the 3B and 72B models are under the Qwen licence. See
  https://ollama.com/library/qwen2.5:3b.

The model files are not redistributed in this repository. They are downloaded
separately by the user and remain under their own licences.

## Libraries

The Python libraries used here are covered by their own licences as declared in
their package metadata, including: FastAPI (MIT), Uvicorn (BSD-3-Clause),
Faker (MIT), pytest (MIT), HTTPX (BSD-3-Clause), PyTorch (BSD-3-Clause),
sentence-transformers (Apache-2.0), ChromaDB (Apache-2.0), rank-bm25
(Apache-2.0), LangChain and LangGraph (MIT), and Gradio (Apache-2.0).
