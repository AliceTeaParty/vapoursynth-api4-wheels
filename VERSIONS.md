# Source and wheel version records

Native plugin subtrees and centrally maintained Python module subtrees have
separate tables. Revisions below are pinned source identities, not claims
that a wheel has already been published. Existing external modules rksfunc
and rkstool remain owned and versioned in their original repositories.

## Native plugins

This table records the existing plugin metadata and subtree baseline. Variant
and component packaging can have additional pyproject.toml files under a
plugin; those files remain authoritative for each native wheel.

| Directory | Primary distribution | Wheel version | Subtree upstream revision |
| --- | --- | --- | --- |
| plugins/vapoursynth-bm3dcuda | vapoursynth-bm3dcpu | 2.16+alice.1 | 8c16009ce44b5e9b9fcf3288e1a7a922f9b4ccea |
| plugins/vapoursynth-dfttest | vapoursynth-dfttest | 1.1+alice.1 | bc5e0186a7f309556f20a8e9502f2238e39179b8 |
| plugins/vapoursynth-dfttest2 | vapoursynth-dfttest2-cpu | 10.2+alice.1 | a0a33986fb1fe8a5b7844e8a1b1f197ce19af35d |
| plugins/vapoursynth-fft3dfilter | vapoursynth-fft3dfilter | 2.1+alice.1 | b023e21954423f29fdefcb54a6b0540deb3bdac4 |
| plugins/vapoursynth-knlm | vapoursynth-knlm | 1.1.2+alice.1 | c4af339b1d7b41268b3c5015627e68434bc139c7 |
| plugins/vapoursynth-misc | vapoursynth-misc | 2.1+alice.1 | 07e0589a381f7deb3bf533bb459a94482bccc5c7 |
| plugins/vapoursynth-nnedi3cl | vapoursynth-nnedi3cl | 8.1+alice.1 | eb2a810c0b7dfdd3ad908a1bdc07d6daab64eb57 |
| plugins/vapoursynth-retinex | vapoursynth-retinex | 4.1+alice.1 | 6bfbdd429159c85075dc4b08e0ac4e706470916b |
| plugins/vapoursynth-smoothuv | vapoursynth-smoothuv | 3.1+alice.1 | 30a2851b4573802b7684fd20ec2cec05ab49925f |
| plugins/vapoursynth-tcanny | vapoursynth-tcanny | 14.1+alice.1 | 14ac2ceeb59afc7089974d0ae233fe8d0ea183c8 |
| plugins/vapoursynth-tcomb | vapoursynth-tcomb | 4.2+alice.1 | 29318d2b9b5e2f266202294498533805f48b194f |
| plugins/vs-cfl | vs-cfl | 1.0.2+alice.1 | 502791b86d286ecbf9779ec033fc93789ac5a6c2 |
| plugins/vs-mlrt | vs-mlrt-generic / vs-mlrt-cu121 / vs-mlrt-cu129 | 16.2.6+alice.1 (entry packages) | 1f166ba63dee9af1b19b8c62a333e2525d4a2860 |
| plugins/vs-nlq | vs-nlq | 1.2.0+alice.1 | 97cbb19a9883feb05e558a6fb4a2192b7c6d8005 |

## Python module subtrees

