# SJSU Scraper

Crawls **sjsu.edu** pages and saves main content as `.txt` files for RAG/vector store ingestion.

## Layout

```
tools/scraper/
├── scrape_sjsu.py      # Main script
├── requirements.txt    # Python deps
├── README.md           # This file
├── input/              # URL list files (one URL per line)
│   └── urls_sjsu_sample.txt
└── output/             # Scraped .txt files (default; gitignored)
    └── _scraped_urls.txt   # Resume log (created on first run)
```

## Setup

```bash
pip install -r tools/scraper/requirements.txt
```

## Usage

From project root:

```bash
# Default: reads input/urls_sjsu_sample.txt, writes to output/
python tools/scraper/scrape_sjsu.py tools/scraper/input/urls_sjsu_sample.txt

# Or from inside tools/scraper/
cd tools/scraper
python scrape_sjsu.py input/urls_sjsu_sample.txt
```

Output goes to `tools/scraper/output/` by default. Use `-o` to override.

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `url_file` | (required) | Path to text file with one SJSU URL per line |
| `-o, --output-dir` | `output/` (next to script) | Where to write .txt files |
| `--max-depth` | 1 | Crawl depth (0 = seeds only) |
| `--max-pages` | 200 | Stop after N pages |
| `--max-links-per-page` | 80 | Max links to queue per page |
| `--delay` | 1.0 | Seconds between requests |
| `--no-robots` | off | Ignore robots.txt |
| `--no-content-dedup` | off | Do not skip duplicate content |
| `--no-resume` | off | Do not skip already-scraped URLs |

## Resume

On rerun, URLs listed in `output/_scraped_urls.txt` are skipped. Use `--no-resume` to crawl from scratch.

## Input format

Plain text, one URL per line. Only `sjsu.edu` and `www.sjsu.edu`. Lines starting with `#` are ignored.

## Output format

Each `.txt` file:

```
Source: https://...
Title: Page Title
Type: HTML

Body text...
```

Use RAG API `/embed` or `/embed-upload` to ingest into your vector store.
