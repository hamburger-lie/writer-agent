from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from writing_agent.cli.app import app


class _FakePolisher:
    def run(self, draft, plan, research, review) -> str:
        return "# Polished\n\nBetter draft."


def test_polish_command_writes_polished_output(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    draft_path = tmp_path / "draft.md"
    draft_path.write_text("# Draft\n\nContent", encoding="utf-8")
    monkeypatch.setattr(
        "writing_agent.cli.commands.polish.build_polisher_agent",
        lambda settings: _FakePolisher(),
    )

    output_path = tmp_path / "polished.md"
    result = runner.invoke(app, ["polish", str(draft_path), "--output", str(output_path)])

    assert result.exit_code == 0
    assert output_path.exists()
    assert "Better draft." in output_path.read_text(encoding="utf-8")

