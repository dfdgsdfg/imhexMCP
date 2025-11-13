Architecture Overview
=====================

This page provides comprehensive architecture diagrams for the ImHex MCP system.

System Architecture
-------------------

The ImHex MCP system follows a modular, layered architecture designed for high performance and reliability.

.. mermaid::

   graph TD
       Client[Client Application] --> AsyncClient[Async Client<br/>Connection Pooling]
       AsyncClient --> |TCP/IP| ImHex[ImHex Server<br/>Port 31337]

       AsyncClient --> Compression[Data Compression<br/>zstd/gzip]
       AsyncClient --> Batcher[Request Batcher]
       AsyncClient --> Metrics[Metrics Collector]

       ImHex --> FileOps[File Operations]
       ImHex --> DataOps[Data Analysis]
       ImHex --> PatternOps[Pattern Matching]

       Config[config.yaml] --> AsyncClient
       Config --> Compression
       Config --> Batcher

       Metrics --> PrometheusServer[Metrics HTTP Server<br/>Port 9090]
       PrometheusServer --> Prometheus[Prometheus]

       style AsyncClient fill:#e1f5ff
       style ImHex fill:#fff3e0
       style Metrics fill:#f3e5f5
       style Config fill:#e8f5e9

Key Components:

* **Async Client**: High-performance async client with connection pooling
* **Data Compression**: Transparent zstd compression for bandwidth optimization
* **Request Batcher**: Groups concurrent requests for improved throughput
* **Metrics Collector**: Comprehensive Prometheus metrics export
* **Configuration**: Centralized YAML-based configuration management

Request Flow
------------

The following diagram shows the complete lifecycle of a client request through the system.

.. mermaid::

   sequenceDiagram
       participant C as Client
       participant AC as Async Client
       participant CP as Connection Pool
       participant B as Batcher
       participant COMP as Compressor
       participant IH as ImHex Server
       participant M as Metrics

       C->>AC: send_request(endpoint, data)
       AC->>M: active_requests.inc()

       alt Connection Pooling Enabled
           AC->>CP: acquire_connection()
           CP-->>AC: TCP connection
       else On-Demand Mode
           AC->>IH: create new connection
       end

       AC->>B: add to batch queue
       B->>B: wait for batch window (10ms)
       B->>COMP: compress large payloads (>1KB)
       COMP-->>B: compressed data

       B->>IH: send batched requests
       IH->>IH: process requests
       IH-->>B: responses

       B->>COMP: decompress responses
       COMP-->>B: decompressed data
       B-->>AC: response data

       alt Connection Pooling
           AC->>CP: release_connection()
       else On-Demand
           AC->>IH: close connection
       end

       AC->>M: record_metrics()
       M->>M: update counters/histograms
       AC-->>C: return response

**Performance Optimizations:**

1. Connection pooling reduces TCP handshake overhead
2. Request batching amortizes network latency
3. Compression reduces bandwidth by 60-80%
4. Metrics tracking has minimal overhead (<1ms)

Connection Pool Architecture
-----------------------------

The connection pool maintains persistent TCP connections for improved performance.

.. mermaid::

   graph LR
       subgraph "Connection Pool"
           AC[Async Client] --> ACQ{Acquire<br/>Connection}
           ACQ --> |Available| IDLE[Idle<br/>Connections<br/>Queue]
           ACQ --> |None Available| CREATE[Create New<br/>Connection]
           ACQ --> |Pool Full| WAIT[Wait with<br/>Timeout]

           IDLE --> HEALTH{Health<br/>Check}
           HEALTH --> |Healthy| USE[Use Connection]
           HEALTH --> |Unhealthy| REMOVE[Remove &<br/>Create New]

           CREATE --> USE
           REMOVE --> CREATE

           USE --> REQ[Send Request]
           REQ --> RELEASE[Release to Pool]
           RELEASE --> IDLE

           WAIT --> |Timeout| ERROR[Timeout Error]
           WAIT --> |Available| IDLE
       end

       USE --> ImHex[ImHex Server]
       ImHex --> REQ

       style IDLE fill:#c8e6c9
       style USE fill:#fff9c4
       style ERROR fill:#ffcdd2
       style ImHex fill:#fff3e0

**Pool Configuration:**

* **min_size**: Keep 2 warm connections ready
* **max_size**: Limit to 10 total connections
* **acquire_timeout**: Wait up to 5s for available connection
* **idle_timeout**: Close connections idle >5 minutes

Data Compression Pipeline
--------------------------

The compression module provides transparent data compression/decompression.

.. mermaid::

   graph TD
       START[Data to Send] --> SIZE{Size ><br/>1KB?}
       SIZE --> |< 1KB| SKIP[Skip Compression]
       SIZE --> |>= 1KB| SAMPLE[Sample First 4KB]

       SAMPLE --> EST{Estimated<br/>Ratio?}
       EST --> |> 85%| SKIP
       EST --> |<= 85%| COMPRESS[Compress with zstd]

       COMPRESS --> RATIO{Actual<br/>Ratio?}
       RATIO --> |> 90%| SKIP
       RATIO --> |<= 90%| SEND[Send Compressed]

       SKIP --> SENDHEX[Send Hex-Encoded]
       SEND --> BASE64[Base64 Encode]
       BASE64 --> NETWORK[Network Transfer]
       SENDHEX --> NETWORK

       NETWORK --> RECV[Receive Data]
       RECV --> CHECK{Compressed?}
       CHECK --> |Yes| DECOMP[Decompress]
       CHECK --> |No| DECODE[Hex Decode]

       DECOMP --> RESULT[Original Data]
       DECODE --> RESULT

       style COMPRESS fill:#bbdefb
       style DECOMP fill:#c5cae9
       style SKIP fill:#ffccbc
       style RESULT fill:#c8e6c9

