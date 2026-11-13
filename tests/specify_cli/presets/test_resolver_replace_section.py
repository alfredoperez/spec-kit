"""Composition tests for the replace-section strategy through installed presets."""

import pytest
import yaml

from specify_cli.presets import PresetManager, PresetResolver, PresetValidationError

CORE = (
    "# Feature Specification\n"
    "\n"
    "## User Scenarios & Testing\n"
    "\n"
    "Stock stories.\n"
    "\n"
    "### User Story 1\n"
    "\n"
    "Story text.\n"
    "\n"
    "## Requirements\n"
    "\n"
    "Stock requirements.\n"
    "\n"
    "## Success Criteria\n"
    "\n"
    "Stock criteria.\n"
)


@pytest.fixture
def core_project(project_dir):
    (project_dir / ".specify" / "templates" / "spec-template.md").write_text(
        CORE, encoding="utf-8"
    )
    return project_dir


def _install(project_dir, temp_dir, valid_pack_data, pack_id, body,
             section=None, strategy="replace-section", priority=10,
             template_type="template", name="spec-template"):
    entry = {"type": template_type, "name": name}
    if template_type == "command":
        entry["file"] = f"commands/{name}.md"
    else:
        entry["file"] = f"templates/{name}.md"
    if strategy != "replace":
        entry["strategy"] = strategy
    if section is not None:
        entry["section"] = section
    data = {
        **valid_pack_data,
        "preset": {**valid_pack_data["preset"], "id": pack_id, "name": pack_id},
        "provides": {"templates": [entry]},
    }
    pack_dir = temp_dir / pack_id
    (pack_dir / entry["file"]).parent.mkdir(parents=True)
    (pack_dir / entry["file"]).write_text(body, encoding="utf-8")
    with open(pack_dir / "preset.yml", "w") as f:
        yaml.dump(data, f)
    PresetManager(project_dir).install_from_directory(
        pack_dir, "0.1.5", priority=priority
    )


class TestReplaceSectionComposition:
    def test_replaces_only_the_named_section(
        self, core_project, temp_dir, valid_pack_data
    ):
        _install(core_project, temp_dir, valid_pack_data, "outcomes",
                 "- Outcome one\n", section="User Scenarios & Testing")
        out = PresetResolver(core_project).resolve_content("spec-template")
        expected = CORE.replace(
            "Stock stories.\n\n### User Story 1\n\nStory text.\n",
            "- Outcome one\n",
        )
        assert out == expected

    def test_layer_carries_section(self, core_project, temp_dir, valid_pack_data):
        _install(core_project, temp_dir, valid_pack_data, "outcomes", "x",
                 section="Requirements")
        layers = PresetResolver(core_project).collect_all_layers("spec-template")
        assert layers[0]["strategy"] == "replace-section"
        assert layers[0]["section"] == "Requirements"

    def test_two_presets_on_different_sections_both_apply(
        self, core_project, temp_dir, valid_pack_data
    ):
        _install(core_project, temp_dir, valid_pack_data, "reqs",
                 "EARS reqs.", section="Requirements", priority=5)
        _install(core_project, temp_dir, valid_pack_data, "criteria",
                 "Pass/fail.", section="Success Criteria", priority=20)
        out = PresetResolver(core_project).resolve_content("spec-template")
        assert "## Requirements\n\nEARS reqs.\n\n## Success Criteria" in out
        assert out.endswith("## Success Criteria\n\nPass/fail.\n")
        assert "Stock stories." in out

    def test_same_section_higher_priority_wins(
        self, core_project, temp_dir, valid_pack_data
    ):
        _install(core_project, temp_dir, valid_pack_data, "high",
                 "High.", section="Requirements", priority=1)
        _install(core_project, temp_dir, valid_pack_data, "low",
                 "Low.", section="Requirements", priority=50)
        out = PresetResolver(core_project).resolve_content("spec-template")
        assert "## Requirements\n\nHigh.\n" in out
        assert "Low." not in out

    def test_composes_with_wrap_and_append(
        self, core_project, temp_dir, valid_pack_data
    ):
        _install(core_project, temp_dir, valid_pack_data, "reqs",
                 "New reqs.", section="Requirements", priority=20)
        _install(core_project, temp_dir, valid_pack_data, "footer",
                 "Footer.", strategy="append", priority=5)
        out = PresetResolver(core_project).resolve_content("spec-template")
        assert "## Requirements\n\nNew reqs.\n" in out
        assert out.endswith("Footer.")

    def test_missing_section_fails_with_headings(
        self, core_project, temp_dir, valid_pack_data
    ):
        _install(core_project, temp_dir, valid_pack_data, "stale",
                 "x", section="User Stories")
        with pytest.raises(PresetValidationError) as exc:
            PresetResolver(core_project).resolve_content("spec-template")
        assert "'User Stories' not found" in str(exc.value)
        assert "## Requirements" in str(exc.value)
        assert "stale v" in str(exc.value)

    def test_without_replace_base_returns_none(
        self, project_dir, temp_dir, valid_pack_data
    ):
        _install(project_dir, temp_dir, valid_pack_data, "orphan", "x",
                 section="Anything", name="custom-template")
        assert PresetResolver(project_dir).resolve_content("custom-template") is None

    def test_command_frontmatter_cannot_select_replace_section(
        self, project_dir, temp_dir, valid_pack_data
    ):
        _install(project_dir, temp_dir, valid_pack_data, "cmd",
                 "---\ndescription: X\nstrategy: replace-section\n---\n\nBody\n",
                 strategy="replace", template_type="command",
                 name="speckit.specify")
        layers = PresetResolver(project_dir).collect_all_layers(
            "speckit.specify", "command"
        )
        assert layers[0]["strategy"] == "replace"
