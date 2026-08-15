# Ratchet

**Agent harness evaluation framework that proves deliberate harness engineering measurably improves reliability.**

> Every failure becomes a permanent fix. Ratchet only tightens.

## Results

| Version | Description | Task Success | Catastrophic Failures |
|---------|-------------|--------------|----------------------|
| **V0** | Bare agent - no restrictions | 70% | **10/60 (17%)** |
| **V1** | V0 + AGENTS.md rules (advisory) | 70% | **0/30** |
| **V2** | High-level tools + permission layer | 73% | **0/30** |
| **V3** | V2 + forced verification | 70% | **0/30** |

**Key finding**: Across 60 combined V0 trials, catastrophic failures occurred at a rate of approximately 17%. Every harnessed version (V1, V2, V3) recorded zero catastrophic failures across 30 trials each. Task success held steady across all four versions (70-73%)—within the expected noise range at this sample size—meaning the constraints added for safety did not come at a measurable capability cost, once two implementation bugs were fixed and accounted for.

**Note on V0 variance**: V0 was measured twice independently with no code changes between runs: 7/30 (23%) and 3/30 (10%) catastrophic failures. The combined rate of 10/60 (17%) is reported above. This variance is expected with LLM-based agents and is reported transparently rather than cherry-picking either single run.

## The Thesis

Most "I built an AI agent" projects show a demo with no evidence it's reliable. Ratchet proves, with real measured numbers, that deliberate harness engineering (guardrails, constraints, verification) measurably improves an agent's reliability compared to a bare, unconstrained agent.

## What Each Version Does

### V0 — Bare
Basic agent loop with low-level tools (`read_file`, `write_file`, `delete_file`, `run_shell`). No restrictions, no guidance. Purpose: establish a real baseline including real failures.

### V1 — Guides  
Same tools as V0, plus `AGENTS.md` rules loaded into the system prompt. Rules are advisory only—the agent can still ignore them. Tests whether *telling* the agent the rules is sufficient.

### V2 — Hard Constraints
Completely different tool surface: high-level action tools (`reorganize_files`, `archive_logs`, `delete_duplicates`, etc.) with safety built in. Includes:
- Permission layer with deny-list for protected paths
- Dry-run preview for destructive operations
- The model cannot call raw `delete_file`—it must go through the constrained interface

### V3 — Verified
Everything from V2, plus a forced verification step. The agent cannot claim "done" until `report_done()` is called, which triggers scenario-specific checks that verify the actual sandbox state.

## Methodology

### Practice/Benchmark Split
- **4 practice scenarios**: Used during V0 development to discover failures. Fed `FAILURE_LOG.md` and `AGENTS.md`.
- **10 benchmark scenarios**: Kept sealed until the final evaluation. Never seen during harness development.

This prevents overfitting—the harness wasn't tuned to pass specific benchmark tests.

### Statistical Validity
Each version runs each scenario **3 times** (30 trials per version, 120 total). Results are reported as fractions of 30, not single-run pass/fail.

### Independent Metrics
- **Task success**: Did the agent complete the intended cleanup correctly?
- **Catastrophic failure**: Did the agent delete/damage protected files?

These are tracked separately. An agent can fail a task without causing a catastrophe, or (rarely) complete a task while still causing damage.

## Quick Start

```bash
# Install
pip install -e .

# Set your DeepSeek API key
cp .env.example .env
# Edit .env and add your key

# Run a single scenario
ratchet run --version v0 --task messy_downloads --practice

# Run full benchmark (warning: ~50 minutes, 120 API calls)
ratchet bench --all-versions

# Generate HTML report
ratchet report
```

## Project Structure

```
ratchet/
├── ratchet/
│   ├── cli.py              # CLI commands: run, bench, report
│   ├── agent/
│   │   ├── loop.py         # Core agent loop (hand-written, no framework)
│   │   ├── tools_v0.py     # Low-level tools for V0/V1
│   │   ├── tools_v2.py     # High-level tools for V2/V3
│   │   ├── permissions.py  # V2+ deny-list permission checker
│   │   └── verification.py # V3 verification hook
│   └── ...
├── benchmark/
│   ├── practice/           # 4 scenarios for failure discovery
│   ├── scenarios/          # 10 sealed benchmark scenarios
│   └── results.json        # Raw trial data
├── FAILURE_LOG.md          # Real failures from V0 practice runs
├── AGENTS.md               # Rules derived from observed failures
└── report.html             # Visual comparison chart
```

## Tech Stack

- **Model**: DeepSeek-chat via OpenAI-compatible API
- **Agent loop**: Hand-written (no LangChain, no agent framework)
- **CLI**: Typer
- **Output**: Rich tables and progress bars
- **Tracing**: Structured JSON logs per run

## Detailed Analysis

See `FINDINGS.md` for in-depth analysis including:
- V0 catastrophe rate variance (23% vs 10% across runs, combined 17%)
- Root cause of initial task success regression (bugs, not capability tradeoffs)
- Why task success differences (70-73%) are within noise at n=30
- V3 verification effectiveness assessment
- Bugs identified and fixed during analysis

## Observed Failures

See `FAILURE_LOG.md` for documented V0 failures:

1. **Deleted protected backup files** — When told to "delete all .bak files", V0 deleted critical config backups
2. **Claimed done without verification** — V0 hit max iterations while stuck debugging, never confirmed success
3. **Wasted iterations** — Kept running verification commands after task was complete

Each rule in `AGENTS.md` traces directly to one of these failures.

## License

MIT
