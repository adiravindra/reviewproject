# ReviewInsight Architecture

This document explains ReviewInsight through a set of Mermaid architecture diagrams. The diagrams cover the full product, the frontend, the backend, the model pipeline, persistence, and the end-to-end request lifecycle.

## 1. Whole-System Architecture

This is the highest-level view. Streamlit owns the user experience, FastAPI owns the application boundary, Hugging Face models perform the analysis, and SQLite stores analysis history.

```mermaid
flowchart LR
    User["User"]

    subgraph Frontend["Streamlit Frontend"]
        AnalysisPage["Analysis Page<br/>dashboard/streamlit_app.py"]
        HistoryPage["History Page<br/>dashboard/pages/1_History.py"]
        SharedUI["Shared UI + Styling<br/>dashboard/ui.py"]
        ApiClient["API Client<br/>dashboard/api_client.py"]
    end

    subgraph Backend["FastAPI Backend"]
        App["FastAPI App<br/>backend/app/main.py"]
        Router["Review Router<br/>backend/app/routers/reviews.py"]
        Schemas["Pydantic Schemas<br/>backend/app/schemas/reviews.py"]
        AnalysisService["Analysis Orchestrator<br/>backend/app/services/analysis.py"]
        HistoryService["History Service<br/>backend/app/services/history.py"]
        DBService["SQLite Connection<br/>backend/app/services/db.py"]
    end

    subgraph Models["Model Layer"]
        SummaryModel["Summary Model<br/>google/flan-t5-small"]
        SentimentModel["Sentiment Model<br/>distilbert SST-2"]
        Fallbacks["Rule-Based Fallbacks<br/>used only when model path fails"]
    end

    SQLite[("SQLite DB<br/>data/reviewinsight.db")]

    User --> AnalysisPage
    User --> HistoryPage
    AnalysisPage --> SharedUI
    HistoryPage --> SharedUI
    AnalysisPage --> ApiClient
    HistoryPage --> ApiClient
    ApiClient -->|"HTTP JSON"| Router
    App --> Router
    Router --> Schemas
    Router --> AnalysisService
    AnalysisService --> SummaryModel
    AnalysisService --> SentimentModel
    SummaryModel -. "failure only" .-> Fallbacks
    SentimentModel -. "failure only" .-> Fallbacks
    Router --> HistoryService
    HistoryService --> DBService
    DBService --> SQLite
```

## 2. Frontend Architecture

The frontend is intentionally small. The Analysis page captures one review and renders the latest result. The History page loads saved analyses. Both pages share navigation, styling, result cards, keyword highlighting, and error rendering through `dashboard/ui.py`.

```mermaid
flowchart TD
    subgraph Streamlit["Streamlit Runtime"]
        Config["configure_page(title)"]
        Nav["render_nav(active_page)"]
        Intro["render_page_intro(title, description)"]
        BackendInput["backend_url_input()"]
        ResultTabs["render_result_tabs(result)"]
        HistoryRows["history_rows(items)"]
        Errors["render_error(error)"]
    end

    subgraph AnalysisPage["Analysis Page"]
        TextArea["Customer Review Text Area"]
        AnalyzeButton["Analyze Review Button"]
        SessionState["st.session_state.latest_review_result"]
        ResultView["Summary & Sentiment Tab<br/>Raw Result Tab"]
    end

    subgraph HistoryPage["History Page"]
        HistoryCards["Saved Review Cards"]
    end

    subgraph APIClient["dashboard/api_client.py"]
        AnalyzeCall["analyze_review(text, api_base_url)"]
        HistoryCall["fetch_history(api_base_url)"]
        ErrorBoundary["ApiClientError"]
    end

    TextArea --> AnalyzeButton
    AnalyzeButton --> AnalyzeCall
    AnalyzeCall --> SessionState
    SessionState --> ResultTabs
    ResultTabs --> ResultView

    HistoryCall --> HistoryRows
    HistoryRows --> HistoryCards

    Config --> AnalysisPage
    Config --> HistoryPage
    Nav --> AnalysisPage
    Nav --> HistoryPage
    Intro --> AnalysisPage
    Intro --> HistoryPage
    BackendInput --> AnalyzeCall
    BackendInput --> HistoryCall
    ErrorBoundary --> Errors
```

## 3. Backend Service Architecture

FastAPI exposes two routes. `POST /analysis/single` validates the request, runs the analysis service, saves the result, and returns the complete analysis response. `GET /analysis/history` reads saved payloads from SQLite and returns a compact history response.

