import json
from unittest.mock import patch

from boss_career_ops.commands.skill_update import (
    _parse_frontmatter,
    run_skill_update,
)


class TestParseFrontmatter:
    def test_valid_frontmatter(self):
        content = '---\nname: "boss-career-ops"\nskill_version: "0.2.0"\n---\n# Body'
        fm = _parse_frontmatter(content)
        assert fm["name"] == "boss-career-ops"
        assert fm["skill_version"] == "0.2.0"

    def test_no_frontmatter(self):
        content = "# Just a heading\nSome text"
        fm = _parse_frontmatter(content)
        assert fm == {}

    def test_unclosed_frontmatter(self):
        content = '---\nname: "test"\nNo closing'
        fm = _parse_frontmatter(content)
        assert fm == {}

    def test_invalid_yaml(self):
        content = "---\n: invalid: yaml: {}\n---\n# Body"
        fm = _parse_frontmatter(content)
        assert fm == {}




class TestRunSkillUpdate:
    def test_network_error(self, capsys):
        with patch("boss_career_ops.commands.skill_update._fetch_remote_skill", return_value=None):
            run_skill_update()
            output = json.loads(capsys.readouterr().out)
            assert output["ok"] is False
            assert output["error"]["code"] == "NETWORK_ERROR"

    def test_check_only(self, capsys):
        remote = '---\nskill_version: "0.3.0"\n---\n# Body'
        with patch("boss_career_ops.commands.skill_update._fetch_remote_skill", return_value=remote):
            run_skill_update(check_only=True)
            output = json.loads(capsys.readouterr().out)
            assert output["ok"] is True
            assert output["data"]["remote_version"] == "0.3.0"
            assert output["data"]["content"] is None

    def test_full_update(self, capsys):
        remote = '---\nskill_version: "0.3.0"\n---\n# Updated Body'
        with patch("boss_career_ops.commands.skill_update._fetch_remote_skill", return_value=remote):
            run_skill_update()
            output = json.loads(capsys.readouterr().out)
            assert output["ok"] is True
            assert output["data"]["remote_version"] == "0.3.0"
            assert output["data"]["content"] == remote
            assert "写入" in output["hints"]["next_actions"][0]

    def test_remote_without_version(self, capsys):
        remote = '---\nname: "boss-career-ops"\n---\n# No version'
        with patch("boss_career_ops.commands.skill_update._fetch_remote_skill", return_value=remote):
            run_skill_update(check_only=True)
            output = json.loads(capsys.readouterr().out)
            assert output["ok"] is True
            assert output["data"]["remote_version"] == "0.0.0"
