import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "generate_index.py"
SPEC = importlib.util.spec_from_file_location("generate_index", SCRIPT)
assert SPEC and SPEC.loader
generate_index = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generate_index)


class GenerateIndexTests(unittest.TestCase):
    def test_collects_digest_backed_wheels_and_writes_normalized_index(self) -> None:
        releases = [
            {
                "draft": False,
                "assets": [
                    {
                        "name": "vs_nlq-1.2.0-py3-none-win_amd64.whl",
                        "digest": "sha256:abc123",
                        "browser_download_url": "https://example.invalid/wheel.whl",
                    },
                    {
                        "name": "vs-nlq-windows-x86_64.zip",
                        "digest": "sha256:def456",
                        "browser_download_url": "https://example.invalid/plugin.zip",
                    },
                ],
            }
        ]
        projects = generate_index.collect_wheels(releases)
        self.assertEqual(["vs-nlq"], list(projects))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            generate_index.write_index(projects, output)
            project_page = (output / "simple" / "vs-nlq" / "index.html").read_text()
            self.assertIn("#sha256=abc123", project_page)
            self.assertNotIn(".zip", project_page)


if __name__ == "__main__":
    unittest.main()
