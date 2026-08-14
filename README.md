# Ratchet

> Every failure becomes a permanent fix. Ratchet only tightens.

Agent harness evaluation framework that proves deliberate harness engineering measurably improves agent reliability.

## Status

**Work in progress** - Results will be added after benchmark runs complete.

## Quick Start

```bash
# Install
pip install -e .

# Set your DeepSeek API key
export DEEPSEEK_API_KEY=your_key_here

# Run a single scenario
ratchet run --version v0 --task messy_downloads --practice

# Run full benchmark
ratchet bench --all-versions

# Generate report
ratchet report
```

## The Thesis

Most "I built an AI agent" projects show a demo with no evidence it's reliable. Ratchet proves, with real measured numbers, that deliberate harness engineering (guardrails, constraints, verification) measurably improves an agent's reliability compared to a bare, unconstrained agent.

## Versions

| Version | Description |
|---------|-------------|
| V0 | Bare agent loop - no restrictions, no guidance |
| V1 | V0 + AGENTS.md rules loaded into prompt (advisory only) |
| V2 | High-level action tools with permission layer and dry-run |
| V3 | V2 + forced verification before completion |

## Results

*Results will be populated after running the benchmark.*

## Methodology

- **Practice/Benchmark split**: 4 practice scenarios used to discover V0 failures, 10 benchmark scenarios kept sealed until evaluation
- **3 trials per scenario**: Each version runs each scenario 3 times to account for LLM variance
- **Independent metrics**: Task success and catastrophic failures tracked separately

See `FAILURE_LOG.md` for documented failures and `AGENTS.md` for rules derived from them.