```mermaid
flowchart TD
    Client["Streamlit API Client"]

    subgraph FastAPI["FastAPI Backend"]
        Main["main.py<br/>FastAPI(title='ReviewInsight API')"]
        Router["reviews.py<br/>APIRouter"]
        RequestSchema["ReviewAnalysisRequest"]
        ResponseSchema["ReviewAnalysisResponse"]
        HistorySchema["HistoryResponse"]
    end

    subgraph Services["Backend Services"]
        Prepare["prepare_reviews()"]
        Analyze["analyze_review()"]
        ModelSentiment["analyze_sentiment_with_model()"]
        ModelSummary["summarize_with_model()"]
        Explain["explain_sentiment()"]
        Save["save_review_analysis()"]
        LoadHistory["get_history(limit)"]
    end

    SQLite[("SQLite<br/>analysis_runs")]

    Client -->|"POST /analysis/single"| Router
    Client -->|"GET /analysis/history"| Router
    Main --> Router

    Router --> RequestSchema
    RequestSchema --> Analyze
    Analyze --> Prepare
    Analyze --> ModelSentiment
    Analyze --> ModelSummary
    Analyze --> Explain
    Analyze --> ResponseSchema
    ResponseSchema --> Save
    Save --> SQLite

    Router --> LoadHistory
    LoadHistory --> SQLite
    LoadHistory --> HistorySchema
```

## 4. Model-First Analysis Pipeline

The analysis pipeline is model-first. Rule-based functions still exist, but they are recovery paths. The summary fallback is built before calling the summary model so it is ready if the model load, inference, or decoding path fails.

```mermaid
flowchart TD
    RawReview["Raw Review Text"]
    Clean["prepare_reviews()<br/>trim and normalize input"]

    subgraph SentimentPath["Sentiment Path"]
        LoadSentiment["Load sentiment-analysis pipeline"]
        Distilbert["distilbert/distilbert-base-uncased-finetuned-sst-2-english"]
        ParseSentiment["Parse label + confidence"]
        SentimentFallback["Keyword sentiment fallback"]
    end

    subgraph SummaryPath["Summary Path"]
        BuildFallback["Build fallback summary text"]
        LoadSummary["Load tokenizer + seq2seq model"]
        Flan["google/flan-t5-small"]
        Prompt["Instruction prompt<br/>business-owner review analysis"]
        Generate["model.generate()"]
        CleanSummary["Clean generated text"]
        SummaryFallback["Rule-based summary fallback"]
    end

    Explanation["Sentiment explanation"]
    Response["ReviewAnalysisResponse"]

    RawReview --> Clean
    Clean --> LoadSentiment
    LoadSentiment --> Distilbert
    Distilbert --> ParseSentiment
    LoadSentiment -. "load/inference/parse failure" .-> SentimentFallback
    SentimentFallback --> Explanation
    ParseSentiment --> Explanation

    Clean --> BuildFallback
    Clean --> Prompt
    Prompt --> LoadSummary
    LoadSummary --> Flan
    Flan --> Generate
    Generate --> CleanSummary
    BuildFallback -. "load/inference/empty output failure" .-> SummaryFallback
    LoadSummary -. "failure" .-> SummaryFallback
    Generate -. "failure" .-> SummaryFallback

    Explanation --> Response
    CleanSummary --> Response
    SummaryFallback --> Response
```

## 5. End-to-End Analyze Sequence

This sequence shows the live request path after a user clicks `Analyze Review`.

```mermaid
sequenceDiagram
    actor User
    participant UI as Streamlit Analysis Page
    participant Client as dashboard/api_client.py
    participant API as FastAPI /analysis/single
    participant Analyzer as analysis.py
    participant Sentiment as Sentiment Model Wrapper
    participant Summary as Summary Model Wrapper
    participant History as history.py
    participant DB as SQLite

    User->>UI: Paste review
    User->>UI: Click Analyze Review
    UI->>Client: analyze_review(review_text)
    Client->>API: POST /analysis/single { text }
    API->>Analyzer: analyze_review(text)
    Analyzer->>Analyzer: prepare_reviews([text])
    Analyzer->>Sentiment: analyze_sentiment_with_model(cleaned_text)
    Sentiment-->>Analyzer: sentiment, score, confidence, source
    Analyzer->>Summary: summarize_with_model([cleaned_text], fallback_summary)
    Summary-->>Analyzer: summary, source, model name, fallback reason if needed
    Analyzer-->>API: ReviewAnalysisResponse
    API->>History: save_review_analysis(response)
    History->>DB: INSERT OR REPLACE payload_json
    DB-->>History: committed
    API-->>Client: JSON response
    Client-->>UI: parsed result
    UI->>UI: store latest result in st.session_state
    UI-->>User: Render Summary & Sentiment view
```

