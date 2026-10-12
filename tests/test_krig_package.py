"""Test the submodule/source identity and meaningful prebuilt-package rejection paths."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[1]
WRAPPER=ROOT/'packaging/vapoursynth-krigbilateralvk'
spec=importlib.util.spec_from_file_location('krig_hook',WRAPPER/'hatch_build.py')
hook=importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


class KrigPackagingTests(unittest.TestCase):
    def test_central_gitlink_and_registration_match(self):
        record=hook.source_record()
        tree=subprocess.check_output(['git','ls-files','--stage',record['submodule']],cwd=ROOT,text=True)
        self.assertEqual(tree.split()[:2],['160000',record['commit']])
        self.assertEqual(hook.native_source().resolve(),(ROOT/record['submodule']).resolve())
        self.assertEqual(hook.version(),record['version']+'+alice.1')

    def package(self,path,**overrides):
        record=hook.source_record()
        files={'krigbilateralvk.dll':b'MZ-test-native','manifest.vs':b'[VapourSynth Manifest V1]\nkrigbilateralvk\n',
               'LICENSE':b'LGPL-3.0-or-later','GPL.txt':b'GPL3'}
        manifest={'distribution':hook.NAME,'version':hook.version(),'platform':'windows-x86_64',
                  'upstream_commit':record['commit'],'sha256':{n:hashlib.sha256(v).hexdigest() for n,v in files.items()}}
        manifest.update(overrides)
        with zipfile.ZipFile(path,'w') as archive:
            for name,data in files.items():archive.writestr('krigbilateralvk/'+name,data)
            archive.writestr('krigbilateralvk/manifest.json',json.dumps(manifest))

    def test_correct_package_stages_exact_plugin_bytes(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(hook,'platform_info',return_value=('windows-x86_64','.dll','win_amd64')):
            root=Path(directory);archive=root/'p.zip';self.package(archive)
            target=root/'payload';hook.stage_archive(archive,target)
            self.assertEqual((target/'krigbilateralvk.dll').read_bytes(),b'MZ-test-native')

    def test_wrong_platform_source_version_and_digest_are_rejected(self):
        cases=[{'platform':'linux-x86_64'},{'upstream_commit':'0'*40},{'version':'0.0+alice.1'},
               {'sha256':{'krigbilateralvk.dll':'0'*64}}]
        with tempfile.TemporaryDirectory() as directory,patch.object(hook,'platform_info',return_value=('windows-x86_64','.dll','win_amd64')):
            root=Path(directory)
            for n,overrides in enumerate(cases):
                with self.subTest(overrides=overrides):
                    archive=root/f'p{n}.zip';self.package(archive,**overrides)
                    with self.assertRaises(ValueError):hook.stage_archive(archive,root/f'out{n}')

    def test_archive_cannot_escape_plugin_directory(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(hook,'platform_info',return_value=('windows-x86_64','.dll','win_amd64')):
            root=Path(directory);archive=root/'p.zip';self.package(archive)
            with zipfile.ZipFile(archive,'a') as z:z.writestr('krigbilateralvk/../../escape.dll',b'bad')
            with self.assertRaises(ValueError):hook.stage_archive(archive,root/'payload')
            self.assertFalse((root/'escape.dll').exists())


if __name__=='__main__':
    unittest.main()
