# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Gitlint configuration rules for this repository."""

# aislop-ignore-next-line ai-slop/hallucinated-import -- provided by the gitlint hook
from gitlint.config import LintConfig

# aislop-ignore-next-line ai-slop/hallucinated-import -- provided by the gitlint hook
from gitlint.git import GitCommit

# aislop-ignore-next-line ai-slop/hallucinated-import -- provided by the gitlint hook
from gitlint.options import RegexOption

# aislop-ignore-next-line ai-slop/hallucinated-import -- provided by the gitlint hook
from gitlint.rules import ConfigurationRule


class IgnoreDependabotWorkflowTitle(ConfigurationRule):
    """Accumulate the title-length exception for generated workflow bump subjects."""

    name = "ignore-dependabot-workflow-title"
    id = "UC1"
    options_spec = [
        RegexOption(
            "regex",
            None,
            "Regex matching generated workflow-bump commit titles",
        ),
    ]

    def apply(self, config: LintConfig, commit: GitCommit) -> None:
        """Ignore title length only when a generated workflow-bump title matches."""
        pattern = self.options["regex"].value
        if (
            pattern
            and pattern.match(commit.message.title)
            and "T1" not in config.ignore
        ):
            config.ignore.append("T1")
