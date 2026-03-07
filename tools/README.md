# Tools

Utilities for the Enrollment Assistant project.

## RAG ingest (`ingest_rag.py`)

Upload a directory of documents (e.g. **enrollment_docs/ms-ai**) into the RAG API to build the vector store.

```bash
pip install httpx PyJWT
python tools/ingest_rag.py --dir enrollment_docs/ms-ai
```

Uses `RAG_API_URL` and `JWT_SECRET` (or RAG API `.env`). See **[docs/VECTOR_STORE_INGEST.md](../docs/VECTOR_STORE_INGEST.md)** for chunk size tips and full steps.

## Scraper (`scraper/`)

SJSU (sjsu.edu) web scraper: crawls from URL lists, extracts main content (HTML/PDF), writes `.txt` files for RAG.

- **Input:** URL list files in `tools/scraper/input/` (e.g. `urls_sjsu_sample.txt`)
- **Output:** `.txt` files in `tools/scraper/output/` (default)

See **[tools/scraper/README.md](scraper/README.md)** for setup, usage, and options.

```bash
pip install -r tools/scraper/requirements.txt
python tools/scraper/scrape_sjsu.py tools/scraper/input/urls_sjsu_sample.txt
```
