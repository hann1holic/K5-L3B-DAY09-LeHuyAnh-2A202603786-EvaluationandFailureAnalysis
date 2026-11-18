import pytest

from lab9.trace_case import investigate


@pytest.mark.student
@pytest.mark.parametrize(
    "shape",
    [
        "fixed",
        pytest.param(
            "seeded_regression",
            marks=pytest.mark.xfail(
                strict=True, raises=AssertionError, reason="FM-03: ticket overrides order delay"
            ),
        ),
    ],
)
def test_ticket_delay_does_not_override_order(shape):
    case = investigate(shape, "C-002", 11)
    trial = case["trial"]
    lookup = next(
        event["payload"]["lookup_order"]
        for event in trial["events"]
        if event["kind"] == "investigator"
    )
    assert lookup["order"]["delay_days"] == 2
    assert trial["snapshot"]["refund_vnd"] == case["label"]["refund_vnd"] == 0
    assert trial["result"]["status"] == case["label"]["status"] == "denied"
