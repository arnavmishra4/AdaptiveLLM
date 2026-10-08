# AdaptiveLLM

Cost-aware, self-hosted LLM inference infrastructure. AdaptiveLLM routes each request to an appropriate local or cloud model, serves repeat and near-duplicate prompts from a semantic cache, and gives models access to MCP tools when needed.

> **Status:** an experimental, GPU-oriented reference implementation. It is designed to be run locally with Docker Compose and an NVIDIA GPU.

## What it does

- **Routes by task complexity.** A small local Qwen router selects `local-model` for inexpensive, straightforward work or `cloud-glm` for more demanding requests.
- **Serves a local model through vLLM.** The local inference path is exposed through an OpenAI-compatible API.
- **Uses LiteLLM as a gateway.** Local vLLM and the remote Hugging Face-routed GLM model are available behind one interface, with configured fallbacks.
- **Caches semantically similar requests.** Prompts are embedded with `Qwen/Qwen3-Embedding-0.6B` and stored in Redis Stack's vector index; cache entries expire after one hour.
- **Supports tool calls over MCP.** The router service fetches tools from an MCP server and can execute a web-search tool through SerpAPI.
- **Exposes operational endpoints.** Prometheus, Grafana, and NVIDIA DCGM Exporter are included in the Compose stack.

## Architecture

```text
Client
  |
  v
router_app :8080
  |-- semantic-cache :8090 --> Redis Stack :6379
  |       | cache hit: return saved response
  |
  |-- Qwen router --> local-model or cloud-glm
  |                         |
  |                         v
  |                  LiteLLM :4000
  |                   |              |
  |                   v              v
  |              vLLM :8000      Hugging Face router
  |
  `-- MCP tools :8095 --> SerpAPI web search

Prometheus :9090 <-- vLLM / LiteLLM / DCGM Exporter --> Grafana :3000
```

## Services

| Service | Purpose | Port |
| --- | --- | --- |
| `router_app` | Chat API, routing, cache orchestration, and tool-call loop | `8080` |
| `vllm` | Local OpenAI-compatible model serving | `8000` |
| `litellm-proxy` | Unified local/cloud model gateway | `4000` |
| `semantic-cache` | Embedding-based cache API | `8090` |
| `redis` | Redis Stack vector store | `6379` |
| `tools` | MCP tool server | `8095` |
| `prometheus` | Metrics collection | `9090` |
| `grafana` | Metrics visualization | `3000` |
| `nvidia-exporter` | GPU metrics exporter | `9835` |

## Prerequisites

- Docker Desktop or Docker Engine with Docker Compose v2
- NVIDIA GPU, current NVIDIA driver, and NVIDIA Container Toolkit
- A Hugging Face token with access to the selected model(s)
- A SerpAPI key if you want web-search tool calls
- Enough disk space for the Qwen router, embedding model, and the model served by vLLM

## Quick start

1. Clone the repository and enter it.

   ```bash
   git clone https://github.com/arnavmishra4/AdaptiveLLM.git
   cd AdaptiveLLM
   ```

2. Create a `.env` file. It is intentionally ignored by Git.

   ```dotenv
   # Absolute path to a writable directory used for Hugging Face model downloads
   HF_CACHE_PATH=/absolute/path/to/hf-cache

   # Required for gated/private Hugging Face models and the cloud gateway
   HF_TOKEN=your_huggingface_token

   # Model served by vLLM
   MODEL_NAME=Qwen/Qwen2.5-1.5B-Instruct

   # Required only for the MCP web-search tool
   SERP_API=your_serpapi_key
   ```

3. Start the stack.

   ```bash
   docker compose up --build
   ```

   The first run downloads several models and can take a while. Follow startup logs with:

   ```bash
   docker compose logs -f router_app vllm semantic-cache
   ```

4. Send a request once the services are healthy.

   ```bash
   curl -X POST http://localhost:8080/chat \
     -H "Content-Type: application/json" \
     -d '{"text":"Summarize the benefits of semantic caching."}'
   ```

   Example response:

   ```json
   {
     "reply": "...",
     "model_used": "local-model"
   }
   ```

## API

### `POST /chat`

Routes a prompt, checks the semantic cache first, optionally runs MCP tools, and returns the response.

```json
{
  "text": "What are the latest developments in quantum computing?",
  "history": [
    {"role": "user", "content": "Earlier question"},
    {"role": "assistant", "content": "Earlier answer"}
  ]
}
```

`history` is optional. A cache hit reports `"model_used": "cache"`.

### Health checks

```bash
curl http://localhost:8080/health
curl http://localhost:8090/health
```

## Routing and caching

The router uses `Qwen/Qwen3-0.6B` with a constrained prompt that returns one of two model names:

| Choice | Best for |
| --- | --- |
| `local-model` | Simple writing, summarization, formatting, basic coding, and classification |
| `cloud-glm` | Multi-step analysis, research synthesis, current information, and high-accuracy tasks |

Before routing, AdaptiveLLM checks Redis for the closest prompt embedding. A result with cosine distance below `0.15` is returned directly; otherwise the completed response is cached for 3,600 seconds.

LiteLLM fallbacks are configured in `config.yaml`: if one backend is unavailable, it can fall back to the other.

## Observability

- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`
- GPU metrics: DCGM Exporter is available at `http://localhost:9835/metrics`

The provided Prometheus configuration scrapes vLLM, LiteLLM, and DCGM Exporter every 15 seconds.

## Project layout

```text
.
├── Agentic_tools/       # MCP server and SerpAPI-backed web-search tool
├── observability/       # Prometheus scrape configuration
├── router_app/          # FastAPI chat API and local Qwen router
├── semantic_cache/      # FastAPI cache service and Redis vector index
├── config.yaml          # LiteLLM model and fallback configuration
├── docker-compose.yml   # Full local deployment
└── main.py              # Minimal interactive client
```

## Configuration notes

- Keep `.env` private. Do not commit tokens, API keys, or local cache paths.
- `config.yaml` controls LiteLLM models and fallback behavior. Change it to use a different cloud provider or local model.
- The vLLM service includes a commented EAGLE-3 speculative-decoding configuration. Enable and benchmark it only after verifying model compatibility.
- GPU resource declarations in `docker-compose.yml` require NVIDIA Container Toolkit support.

## Known limitations

- The router, embedding model, and vLLM model each download independently on first use; cold starts are significant.
- Cache similarity is based solely on prompt embeddings. It does not account for conversation history, model selection, or tool availability.
- The bundled Prometheus path in `docker-compose.yml` is case-sensitive on Linux. Ensure it points to `./observability/prometheus.yml`.
- Treat the included configuration as a development setup. Use a secret manager, authentication, TLS, rate limits, and persistent monitoring before exposing it publicly.

## Contributing

Issues and pull requests are welcome. For changes that affect routing, cache behavior, or model configuration, include a reproducible request and note the local/cloud model used.

## License

No license has been specified yet. Add one before distributing or accepting external contributions.
