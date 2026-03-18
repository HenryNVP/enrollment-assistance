# Database and vector store in `mydb`

## Why you don’t see vector store tables

In `mydb` you see **user**, **session**, **thread**, and **checkpoint_*** tables, but not **`langchain_pg_collection`** or **`langchain_pg_embedding`**.

Those vector store tables are **created by the RAG API** the first time it **writes** to the store (e.g. when you ingest documents or the first similarity search that triggers table creation). So either:

1. **RAG has never been run against this DB** – e.g. RAG was using another database (or another machine), or  
2. **RAG was run but no document was ever ingested** – so the code path that creates the pgvector tables never ran.

### How to get vector store tables in `mydb`

1. **Confirm RAG uses `mydb`**  
   In `backend/services/rag_api/.env` you should have something like:
   ```bash
   DB_HOST=localhost
   POSTGRES_DB=mydb
   POSTGRES_USER=henry
   POSTGRES_PASSWORD=...
   ```

2. **Enable pgvector in `mydb`** (if not already):
   ```sql
   \c mydb
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

3. **Start the RAG API** (so it connects to `mydb`), then **ingest at least one document** (e.g. via the `/embed-upload` or ingest script).  
   After that, list tables again:
   ```sql
   \dt
   ```
   You should see **`langchain_pg_collection`** and **`langchain_pg_embedding`** in `public`.

4. **If you use a different DB for RAG**  
   Then the vector store lives in that other database. Set `POSTGRES_DB` (and `DB_HOST`/user/password) in RAG’s `.env` to the DB where you want the vector store, then run RAG and ingest there.

---

## How user and chat data are stored (tables you see)

All of these are in **the same database** the Agent API uses (here, `mydb`).

### 1. **`user`** (Agent API – SQLModel)

- **Purpose:** User accounts (auth).
- **Contents:** `id`, `email`, `hashed_password` (bcrypt), `created_at`.
- **Used for:** Register, login, and linking sessions to a user.

### 2. **`session`** (Agent API – SQLModel)

- **Purpose:** Chat sessions (one per conversation).
- **Contents:** `id` (session ID), `user_id` (→ `user.id`), `name`, `created_at`.
- **Used for:** Identifying the conversation; chat and history endpoints use `session.id`.

### 3. **`thread`** (Agent API – SQLModel)

- **Purpose:** Conversation threads (LangGraph thread ID).
- **Contents:** `id`, `created_at`.
- **Used for:** LangGraph thread identity (often 1:1 with a session in practice).

### 4. **`checkpoints`**, **`checkpoint_writes`**, **`checkpoint_blobs`** (LangGraph)

- **Purpose:** Persistence for the LangGraph agent (checkpointing).
- **Contents:** Serialized graph state for each step (including the **conversation messages**).
- **Used for:** Storing and loading chat history; `get_chat_history(session_id)` reads from this checkpoint store, not from a separate “message” table.

So: **user data** (account + session + thread) is in **`user`**, **`session`**, **`thread`**. **Chat messages** are stored inside the **checkpoint_*** tables as part of the graph state.

---

## Summary

| What                | Where it lives                          | Tables / mechanism                    |
|---------------------|-----------------------------------------|--------------------------------------|
| User accounts       | Same DB as Agent (here `mydb`)          | `user`                               |
| Sessions / threads  | Same DB                                 | `session`, `thread`                   |
| Chat messages       | Same DB                                 | `checkpoints` + `checkpoint_writes` + `checkpoint_blobs` |
| RAG vector store    | DB pointed to by RAG’s `.env` (e.g. `mydb`) | `langchain_pg_collection`, `langchain_pg_embedding` (after first ingest) |

If you want the vector store in `mydb`, ensure RAG’s `.env` uses `mydb`, enable the `vector` extension, then run RAG and ingest at least one document so the vector store tables are created.
