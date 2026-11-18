"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
from itertools import product
from math import isclose, isfinite
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, aggregate, load_spec, per_item
from lab9.graders import GRADERS


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems = []
    graded = {m["id"] for m in spec["metrics"] if m["id"] in GRADERS}
    tags_by_report = []
    for name, report in (("PR", pr), ("baseline", base)):
        manifest, rows = report["manifest"], report["rows"]
        seeds = manifest["seeds"]
        tags = {(r["item_id"], r["seed"]): frozenset(r.get("slices") or []) for r in rows}
        items = {item for item, _ in tags}
        if (len(rows) != len(tags) or len(items) != manifest["items"]
                or len(set(seeds)) != len(seeds) or set(tags) != set(product(items, seeds))
                or not rows):
            problems.append(f"{name}: incomplete or duplicate item/seed rows")
        if "seeds" in spec and set(seeds) != set(spec["seeds"]):
            problems.append(f"{name}: manifest seeds differ from spec")
        if report.get("evaluator_failures"):
            problems.append(f"{name}: evaluator failures")
        metrics = report["metrics"]
        for metric, value in metrics.items():
            if value is not None and (not isinstance(value, (int, float)) or not isfinite(value)):
                problems.append(f"{name}: {metric} is not a finite number")
        invalid_grades = any(type(row.get(metric)) is not bool for row in rows for metric in graded)
        if invalid_grades:
            problems.append(f"{name}: missing or non-boolean grader result")
        elif rows:
            # Recompute graded rates and pass^k from the rows the gate actually compares.
            # Cost is platform-dependent and has its own advisory threshold.
            scored_rows = [{"cost": 0.0, **row} for row in rows]
            recomputed = aggregate(scored_rows, sorted(graded), k_values=spec.get("pass_k", []))
            derived = set(recomputed) - {"cost_per_success"}
            required = graded | (derived & {m["id"] for m in spec["metrics"]})
            for metric in sorted(required):
                actual, expected = metrics.get(metric), recomputed[metric]
                if (not isinstance(actual, (int, float)) or expected is None
                        or not isclose(actual, expected, abs_tol=0.00005)):
                    problems.append(f"{name}: {metric} disagrees with rows")
        tags_by_report.append(tags)

    pr_tags, base_tags = tags_by_report
    if pr_tags.keys() != base_tags.keys():
        problems.append("PR and baseline item/seed pairs differ")
    elif pr_tags != base_tags:
        problems.append("PR and baseline slice tags differ")
    if base_spec is not None and spec["eval_set_version"] == base_spec["eval_set_version"]:
        problems.extend(_ratchet(spec, base_spec))
    return problems


def _ratchet(spec: dict, base_spec: dict) -> list[str]:
    def rules(config):
        comparisons = {m["id"]: (m, m.get("threshold", {})) for m in config["metrics"]}
        comparisons.update({
            f"slice:{s['name']}/{s['metric']}": (s, s) for s in config.get("slices", [])
        })
        return comparisons

    current = rules(spec)
    problems = []
    for name, (previous, old) in rules(base_spec).items():
        if name not in current:
            problems.append(f"ratchet: removed {name}")
            continue
        present, new = current[name]
        if previous.get("blocking") and not present.get("blocking"):
            problems.append(f"ratchet: {name} is no longer blocking")
        for key in ("min", "max", "max_increase", "no_significant_drop"):
            if key not in old or (key == "no_significant_drop" and not old[key]):
                continue
            if (key not in new or (key == "min" and new[key] < old[key])
                    or (key in ("max", "max_increase") and new[key] > old[key])
                    or (key == "no_significant_drop" and not new[key])):
                problems.append(f"ratchet: loosened {name} {key}")
    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    for rule in spec.get("slices", []):
        name, metric = rule["name"], rule["metric"]
        ident = f"slice:{name}/{metric}"
        current = per_item(pr, metric, slice_name=name)
        previous = per_item(base, metric, slice_name=name)
        value = sum(current.values()) / len(current) if current else None
        failed = value is None or value < rule.get("min", float("-inf"))
        note = ""
        if rule.get("no_significant_drop"):
            if not current or current.keys() != previous.keys():
                failed = True
                note = "missing matched slice items"
            else:
                d, lo, hi = _paired_ci(current, previous, spec.get("bootstrap", {}))
                failed |= hi < 0
                note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
        verdict = "ok"
        if failed:
            verdict = "BLOCK" if rule.get("blocking") else "warn"
            if rule.get("blocking"):
                blocked.append(ident)
        lines.append(f"  {ident:<38} {value!s:<8} {note} {verdict}")
    return blocked, lines


def _paired_ci(a: dict, b: dict, options: dict) -> tuple[float, float, float]:
    keys = sorted(a.keys() & b.keys())
    return stats.paired_bootstrap(
        [a[k] for k in keys], [b[k] for k in keys],
        n_resamples=options.get("n_resamples", 1000), rng=options.get("rng", 2027),
        confidence=options.get("confidence", 0.95),
    )


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid) is not None:
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            if not a or a.keys() != b.keys():
                verdict, note = "fail", "missing matched metric items"
            else:
                d, lo, hi = _paired_ci(a, b, bs)
                note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                if hi < 0:
                    verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
