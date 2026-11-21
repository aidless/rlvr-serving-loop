"""Deployment gate for rlvr-serving-loop.

Fail-closed rules:
- train manifest must declare reward_mode, backend, commit_or_note, evidence_level
- verifier verdict must PASS with zero hacks/findings
- judge rule_judge TPR=1.0 and FPR=0 or (None with fp=tn=0)
- simulated evidence only allowed when allow_simulated=True
"""
import json
import sys

REQUIRED_TRAIN_KEYS = ["reward_mode", "backend", "commit_or_note", "evidence_level"]
EXIT_CODES = {"DEPLOY_READY": 0, "WEAK": 1, "BLOCKED": 2, "INSTRUMENT_GAP": 3}


def evaluate(payload):
    findings = []
    train = payload.get("train_manifest") or {}
    verify = payload.get("verifier") or {}
    judge = payload.get("judge") or {}
    allow_sim = bool(payload.get("allow_simulated", False))

    missing = [k for k in REQUIRED_TRAIN_KEYS if k not in train]
    if missing:
        findings.append(f"INSTRUMENT_GAP: train manifest missing {missing}")
        return "INSTRUMENT_GAP", findings

    if verify.get("verdict") != "PASS":
        findings.append(f"BLOCKED: verifier verdict={verify.get('verdict')!r}")
    for v in verify.get("verifiers", []):
        if v.get("fpr") not in (0.0, None):
            findings.append(f"BLOCKED: verifier {v.get('name')} fpr={v.get('fpr')}")
        if v.get("tpr") != 1.0:
            findings.append(f"BLOCKED: verifier {v.get('name')} tpr={v.get('tpr')}")
    if verify.get("findings"):
        findings.append(f"BLOCKED: verifier findings={verify['findings']}")

    rj = judge.get("rule_judge") or {}
    if rj.get("tpr") != 1.0:
        findings.append(f"BLOCKED: rule_judge tpr={rj.get('tpr')}")
    fpr = rj.get("fpr")
    if not (fpr == 0.0 or (fpr is None and rj.get("fp", 0) == 0 and rj.get("tn", 0) == 0)):
        findings.append(f"BLOCKED: rule_judge fpr={fpr} (fp={rj.get('fp')}, tn={rj.get('tn')})")

    if train.get("evidence_level") == "SIMULATED" and not allow_sim:
        findings.append("WEAK: simulated evidence not allowed for deployment")
    elif train.get("evidence_level") not in ("SIMULATED", "EMPIRICAL_GPU"):
        findings.append(f"WEAK: unknown evidence_level={train.get('evidence_level')!r}")

    if any(f.startswith("BLOCKED") for f in findings):
        return "BLOCKED", findings
    if any(f.startswith("INSTRUMENT_GAP") for f in findings):
        return "INSTRUMENT_GAP", findings
    if findings:
        return "WEAK", findings
    return "DEPLOY_READY", findings


def selftest():
    good_train = {
        "reward_mode": "true_reward", "backend": "simulated",
        "commit_or_note": "stub", "evidence_level": "SIMULATED",
    }
    good_verify = {
        "verdict": "PASS", "verifiers": [{"name": "exact_match", "tpr": 1.0, "fpr": 0.0}],
        "findings": [],
    }
    good_judge = {"rule_judge": {"tpr": 1.0, "fpr": None, "fp": 0, "tn": 0, "n": 20}}
    green = evaluate({
        "train_manifest": good_train, "verifier": good_verify,
        "judge": good_judge, "allow_simulated": True,
    })
    red_manifest = evaluate({
        "train_manifest": {"backend": "simulated"}, "verifier": good_verify,
        "judge": good_judge, "allow_simulated": True,
    })
    red_verify = evaluate({
        "train_manifest": good_train,
        "verifier": {**good_verify, "verdict": "HACKABLE", "findings": ["hacked"]},
        "judge": good_judge, "allow_simulated": True,
    })
    red_judge = evaluate({
        "train_manifest": good_train, "verifier": good_verify,
        "judge": {"rule_judge": {"tpr": 1.0, "fpr": 0.5, "fp": 10, "tn": 10}},
        "allow_simulated": True,
    })
    red_evidence = evaluate({
        "train_manifest": good_train, "verifier": good_verify,
        "judge": good_judge, "allow_simulated": False,
    })
    result = {
        "green_ok": green[0] == "DEPLOY_READY",
        "red_manifest_ok": red_manifest[0] == "INSTRUMENT_GAP",
        "red_verify_ok": red_verify[0] == "BLOCKED",
        "red_judge_ok": red_judge[0] == "BLOCKED",
        "red_evidence_ok": red_evidence[0] == "WEAK",
    }
    print("SELFTEST:", "PASS" if all(result.values()) else "FAIL", json.dumps(result))
    return 0 if all(result.values()) else 1


def main():
    parser = __import__("argparse").ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--input", help="gate_input.json path")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if not args.input:
        parser.error("--input required unless --selftest")
    verdict, findings = evaluate(json.loads(open(args.input, encoding="utf-8").read()))
    print(json.dumps({"verdict": verdict, "findings": findings}, indent=2))
    return EXIT_CODES[verdict]


if __name__ == "__main__":
    sys.exit(main())
