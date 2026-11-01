# Public repository seed profile

**This profile builds the ITP public candidate without editing the Nexus_AI source tree.**
It publishes the current explicit operational inventory, curated installation
documents and rebuilding assets. It excludes unrelated component navigation,
private products, runs, checkpoints, logs, archives and local Git metadata.

From the source repository root:

```powershell
.\.venv\Scripts\python.exe tools/intent-tool-pipeline/packaging/public/build.py --output tools/intent-tool-pipeline/dist/intent-tool-pipeline-0.3.0-rc.1.zip
.\.venv\Scripts\python.exe -m pytest tools/intent-tool-pipeline/tests/test_public_seed.py -q --basetemp=.tmp/public
```

The [inventory](include-list.json) is explicit. [Overlays](overlays.json) map
public destinations to portable text assets, while the [document policy](document-policy.json)
lists every retained source-only/template-context Markdown target separately.
The shared distribution builder supplies path safety and exact document closure;
no blanket historical exception is added. Both undeclared and stale exceptions
fail. Original component manifests and histories remain unchanged.

Public packaging adapts exactly two Nexus-layout assertions in
`tests/test_distribution.py`: the public suite asserts that research,
experiments, discussion and develop directories are absent and the public
builder is present. All runtime assertions remain unchanged. Both inventories
and the active document policy receive public-profile replacements. Runtime,
role and procedure files otherwise retain their input bytes.

The public component VERSION is `0.3.0-rc.1`; the source component VERSION is
recorded separately in generated `PUBLIC_PROVENANCE.json`. This is a public
candidate identity, independent of default control `1.2`, and not a claim that
the Nexus_AI working tree is a clean upstream release. The root generated
manifest hashes this assembly; the retained component manifest still describes
the original 0.2.0 import.

Generated provenance records every shipped input path/hash, replaced original
path/hash, final hash and transformation. Source context records Git HEAD and
dirty status without local absolute paths, omitted file names or usernames.
Rebuilding an unchanged extraction retains the original provenance and yields
the identical ZIP. A changed extraction fails provenance validation rather than
silently inventing an updated source history; prepare a newly reviewed snapshot
from the authoritative source to publish a revision.

Integrity, source provenance, deterministic packaging, tests and actual live
agent discovery are distinct claims. The profile does not perform live model
dispatch, grant redistribution rights, migrate existing runs or publish a remote
repository. See the packaged root README and SOURCE_IDENTITY for installation
and limitations.
