from boss_career_ops.schema import COMMANDS, get_all_commands, get_command


class TestSchema:
    def test_commands_not_empty(self):
        assert len(COMMANDS) > 0

    def test_each_command_has_required_keys(self):
        for cmd in COMMANDS:
            assert "name" in cmd
            assert "description" in cmd
            assert "usage" in cmd
            assert "params" in cmd

    def test_get_all_commands(self):
        result = get_all_commands()
        assert result == COMMANDS

    def test_get_command_found(self):
        result = get_command("search")
        assert result is not None
        assert result["name"] == "search"

    def test_get_command_not_found(self):
        result = get_command("nonexistent")
        assert result is None

    def test_known_commands_exist(self):
        names = [cmd["name"] for cmd in COMMANDS]
        assert "doctor" in names
        assert "search" in names
        assert "evaluate" in names
        assert "greet" in names
        assert "apply" in names
        assert "pipeline" in names
