# Ratchet

A small benchmark for testing whether agent harness constraints reduce dangerous actions.

## What this is

I kept seeing agent reliability framed as "use a better model" or "write better prompts." I wanted to test a narrower question: **what happens if I keep the model the same and only change what the environment lets it do?**

Ratchet runs a simple "repo janitor" agent through 10 filesystem cleanup scenarios with four different harness configurations:

| Version | What changes | Tools |
|---------|--------------|-------|
| V0 | Nothing - raw tools, no guidance | `read_file`, `write_file`, `delete_file`, `run_shell` |
| V1 | Same tools + written rules in the system prompt | Same as V0 |
| V2 | Higher-level tools with built-in safety | `reorganize_files`, `archive_logs`, `delete_files` (with permissions + dry-run) |
| V3 | V2 + mandatory verification before completion | Same as V2 + `report_done()` triggers checks |

The key distinction being tested:
- **V1**: The agent is *told* not to delete protected files
- **V2/V3**: The agent *cannot* delete protected files (permission layer blocks it)

## Results

| Version | Task Success | Catastrophic Failures |
|---------|--------------|----------------------|
| V0 | 21/30 (70%) | 10/60 (17%) |
| V1 | 21/30 (70%) | 0/30 |
| V2 | 22/30 (73%) | 0/30 |
| V3 | 21/30 (70%) | 0/30 |

**What I observed:**
- V0's catastrophe rate varied between runs (7/30 in one run, 3/30 in another). The combined 10/60 is reported rather than cherry-picking either.
- V1-V3 had zero catastrophic failures across 30 trials each.
- Task success stayed in the 70-73% range for all versions.

**What I think this means:**
- For these scenarios, system prompt rules (V1) were enough to prevent catastrophes.
- Hard constraints (V2/V3) provide defense-in-depth but didn't show additional benefit in this limited test.
- The safety constraints didn't measurably hurt task completion.

**What this doesn't prove:**
- Zero observed failures ≠ zero probability of failure
- 30 trials per version is small
- This is one model (DeepSeek) on synthetic local filesystem tasks
- Results might not transfer to other models, longer tasks, or real-world scenarios

## Quick start

```bash
# Clone and install
git clone https://github.com/zohaib-md/ratchet.git
cd ratchet
pip install -e .

# Configure API key
cp .env.example .env
# Edit .env and add your DeepSeek API key

# Run a single scenario
ratchet run --version v0 --task messy_downloads --practice

# Run full benchmark (~50 minutes, 120 API calls)
ratchet bench --all-versions

# Generate HTML report from results
ratchet report
```

Requires Python 3.11+ and a [DeepSeek API key](https://platform.deepseek.com/).

## How the experiment works

### Practice vs. Benchmark split

I developed the harness against 4 practice scenarios, logging failures to `FAILURE_LOG.md` and adding rules to `AGENTS.md`. The 10 benchmark scenarios were kept sealed until final evaluation to avoid overfitting.

### What gets measured

- **Task success**: Did the agent complete the cleanup task correctly?
- **Catastrophic failure**: Did the agent delete or damage protected files?

These are tracked separately. An agent can fail a task without causing a catastrophe (incomplete work) or complete a task while still causing damage (rare).

### Trial methodology

Each version runs each scenario 3 times (30 trials per version). V0 was run twice independently to get a better sense of variance, giving 60 total V0 trials.

## Project structure

```
ratchet/
├── ratchet/
│   ├── cli.py              # CLI: run, bench, report
│   ├── agent/
│   │   ├── loop.py         # Core agent loop
│   │   ├── tools_v0.py     # Low-level tools (V0/V1)
│   │   ├── tools_v2.py     # High-level tools (V2/V3)
│   │   ├── permissions.py  # Path deny-list
│   │   └── verification.py # V3 verification
│   └── ...
├── benchmark/
│   ├── practice/           # 4 development scenarios
│   ├── scenarios/          # 10 sealed benchmark scenarios
│   └── results.json        # Raw trial data
├── FAILURE_LOG.md          # Failures observed during V0 development
├── AGENTS.md               # Rules derived from failures
└── FINDINGS.md             # Detailed analysis
```

## Limitations

This experiment has significant limitations:

- **One model**: All results are from DeepSeek-chat. Other models may behave differently.
- **Small sample**: 30 trials per version is enough to see large effects but not enough to detect small differences or estimate precise failure rates.
- **Synthetic tasks**: The scenarios are local filesystem cleanup tasks I created. They don't represent real-world agent workloads.
- **Short horizon**: Each task completes in under 10 turns. Longer tasks might show different failure patterns.
- **No adversarial testing**: The scenarios test normal operation, not adversarial prompts or jailbreaks.
- **Zero ≠ impossible**: Observing zero catastrophic failures in 30 trials doesn't mean the probability is zero.

## Why I built this

Most agent benchmarks measure capability (can the agent solve this task?). I wanted to measure something different: given a fixed capability level, can the environment make dangerous actions less likely?

The "ratchet" idea is that every observed failure should become a permanent fix—either a rule the agent sees or a constraint it can't bypass. The harness should only tighten.

## Development note

This project was built with AI coding tools (Cursor). The experiment design, analysis, and documentation reflect my own decisions about what to test and how to interpret results.

## License

MIT
