# Decisions

Single source of truth. Each entry is the decision plus why, in one or two lines, updated in place.

## Made
- **Vision (2026-10-10):** `amd/vision` (:8084) computes thermal/gauge readings and comparisons in CPU code; the VLM only explains citable V# evidence. Contract: `docs/vision-contract.md`.
- **Phase (2026-10-09):** Research done; now building.
- **Idea (2026-10-09):** an operator dashboard for NextEra's SPOT challenge (live replay + post-mission review). It's the only prompt with an internship prize, and sponsor tracks reward literal, on-prompt answers (winners-knighthacks-history).
- **Sponsor targets:** NextEra (core), Hugging Face, AMD, Neon, Figma, plus the auto-entered general tracks. Every sponsor's tech must be load-bearing, not a logo (synthesis §5: "sponsormaxxing").
- **Stack:** Next.js web app + Neon Postgres (operational DB) + AMD-hosted HF models (Laya for failure risk, an LLM/VLM for System 2). The user chose it; it maps one sponsor to each layer.
- **Two-tier AI:** System 1 = fast, explainable rule/statistics triage running locally; System 2 = an HF open-source model on AMD ROCm that explains escalated flags. This puts hard gates first and the LLM second (lablab "LLM proposes, gates decide"), and gives a measurable routing saving for AMD judges.
- **Repo layout (2026-10-10):** one repo (`SpotTheDOT`). AMD-side code lives in `amd/` with its own Python deps and runs on the Radeon Cloud box; the app talks to it only over HTTP. Judges review one public repo, and API-contract changes land in one commit.
- **Databricks dropped (2026-10-10).** We stick to AMD servers: Laya, fine-tuned on AMD, produces the failure-risk scores, and the analytics become SQL views in Neon. That's one fewer platform, and all model work stays on AMD.
- **System 2 context = custom read-only MCP server doing RAG on pgvector in Neon (2026-10-10).** Tools embed a query with an open-source embedding model hosted on AMD and retrieve from Neon pgvector with metadata filters; numeric stats stay plain SQL. Embedding model: **Qwen3-Embedding-0.6B** (1024-d, Apache-2.0; fallback snowflake-arctic-embed-l-v2.0), exact vector search at our scale (`research/tech-embedding-model-amd-2026-10-10.md`).
- **Logs + raw data in Neon (2026-10-10):** same database, schemas `raw` (SPOT data verbatim, append-only) and `app` (model calls, MCP tool calls, requests, jobs); `LOGS_DATABASE_URL` can split them out later. One connection string, and logs join to flags.
- **Containerize everything (2026-10-10):** every service ships a Dockerfile and joins a root docker-compose.yml, so the whole stack starts with one command; on the no-root AMD Jupyter VMs the same code runs in a venv.
- **Backend = FastAPI (2026-10-10)** in `backend/`, its own container: same language as Laya, the validator and the MCP client. Route tree in `docs/backend-services-contract.md`.
- **Laya runs in its own container (2026-10-10)** (`amd/system1/service/`, port 8082), called by the backend over HTTP; keeps the GPU/model concerns out of the API.
- **Keep LoRA for the Laya fine-tune (2026-10-10).** PEFT ports to other HF models. The gap vs full FT (run2 0.805 vs 0.733 real, 0.846 vs 0.602 counterfactual) most likely comes from setup (to be confirmed by the sweep): 3 epochs, LLRD on adapters, frozen norms, no training counterfactuals. Fixed in code and swept via `scripts/sweep_lora.sh`; compare on held-out F1/calib CE, never train loss.
- **System 2 output mirrors Orbit's AI-inspection format** (question / answer / reasoning, plus a recommended action). NextEra operators already use Orbit (kit screenshots).

- **System 2 plan (2026-10-10):** prompt + grammar-JSON + deterministic post-check first; LoRA is a gated stretch, shipped only if it beats the prompt baseline. Fine-tuning teaches format, not facts (research R5).
- **System 2 model (2026-10-10, provisional):** Qwen3.5-9B Q4_K_M serves for now (AMD 2026-10-10: 5/5 first-attempt accepted, p95 7.9 s ≤ 15 s; `amd/system2/results/eval/README.md`). The 27B / 35B-A3B bake-off on the same harness is pending AMD box availability; switch only if one wins within 15 s p95.
- **System 2 owns the flag contract (2026-10-10):** typed Pydantic contract, with flags faked from `policy.py` until Laya output is wired in, so System 2 isn't blocked on System 1.
- **System 2 adapts to the backend stack (2026-10-10, after 8aaac30):** the backend owns retrieval and POSTs one prepared MCP `get_flag_context` packet to System 2 on port 8083; the model does not call tools (tool loops break the ≤15 s p95). System 2 accepts the backend's request shape (unknown fields ignored, consumed fields validated, strict output), MCP action codes and doc_id citations, and drops its own CSV packet builder in favour of saved MCP packets.
- **System 2 eval leakage rule (2026-10-10):** headline numbers only on controlled held-out packets with nothing after the event's time, no target labels and no previously generated explanations; action quality is scored against human labels, with agreement against the validator's `suggested_action` reported separately.
- **AMD serving works on ROCm (2026-10-10):** Qwen3.5-9B Q4_K_M via a llama.cpp HIP build for gfx1151 ran fully on the GPU, 3/3 schema-valid replies, 35.6 tok/s generation, 12.4 s for 439 output tokens. Vulkan stays a fallback only.
- **System 2 eval (2026-10-10):** headline numbers on real mission-held-out flags only, with bootstrap CIs and a human-checked judge; the templated explanation is both the fallback and the baseline. Only ~40 real anomalies, so synthetic data can't inflate the numbers.

## Pending
- **Qwen vision fine-tune:** remains a separate, gated stretch in `docs/TEAMMATE-qwen-vision-finetune.md`; phase-one CPU service is defined above.
- **LiteLLM gateway (:4000) and LangGraph orchestrator (:8085)** from the same brief: not built, no contract yet. Laya isn't an OpenAI-style model, so a gateway alias for it needs a custom handler.
- Exact ROCm serving stack on gfx1151 (research agent running).
- Roles.
