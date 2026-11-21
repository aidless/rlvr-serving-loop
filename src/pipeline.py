"""Train -> verify -> judge-anchor -> gate -> deploy-ready manifest.

Local smoke uses simulated artifacts only; evidence_level is carried through
from the training manifest and never upgraded by this pipeline.
"""
import json
from datetime import datetime, timezone
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def stage_train(out_dir, train_manifest_path=None):
    if train_manifest_path:
        m = load_json(train_manifest_path)
    else:
        m = {
            "reward_mode": "true_reward",
            "backend": "simulated",
            "commit_or_note": "local-train-stub",
            "evidence_level": "SIMULATED",
            "steps": 12,
            "seed": 7,
        }
    write_json(Path(out_dir) / "train_manifest.json", m)
    return m


def stage_verify(out_dir, verifier_report_path=None, judge_report_path=None):
    if verifier_report_path:
        v = load_json(verifier_report_path)
    else:
        # stub verifier result: two correctness verifiers, no hacks in clean set
        v = {
            "verdict": "PASS",
            "verifiers": [
                {"name": "exact_match", "tpr": 1.0, "fpr": 0.0, "n": 20},
                {"name": "hidden_tests", "tpr": 1.0, "fpr": 0.0, "n": 20},
            ],
            "findings": [],
            "evidence_level": "SIMULATED",
        }
    if judge_report_path:
        j = load_json(judge_report_path)
    else:
        j = {
            "rule_judge": {"tpr": 1.0, "fpr": None, "fp": 0, "tn": 0, "n": 20},
            "open": {"n": 10, "good_rate": 0.0},
            "evidence_level": "SIMULATED",
        }
    write_json(Path(out_dir) / "verify_report.json", v)
    write_json(Path(out_dir) / "judge_report.json", j)
    return v, j


def run_loop(out_dir, train_manifest_path=None, verifier_report_path=None,
             judge_report_path=None, allow_simulated=True):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    train = stage_train(out_dir, train_manifest_path)
    verify, judge = stage_verify(out_dir, verifier_report_path, judge_report_path)
    gate_payload = {
        "train_manifest": train,
        "verifier": verify,
        "judge": judge,
        "allow_simulated": allow_simulated,
    }
    write_json(out_dir / "gate_input.json", gate_payload)
    from .gate import evaluate
    verdict, findings = evaluate(gate_payload)
    gate_report = {
        "verdict": verdict,
        "findings": findings,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(out_dir / "gate_report.json", gate_report)

    evidence = train.get("evidence_level", "UNKNOWN")
    deploy_ok = verdict == "DEPLOY_READY" and (allow_simulated or evidence == "EMPIRICAL_GPU")
    if deploy_ok:
        write_json(out_dir / "deploy_ready.json", {
            "status": "DEPLOY_READY",
            "evidence_level": evidence,
            "source_manifest": "train_manifest.json",
            "gate_report": "gate_report.json",
            "artifacts": ["train_manifest.json", "verify_report.json", "judge_report.json", "gate_report.json"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    return gate_report