Migration source: [https://github.com/RyougiKukoc/VapourSynth-Scripts-Collection](https://github.com/RyougiKukoc/VapourSynth-Scripts-Collection)
at 14091484381778fe55102b58ac584e38f5e0fc6a, Collection version 0.3.0. Every runtime file matches this
final Collection snapshot. The per-directory patch combines the recorded
gist/fork edits and all subsequent Collection edits into one commit.

| Directory | Wheel version | Canonical upstream | Upstream revision | Intermediate snapshot | Import commit | Combined patch commit |
| --- | --- | --- | --- | --- | --- | --- |
| modules/sdering-fix | 0.3.0.post1+alice.1 | [https://gist.github.com/RyougiKukoc/c3832d96a8dce6f609f6e29888af94a6](https://gist.github.com/RyougiKukoc/c3832d96a8dce6f609f6e29888af94a6) | 257d981098f67479bf029acda0fdeffa7c38ee08 | same as upstream | 1a45353bc479070662af616ce3bbc8313636d42f | 285a913c1314b4ddd531127f6d4f539f28ed0ac6 |
| modules/csmod | 0.3.0.post1+alice.1 | [https://github.com/fdar0536/VapourSynth-Contra-Sharpen-mod](https://github.com/fdar0536/VapourSynth-Contra-Sharpen-mod) | b9ff7253bf217dded071b88fb8a6d212aceb81f4 | same as upstream | 03e969984742a71409376c4de6898b6a5975355f | bfb8abc11413dd32afea6ca3b03c4e4b63099f28 |
| modules/nnedi3-resample | 2.post1+alice.1 | [https://github.com/HomeOfVapourSynthEvolution/nnedi3_resample](https://github.com/HomeOfVapourSynthEvolution/nnedi3_resample) | 314c6446a65c2e25fd7a997051b09830f361675e | same as upstream | d146a460436349d8bf52569a3965907164bf1b17 | 4948a7ebbdf6b4ff9246af59d720f31960bc75fc |
| modules/nnedi3-rpow2 | 1.1.0.post1+alice.1 | [https://gist.github.com/4re/342624c9e1a144a696c6](https://gist.github.com/4re/342624c9e1a144a696c6) | 68ec4bdff1e51a3832b163198ed7ea00e1c1ab46 | 4e6c2fac9d3159f1f1c93e2a92d492ce7b69b1b3 | 17d595f7441a123c71ee75bfd065b723fe8ed897 | 76c37e37c47c69fe0c68f77994f9e34f6112fad1 |
| modules/havsfunc | 33.post1+alice.1 | [https://github.com/HomeOfVapourSynthEvolution/havsfunc](https://github.com/HomeOfVapourSynthEvolution/havsfunc) | 7f0a9a7a37b60a05b9f408024d203e511e544a61 | 4e0d21258869283ce04568dda0173e4c8b890668 | 602c6cddca4a1f19c99b16527a383cc066905548 | 1c88bf06cf806c16e08b38fdf3c4814f586de407 |
| modules/getfnative | 0.3.0.post1+alice.1 | [https://github.com/YomikoR/GetFnative](https://github.com/YomikoR/GetFnative) | 9edcd58346fbffa46f6735637f91ae24dfabcb74 | same as upstream | eee47fdb06b71ee33e22a7709d30aa163c26bf4f | bc147d8926095ae436e45f43e67b49092c101b7b |
| modules/mvsfunc | 11.post1+alice.1 | [https://github.com/HomeOfVapourSynthEvolution/mvsfunc](https://github.com/HomeOfVapourSynthEvolution/mvsfunc) | 865c7486ca860d323754ec4774bc4cca540a7076 | same as upstream | b0884169d8b99ac049b1dc0ed625bf959bed4b93 | 8b8d2a30d2c466a3d22a21fc1569e29f571d2360 |
| modules/muvsfunc | 0.3.0.post1+alice.1 | [https://github.com/WolframRhodium/muvsfunc](https://github.com/WolframRhodium/muvsfunc) | d278cd3a68250a4d9562c6ec2b401f1a76c324a3 | same as upstream | 62f5893814685afee21ca1bc9876c97721fbb73a | ee3bb3e7df770fc76359803a07c1115f09c92894 |
| modules/fvsfunc | 0.3.0.post1+alice.1 | [https://github.com/Irrational-Encoding-Wizardry/fvsfunc](https://github.com/Irrational-Encoding-Wizardry/fvsfunc) | 076dbde68227f6cca91304a447b2a02b0e95413e | same as upstream | 64191bb0dd8ea15bd9ababc74f7ccea3479abbe8 | 84f83a60a2404817f951550b6606969ee0de7f79 |
| modules/vstaambk | 0.3.0.post1+alice.1 | [https://github.com/HomeOfVapourSynthEvolution/vsTAAmbk](https://github.com/HomeOfVapourSynthEvolution/vsTAAmbk) | fef19f85c96c0d7e281627942c358ee1b92d7dbe | same as upstream | 51627e28e665385de04bd5e47e98391374a22231 | 906a1e5b61d5b44936dc48bdcd316677aaed0337 |
| modules/kagefunc | 0.3.0.post1+alice.1 | [https://github.com/Irrational-Encoding-Wizardry/kagefunc](https://github.com/Irrational-Encoding-Wizardry/kagefunc) | 96947a1bda5639a4e0b89202e964a15bc337521d | same as upstream | 774f85fcbf56c16f59b78e0abbca13dcfd9cd0bb | e4ea32257081ba9137db135df2c956247881882d |
| modules/yvsfunc | 0.3.0.post1+alice.1 | [https://github.com/YomikoR/yvsfunc](https://github.com/YomikoR/yvsfunc) | ee3309efe2543c6680619f6deb64496102e7eb64 | same as upstream | fd80ac44f424dcfd62d4d8ac0279868209eb32ad | 1eab14ba306ee832738cb489a7835dfae606d9f1 |

## Collection entry

| Directory | Distribution | Wheel version | Dependency policy |
| --- | --- | --- | --- |
| modules/vs-collection-rk | vs-collection-rk | 0.4.0+alice.1 | Exact pins for the 12 component wheels above |

## HAvsFunc modification chain

1. HomeOfVapourSynthEvolution/havsfunc at 7f0a9a7a37b60a05b9f408024d203e511e544a61.
2. RyougiKukoc gist ea451bd51d0dc33ba5e0c4d5566653cf at 4e0d21258869283ce04568dda0173e4c8b890668.
3. VapourSynth-Scripts-Collection through 14091484381778fe55102b58ac584e38f5e0fc6a.
4. The one combined patch shown in the module table.

The Collection's initial HAvsFunc blob is byte-identical to the recorded gist.
The gist adds 42 and removes 12 lines relative to the real upstream baseline;
the Collection then adds 1554 and removes 88 lines relative to that gist.
Those layers are both retained; importing only the gist would omit substantial
Collection changes. Full intermediate and Collection commit lists are stored
in modules/havsfunc/provenance.toml and the combined patch commit message.

nnedi3_rpow2 similarly uses the canonical gist's common ancestor
68ec4bdff1e51a3832b163198ed7ea00e1c1ab46, with the two fork commits
2afe972e5e09b0278924a146a137dffd494e2926 and
4e6c2fac9d3159f1f1c93e2a92d492ce7b69b1b3 plus Collection edits in one patch.

## Updating a module

Fetch and review a chosen canonical upstream commit first. Run git subtree
pull --prefix=modules/<id> <canonical-url> <commit> --squash, then resolve
any conflicts with the local modifications. Keep the original upstream layout
so the subtree machinery can perform this three-way merge. Do not replace
the subtree with a downloaded gist or an untracked source directory.

After adapting changes, update the component wheel version, provenance.toml
and runtime hashes in modules/collection.json. Update the entry's exact pin
and _registry.json, bump the entry version, and update this table. Run the
collection source, wheel, resolver and upgrade tests before a manual release.
The initial migration commits are kept intact as provenance anchors; later
upstream merges and local patches extend that history.

modules/collection-history.json freezes the initial import/patch pairs and
Collection byte hashes. Keep that history record intact when updating current
runtime hashes in modules/collection.json. CI compares the initial patch Git
objects with the old Collection, so a reviewed later upstream update does not
have to pretend that its new runtime still equals the initial snapshot.
