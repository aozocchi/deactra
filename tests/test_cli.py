import json

from deactra.cli import main


def test_cli_json_output(capsys):
    code = main(["-1000", "600", "600", "-t", "0", "1", "2", "--json"])
    captured = capsys.readouterr()
    assert code == 0
    data = json.loads(captured.out)
    assert data["project"] == "Deactra"
    assert data["solver_result"]["converged"] is True
    assert data["equivalent_rates"]["effective_annual"] > 0


def test_cli_rejects_mismatched_data(capsys):
    code = main(["-1000", "600", "-t", "0"])
    captured = capsys.readouterr()
    assert code == 2
    assert "Data mismatch" in captured.err
