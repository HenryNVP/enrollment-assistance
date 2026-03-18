# Building the vector store from enrollment docs

How to ingest documents (e.g. `enrollment_docs/ms-ai`) into the RAG API so the enrollment assistant can search them.

## 1. Put documents in place

- Create **`enrollment_docs/ms-ai/`** (or any folder).
- Add your files: **.txt**, **.pdf**, **.md**, etc.  
  RAG supports: pdf, txt, md, csv, docx, xlsx, json, and others (see `backend/services/rag_api/app/utils/document_loader.py`).

Example:

```text
enrollment_docs/
└── ms-ai/
    ├── prerequisites.txt
    ├── program-requirements.md
    └── admissions.pdf
```

## 2. Chunk size (few / small documents)

The RAG API splits each file into chunks using **CHUNK_SIZE** and **CHUNK_OVERLAP** (env vars in `backend/services/rag_api`).

- **Default:** `CHUNK_SIZE=1500`, `CHUNK_OVERLAP=100` (good for long docs).
- **For only a few, short docs:** use **smaller chunks** so retrieval is more precise (e.g. one requirement or one section per chunk).

Suggested settings for a small MS-AI doc set:

```bash
# In backend/services/rag_api/.env or your run environment
CHUNK_SIZE=500
CHUNK_OVERLAP=50
```

Then **restart the RAG API** so it picks up the new values. All future ingests will use these until you change them again.

| Situation              | CHUNK_SIZE | CHUNK_OVERLAP |
|------------------------|------------|----------------|
| Few, short docs        | 400–600    | 40–60         |
| Mixed / long docs      | 1000–1500  | 80–100        |

## 3. Start the RAG API

From the project root (or your usual run):

```bash
# Example: run RAG API (adjust to your setup)
cd backend/services/rag_api && uvicorn main:app --port 8010
```

Ensure **JWT_SECRET** is set (e.g. in `backend/services/rag_api/.env`) so the ingest script can obtain a token.

## 4. Ingest the directory

From the **project root**:

```bash
# Install deps once
pip install httpx PyJWT

# Ingest default folder enrollment_docs/ms-ai
python tools/ingest_rag.py

# Or specify folder and RAG URL
python tools/ingest_rag.py --dir enrollment_docs/ms-ai --rag-url http://localhost:8010

# See what would be uploaded (no upload)
python tools/ingest_rag.py --dir enrollment_docs/ms-ai --dry-run
```

The script uploads each file to **POST /embed** with a stable **file_id** (from the file path). Re-running will **add duplicates** unless you first delete that file_id via **DELETE /documents**; to “replace” a doc, delete its file_id then ingest again.

## 5. Optional: replace before re-ingest

To refresh a document that’s already in the store:

1. Delete by file_id (e.g. `ms-ai-prerequisites`):
   ```bash
   curl -X DELETE "http://localhost:8010/documents" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '["ms-ai-prerequisites"]'
   ```
2. Run the ingest script again; the same file_id will be used for the new content.

## Summary

1. Put files in **enrollment_docs/ms-ai/** (or your chosen folder).
2. For few/small docs, set **CHUNK_SIZE=500** (and **CHUNK_OVERLAP=50**) in the RAG API env and restart.
3. Start the RAG API.
4. Run **`python tools/ingest_rag.py`** (optionally with `--dir` and `--rag-url`).

After that, the enrollment assistant’s **rag_search** tool (with no `file_id`) will search over these documents in the vector store.
