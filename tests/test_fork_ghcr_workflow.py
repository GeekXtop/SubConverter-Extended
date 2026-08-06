from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ForkGhcrWorkflowTests(unittest.TestCase):
    def test_workflow_is_fork_only_amd64_ghcr(self):
        workflow = (ROOT / ".github/workflows/build-fork-ghcr.yml").read_text()

        self.assertIn("- local-customizations", workflow)
        self.assertIn("packages: write", workflow)
        self.assertIn("linux/amd64", workflow)
        self.assertIn('image="ghcr.io/${GITHUB_REPOSITORY,,}"', workflow)
        self.assertNotIn("linux/arm", workflow)
        self.assertNotIn("aethersailor/subconverter-extended", workflow.lower())
        self.assertNotIn("DOCKERHUB_", workflow)

    def test_candidate_is_tested_before_deployable_tags_are_promoted(self):
        workflow = (ROOT / ".github/workflows/build-fork-ghcr.yml").read_text()

        build = workflow.index("Build candidate image")
        smoke = workflow.index("Smoke test candidate image")
        current = workflow.index("Verify current branch head")
        promote = workflow.index("Promote tested image")
        self.assertLess(build, smoke)
        self.assertLess(smoke, current)
        self.assertLess(current, promote)

    def test_compose_uses_published_fork_image(self):
        compose = (ROOT / "docker-compose.yml").read_text()

        self.assertIn(
            'image: "ghcr.io/geekxtop/subconverter-extended:latest"',
            compose,
        )


if __name__ == "__main__":
    unittest.main()
