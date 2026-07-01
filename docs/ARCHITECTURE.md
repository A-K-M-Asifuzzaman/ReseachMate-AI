# ResearchMate AI — Architecture

In-depth diagrams of the system, the ingestion pipeline, the RAG query flow, the data
model, the knowledge graph, the agent layer, and the deployment topology.

---

## 1. System architecture (high level)

```mermaid
flowchart TB
    subgraph Client["🖥️ Frontend — Next.js (App Router)"]
        UI_Landing["Landing"]
        UI_Dash["Dashboard"]
        UI_Upload["Upload"]
        UI_Chat["AI Chat (SSE stream)"]
        UI_Lib["Paper Library"]
        UI_KG["Knowledge Graph"]
        UI_Hist["History"]
    end

    subgraph API["⚙️ Backend — FastAPI (async)"]
        direction TB
        Auth["/auth\nJWT · bcrypt"]
        DocAPI["/documents\nupload · list · delete"]
        RAGAPI["/rag\nquery · stream"]
        ChatAPI["/chat\nconversations · memory"]
        SumAPI["/summaries"]
        CmpAPI["/comparison"]
        KGAPI["/knowledge-graph"]
        AgentAPI["/agents"]
    end

    subgraph Services["🧠 Service layer"]
        direction TB
        Ingest["Document pipeline\nextract · clean · chunk"]
        Embed["Embedding service\nBGE / E5"]
        Vec["Vector store\nQdrant adapter"]
        Rag["RAG pipeline\nexpand · retrieve · rerank · generate"]
        Rerank["Cross-encoder reranker"]
        LLM["LLM adapter\nOpenAI · Anthropic · Ollama"]
        KGExtract["KG extractor\nentities · relations"]
        Agents["Agent orchestrator"]
    end

    subgraph Data["💾 Data stores"]
        PG[("PostgreSQL\nusers · documents\nchunks · chat memory")]
        QD[("Qdrant\ndense vectors + payload")]
        NEO[("Neo4j\nentities + relations")]
        OBJ[("Object storage\nS3 / local — PDFs")]
    end

    subgraph External["☁️ External"]
        OAI["OpenAI API"]
        HF["Hugging Face models\n(embeddings + reranker)"]
    end

    Client -->|"REST + SSE"| API
    API --> Services

    Ingest --> Embed --> Vec --> QD
    Ingest --> PG
    Ingest --> OBJ
    Rag --> Embed
    Rag --> Vec
    Rag --> Rerank
    Rag --> LLM
    Rag --> PG
    Rerank -.loads.-> HF
    Embed -.loads.-> HF
    LLM --> OAI
    KGExtract --> LLM
    KGExtract --> NEO
    Agents --> Rag
    Agents --> LLM

    DocAPI --> Ingest
    RAGAPI --> Rag
    ChatAPI --> Rag
    KGAPI --> KGExtract
    AgentAPI --> Agents
```

---

## 2. Document ingestion pipeline

From uploaded PDF to searchable, cited-ready chunks.

```mermaid
flowchart LR
    A["📄 PDF upload"] --> B{"Validate\ntype · size · magic bytes"}
    B -- invalid --> Berr["422 reject"]
    B -- ok --> C["Persist file\nS3 / local storage"]
    C --> D["Create Document row\nstatus = UPLOADED"]
    D --> E["Enqueue background ingest\nstatus = PROCESSING"]

    subgraph Pipeline["DocumentPipeline (thread pool for CPU work)"]
        direction TB
        F["PyMuPDF text extraction\nper-page + metadata"]
        G["pdfplumber tables\n(best-effort)"]
        H["Clean\nstrip headers/footers · de-hyphenate · dedupe"]
        I["Bibliographic metadata\ntitle · authors · year · abstract"]
        J["Semantic chunking\nsection-aware recursive split + overlap"]
        K["Embed chunks\nBGE (doc prefix), normalized"]
    end

    E --> F --> G --> H --> I --> J --> K
    K --> L["Write Chunk rows\n(Postgres = source of truth)"]
    K --> M["Upsert vectors\nQdrant (payload: user/doc/page/section)"]
    L --> N["Document status = READY\nnum_pages · num_chunks"]
    M --> N
    N -.on error.-> O["status = FAILED\nstore error message"]
```

---

## 3. RAG query pipeline (detailed)

The full advanced-RAG path: understanding → expansion → hybrid retrieval → fusion →
reranking → grounded generation with citations.

```mermaid
flowchart TB
    Q["❓ User query\n(+ conversation history)"] --> QE["Query understanding\n& expansion (LLM)\nN paraphrases"]

    QE --> EMB["Embed queries\n(BGE query prefix)"]
    QE --> KW["Keyword branch"]

    subgraph Retrieval["Hybrid retrieval"]
        direction TB
        EMB --> VS["Dense search\nQdrant · cosine · metadata filter\n(user_id, document_ids)"]
        KW --> BM["BM25 keyword search\nover Postgres chunk pool"]
        VS --> RRF["Reciprocal Rank Fusion\nscore = Σ 1/(k + rank)"]
        BM --> RRF
    end

    RRF --> TOPK["Fused shortlist\n(top_k candidates)"]
    TOPK --> RR["Cross-encoder rerank\n(query, passage) joint scoring"]
    RR --> CTX["Context selection\ntop_n passages"]

    CTX --> GEN["LLM generation\nsystem: grounded + cite [n]\ncontext + question + history"]
    GEN --> ANS["✅ Answer"]
    CTX --> CIT["Build citations\ndoc · page · section · snippet · score"]
    ANS --> PARSE["Parse inline [n] refs"]
    CIT --> PARSE
    PARSE --> OUT["Answer + citations\n+ latency + tokens"]

    OUT --> MEM["Persist to chat memory\n(Conversation / Message)"]

    classDef store fill:#1f2937,stroke:#60a5fa,color:#e5e7eb;
    class VS,BM,MEM store;
```