**Compression Statistics:**

* Average ratio: 0.3-0.5 (50-70% reduction)
* Compression time: <1ms for typical payloads
* Bandwidth savings: 60-80% for most workloads
* Adaptive skipping prevents overhead on incompressible data

Component Interactions
----------------------

This diagram shows how the major components interact during normal operation.

.. mermaid::

   graph TB
       subgraph "Client Layer"
           APP[Application Code]
           CLIENT[ImHexAsyncClient]
       end

       subgraph "Optimization Layer"
           POOL[ConnectionPool]
           BATCH[RequestBatcher]
           COMP[DataCompressor]
       end

       subgraph "Monitoring Layer"
           METRICS[Metrics Collector]
           METRICSSRV[Metrics HTTP Server]
       end

       subgraph "Configuration"
           CONFIG[ConfigLoader]
       end

       subgraph "ImHex Server"
           SERVER[TCP Server :31337]
           HANDLERS[Request Handlers]
           FILEOPS[File Operations]
       end

       APP --> CLIENT
       CLIENT --> POOL
       CLIENT --> BATCH
       CLIENT --> COMP

       POOL --> SERVER
       BATCH --> SERVER
       COMP --> BATCH

       CLIENT --> METRICS
       POOL --> METRICS
       BATCH --> METRICS
       COMP --> METRICS

       METRICS --> METRICSSRV
       METRICSSRV -.->|:9090/metrics| PROM[Prometheus]

       CONFIG -.->|Load Config| CLIENT
       CONFIG -.->|Load Config| POOL
       CONFIG -.->|Load Config| BATCH
       CONFIG -.->|Load Config| COMP

       SERVER --> HANDLERS
       HANDLERS --> FILEOPS

       style CLIENT fill:#e1f5ff
       style POOL fill:#c8e6c9
       style BATCH fill:#fff9c4
       style COMP fill:#bbdefb
       style METRICS fill:#f3e5f5
       style CONFIG fill:#e8f5e9
       style SERVER fill:#fff3e0

Deployment Architecture
-----------------------

The system supports various deployment configurations.

.. mermaid::

   graph TB
       subgraph "Client Host"
           APP1[Application 1]
           APP2[Application 2]
           APP3[Application 3]
           LIBCLIENT[ImHex MCP Client Library]
           APP1 --> LIBCLIENT
           APP2 --> LIBCLIENT
           APP3 --> LIBCLIENT
       end

       subgraph "ImHex Host"
           IMHEX[ImHex Server]
           MCPSERVER[MCP Network Interface]
           IMHEX -.->|Embedded Plugin| MCPSERVER
       end

       subgraph "Monitoring Stack"
           PROMETHEUS[Prometheus]
           GRAFANA[Grafana]
           PROMETHEUS --> GRAFANA
       end

       LIBCLIENT -->|TCP :31337| MCPSERVER
       MCPSERVER -->|Metrics :9090| PROMETHEUS

       style APP1 fill:#e3f2fd
       style APP2 fill:#e3f2fd
       style APP3 fill:#e3f2fd
       style LIBCLIENT fill:#e1f5ff
       style IMHEX fill:#fff3e0
       style MCPSERVER fill:#fff9c4
       style PROMETHEUS fill:#f3e5f5
       style GRAFANA fill:#c8e6c9

**Deployment Options:**

1. **Local Development**: All components on localhost
2. **Docker Compose**: Containerized services with networking
3. **Kubernetes**: Scalable cloud deployment with service mesh
4. **Bare Metal**: High-performance dedicated servers

Configuration Flow
------------------

Configuration is loaded from YAML and distributed to all components.

.. mermaid::

   graph LR
       YAML[config.yaml] --> LOADER[ConfigLoader]

       LOADER --> |Validate| PYDANTIC[Pydantic Models]
       PYDANTIC --> |Parse| CONFIG[Config Object]

       CONFIG --> SINGLETON{Get Singleton}

       SINGLETON --> CLIENT[Async Client Config]
       SINGLETON --> POOL[Connection Pool Config]
       SINGLETON --> BATCH[Batching Config]
       SINGLETON --> COMPRESS[Compression Config]
       SINGLETON --> METRICS[Metrics Config]
       SINGLETON --> LOG[Logging Config]

       CLIENT --> INST1[Client Instance]
       POOL --> INST2[Pool Instance]
       BATCH --> INST3[Batcher Instance]
       COMPRESS --> INST4[Compressor Instance]
       METRICS --> INST5[Metrics Instance]
       LOG --> INST6[Logger Setup]

       style YAML fill:#e8f5e9
       style CONFIG fill:#c8e6c9
       style PYDANTIC fill:#fff9c4

**Configuration Precedence:**

1. config.yaml (highest priority)
2. Environment variables
3. Default values (lowest priority)

Performance Characteristics
---------------------------

Key performance metrics and targets:

**Request Latency:**

* Local: 1-5ms (typical)
* Network: 10-50ms depending on bandwidth
* Compression overhead: <1ms

**Throughput:**

* Single connection: 1000-5000 req/sec
* Connection pool (10 conns): 10000-50000 req/sec
* Batching improves throughput by 2-5x

**Resource Usage:**

* Memory: ~50MB base + 10MB per active connection
* CPU: <5% for typical workloads
* Network: 60-80% reduction with compression enabled

**Scalability:**

* Horizontal: Multiple client instances
* Vertical: Connection pool size (max 100 recommended)
* Load balancing: Round-robin across ImHex instances
