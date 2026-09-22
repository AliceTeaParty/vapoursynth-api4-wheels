import importlib.util
import tempfile
import unittest
from pathlib import Path


def load_tool(name: str):
    path = Path(__file__).parents[1] / "plugins" / "vs-nlq" / "tools" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InstalledPluginPathTests(unittest.TestCase):
    def test_supports_extension_module_and_package_layouts(self) -> None:
        tools = [load_tool("smoke_installed_wheel.py"), load_tool("smoke_native_package.py")]
        with tempfile.TemporaryDirectory() as directory:
            site_packages = Path(directory) / "site-packages"
            expected = (site_packages / "vapoursynth" / "plugins" / "vs-nlq").resolve()
            module_layouts = [
                site_packages / "vapoursynth.pyd",
                site_packages / "vapoursynth" / "__init__.py",
            ]
            for tool in tools:
                for module_file in module_layouts:
                    with self.subTest(tool=tool.__name__, module_file=module_file):
                        self.assertEqual(expected, tool.installed_plugin_dir(str(module_file)))


if __name__ == "__main__":
    unittest.main()
