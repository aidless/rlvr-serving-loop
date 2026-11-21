# rlvr-serving-loop

把「训练 → 验证器/奖励质量检查 → 门禁 → 部署就绪产物」串成可一条命令跑通的最小闭环。

## 目标

- 训练产物（checkpoint 或 simulated 产物）进入验证；
- 复用 `rlvr-verifier-lab` 风格的 verifier 质量检查与 `judge-anchor` 的锚点校准信号；
- 通过门禁才产出 `deploy_ready` 产物与 manifest；未通过则阻断并给出 findings；
- 全流程一条命令、可复算、可自检（RED/GREEN）。

## 能证明什么 / 证据边界

- 能证明：在本地 smoke（无 GPU/无真实训练）下，管线可执行、门禁可失败可通过、产物链完整且可追溯。
- 证据不支持：未在云端跑真实 RLVR 训练时，闭环中的“训练改进”来自 stub/simulated 数据，不代表真实性能提升。真实训练应在 GPU 环境运行并接入真实 checkpoint。

## Quickstart

```bash
# 一条命令跑通 smoke 闭环（train-stub -> verify -> gate -> deploy artifact）
bash examples/run_loop.sh

# 自检（RED/GREEN）
python3 -m src.gate --selftest

# pytest
python3 -m pytest -q
```

## 门禁

- verifier gate verdict 必须 PASS（HACKABLE/INSTRUMENT_GAP 阻断）
- judge anchor 必须可用且 rule-judge TPR=1.0 且 FPR 为 0 或（None 且无负例）
- train artifact manifest 必须存在且含 `reward_mode`, `backend`, `commit_or_note`, `evidence_level`
- 退出码：0=DEPLOY_READY, 1=WEAK, 2=BLOCKED, 3=INSTRUMENT_GAP

## 产物

- `artifacts/demo/train_manifest.json`
- `artifacts/demo/verify_report.json`
- `artifacts/demo/judge_report.json`
- `artifacts/demo/gate.json`
- `artifacts/demo/deploy_manifest.json`（仅 gate 通过）

## 云端说明

真实 RLVR 训练建议在可达 GPU 环境执行（本轮 AMD T4 `36.150.116.206:34677` ssh Connection refused，未实跑）。将训练输出目录指向本管线 `--train-manifest` 即可接入同一验证门禁。

## 许可

MIT
