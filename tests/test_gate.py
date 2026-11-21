"""RED/GREEN tests for the serving-loop gate."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_selftest_red_green():
    r = subprocess.run([sys.executable, "-m", "src.gate", "--selftest"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert '"green_ok": true' in r.stdout
    assert '"red_manifest_ok": true' in r.stdout
    assert '"red_verify_ok": true' in r.stdout
    assert '"red_judge_ok": true' in r.stdout


def test_demo_loop_deploy_ready(tmp_path):
    r = subprocess.run([sys.executable, "-m", "src.cli", "--out-dir", str(tmp_path)],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    out = json.loads(r.stdout)
    assert out["verdict"] == "DEPLOY_READY"
    assert (tmp_path / "deploy_ready.json").exists()
    manifest = json.loads((tmp_path / "deploy_ready.json").read_text())
    assert manifest["evidence_level"] == "SIMULATED"


def test_blocked_on_hacked_verifier(tmp_path):
    bad = {
        "verdict": "HACKABLE",
        "verifiers": [{"name": "exact_match", "tpr": 1.0, "fpr": 0.5}],
        "findings": ["hack_pass"],
    }
    vp = tmp_path / "bad_verify.json"
    vp.write_text(json.dumps(bad))
    r = subprocess.run([sys.executable, "-m", "src.cli", "--out-dir", str(tmp_path / "out"),
                        "--verifier-report", str(vp)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 2, r.stdout + r.stderr
    assert json.loads(r.stdout)["verdict"] == "BLOCKED"
