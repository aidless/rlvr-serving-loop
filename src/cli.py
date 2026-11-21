"""CLI: one command train -> verify -> gate -> deploy manifest."""
import argparse
import json
from pathlib import Path

from .pipeline import run_loop


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="artifacts/demo")
    ap.add_argument("--train-manifest")
    ap.add_argument("--verifier-report")
    ap.add_argument("--judge-report")
    ap.add_argument("--no-simulated", action="store_true")
    args = ap.parse_args()
    report = run_loop(
        args.out_dir,
        train_manifest_path=args.train_manifest,
        verifier_report_path=args.verifier_report,
        judge_report_path=args.judge_report,
        allow_simulated=not args.no_simulated,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return {"DEPLOY_READY": 0, "WEAK": 1, "BLOCKED": 2, "INSTRUMENT_GAP": 3}[report["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main())