## 6. History And Persistence

SQLite stores one row per analyzed review. The database keeps legacy aggregate columns for compatibility, but the canonical current data is the serialized `payload_json`.

```mermaid
flowchart LR
    subgraph SavePath["Save Path"]
        Response["ReviewAnalysisResponse"]
        Serialize["model_to_dict(result)"]
        Insert["INSERT OR REPLACE<br/>analysis_runs"]
    end

    subgraph Table["analysis_runs table"]
        ID["id"]
        Created["created_at"]
        Counts["legacy aggregate columns"]
        Summary["overall_summary"]
        Payload["payload_json<br/>canonical response payload"]
    end

    subgraph ReadPath["History Read Path"]
        Query["SELECT payload_json<br/>ORDER BY created_at DESC<br/>LIMIT ?"]
        Parse["json.loads(payload_json)"]
        Item["HistoryItem<br/>id, created_at, text, sentiment, summary"]
        Cards["Streamlit History Cards"]
    end

    Response --> Serialize
    Serialize --> Insert
    Insert --> ID
    Insert --> Created
    Insert --> Counts
    Insert --> Summary
    Insert --> Payload

    Payload --> Query
    Query --> Parse
    Parse --> Item
    Item --> Cards
```

## 7. Startup And Runtime Responsibilities

The combined runner starts both services. It warms models before launch, but warmup is not a hard dependency. Runtime API requests still try the model path first and fallback only if the model path fails during that request.

```mermaid
flowchart TD
    Start["python scripts/run_app.py"]
    WarmSummary["Warm summary model"]
    WarmSentiment["Warm sentiment model"]
    WarmOK["Warmup succeeds"]
    WarmFail["Warmup fails"]
    StartBackend["Start FastAPI<br/>127.0.0.1:8000"]
    StartFrontend["Start Streamlit<br/>127.0.0.1:8501"]
    UserRequest["User submits review"]
    RuntimeModels["Try models during request"]
    RuntimeFallback["Fallback only if model request fails"]
    Result["Return analysis result"]

    Start --> WarmSummary
    WarmSummary --> WarmSentiment
    WarmSentiment --> WarmOK
    WarmSummary -. "exception" .-> WarmFail
    WarmSentiment -. "exception" .-> WarmFail
    WarmOK --> StartBackend
    WarmFail --> StartBackend
    StartBackend --> StartFrontend
    StartFrontend --> UserRequest
    UserRequest --> RuntimeModels
    RuntimeModels --> Result
    RuntimeModels -. "load/inference/parse failure" .-> RuntimeFallback
    RuntimeFallback --> Result
```

## 8. Current Runtime Contracts

```mermaid
classDiagram
    class ReviewAnalysisRequest {
        +str text
    }

    class ReviewAnalysisResponse {
        +str id
        +str created_at
        +str text
        +str sentiment
        +int sentiment_score
        +str summary
        +str summary_source
        +str? model_name
        +str? fallback_reason
        +str sentiment_source
        +str? sentiment_explanation
        +str? sentiment_model_name
        +float? sentiment_confidence
        +str? sentiment_fallback_reason
        +bool saved_to_history
    }

    class HistoryItem {
        +str id
        +str created_at
        +str text
        +str sentiment
        +str summary
    }

    class HistoryResponse {
        +list~HistoryItem~ items
    }

    ReviewAnalysisRequest --> ReviewAnalysisResponse : "POST /analysis/single"
    ReviewAnalysisResponse --> HistoryItem : "stored payload becomes history item"
    HistoryItem --> HistoryResponse : "GET /analysis/history"
```

## Reading Guide

- Start with the whole-system diagram to understand ownership boundaries.
- Use the frontend and backend diagrams to find files quickly.
- Use the model pipeline diagram to understand model-first analysis and fallback boundaries.
- Use the sequence diagram when debugging a live `Analyze Review` request.
- Use the persistence diagram when changing history behavior or the SQLite schema.
