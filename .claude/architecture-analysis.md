# Architecture Analysis: API-First vs Local-First Approach

**Date:** 2026-01-07
**Decision:** Evaluate shift from local Kaggle dump + Ollama to Gemini + Semantic Scholar APIs

---

## Cost & Limits Comparison

### Option A: Original Plan (Local-First)

| Component | Cost | Limits | Storage |
|-----------|------|--------|---------|
| Kaggle metadata dump | Free | 4.7GB download once | 4.7GB |
| Ollama + Llama 3.2 8B | Free | Local compute only | 5GB model |
| ChromaDB | Free | RAM-limited (~1M vectors) | ~2GB per 100k |
| Neo4j Community | Free | RAM-limited | ~5GB per 100k |
| PDFs (optional) | Free | arXiv rate limits | ~50GB per 100k |

**Total Storage:** ~10-70GB depending on PDFs
**Compute:** M1/M2 Mac required, ~30 tok/s inference
**Data Freshness:** Static snapshot (updated manually)

---

### Option B: API-First (Gemini + Semantic Scholar)

| Component | Cost | Rate Limits | Storage |
|-----------|------|-------------|---------|
| **Gemini API (Free Tier)** | $0 | 15 RPM (Pro), 60 RPM (Flash), 1M tokens/day | 0 |
| **Semantic Scholar API** | $0 | 1 req/sec (no key), 10 req/sec (with free key) | 0 |
| ChromaDB | Free | Same as Option A | ~2GB |
| Neo4j Community | Free | Same as Option A | ~5GB |
| PDFs (on-demand) | Free | arXiv rate limits | ~1GB (cache only) |

**Total Storage:** ~8GB (no bulk metadata, no LLM weights)
**Compute:** Any machine (API-based)
**Data Freshness:** Real-time, always current

---

## Detailed API Analysis

### Gemini API (google.generativeai)

**Free Tier Limits:**
- **Gemini 1.5 Flash:** 60 requests/min, 1M tokens/min, 1500 RPD
- **Gemini 1.5 Pro:** 15 requests/min, 32k tokens/min, 1500 RPD
- **Context Window:** 1M tokens (can fit entire papers!)
- **Output:** 8k tokens per request

**Use Cases in Project:**
- Paper summarization (TLDR, detailed)
- Entity extraction (theorems, methods, equations)
- Citation intent classification
- Hypothesis generation
- Concept clustering

**Cost for 100k Papers:**
- Flash (cheap): 100k requests ÷ 60 RPM = ~28 hours
- Pro (quality): 100k requests ÷ 15 RPM = ~111 hours
- **Total Cost:** $0 (within free tier if spread over time)

---

### Semantic Scholar API

**Free Tier Limits:**
- **No API Key:** 1 request/sec (3,600/hour)
- **With Free API Key:** 10 requests/sec (36,000/hour)
- **No daily cap** (just rate-limited)

**Available Data per Paper:**
- `paperId`, `externalIds` (arXiv, DOI, PubMed)
- `title`, `abstract`, `year`, `venue`
- `authors` (with IDs, affiliations)
- `citationCount`, `influentialCitationCount`
- `references` (outgoing citations)
- `citations` (incoming citations)
- `tldr` (AI-generated summary)
- `fieldsOfStudy`, `s2FieldsOfStudy`
- `publicationTypes`, `publicationDate`
- `isOpenAccess`, `openAccessPdf`

**Additional Endpoints:**
- `/paper/search` - Semantic search
- `/paper/{id}/citations` - Citation context
- `/recommendations` - Related papers
- `/author/{id}` - Author profiles

**Cost for 100k Papers:**
- With free API key: 100k requests ÷ 36k/hour = ~3 hours
- **Total Cost:** $0

---

## Feasibility Analysis

### Target Scale: 100,000 Papers

**Time to Process (One-Time Ingestion):**
1. **Fetch metadata from S2:** 100k ÷ 36k/hour = ~3 hours
2. **Download PDFs (if needed):** 100k ÷ 200/hour (arXiv limit) = ~500 hours (skip for now)
3. **Gemini analysis (Flash):** 100k ÷ 60/min = ~28 hours
4. **Store in Neo4j:** ~2 hours (batch import)

**Total Initial Ingestion:** ~33 hours (can run overnight)
**Ongoing Sync:** ~100 new papers/day × 2 min = 3-4 minutes/day

✅ **Feasible for target scale**

---

### Data Quality Comparison

