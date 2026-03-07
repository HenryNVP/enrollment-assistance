# Tools

Utilities for the Enrollment Assistant project.

## Scraper (`scraper/`)

SJSU (sjsu.edu) web scraper: crawls from URL lists, extracts main content (HTML/PDF), writes `.txt` files for RAG.

- **Input:** URL list files in `tools/scraper/input/` (e.g. `urls_sjsu_sample.txt`)
- **Output:** `.txt` files in `tools/scraper/output/` (default)

See **[tools/scraper/README.md](scraper/README.md)** for setup, usage, and options.

```bash
pip install -r tools/scraper/requirements.txt
python tools/scraper/scrape_sjsu.py tools/scraper/input/urls_sjsu_sample.txt
```
