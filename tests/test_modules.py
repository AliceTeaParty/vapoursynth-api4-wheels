"""Exercise real wheel installs and the source/publish trust boundaries."""
from __future__ import annotations

import base64
import copy
import csv
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import venv
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import module_common as common
import publish_module as publisher
import submit_module_update as submitter
from validate_module_wheel import validate_wheel

SOURCE_SHA = "a" * 40
CENTRAL_SHA = "b" * 40
PYPROJECT = b'[build-system]\nrequires=["hatchling>=1.26"]\nbuild-backend="hatchling.build"\n[project]\nname="demo"\nversion="1.0"\nrequires-python=">=3.10"\ndependencies=[]\n'


def registration() -> dict:
    return {
        "schema_version": 1, "repository": "owner/demo", "repository_id": 123,
        "distribution": "demo", "import_name": "demo",
        "project_subdirectory": ".", "default_ref": "main",
        "requesters": ["owner"], "required_files": ["demo/__init__.py", "demo/data.glsl"],
        "module": "demo", "config_sha256": "c" * 64,
    }


def request() -> dict:
    return {
        "api_version": "1", "module": "demo", "source_ref": "main",
        "source_sha": SOURCE_SHA, "expected_version": "1.0", "request_id": "demo-request",
    }


class SourceAPI:
    def __init__(self):
        self.repository_id = 123
        self.sha = SOURCE_SHA
        self.pyproject = PYPROJECT
        self.compare_status = "identical"
        self.run = {
            "id": 1234, "repository": {"id": common.CENTRAL_REPOSITORY_ID},
            "path": common.BUILD_WORKFLOW, "event": "workflow_dispatch",
            "head_branch": "main", "head_sha": CENTRAL_SHA,
            "status": "completed", "conclusion": "success",
            "actor": {"login": "owner"}, "html_url": "https://example.invalid/run/1234",
        }

    def request(self, path: str, **kwargs):
        if path == f"repos/{common.CENTRAL_REPOSITORY}":
            return {"id": common.CENTRAL_REPOSITORY_ID, "default_branch": "main"}
        if path == "repos/owner/demo":
            return {"id": self.repository_id, "full_name": "owner/demo", "default_branch": "main"}
        if "/actions/runs/" in path:
            return self.run
        if "/commits/" in path:
            return {"sha": self.sha}
        if "/compare/" in path:
            return {"status": self.compare_status}
        raise AssertionError(path)

    def contents(self, repository, path, sha):
        assert repository == "owner/demo" and path == "pyproject.toml" and sha == self.sha
        return self.pyproject


def source_plan(api=None):
    return common.resolve_plan(registration(), request(), api or SourceAPI(), actor="owner", central_sha=CENTRAL_SHA)


def wheel_files():
    return {
        "demo/__init__.py": b"import intentionally_missing_demo_runtime_dependency\n",
        "demo/data.glsl": b"// fixture shader\n",
        "demo-1.0.dist-info/METADATA": b"Metadata-Version: 2.4\nName: demo\nVersion: 1.0\nRequires-Python: >=3.10\n\n",
        "demo-1.0.dist-info/WHEEL": b"Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
    }


def write_wheel(directory: Path, files=None, *, bad_record=False, duplicate=False) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    wheel = directory / "demo-1.0-py3-none-any.whl"
    files = copy.deepcopy(files or wheel_files())
    record = io.StringIO()
    writer = csv.writer(record, lineterminator="\n")
    for name, content in files.items():
        encoded = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).decode().rstrip("=")
        writer.writerow([name, "sha256=" + ("bad" if bad_record else encoded), len(content)])
    writer.writerow(["demo-1.0.dist-info/RECORD", "", ""])
    files["demo-1.0.dist-info/RECORD"] = record.getvalue().encode()
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
        if duplicate:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                archive.writestr("demo/data.glsl", files["demo/data.glsl"])
    return wheel


