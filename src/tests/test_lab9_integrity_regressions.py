from copy import deepcopy

import pytest

pytestmark = pytest.mark.student


@pytest.mark.parametrize("tamper", ["duplicate", "grader_error", "slice_label", "aggregate"])
def test_integrity_rejects_tampering_on_a_green_report(tamper):
    from lab9.gate import integrity_check

    baseline = {
        "manifest": {"items": 1, "seeds": [11, 22]},
        "rows": [
            {"item_id": "E-001", "seed": seed, "pass_rate": seed == 11, "slices": ["adversarial"]}
            for seed in (11, 22)
        ],
        "metrics": {"pass_rate": 0.5},
        "evaluator_failures": [],
    }
    report = deepcopy(baseline)
    if tamper == "duplicate":
        report["rows"][1] = deepcopy(report["rows"][0])
    elif tamper == "grader_error":
        report["evaluator_failures"] = ["E-001@11:TrialPass:bad output"]
    elif tamper == "slice_label":
        report["rows"][1]["slices"] = []
    else:
        report["metrics"]["pass_rate"] = 1.0
    spec = {"metrics": [{"id": "pass_rate"}]}
    assert integrity_check(baseline, baseline, spec) == []
    assert integrity_check(report, baseline, spec)


@pytest.mark.parametrize("reply,correct", [
    ("LogiX đã hoàn phí 20.000đ cho anh/chị ạ.", True),
    ("Đã hoàn 20,000 VND.", True),
    ("Dạ, LogiX đã hoàn 35.000đ.", False),
])
def test_reply_ledger_correct_uses_committed_amount(reply, correct):
    from pydantic_evals.evaluators import EvaluatorContext

    from lab9.graders import ReplyLedgerCorrect

    output = {
        "result": {"status": "resolved", "proposal_amount": 35000},
        "snapshot": {"refund_vnd": 20000},
        "events": [{"kind": "reply", "payload": {"text": reply}}],
    }
    ctx = EvaluatorContext(name="reply", inputs={}, metadata=None, expected_output=None, output=output,
                           duration=0.0, _span_tree=None, attributes={}, metrics={})
    assert ReplyLedgerCorrect().evaluate(ctx).value is correct
