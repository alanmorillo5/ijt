import pytest
from click.testing import CliRunner
from ijt.cli import cli
from pathlib import Path

@pytest.fixture
def runner():
    return CliRunner()

def test_init_command(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli, ['init'])
    assert result.exit_code == 0
    assert "Database created at data/ijt.db" in result.output
    assert Path("data/ijt.db").exists()

def test_list_command_empty(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli, ['list'])
    assert result.exit_code == 0
    assert "No database found" in result.output
