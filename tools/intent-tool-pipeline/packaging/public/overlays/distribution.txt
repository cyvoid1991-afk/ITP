# Public framework distribution boundary

**The public seed publishes an explicit operational inventory, with curated
installation documents and exact disclosure for every intentionally absent local
Markdown target.** It omits unrelated Nexus_AI navigation and private workspace
evidence. It is not a complete source-repository archive.

The [public profile](../packaging/public/README.md),
[inventory](../packaging/public/include-list.json),
[overlays](../packaging/public/overlays.json) and
[exact policy](../packaging/public/document-policy.json) define the publication.
The active [legacy-format inventory](../packaging/itp/include-list.json) and
[policy](../packaging/itp/document-policy.json) receive equivalent public-profile
replacements so the shipped distribution checks run against the public boundary.
No original source inventory is edited by the builder.

Original component manifests, history, roles and operational procedures retain
their inventoried bytes. Public root documents, setup/distribution guidance and
VERSION are explicit overlays; two Nexus-layout distribution-test assertions are
adapted to require the public layout and exclude unrelated directories. Every
transformation and original/final hash is recorded in root PUBLIC_PROVENANCE.json.
The public version `0.3.0-rc.1` is separate from control default `1.2`.

The [shared validator](../packaging/itp/build.py) enforces member path safety and
inline Markdown closure. It scans rendered inline Markdown links, excluding
fenced code, and resolves relative paths against the inventory. It does not
validate heading anchors, reference-style/HTML links, remote URLs or arbitrary
plain-text paths. Every absent target needs an exact source-target pair, kind
and reason. Wildcards, duplicates, unknown sources, undeclared targets and stale
exceptions fail. Public replacements prune superseded exceptions explicitly;
there is no directory-wide historical evidence exemption.

The archive generates root SOURCE_MANIFEST.json, PUBLIC_PROVENANCE.json,
DOCUMENT_REFERENCES.json and DISTRIBUTION_NOTICE.md. The reference catalogue
separately counts source-only and setup-template-context occurrences and records
their referring-file digests. Source-only targets are physically absent, not
bundled evidence or current verification; their original source may itself be
unavailable. Source-only references need not exist to rebuild the extracted seed.

From a fresh extraction, verify integrity before creating caches or environments,
then follow the [public installation commands](../../../README.md). Build with:

```powershell
.\.venv\Scripts\python.exe tools/intent-tool-pipeline/packaging/public/build.py --output .tmp/itp-public.zip
```

Run that command from the repository root. An unchanged extraction reproduces
the ZIP and original provenance. Changed packaged source fails the snapshot
binding; prepare a newly reviewed authoritative-source snapshot for a new
candidate. Packaging does not migrate runs, authorize releases, verify live
model dispatch or select a license.
