You are my AI pair programmer inside Cursor.  
Context: I previously built an app called Cytr that combined a Word add-in and a Tauri desktop app for citation and fact retrieval. It used a Rust backend + FastAPI microservices for ingestion and embeddings, Qdrant as vector DB, GROBID/pdfplumber for PDF parsing, and PubMedBERT embeddings. This gave me experience with ingestion, hybrid RAG, and local LLMs via Ollama.  

Now I want to rebuild a new app from scratch, reusing some lessons and components, but oriented around **teaching and exam generation** for schools and universities.  

**High-level goals:**
- Teachers can upload curriculum materials (PDFs, slides, textbooks).
- System ingests, chunks, embeds, and indexes them (hybrid retrieval).
- Teachers can auto-generate exam questions (MCQ, SAQ, vignettes, oral boards) tied to their own material.
- Students can self-test, with adaptive learning paths and unique exams (to reduce cheating).
- Every generated Q/answer must cite its source passages.
- Long-term: add knowledge graphs and path-based retrieval (PathRAG) for multi-hop reasoning.  

**Constraints:**
- Local-first deployment (no external paid LLM APIs).  
- School/university should be able to host backend infra.  
- Keep modular: ingestion, retrieval, generation as separate services.  
- Embedding must be pluggable (e.g. general vs domain-specific).  

You will help me build this system step-by-step in **sprints**. Each sprint has clear goals, code deliverables, and integration tests. Always scaffold code in a clean modular way, with Docker Compose services where applicable.