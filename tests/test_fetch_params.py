"""deploy/fetch_params.py reads every setting the deploy needs from Parameter Store."""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "fetch_params", Path(__file__).parent.parent / "deploy" / "fetch_params.py"
)
fetch_params = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch_params)


class FakeSsm:
    """Answers like SSM, including its limit of 10 names per call."""

    def __init__(self, stored):
        self.stored = stored
        self.calls = 0

    def get_parameters(self, Names, WithDecryption):  # noqa: N803 - boto3's names
        assert len(Names) <= 10, "SSM rejects more than 10 names"
        self.calls += 1
        return {
            "Parameters": [{"Name": n, "Value": self.stored[n]} for n in Names if n in self.stored],
            "InvalidParameters": [n for n in Names if n not in self.stored],
        }


def test_reads_all_parameters_in_batches_of_ten():
    names = [f"/motivetag/{n}" for n in {**fetch_params.NAMES, **fetch_params.OPTIONAL}]
    assert len(names) > 10  # the case that broke a deploy
    ssm = FakeSsm({n: "value" for n in names[:-1]})
    found, invalid = fetch_params.get_parameters(ssm, names)
    assert ssm.calls == -(-len(names) // 10)  # batches of ten, rounded up
    assert {p["Name"] for p in found} == set(names[:-1])
    assert invalid == [names[-1]]
