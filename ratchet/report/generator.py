"""Generate static HTML report from results.json."""

import json
from pathlib import Path


def generate_report(results_path: Path, output_path: Path):
    """Generate a single-page HTML report with comparison charts."""
    with open(results_path) as f:
        results = json.load(f)
    
    summary = results.get("summary", {})
    combined_v0 = results.get("combined_v0_baseline")
    
    versions = list(summary.keys())
    success_rates = []
    catastrophes = []
    
    for v in versions:
        data = summary[v]
        total = data.get("total_trials", 1)
        success_count = data.get("task_success_count", 0)
        success_rates.append(round(success_count / total * 100, 1))
        
        # Use combined V0 baseline if available
        if v == "v0" and combined_v0:
            catastrophes.append(combined_v0["combined"]["catastrophic_failure_count"])
        else:
            catastrophes.append(data.get("catastrophic_failure_count", 0))
    
    table_rows = _generate_table_rows(summary, combined_v0)
    footnote = _generate_footnote(combined_v0)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ratchet Benchmark Results</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
            padding: 2rem;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}
        h1 {{
            text-align: center;
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(90deg, #00d4ff, #7b2ff7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .tagline {{
            text-align: center;
            color: #888;
            font-style: italic;
            margin-bottom: 2rem;
        }}
        .charts-container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            margin-bottom: 2rem;
        }}
        .chart-card {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 1rem;
            padding: 1.5rem;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .chart-title {{
            text-align: center;
            margin-bottom: 1rem;
            font-size: 1.2rem;
            color: #ccc;
        }}
        .summary-table {{
            width: 100%;
            border-collapse: collapse;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 1rem;
            overflow: hidden;
        }}
        .summary-table th, .summary-table td {{
            padding: 1rem;
            text-align: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .summary-table th {{
            background: rgba(0, 212, 255, 0.2);
            font-weight: 600;
        }}
        .summary-table tr:last-child td {{
            border-bottom: none;
        }}
        .success {{
            color: #4ade80;
        }}
        .danger {{
            color: #f87171;
        }}
        .version-badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-weight: 600;
            font-size: 0.875rem;
        }}
        .v0 {{ background: #374151; }}
        .v1 {{ background: #1e40af; }}
        .v2 {{ background: #7c3aed; }}
        .v3 {{ background: #059669; }}
        .footnote {{
            text-align: center;
            color: #666;
            font-size: 0.875rem;
            margin-top: 1rem;
        }}
        footer {{
            text-align: center;
            margin-top: 2rem;
            color: #666;
            font-size: 0.875rem;
        }}
        @media (max-width: 768px) {{
            .charts-container {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Ratchet Benchmark Results</h1>
        <p class="tagline">Agent harness constraint benchmark</p>
        
        <div class="charts-container">
            <div class="chart-card">
                <h3 class="chart-title">Task Success Rate (%)</h3>
                <canvas id="successChart"></canvas>
            </div>
            <div class="chart-card">
                <h3 class="chart-title">Catastrophic Failures (count)</h3>
                <canvas id="failureChart"></canvas>
            </div>
        </div>
        
        <table class="summary-table">
            <thead>
                <tr>
                    <th>Version</th>
                    <th>Task Success</th>
                    <th>Success Rate</th>
                    <th>Catastrophic Failures</th>
                </tr>
            </thead>
            <tbody>
                {"".join(table_rows)}
            </tbody>
        </table>
        {footnote}
        <footer>
            Generated from benchmark/results.json
        </footer>
    </div>
    
    <script>
        const versions = {json.dumps(versions)};
        const successRates = {json.dumps(success_rates)};
        const catastrophes = {json.dumps(catastrophes)};
        
        const colors = {{
            v0: '#6b7280',
            v1: '#3b82f6',
            v2: '#8b5cf6',
            v3: '#10b981'
        }};
        
        new Chart(document.getElementById('successChart'), {{
            type: 'bar',
            data: {{
                labels: versions.map(v => v.toUpperCase()),
                datasets: [{{
                    label: 'Success Rate (%)',
                    data: successRates,
                    backgroundColor: versions.map(v => colors[v]),
                    borderRadius: 8,
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100,
                        grid: {{ color: 'rgba(255,255,255,0.1)' }},
                        ticks: {{ color: '#888' }}
                    }},
                    x: {{
                        grid: {{ display: false }},
                        ticks: {{ color: '#888' }}
                    }}
                }}
            }}
        }});
        
        new Chart(document.getElementById('failureChart'), {{
            type: 'bar',
            data: {{
                labels: versions.map(v => v.toUpperCase()),
                datasets: [{{
                    label: 'Catastrophic Failures',
                    data: catastrophes,
                    backgroundColor: '#ef4444',
                    borderRadius: 8,
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        grid: {{ color: 'rgba(255,255,255,0.1)' }},
                        ticks: {{ color: '#888', stepSize: 1 }}
                    }},
                    x: {{
                        grid: {{ display: false }},
                        ticks: {{ color: '#888' }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
    
    with open(output_path, "w") as f:
        f.write(html)


def _generate_table_rows(summary: dict, combined_v0: dict | None) -> list[str]:
    """Generate HTML table rows for each version."""
    rows = []
    for version, data in summary.items():
        total = data.get("total_trials", 1)
        success = data.get("task_success_count", 0)
        rate = round(success / total * 100, 1)
        
        # Use combined V0 baseline if available
        if version == "v0" and combined_v0:
            combined = combined_v0["combined"]
            catastrophe_text = f"{combined['catastrophic_failure_count']}/{combined['total_trials']}*"
            catastrophe = combined['catastrophic_failure_count']
        else:
            catastrophe = data.get("catastrophic_failure_count", 0)
            catastrophe_text = str(catastrophe)
        
        rows.append(f"""
            <tr>
                <td><span class="version-badge {version}">{version.upper()}</span></td>
                <td>{success}/{total}</td>
                <td class="success">{rate}%</td>
                <td class="{'danger' if catastrophe > 0 else ''}">{catastrophe_text}</td>
            </tr>
        """)
    return rows


def _generate_footnote(combined_v0: dict | None) -> str:
    """Generate footnote explaining V0 combined baseline if present."""
    if not combined_v0:
        return ""
    
    run1 = combined_v0.get("run_1_extended_trials", {})
    run2 = combined_v0.get("run_2_post_bugfix", {})
    
    run1_count = run1.get("catastrophic_failure_count", 0)
    run1_total = run1.get("total_trials", 0)
    run2_count = run2.get("catastrophic_failure_count", 0)
    run2_total = run2.get("total_trials", 0)
    
    return f"""
        <p class="footnote">
            *V0 was measured twice independently ({run1_count}/{run1_total} and {run2_count}/{run2_total} catastrophes). Combined rate shown.
        </p>
    """