class RegistryAndSourceTests(unittest.TestCase):
    def test_existing_modules_keep_original_authority(self):
        registry = common.load_registry()
        self.assertTrue({"rksfunc", "rkstool"}.issubset(registry))
        self.assertEqual(registry["rksfunc"]["repository"], "RyougiKukoc/rksfunc")
        self.assertEqual(registry["rkstool"]["repository"], "RyougiKukoc/rkstool")
        self.assertIn("rksfunc/KrigBilateral.glsl", registry["rksfunc"]["required_files"])
        self.assertTrue(any("LGPL-3.0-or-later.txt" in value for value in registry["rksfunc"]["required_files"]))

    def test_additional_registration_keeps_seed_module_checks_working(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for module in ("rksfunc", "rkstool"):
                target = root / "modules" / module / "module.toml"
                target.parent.mkdir(parents=True)
                shutil.copyfile(common.ROOT / "modules" / module / "module.toml", target)
            target = root / "modules/third-module/module.toml"
            target.parent.mkdir()
            target.write_text(
                'schema_version=1\nrepository="example/third-module"\nrepository_id=123456\n'
                'distribution="third-module"\nimport_name="third_module"\nproject_subdirectory="."\n'
                'default_ref="main"\nrequesters=["owner"]\nrequired_files=["third_module/__init__.py"]\n',
                encoding="utf-8",
            )
            registry = common.load_registry(root)
            self.assertEqual(registry["third-module"]["distribution"], "third-module")
            with patch.object(common, "load_registry", return_value=registry):
                self.test_existing_modules_keep_original_authority()

    def test_request_rejects_repository_commands_and_publish_switches(self):
        for key in ("repository", "command", "publish", "download_url"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                common.validate_request({**request(), key: "unsafe"})

    def test_registry_hash_survives_windows_checkout_line_endings(self):
        original = common.ROOT / "modules/rkstool/module.toml"
        raw = original.read_bytes().replace(b"\r\n", b"\n")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file = root / "modules/rkstool/module.toml"
            file.parent.mkdir(parents=True)
            file.write_bytes(raw)
            before = common.load_registry(root)["rkstool"]
            file.write_bytes(raw.replace(b"\n", b"\r\n"))
            self.assertEqual(common.load_registry(root)["rkstool"], before)

    def test_author_requires_fixed_source_and_all_has_no_shared_overrides(self):
        common.validate_request(request(), author_request=True)
        for key in ("source_sha", "expected_version", "source_ref", "request_id"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                common.validate_request({**request(), key: ""}, author_request=True)
        with self.assertRaises(ValueError):
            common.validate_request({**request(), "module": "all"})

    def test_path_and_ref_escape_are_rejected(self):
        for path in ("../demo", "/demo", "D:/demo", "demo\\file", "demo//file"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                common.relative_path(path)
        for ref in ("main;echo", "-main", "main\n", "refs/pull/1/head", "../main"):
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                common.validate_ref(ref)

    def test_ref_is_resolved_once_and_dependencies_stay_empty(self):
        plan = source_plan()
        self.assertEqual(plan["source_sha"], SOURCE_SHA)
        self.assertEqual(plan["dependencies"], [])
        self.assertEqual(plan["requires_python"], ">=3.10")
        self.assertEqual(plan["pyproject_sha256"], hashlib.sha256(PYPROJECT).hexdigest())

    def test_source_race_repo_identity_actor_and_version_are_rejected(self):
        for change in ("sha", "repository_id", "version", "actor"):
            with self.subTest(change=change):
                api = SourceAPI()
                actor = "owner"
                if change == "sha":
                    api.sha = "d" * 40
                elif change == "repository_id":
                    api.repository_id = 999
                elif change == "version":
                    api.pyproject = PYPROJECT.replace(b'version="1.0"', b'version="2.0"')
                else:
                    actor = "other"
                with self.assertRaises(ValueError):
                    common.resolve_plan(registration(), request(), api, actor=actor, central_sha=CENTRAL_SHA)

    def test_dynamic_and_wrong_project_metadata_are_rejected(self):
        for data in (
            PYPROJECT.replace(b'name="demo"', b'name="other"'),
            PYPROJECT.replace(b'version="1.0"', b'dynamic=["version"]'),
            PYPROJECT.replace(b'version="1.0"', b'version="1.0+local"'),
        ):
            with self.subTest(data=data), self.assertRaises(ValueError):
                common.project_metadata(data, "demo")

    def test_notification_binds_caller_and_sends_commit_not_moving_branch(self):
        with patch.object(submitter, "load_registry", return_value={"demo": registration()}), patch.object(submitter, "git_sha", return_value=CENTRAL_SHA):
            payload = submitter.prepare_request("demo", "main", "owner/demo", "owner", "req", SourceAPI())
            self.assertEqual(payload["source_ref"], SOURCE_SHA)
            self.assertEqual(payload["source_sha"], SOURCE_SHA)
            with self.assertRaises(ValueError):
                submitter.prepare_request("demo", "main", "other/demo", "owner", "req", SourceAPI())


class WheelTests(unittest.TestCase):
    def test_python2_tag_and_missing_python_requirement_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wheel = write_wheel(root)
            incompatible = wheel.with_name(wheel.name.replace("py3-none-any", "py2.py3-none-any"))
            wheel.rename(incompatible)
            with self.assertRaisesRegex(ValueError, "py3-none-any"):
                validate_wheel(incompatible, source_plan())
            files = wheel_files()
            files["demo-1.0.dist-info/METADATA"] = files["demo-1.0.dist-info/METADATA"].replace(b"Requires-Python: >=3.10\n", b"")
            with self.assertRaisesRegex(ValueError, "Requires-Python"):
                validate_wheel(write_wheel(root, files), source_plan())

    def test_pure_module_is_valid_and_runtime_import_is_not_claimed(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = validate_wheel(write_wheel(Path(temp)), source_plan())
        self.assertEqual(manifest["dependencies"], [])
        self.assertIn("not tested", manifest["validation"]["runtime_import"])
        self.assertIn("demo/data.glsl", manifest["file_sha256"])

    def test_missing_resource_metadata_dependency_and_native_file_are_rejected(self):
        variants = []
        files = wheel_files()
        del files["demo/data.glsl"]
        variants.append(files)
        files = wheel_files()
        files["demo-1.0.dist-info/METADATA"] = files["demo-1.0.dist-info/METADATA"].replace(b"Version: 1.0", b"Version: 2.0")
        variants.append(files)
        files = wheel_files()
        files["demo-1.0.dist-info/METADATA"] = files["demo-1.0.dist-info/METADATA"].replace(b"\n\n", b"\nRequires-Dist: unwanted\n\n")
        variants.append(files)
        files = wheel_files()
        files["demo/native.pyd"] = b"not pure"
        variants.append(files)
        for files in variants:
            with self.subTest(files=tuple(files)), tempfile.TemporaryDirectory() as temp, self.assertRaises(ValueError):
                validate_wheel(write_wheel(Path(temp), files), source_plan())

    def test_traversal_duplicate_and_bad_record_are_rejected(self):
        for mode in ("traversal", "duplicate", "bad-record"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                files = wheel_files()
                if mode == "traversal":
                    files["../outside"] = b"unsafe"
                with self.assertRaises(ValueError):
                    validate_wheel(write_wheel(Path(temp), files, duplicate=mode == "duplicate", bad_record=mode == "bad-record"), source_plan())

    def test_real_hatch_build_installs_resources_and_keeps_missing_dependency_error(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            (source / "demo").mkdir(parents=True)
            (source / "pyproject.toml").write_bytes(PYPROJECT)
            (source / "demo/__init__.py").write_bytes(wheel_files()["demo/__init__.py"])
            (source / "demo/data.glsl").write_bytes(wheel_files()["demo/data.glsl"])
            subprocess.run([sys.executable, "-m", "build", "--wheel", "--no-isolation", "--outdir", str(root / "wheel"), str(source)], check=True, capture_output=True)
            wheel = next((root / "wheel").glob("*.whl"))
            plan = source_plan()
            manifest = validate_wheel(wheel, plan)
            env = root / "env"
            venv.EnvBuilder(with_pip=True).create(env)
            python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            subprocess.run([str(python), "-m", "pip", "install", "--no-deps", "--no-index", str(wheel)], check=True, capture_output=True)
            plan_file, manifest_file = root / "plan.json", root / "manifest.json"
            common.write_json(plan_file, plan)
            common.write_json(manifest_file, manifest)
            subprocess.run([str(python), "-I", str(SCRIPTS / "smoke_installed_module.py"), "--plan", str(plan_file), "--manifest", str(manifest_file)], check=True, cwd=root, capture_output=True)
            self.assertEqual(common.read_json(manifest_file)["validation"]["installed_files"], "passed")
            result = subprocess.run([str(python), "-I", "-c", "import demo"], cwd=root, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ModuleNotFoundError", result.stderr)
            self.assertIn("intentionally_missing_demo_runtime_dependency", result.stderr)


class PublisherTests(unittest.TestCase):
    def test_draft_lookup_paginates_and_rejects_ambiguous_drafts(self):
        tag = "module-demo-v1.0"
        other = {"id": 1, "tag_name": "other", "draft": True}
        draft = {"id": 9, "tag_name": tag, "draft": True}

        class ListingAPI:
            def __init__(self, duplicate=False):
                self.pages = []
                self.duplicate = duplicate

            def request(self, path, **kwargs):
                if "/releases/tags/" in path:
                    raise common.GitHubError("GET", path, 404)
                page = int(path.rsplit("=", 1)[1])
                self.pages.append(page)
                if page == 1:
                    return [other] * 99 + ([draft] if self.duplicate else [other])
                return [draft]

        api = ListingAPI()
        self.assertEqual(publisher.release_state(api, tag), draft)
        self.assertEqual(api.pages, [1, 2])
        with self.assertRaisesRegex(ValueError, "multiple drafts"):
            publisher.release_state(ListingAPI(duplicate=True), tag)

    def test_draft_lookup_does_not_hide_authentication_failures(self):
        class DeniedAPI:
            def request(self, path, **kwargs):
                raise common.GitHubError("GET", path, 403)

        with self.assertRaises(common.GitHubError):
            publisher.release_state(DeniedAPI(), "module-demo-v1.0")

    def test_only_successful_manual_default_branch_runs_are_accepted(self):
        with patch.object(publisher, "load_registry", return_value={"demo": registration()}):
            self.assertEqual(publisher.verify_run(SourceAPI(), "1234", "demo")["id"], 1234)
            for field, value in (
                ("event", "pull_request"), ("head_branch", "feature"), ("path", ".github/workflows/other.yml"),
                ("conclusion", "failure"), ("status", "in_progress"), ("repository", {"id": 999}),
                ("actor", {"login": "stranger"}),
            ):
                with self.subTest(field=field):
                    api = SourceAPI()
                    api.run[field] = value
                    with self.assertRaises(ValueError):
                        publisher.verify_run(api, "1234", "demo")

    def test_publish_requires_all_four_installed_validation_results_and_reviewed_hash(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(publisher, "load_registry", return_value={"demo": registration()}):
            root = Path(temp)
            wheel = write_wheel(root / "wheel")
            plan = source_plan()
            result = validate_wheel(wheel, plan)
            checks = root / "validation"
            for label, (system, prefix) in publisher.VALIDATION_LABELS.items():
                tested = copy.deepcopy(result)
                tested["validation"].update(platform=system, python=prefix + "1", installed_files="passed")
                common.write_json(checks / f"{label}.json", tested)
            api = SourceAPI()
            self.assertEqual(publisher.validate_candidate(api, api.run, plan, wheel.parent, checks, result["sha256"])[0], wheel)
            with self.assertRaises(ValueError):
                publisher.validate_candidate(api, api.run, plan, wheel.parent, checks, "0" * 64)
            api.compare_status = "diverged"
            with self.assertRaises(ValueError):
                publisher.validate_candidate(api, api.run, plan, wheel.parent, checks, result["sha256"])
            api.compare_status = "identical"
            (checks / "windows-latest-3.13.json").unlink()
            with self.assertRaises(ValueError):
                publisher.validate_candidate(api, api.run, plan, wheel.parent, checks, result["sha256"])

    def test_metadata_change_after_build_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(publisher, "load_registry", return_value={"demo": registration()}):
            api = SourceAPI()
            api.pyproject = PYPROJECT + b"\n# changed\n"
            wheel = write_wheel(Path(temp))
            with self.assertRaisesRegex(ValueError, "pyproject_sha256"):
                publisher.validate_candidate(api, api.run, source_plan(), wheel.parent, wheel.parent, common.digest_file(wheel))

    def test_release_upload_is_resumable_and_never_clobbers_published_content(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wheel = write_wheel(root)
            manifest = validate_wheel(wheel, source_plan())
            manifest.update(build_run_url="https://example.invalid/run", build_run_id=1234)
            manifest_file = root / "source-manifest.json"
            common.write_json(manifest_file, manifest)
            state = {"release": None, "uploads": [], "fail_manifest_once": True, "creates": 0}

            class ReleaseAPI:
                def request(self, path, method="GET", data=None):
                    if path == f"repos/{common.CENTRAL_REPOSITORY}":
                        return {"default_branch": "main"}
                    if "/releases/tags/" in path:
                        if state["release"] is None or state["release"]["draft"]:
                            raise common.GitHubError("GET", path, 404)
                        return copy.deepcopy(state["release"])
                    if "/releases?" in path:
                        return [copy.deepcopy(state["release"])] if state["release"] else []
                    if method == "DELETE":
                        asset_id = int(path.rsplit("/", 1)[1])
                        state["release"]["assets"] = [asset for asset in state["release"]["assets"] if asset["id"] != asset_id]
                        return None
                    if method == "POST":
                        state["creates"] += 1
                        self_data = data
                        state["release"] = {"id": 99, "draft": True, "assets": [], "html_url": "https://example.invalid/release", **self_data}
                    elif method == "PATCH":
                        state["release"].update(data)
                    return copy.deepcopy(state["release"])

            def upload(command, **kwargs):
                self.assertNotIn("--clobber", command)
                self.assertIn("/releases/99/assets?name=", command[4])
                file = Path(command[command.index("--input") + 1])
                if file.name == "source-manifest.json" and state["fail_manifest_once"]:
                    state["fail_manifest_once"] = False
                    state["release"]["assets"].append({"id": 999, "name": file.name, "state": "starter", "size": 0})
                    raise subprocess.CalledProcessError(1, command)
                state["uploads"].append(file.name)
                state["release"]["assets"].append({
                    "id": 100 + len(state["uploads"]), "size": file.stat().st_size,
                    "state": "uploaded",
                    "name": file.name, "digest": "sha256:" + common.digest_file(file),
                    "browser_download_url": f"https://github.com/{common.CENTRAL_REPOSITORY}/releases/download/tag/{file.name}",
                })

            with patch.object(publisher.subprocess, "run", side_effect=upload), patch.object(publisher.subprocess, "check_output", return_value=manifest_file.read_bytes()):
                api = ReleaseAPI()
                with self.assertRaises(subprocess.CalledProcessError):
                    publisher.publish_release(api, wheel, manifest_file, manifest)
                self.assertTrue(state["release"]["draft"])
                self.assertEqual(state["uploads"], [wheel.name])
                self.assertEqual(publisher.publish_release(api, wheel, manifest_file, manifest)[1], "published")
                self.assertEqual(state["uploads"], [wheel.name, "source-manifest.json"])
                self.assertEqual(state["creates"], 1)
                self.assertEqual(state["release"]["target_commitish"], "main")
                self.assertEqual(publisher.publish_release(api, wheel, manifest_file, manifest)[1], "already_published")
                self.assertEqual(len(state["uploads"]), 2)
                state["release"]["assets"][0]["digest"] = "sha256:" + "0" * 64
                with self.assertRaises(ValueError):
                    publisher.publish_release(api, wheel, manifest_file, manifest)


if __name__ == "__main__":
    unittest.main()
