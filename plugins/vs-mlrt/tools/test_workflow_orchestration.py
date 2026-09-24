from __future__ import annotations

from pathlib import Path
import unittest


REPOSITORY = Path(__file__).resolve().parents[3]
WORKFLOWS = REPOSITORY / ".github" / "workflows"


class WorkflowOrchestrationTests(unittest.TestCase):
    def test_expensive_builds_are_manual_only(self) -> None:
        for name in (
            "package-vs-mlrt-windows-generic.yml",
            "package-vs-mlrt-windows-cuda.yml",
            "package-vs-mlrt-linux.yml",
        ):
            workflow = (WORKFLOWS / name).read_text(encoding="utf-8")
            trigger = workflow.split("permissions:", 1)[0]
            self.assertIn("workflow_dispatch:", trigger, name)
            self.assertNotIn("  push:", trigger, name)
            self.assertNotIn("  release:", trigger, name)

    def test_contract_runs_before_merge_not_after_merge(self) -> None:
        workflow = (WORKFLOWS / "package-vs-mlrt.yml").read_text(encoding="utf-8")
        trigger = workflow.split("permissions:", 1)[0]
        self.assertIn("  pull_request:", trigger)
        self.assertNotIn("  push:", trigger)
        self.assertIn("unittest discover", workflow)

    def test_pages_deploys_from_default_branch_dispatch(self) -> None:
        index = (WORKFLOWS / "index-pages.yml").read_text(encoding="utf-8")
        trigger = index.split("permissions:", 1)[0]
        self.assertIn("  repository_dispatch:", trigger)
        self.assertNotIn("  release:", trigger)

        finalizer = (WORKFLOWS / "package-vs-mlrt-finalize.yml").read_text(encoding="utf-8")
        self.assertIn('gh api "repos/$GITHUB_REPOSITORY/dispatches" -f event_type=index', finalizer)

    def test_published_smoke_uses_platform_specific_verifiers(self) -> None:
        workflow = (WORKFLOWS / "quality-vs-mlrt-published.yml").read_text(encoding="utf-8")
        self.assertGreaterEqual(workflow.count('"${{ runner.os }}" == Linux'), 2)
        self.assertGreaterEqual(workflow.count("smoke_linux_vcs_install.py"), 2)
        self.assertGreaterEqual(workflow.count("smoke_vcs_extras_install.py"), 2)


if __name__ == "__main__":
    unittest.main()
