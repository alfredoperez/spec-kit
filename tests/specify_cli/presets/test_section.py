"""Tests for the replace-section matcher in specify_cli.presets._section."""

import pytest

from specify_cli.presets import PresetValidationError
from specify_cli.presets._section import replace_section

TEMPLATE = (
    "# Feature Specification\n"
    "\n"
    "Intro line.\n"
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


class TestReplaceSection:
    def test_swaps_body_and_keeps_heading_and_other_sections(self):
        out = replace_section(TEMPLATE, "User Scenarios & Testing", "New body.\n", "p")
        assert out == (
            "# Feature Specification\n"
            "\n"
            "Intro line.\n"
            "\n"
            "## User Scenarios & Testing\n"
            "\n"
            "New body.\n"
            "\n"
            "## Requirements\n"
            "\n"
            "Stock requirements.\n"
            "\n"
            "## Success Criteria\n"
            "\n"
            "Stock criteria.\n"
        )

    def test_subsections_are_replaced_with_their_parent(self):
        out = replace_section(TEMPLATE, "User Scenarios & Testing", "X", "p")
        assert "### User Story 1" not in out
        assert "Story text." not in out
        assert "## Requirements\n\nStock requirements." in out

    def test_subsection_alone_ends_at_next_higher_heading(self):
        out = replace_section(TEMPLATE, "User Story 1", "Only this.", "p")
        assert "### User Story 1\n\nOnly this.\n\n## Requirements\n" in out
        assert "Stock stories." in out

    def test_last_section_runs_to_end_of_file(self):
        out = replace_section(TEMPLATE, "Success Criteria", "\n\nDone.\n\n\n", "p")
        assert out.endswith("## Success Criteria\n\nDone.\n")

    def test_top_level_heading_owns_whole_document(self):
        out = replace_section(TEMPLATE, "Feature Specification", "All.", "p")
        assert out == "# Feature Specification\n\nAll.\n"

    def test_matches_trimmed_text_at_any_level(self):
        text = "#   Requirements   \nold\n"
        assert replace_section(text, " Requirements ", "new", "p") == (
            "#   Requirements   \n\nnew\n"
        )

    def test_match_is_case_sensitive(self):
        with pytest.raises(PresetValidationError, match="not found"):
            replace_section(TEMPLATE, "requirements", "x", "p")

    def test_empty_body_keeps_heading(self):
        out = replace_section(TEMPLATE, "Requirements", "", "p")
        assert "## Requirements\n\n## Success Criteria\n" in out

    def test_heading_without_trailing_newline(self):
        assert replace_section("## Notes", "Notes", "n", "p") == "## Notes\n\nn\n"

    def test_crlf_template_keeps_its_own_lines(self):
        text = "## A\r\nold\r\n## B\r\nkeep\r\n"
        assert replace_section(text, "A", "new", "p") == "## A\r\n\nnew\n\n## B\r\nkeep\r\n"


class TestExactlyOneMatch:
    def test_zero_matches_names_section_source_and_headings(self):
        with pytest.raises(PresetValidationError) as exc:
            replace_section(TEMPLATE, "User Stories", "x", "outcomes v1.0.0")
        message = str(exc.value)
        assert "'User Stories' not found" in message
        assert "outcomes v1.0.0" in message
        assert (
            "# Feature Specification, ## User Scenarios & Testing, "
            "### User Story 1, ## Requirements, ## Success Criteria"
        ) in message

    def test_two_matches_fail(self):
        text = "## Notes\na\n## Other\nb\n### Notes\nc\n"
        with pytest.raises(PresetValidationError, match="'Notes' matches 2 headings"):
            replace_section(text, "Notes", "x", "p")


class TestFencedCode:
    @pytest.mark.parametrize("fence", ["```", "~~~", "````markdown"])
    def test_headings_inside_fences_are_ignored(self, fence):
        closing = fence.rstrip("markdown")
        text = (
            "## Example\n"
            f"{fence}\n"
            "## Requirements\n"
            f"{closing}\n"
            "## Requirements\n"
            "real\n"
        )
        out = replace_section(text, "Requirements", "new", "p")
        assert out == (
            "## Example\n"
            f"{fence}\n"
            "## Requirements\n"
            f"{closing}\n"
            "## Requirements\n\nnew\n"
        )

    def test_shorter_or_other_fence_does_not_close(self):
        text = "````\n```\n## Hidden\n~~~~\n````\n## Shown\nx\n"
        with pytest.raises(PresetValidationError, match="Headings: ## Shown$"):
            replace_section(text, "Hidden", "x", "p")

    def test_fenced_heading_alone_is_not_found(self):
        with pytest.raises(PresetValidationError, match="not found"):
            replace_section("```\n## Hidden\n```\n", "Hidden", "x", "p")


def test_lines_that_are_not_headings_are_skipped():
    text = "#hashtag\n####### seven\n## Real\n    ## indented code\n"
    with pytest.raises(PresetValidationError, match="Headings: ## Real$"):
        replace_section(text, "hashtag", "x", "p")
