"""Junta os resultados de uma rodada (uma pasta por volume) numa tabela só.

Uso: python load/summarize.py load/results/<rodada>

Lê seed-<N>/vegeta-*.json, seed-<N>/locust_stats.csv e counts.csv, e grava
summary.csv e summary.md na pasta da rodada (o .md também vai para a saída).
Com a tabela ordenada por volume dá para ver em que tamanho de banco a
latência de cada cenário começa a subir.
"""

import csv
import json
import sys
from pathlib import Path

VEGETA_SCENARIOS = ["read", "list", "write"]
# Linhas do Locust que entram no resumo (nomes definidos no locustfile.py).
LOCUST_ROWS = ["/tasks?status=pending", "Aggregated"]
COLUMNS = [
    "volume",
    "cenário",
    "p50 ms",
    "p95 ms",
    "p99 ms",
    "req/s",
    "falhas",
    "bytes/resp",
    "total início",
    "total fim",
    "pendentes início",
    "pendentes fim",
]


def vegeta_row(path: Path):
    report = json.loads(path.read_text())
    latency = report["latencies"]
    return {
        "p50 ms": latency["50th"] / 1e6,
        "p95 ms": latency["95th"] / 1e6,
        "p99 ms": latency["99th"] / 1e6,
        "req/s": report["throughput"],
        "falhas": report["requests"] - round(report["success"] * report["requests"]),
        "bytes/resp": report["bytes_in"]["mean"],
    }


def locust_rows(path: Path):
    with path.open() as file:
        for row in csv.DictReader(file):
            if row["Name"] in LOCUST_ROWS:
                yield row["Name"], {
                    "p50 ms": float(row["50%"]),
                    "p95 ms": float(row["95%"]),
                    "p99 ms": float(row["99%"]),
                    "req/s": float(row["Requests/s"]),
                    "falhas": int(row["Failure Count"]),
                    "bytes/resp": float(row["Average Content Size"]),
                }


def read_counts(path: Path):
    """{(volume, servidor): {"início": (total, pendentes), "fim": (...)}}"""
    counts = {}
    if path.exists():
        with path.open() as file:
            for row in csv.DictReader(file):
                key = (int(row["volume"]), row["scenario"])
                counts.setdefault(key, {})[row["phase"]] = (row["total"], row["pending"])
    return counts


def collect(run: Path):
    counts = read_counts(run / "counts.csv")
    rows = []
    for volume_dir in sorted(run.glob("seed-*"), key=lambda path: int(path.name.split("-")[1])):
        volume = int(volume_dir.name.split("-")[1])
        measured = []
        for scenario in VEGETA_SCENARIOS:
            report = volume_dir / f"vegeta-{scenario}.json"
            if report.exists():
                # "list" roda no mesmo servidor/banco que "read" (os dois só leem).
                server = "vegeta-write" if scenario == "write" else "vegeta-read"
                measured.append((f"vegeta {scenario}", server, vegeta_row(report)))
        stats = volume_dir / "locust_stats.csv"
        if stats.exists():
            measured += [(f"locust {name}", "locust", row) for name, row in locust_rows(stats)]

        for scenario, server, row in measured:
            phases = counts.get((volume, server), {})
            start, end = phases.get("início", ("", "")), phases.get("fim", ("", ""))
            rows.append(
                {
                    "volume": volume,
                    "cenário": scenario,
                    **row,
                    "total início": start[0],
                    "total fim": end[0],
                    "pendentes início": start[1],
                    "pendentes fim": end[1],
                }
            )
    return rows


def fmt(value):
    if isinstance(value, float):
        return f"{value:.1f}" if value < 100 else f"{value:.0f}"
    return str(value)


def to_markdown(rows):
    lines = ["| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS)]
    lines += ["| " + " | ".join(fmt(row[column]) for column in COLUMNS) + " |" for row in rows]
    return "\n".join(lines) + "\n"


def main():
    run = Path(sys.argv[1])
    rows = collect(run)
    with (run / "summary.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    markdown = to_markdown(rows)
    (run / "summary.md").write_text(markdown)
    print(markdown, end="")


if __name__ == "__main__":
    main()
