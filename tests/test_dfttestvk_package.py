"""Test the submodule/source identity and meaningful prebuilt-package rejection paths."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import tarfile
import unittest
from unittest.mock import patch
import zipfile
from packaging.version import Version
from hatchling.builders.sdist import SdistBuilder

ROOT=Path(__file__).resolve().parents[1]
WRAPPER=ROOT/'plugins/vapoursynth-dfttestvk'
spec=importlib.util.spec_from_file_location('dfttestvk_hook',WRAPPER/'hatch_build.py')
hook=importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


class DFTTestVKPackagingTests(unittest.TestCase):
    def test_build_rejects_a_local_label_on_the_original_version(self):
        candidate=hook.CustomHook(str(WRAPPER),{},None,None,str(WRAPPER),'wheel')
        with patch.object(hook,'version',return_value=hook.source_record()['version']+'+alice.1'):
            with self.assertRaisesRegex(RuntimeError,'must equal the registered upstream version'):
                candidate.initialize('standard',{})

    def test_central_gitlink_and_registration_match(self):
        record=hook.source_record()
        tree=subprocess.check_output(['git','ls-files','--stage',record['submodule']],cwd=ROOT,text=True)
        self.assertEqual(tree.split()[:2],['160000',record['commit']])
        self.assertEqual(hook.native_source().resolve(),(ROOT/record['submodule']).resolve())
        self.assertEqual(hook.version(),record['version'])
        self.assertIsNone(Version(hook.version()).local)

    def test_nested_submodule_still_rejects_wrong_revision_and_dirty_source(self):
        record=hook.source_record()
        with patch.object(hook.subprocess,'check_output',return_value='0'*40):
            with self.assertRaisesRegex(RuntimeError,'differs from source.json'):
                hook.native_source()
        with patch.object(hook.subprocess,'check_output',side_effect=[record['commit'],' M src/dfttestvk.cpp']):
            with self.assertRaisesRegex(RuntimeError,'uncommitted changes'):
                hook.native_source()

    def test_sdist_contains_standalone_source_and_preserves_native_submodule(self):
        native=hook.native_source()
        marker=(native/'.git').read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            artifact=next(SdistBuilder(str(WRAPPER)).build(directory=directory))
            with tarfile.open(artifact) as archive:
                prefix=archive.getnames()[0].split('/')[0]+'/'
                names={name.removeprefix(prefix) for name in archive.getnames()}
                self.assertIn('native/CMakeLists.txt',names)
                self.assertIn('native/src/dfttestvk.cpp',names)
                self.assertIn('native/reference/source-lock.json',names)
                self.assertIn('native/tools/fetch_dependencies.py',names)
                self.assertTrue(all('.git' not in Path(name).parts for name in names))
                self.assertFalse(any(name.startswith(('native/build/','native/dependencies/','native/docs/')) for name in names))
        self.assertEqual((native/'.git').read_bytes(),marker)
        self.assertEqual(hook.native_source(),native)

    def package(self,path,**overrides):
        record=hook.source_record()
        files={'dfttestvk.dll':b'MZ-test-native','manifest.vs':b'[VapourSynth Manifest V1]\ndfttestvk\n',
               'LICENSE':b'GPL-3.0-or-later','THIRD_PARTY.md':b'DFTTest/DFTTest2 and FFTW notices'}
        manifest={'distribution':hook.NAME,'version':hook.version(),'platform':'windows-x86_64',
                  'upstream_commit':record['commit'],'sha256':{n:hashlib.sha256(v).hexdigest() for n,v in files.items()}}
        manifest.update(overrides)
        with zipfile.ZipFile(path,'w') as archive:
            for name,data in files.items():archive.writestr('dfttestvk/'+name,data)
            archive.writestr('dfttestvk/manifest.json',json.dumps(manifest))

    def test_correct_package_stages_exact_plugin_bytes(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(hook,'platform_info',return_value=('windows-x86_64','.dll','win_amd64')):
            root=Path(directory);archive=root/'p.zip';self.package(archive)
            target=root/'payload';hook.stage_archive(archive,target)
            self.assertEqual((target/'dfttestvk.dll').read_bytes(),b'MZ-test-native')

    def test_wrong_platform_source_version_and_digest_are_rejected(self):
        cases=[{'platform':'linux-x86_64'},{'upstream_commit':'0'*40},{'version':'0.0'},
               {'version':hook.version()+'+alice.1'},
               {'sha256':{'dfttestvk.dll':'0'*64}}]
        with tempfile.TemporaryDirectory() as directory,patch.object(hook,'platform_info',return_value=('windows-x86_64','.dll','win_amd64')):
            root=Path(directory)
            for n,overrides in enumerate(cases):
                with self.subTest(overrides=overrides):
                    archive=root/f'p{n}.zip';self.package(archive,**overrides)
                    with self.assertRaises(ValueError):hook.stage_archive(archive,root/f'out{n}')

    def test_archive_cannot_escape_plugin_directory(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(hook,'platform_info',return_value=('windows-x86_64','.dll','win_amd64')):
            root=Path(directory);archive=root/'p.zip';self.package(archive)
            with zipfile.ZipFile(archive,'a') as z:z.writestr('dfttestvk/../../escape.dll',b'bad')
            with self.assertRaises(ValueError):hook.stage_archive(archive,root/'payload')
            self.assertFalse((root/'escape.dll').exists())


if __name__=='__main__':
    unittest.main()
