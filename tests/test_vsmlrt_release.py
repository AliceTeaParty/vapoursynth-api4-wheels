"""Native build provenance and resumable, immutable vs-mlrt publication."""
import copy
import hashlib
import io
import sys
import tempfile
import unittest
import zipfile
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import publish_vsmlrt as publisher
from module_common import CENTRAL_REPOSITORY_ID, digest_file, write_json


class VsmlrtPublisherTests(unittest.TestCase):
    def test_artifact_transfer_resumes_and_extracts_only_verified_wheels(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("dist/wheels/demo.whl", b"wheel bytes")
            archive.writestr("dist/wheels/component-wheel-inventory-demo.json", b"{}")
            archive.writestr("large-native-payload.zip", b"unused native archive")
        payload = buffer.getvalue()
        artifact = {"id": 123, "name": "test", "size_in_bytes": len(payload),
                    "digest": "sha256:" + hashlib.sha256(payload).hexdigest()}
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "artifact"
            offsets = []
            def curl(args, **kwargs):
                output = Path(args[args.index("--output") + 1])
                offsets.append(output.stat().st_size if output.exists() else 0)
                self.assertIn("--continue-at", args)
                self.assertNotIn("signed-secret", " ".join(args))
                self.assertIn("signed-secret", kwargs["input"])
                if len(offsets) == 1:
                    output.write_bytes(payload[:20])
                    return SimpleNamespace(returncode=28)
                with output.open("ab") as stream:
                    stream.write(payload[20:])
                return SimpleNamespace(returncode=0)
            with patch.object(publisher, "artifact_download_url", return_value="https://example.invalid/signed-secret"), \
                 patch.object(publisher.subprocess, "run", side_effect=curl), patch.object(publisher.time, "sleep"):
                publisher.download_artifact(None, artifact, target)
            self.assertEqual(offsets, [0, 20])
            self.assertEqual((target / "dist/wheels/demo.whl").read_bytes(), b"wheel bytes")
            self.assertFalse((target / "download.zip").exists())
            self.assertFalse((target / "large-native-payload.zip").exists())

    def test_corrupt_artifact_is_rejected_before_extraction(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "artifact"
            def curl(args, **kwargs):
                Path(args[args.index("--output") + 1]).write_bytes(b"bad")
                return SimpleNamespace(returncode=0)
            artifact = {"id": 123, "name": "test", "size_in_bytes": 3, "digest": "sha256:" + "0" * 64}
            with patch.object(publisher, "artifact_download_url", return_value="https://example.invalid/blob"), \
                 patch.object(publisher.subprocess, "run", side_effect=curl), self.assertRaisesRegex(ValueError, "digest mismatch"):
                publisher.download_artifact(None, artifact, target)
            self.assertEqual([path.name for path in target.iterdir()], ["download.zip"])

    def test_only_successful_manual_default_branch_worker_runs_are_accepted(self):
        workflow = publisher.WORKFLOWS["linux"]
        run = {"repository": {"id": CENTRAL_REPOSITORY_ID}, "path": f".github/workflows/{workflow}",
               "event": "workflow_dispatch", "head_branch": "main", "status": "completed",
               "conclusion": "success", "head_sha": "a" * 40}
        self.assertEqual(publisher.verify_run(run, workflow, "main"), "a" * 40)
        for key, value in {"repository": {"id": 123}, "path": "wrong.yml", "event": "pull_request",
                           "head_branch": "feature", "status": "in_progress", "conclusion": "failure",
                           "head_sha": "not-a-sha"}.items():
            with self.subTest(key=key), self.assertRaises(ValueError):
                publisher.verify_run({**run, key: value}, workflow, "main")

    def test_only_publication_helpers_may_change_after_build(self):
        allowed = "\n".join(sorted(publisher.PUBLICATION_ONLY))
        with patch.object(publisher.subprocess, "check_output", return_value=allowed):
            publisher.verify_unchanged_sources("a" * 40)
        for file in ("plugins/vs-mlrt/scripts/vsmlrt.py", "plugins/vs-mlrt/pyproject.toml",
                     ".github/workflows/package-vs-mlrt-linux.yml"):
            with patch.object(publisher.subprocess, "check_output", return_value=file), self.assertRaises(ValueError):
                publisher.verify_unchanged_sources("a" * 40)

    def test_interrupted_upload_resumes_and_published_assets_are_immutable(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            wheel = directory / "vs_mlrt_generic-16.2.6+alice.1-py3-none-any.whl"
            wheel.write_bytes(b"fixture wheel bytes")
            inventory = {"source_revision": "a" * 40, "build_runs": [],
                         "wheels": [{"name": wheel.name, "sha256": digest_file(wheel)}]}
            write_json(directory / "vs-mlrt-release-inventory.json", inventory)
            release = {"id": 41, "draft": True, "assets": [], "html_url": "https://example.invalid/release"}
            class API:
                patches = 0
                def request(self, path, *, method="GET", data=None):
                    if path == f"repos/{publisher.CENTRAL_REPOSITORY}":
                        return {"default_branch": "main"}
                    if method == "PATCH":
                        self.patches += 1
                        self.assert_complete()
                        release.update(data)
                    return copy.deepcopy(release)
                def assert_complete(self):
                    if len(release["assets"]) != 2:
                        raise AssertionError("published before every asset was uploaded")
            api = API()
            def upload(args, **kwargs):
                path = Path(args[args.index("--input") + 1])
                release["assets"].append({"name": path.name, "state": "uploaded", "digest": "sha256:" + digest_file(path)})
            calls = 0
            def interrupted(args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise RuntimeError("connection interrupted")
                upload(args, **kwargs)
            with patch.object(publisher, "release_state", side_effect=lambda *args: copy.deepcopy(release)):
                with patch.object(publisher.subprocess, "run", side_effect=interrupted), self.assertRaisesRegex(RuntimeError, "interrupted"):
                    publisher.publish(api, directory, inventory, "16.2.6+alice.1")
                self.assertTrue(release["draft"])
                self.assertEqual(api.patches, 0)
                with patch.object(publisher.subprocess, "run", side_effect=upload) as uploader:
                    publisher.publish(api, directory, inventory, "16.2.6+alice.1")
                    self.assertEqual(uploader.call_count, 1)
                self.assertFalse(release["draft"])
                with patch.object(publisher.subprocess, "run") as uploader:
                    publisher.publish(api, directory, inventory, "16.2.6+alice.1")
                    uploader.assert_not_called()
                release["assets"][0]["digest"] = "sha256:" + "0" * 64
                with self.assertRaisesRegex(ValueError, "digest differs"):
                    publisher.publish(api, directory, inventory, "16.2.6+alice.1")


if __name__ == "__main__":
    unittest.main()