| Feature | Kaggle Dump | Semantic Scholar API |
|---------|-------------|---------------------|
| arXiv metadata | ✅ Complete | ✅ Complete |
| Citation counts | ❌ No | ✅ Yes (with influence) |
| Citation context | ❌ No | ✅ Yes |
| Related papers | ❌ No | ✅ Yes (recommendations) |
| Author profiles | ❌ No | ✅ Yes |
| Fields of study | ❌ No | ✅ Yes (AI-classified) |
| TLDR summaries | ❌ No | ✅ Yes |
| Publication venues | ✅ Limited | ✅ Complete |
| Update frequency | Manual download | Real-time |
| Cross-references | arXiv only | arXiv + DOI + PubMed |

**Winner:** Semantic Scholar API (much richer data)

---

## Revised Architecture

### Data Flow (API-First)

```
User Query (arXiv ID or topic)
    ↓
[1] Semantic Scholar API
    ├─ Fetch paper metadata
    ├─ Fetch citations (in/out)
    └─ Fetch author info
    ↓
[2] Optional: Download PDF from arXiv
    ├─ Only if full-text analysis needed
    └─ Cache locally (1GB limit)
    ↓
[3] Gemini API Analysis
    ├─ Summarize (if no S2 TLDR)
    ├─ Extract entities
    ├─ Classify citations
    └─ Generate embeddings (S2 SPECTER or sentence-transformers)
    ↓
[4] Store in Knowledge Graph
    ├─ Neo4j: Papers + Citations + Concepts
    └─ ChromaDB: Embeddings for semantic search
    ↓
[5] Advanced Features
    ├─ Link prediction (GraphSAGE - still local)
    └─ Hypothesis generation (Gemini + graph queries)
```

---

## What We Can Remove

### Delete Immediately:
- ❌ `data/raw/arxiv.zip` (1.5GB)
- ❌ `data/raw/arxiv-metadata-oai-snapshot.json` (4.7GB)
- ❌ Ollama dependency (if only using Gemini)
- ❌ Large PDF corpus (download on-demand only)

### Keep:
- ✅ `data/raw/arxiv-subset-100.json` (test data)
- ✅ Neo4j (graph storage)
- ✅ ChromaDB (vector search)
- ✅ sentence-transformers (for embeddings - local)

---

## Updated Dependency List

**Remove:**
- `kaggle` - No longer downloading bulk dump

**Add:**
- `semanticscholar` - Official S2 Python client

**Keep:**
- `google-generativeai` - Already have this
- `groq` - Backup LLM option
- `arxiv` - Fallback for PDF downloads

---

## Cost Projections

### For 100,000 Papers:

| Task | API Calls | Cost |
|------|-----------|------|
| Initial metadata fetch (S2) | 100k | $0 |
| Citation data (S2) | 200k (2× for in/out) | $0 |
| Summarization (Gemini Flash) | 100k | $0 (free tier) |
| Entity extraction (Gemini Flash) | 100k | $0 (free tier) |
| **Total One-Time Cost** | | **$0** |

**Monthly Maintenance:**
- New papers: ~3k/month × API calls = $0
- Re-analysis: Minimal

✅ **Confirmed: Zero cost for target scale**

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| S2 API rate limit (10 req/sec) | Add exponential backoff, run overnight |
| Gemini free tier exhausted | Use Groq (free tier 30 RPM) as fallback |
| API availability | Cache responses in Neo4j, can replay |
| No offline mode | Keep sentence-transformers for embeddings |
| Missing papers in S2 | Fallback to arXiv API for metadata |

---

## Recommendation

✅ **PROCEED with API-first architecture**

**Rationale:**
1. **Zero cost** (both approaches are free, but API is easier)
2. **Better data quality** (S2 provides citation context, influence scores)
3. **Less storage** (6GB saved immediately)
4. **Real-time data** (always up-to-date)
5. **Simpler pipeline** (no 4.7GB dump to manage)
6. **Gemini 1M context** (can analyze full papers without chunking)

**Trade-offs:**
- Requires internet (acceptable for research tool)
- Rate-limited (but manageable overnight runs)
- Dependency on external APIs (mitigated by caching in Neo4j)

---

## Next Steps

1. Add `semanticscholar` to pyproject.toml
2. Create `packages/ingestion/s2_client.py`
3. Update ingestion pipeline to fetch from S2 first
4. Update plan and README
5. Add cleanup script for large files
6. Test with 100-paper subset

**Estimated Implementation Time:** 2-3 hours
