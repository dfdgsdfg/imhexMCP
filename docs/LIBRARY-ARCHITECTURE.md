# ImHex MCP Python Library Architecture

## Overview

This document covers the architecture of the ImHex MCP **Python client library** (`lib/` directory), which provides high-performance, feature-rich clients for interacting with the ImHex MCP server. This complements the main [ARCHITECTURE.md](ARCHITECTURE.md) which covers the C++ plugin and overall system architecture.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Component Architecture](#component-architecture)
3. [Data Flow Architecture](#data-flow-architecture)
4. [Caching Architecture](#caching-architecture)
5. [Security Architecture](#security-architecture)
6. [Performance Architecture](#performance-architecture)
7. [Deployment Architecture](#deployment-architecture)

---

## System Architecture

### High-Level System Overview

```mermaid
graph TB
    Client[MCP Client<br/>Claude/AI Agent]
    Server[MCP Server<br/>Python]
    ImHex[ImHex Instance<br/>Binary Editor]

    Client -->|MCP Protocol<br/>JSON-RPC| Server
    Server -->|TCP Socket<br/>JSON| ImHex

    subgraph "MCP Server Components"
        AsyncClient[Async Client]
        Security[Security Manager]
        Cache[Cache System]
        Metrics[Metrics & Monitoring]

        AsyncClient --> Security
        AsyncClient --> Cache
        AsyncClient --> Metrics
    end

    Server --> AsyncClient

    style Client fill:#e1f5ff
    style Server fill:#fff4e1
    style ImHex fill:#f0f0f0
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Client** | MCP Protocol | Standard protocol for AI agents |
| **Server** | Python 3.10+ | Async I/O, high performance |
| **Communication** | JSON-RPC over TCP | Socket-based communication |
| **Backend** | ImHex C++ | Binary analysis engine |
| **Caching** | In-memory LRU | Performance optimization |
| **Security** | Custom validation | Input validation & rate limiting |
| **Monitoring** | Prometheus | Metrics and observability |

---

## Component Architecture

### Core Components

```mermaid
graph LR
    subgraph "Client Layer"
        AC[AsyncImHexClient]
        CC[CachedClient]
        LC[LazyClient]
    end

    subgraph "Connection Layer"
        CP[Connection Pool]
        SM[Socket Manager]
    end

    subgraph "Processing Layer"
        BA[Batch Processor]
        ST[Streaming Handler]
        RB[Request Batching]
    end

    subgraph "Optimization Layer"
        CA[Cache System]
        DC[Data Compression]
        PR[Profiling]
    end

    subgraph "Security Layer"
        SE[Security Manager]
        RL[Rate Limiter]
        IV[Input Validator]
        IPF[IP Filter]
    end

    subgraph "Monitoring Layer"
        MT[Metrics]
        HM[Health Monitor]
        LG[Logging]
    end

    AC --> CP
    CC --> AC
    LC --> AC

    CP --> SM
    AC --> BA
    AC --> ST
    BA --> RB

    AC --> CA
    AC --> DC
    AC --> PR

    AC --> SE
    SE --> RL
    SE --> IV
    SE --> IPF

    AC --> MT
    AC --> HM
    AC --> LG
```

### Module Dependency Graph

```mermaid
graph TD
    A[async_client.py]
    B[cached_client.py]
    C[connection_pool.py]
    D[batching.py]
    E[request_batching.py]
    F[cache.py]
    G[advanced_cache.py]
    H[data_compression.py]
    I[security.py]
    J[metrics.py]
    K[config.py]
    L[error_handling.py]
    M[profiling.py]
    N[health_monitor.py]
    O[streaming.py]
    P[advanced_features.py]
    Q[lazy.py]

    A --> C
    A --> E
    A --> F
    A --> H
    A --> I
    A --> J
    A --> K
    A --> L

    B --> A
    B --> G

    C --> L

    D --> L
    E --> L

    G --> F

    I --> K

    M --> A

    N --> A
    N --> J

    O --> A

    P --> A
    P --> E

    Q --> L

    style A fill:#ffcccc
    style B fill:#ccffcc
    style I fill:#ccccff
```

---

## Data Flow Architecture

### Request Processing Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant SM as Security Manager
    participant AC as AsyncClient
    participant CA as Cache
    participant CP as Connection Pool
    participant IH as ImHex

    C->>SM: Request
    SM->>SM: IP Filter Check
    SM->>SM: Rate Limit Check
    SM->>SM: Input Validation

    SM->>AC: Validated Request

    AC->>CA: Check Cache
    alt Cache Hit
        CA-->>AC: Cached Response
        AC-->>C: Response
    else Cache Miss
        AC->>CP: Get Connection
        CP-->>AC: Socket Connection
        AC->>IH: JSON Request
        IH-->>AC: JSON Response
        AC->>CA: Store in Cache
        AC->>CP: Return Connection
        AC-->>C: Response
    end
```

### Batch Processing Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant BP as Batch Processor
    participant RB as Request Batching
    participant AC as AsyncClient
    participant IH as ImHex

    C->>BP: Request 1
    C->>BP: Request 2
    C->>BP: Request 3

    BP->>RB: Queue Requests
    RB->>RB: Collect (100ms window)
    RB->>AC: Batch of 3 Requests

    par Parallel Execution
        AC->>IH: Request 1
        AC->>IH: Request 2
        AC->>IH: Request 3
    end

    IH-->>AC: Response 1
    IH-->>AC: Response 2
    IH-->>AC: Response 3

    AC-->>BP: Batch Results
    BP-->>C: Response 1
    BP-->>C: Response 2
    BP-->>C: Response 3
```

### Streaming Data Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant ST as Streaming Handler
    participant IH as ImHex

    C->>ST: Read Large File (10GB)
    ST->>ST: Calculate Chunks (1MB each)

    loop For Each Chunk
        ST->>IH: Read Chunk (offset, size)
        IH-->>ST: Chunk Data
        ST->>ST: Compress (optional)
        ST-->>C: Yield Chunk
    end

    ST-->>C: Stream Complete
```

---

## Caching Architecture

### Two-Tier Cache System

```mermaid
graph TB
    Client[Client Request]

    subgraph "L1 Cache: Simple LRU"
        L1[In-Memory LRU<br/>Fast Access<br/>Limited Size]
    end

    subgraph "L2 Cache: Advanced Cache"
        L2[Advanced Cache<br/>TTL Support<br/>Statistics<br/>Eviction Policies]
    end

    Backend[ImHex Backend]

    Client --> L1
    L1 -->|Miss| L2
    L2 -->|Miss| Backend

    Backend -->|Response| L2
    L2 -->|Store & Return| L1
    L1 -->|Return| Client

    style L1 fill:#ccffcc
    style L2 fill:#ccccff
```

### Cache Key Strategy

```mermaid
graph LR
    Request[Request<br/>endpoint + data]

    Hash[Hash Function<br/>hashlib.sha256]

    Key[Cache Key<br/>endpoint:hash]

    Request --> Hash
    Hash --> Key

    subgraph "Cache Lookup"
        Key --> CL{Key Exists?}
        CL -->|Yes| Hit[Cache Hit<br/>Return Value]
        CL -->|No| Miss[Cache Miss<br/>Query Backend]
    end
```

### Cache Invalidation

```mermaid
stateDiagram-v2
    [*] --> Cached: Store Value

    Cached --> Expired: TTL Timeout
    Cached --> Evicted: LRU Eviction
    Cached --> Invalidated: Manual Invalidation
    Cached --> Retrieved: Cache Hit

    Retrieved --> Cached: Update Access Time

    Expired --> [*]
    Evicted --> [*]
    Invalidated --> [*]
```

---

## Security Architecture

### Defense in Depth

```mermaid
graph TB
    Request[Incoming Request]

    subgraph "Layer 1: Network"
        IPF[IP Filtering<br/>Whitelist/Blacklist]
    end

    subgraph "Layer 2: Rate Limiting"
        RL[Token Bucket<br/>Global & Per-Client]
    end

    subgraph "Layer 3: Input Validation"
        IV[Input Validator<br/>Type & Length Checks]
    end

    subgraph "Layer 4: Attack Prevention"
        SQL[SQL Injection Detection]
        CMD[Command Injection Detection]
        PT[Path Traversal Prevention]
    end

    subgraph "Layer 5: Size Limits"
        PL[Payload Size Limit<br/>10 MB Default]
    end

    Allow[Process Request]
    Reject[Reject Request<br/>Log Security Event]

    Request --> IPF
    IPF -->|Allowed| RL
    IPF -->|Blocked| Reject

    RL -->|Within Limit| IV
    RL -->|Exceeded| Reject

    IV -->|Valid| SQL
    IV -->|Invalid| Reject

    SQL -->|Clean| CMD
    SQL -->|Attack| Reject

    CMD -->|Clean| PT
    CMD -->|Attack| Reject

    PT -->|Clean| PL
    PT -->|Attack| Reject

    PL -->|OK| Allow
    PL -->|Too Large| Reject

    style Reject fill:#ffcccc
    style Allow fill:#ccffcc
```

### Security Event Flow

```mermaid
sequenceDiagram
    participant R as Request
    participant SM as Security Manager
    participant IPF as IP Filter
    participant RL as Rate Limiter
    participant IV as Input Validator
    participant L as Logger
    participant M as Metrics

    R->>SM: Incoming Request
    SM->>IPF: Check IP

    alt IP Blocked
        IPF->>L: Log IP Rejection
        IPF->>M: Increment ip_filter_rejections
        IPF-->>R: 403 Forbidden
    else IP Allowed
        SM->>RL: Check Rate Limit

        alt Rate Limited
            RL->>L: Log Rate Limit
            RL->>M: Increment rate_limit_exceeded
            RL-->>R: 429 Too Many Requests
        else Rate OK
            SM->>IV: Validate Input

            alt Validation Failed
                IV->>L: Log Validation Failure
                IV->>M: Increment validation_failures
                IV-->>R: 400 Bad Request
            else Validation Passed
                SM->>L: Log Success (DEBUG)
                SM->>M: Increment requests_processed
                SM-->>R: 200 OK (Continue)
            end
        end
    end
```

---

## Performance Architecture

### Optimization Layers

```mermaid
graph TB
    subgraph "Application Layer"
        Async[Async I/O<br/>asyncio]
        Pool[Connection Pooling<br/>Reuse Connections]
    end

    subgraph "Data Layer"
        Comp[Compression<br/>zlib/brotli]
        Batch[Batching<br/>Combine Requests]
    end

    subgraph "Cache Layer"
        L1[L1 Cache<br/>Hot Data]
        L2[L2 Cache<br/>Warm Data]
    end

    subgraph "Monitoring Layer"
        Prof[Profiling<br/>Performance Tracking]
        Met[Metrics<br/>Prometheus]
    end

    Request[Request] --> Async
    Async --> Pool
    Pool --> Comp
    Comp --> Batch
    Batch --> L1
    L1 --> L2

    Async --> Prof
    Async --> Met

    style L1 fill:#ccffcc
    style Async fill:#ccccff
```

### Performance Metrics

```mermaid
graph LR
    subgraph "Request Metrics"
        RT[Request Time<br/>Histogram]
        RC[Request Count<br/>Counter]
        RA[Active Requests<br/>Gauge]
    end

    subgraph "Cache Metrics"
        CH[Cache Hits<br/>Counter]
        CM[Cache Misses<br/>Counter]
        CR[Hit Rate<br/>Calculated]
    end

    subgraph "Compression Metrics"
        CBR[Compression Ratio<br/>Histogram]
        CT[Compression Time<br/>Histogram]
        BS[Bytes Saved<br/>Counter]
    end

    subgraph "Connection Metrics"
        CAct[Active Connections<br/>Gauge]
        CIdle[Idle Connections<br/>Gauge]
        CTot[Total Connections<br/>Gauge]
    end
```

---

## Deployment Architecture

### Production Deployment

```mermaid
graph TB
    subgraph "Load Balancer Layer"
        LB[Load Balancer<br/>HAProxy/nginx]
    end

    subgraph "MCP Server Cluster"
        S1[MCP Server 1]
        S2[MCP Server 2]
        S3[MCP Server 3]
    end

    subgraph "ImHex Instances"
        I1[ImHex Instance 1]
        I2[ImHex Instance 2]
        I3[ImHex Instance 3]
    end

    subgraph "Monitoring Stack"
        Prom[Prometheus<br/>Metrics Collection]
        Graf[Grafana<br/>Visualization]
        Alert[Alertmanager<br/>Alerts]
    end

    subgraph "Logging Stack"
        Log[Logging Service<br/>ELK/Loki]
    end

    Client[Clients] --> LB
    LB --> S1
    LB --> S2
    LB --> S3

    S1 --> I1
    S2 --> I2
    S3 --> I3

    S1 --> Prom
    S2 --> Prom
    S3 --> Prom

    Prom --> Graf
    Prom --> Alert

    S1 --> Log
    S2 --> Log
    S3 --> Log

    style LB fill:#ccccff
    style Prom fill:#ccffcc
```

### Docker Deployment

```mermaid
graph TB
    subgraph "Docker Host"
        subgraph "Network: imhex-mcp"
            MC[MCP Server Container<br/>Python 3.10+]
            IC[ImHex Container<br/>C++ Binary]
            PC[Prometheus Container<br/>Metrics]
            GC[Grafana Container<br/>Dashboard]
        end

        V1[Volume: config]
        V2[Volume: data]
        V3[Volume: prometheus-data]
        V4[Volume: grafana-data]
    end

    MC --> IC
    MC --> PC
    PC --> GC

    MC -.->|Mount| V1
    MC -.->|Mount| V2
    PC -.->|Mount| V3
    GC -.->|Mount| V4
```

---

**Version**: 1.0
**Last Updated**: 2025-11-14
**Maintained By**: ImHex MCP Team