---

## 4. Streaming answer (SSE) sequence

```mermaid
sequenceDiagram
    autonumber
    participant U as Browser
    participant API as FastAPI /rag/query/stream
    participant P as RAGPipeline
    participant R as Retriever+Reranker
    participant L as LLM (OpenAI)
    participant DB as Postgres

    U->>API: POST query {stream:true} (Bearer JWT)
    API->>DB: load conversation history
    API->>P: run_stream(query, history)
    P->>R: expand → hybrid retrieve → rerank
    R-->>P: top_n passages
    P-->>API: event: expanded (queries)
    API-->>U: SSE: expanded
    P-->>API: event: citations (passages)
    API-->>U: SSE: citations
    loop token stream
        P->>L: stream completion
        L-->>P: delta
        P-->>API: event: token
        API-->>U: SSE: token
    end
    P-->>API: event: done (full answer)
    API->>DB: save user + assistant messages
    API-->>U: SSE: done
```

---

## 5. Relational data model (PostgreSQL)

```mermaid
erDiagram
    USERS ||--o{ DOCUMENTS : owns
    USERS ||--o{ CONVERSATIONS : has
    USERS ||--o{ CHUNKS : owns
    DOCUMENTS ||--o{ CHUNKS : "split into"
    CONVERSATIONS ||--o{ MESSAGES : contains

    USERS {
        uuid id PK
        string name
        string email UK
        string hashed_password
        bool is_active
        bool is_superuser
        datetime created_at
    }
    DOCUMENTS {
        uuid id PK
        uuid user_id FK
        string title
        string authors
        int year
        string journal
        text abstract
        string filename
        string storage_path
        int num_pages
        int num_chunks
        enum status
        jsonb doc_metadata
    }
    CHUNKS {
        uuid id PK
        uuid document_id FK
        uuid user_id FK
        int chunk_index
        text content
        int page_number
        string section
        int token_count
        jsonb chunk_metadata
    }
    CONVERSATIONS {
        uuid id PK
        uuid user_id FK
        string title
        jsonb document_ids
    }
    MESSAGES {
        uuid id PK
        uuid conversation_id FK
        enum role
        text content
        jsonb citations
        jsonb msg_metadata
    }
```

> Each `CHUNKS` row is mirrored to a Qdrant point keyed by `chunks.id`, so the vector
> index can be rebuilt from Postgres at any time and citations resolve without Qdrant.

---

## 6. Knowledge graph model (Neo4j)

```mermaid
flowchart LR
    subgraph Nodes
        P(["Paper"])
        C1(["Concept: Transformer"])
        C2(["Concept: Attention"])
        C3(["Method: Self-Attention"])
        D(["Dataset: WMT-14"])
        T(["Task: Translation"])
    end

    P -- MENTIONS --> C1
    P -- MENTIONS --> C2
    P -- PROPOSES --> C3
    P -- EVALUATES_ON --> D
    P -- ADDRESSES --> T
    C1 -- USES --> C2
    C3 -- IS_A --> C2
    C1 -- APPLIED_TO --> T
```

Extraction: the KG extractor prompts the (heavy) LLM per document to emit
`{entities:[{name,type}], relations:[{source,relation,target}]}`, which is merged into
Neo4j with `Paper` provenance so the graph is queryable and visualizable per-user.

---

## 7. Agent orchestration

```mermaid
flowchart TB
    Q["User task"] --> PL["Planner\n(classifies intent, picks agent)"]
    PL -->|"find info"| RA["Research Agent"]
    PL -->|"summarize"| SA["Summary Agent"]
    PL -->|"find sources"| CA["Citation Agent"]
    PL -->|"compare"| CmpA["Comparison Agent"]

    subgraph Tools["Shared tools"]
        RT["retrieve()\nhybrid + rerank"]
        SUM["summarize()"]
        CMP["compare()"]
        KGQ["graph_query()"]
    end

    RA --> RT
    SA --> SUM
    CA --> RT
    CmpA --> CMP
    RA --> KGQ

    RT --> AG["Answer generator\n(grounded + citations)"]
    SUM --> AG
    CMP --> AG
    AG --> R["Result to user"]
```

---

## 8. Deployment topology

```mermaid
flowchart TB
    subgraph Edge["Vercel"]
        FE["Next.js frontend\nSSR + static"]
    end
    subgraph Cloud["Backend host — Render / AWS"]
        BE["FastAPI (uvicorn/gunicorn)\nrate-limited · CORS"]
        WK["Background workers\ningestion + KG extraction"]
    end
    subgraph Managed["Managed data"]
        SB[("Supabase Postgres")]
        QC[("Qdrant Cloud")]
        NA[("Neo4j Aura")]
        S3[("AWS S3")]
    end
    OAI["OpenAI API"]

    FE -->|HTTPS| BE
    BE --> SB
    BE --> QC
    BE --> NA
    BE --> S3
    BE --> OAI
    WK --> SB
    WK --> QC
    WK --> NA
```
