# Manhwa Agent improvement plan

This is an implementation backlog, not a record of completed fixes. It turns the supplied **20 October 2026 audit** into sequenced work for a reliable local reading-list application.

**Source baseline:** `main` at [`0b8568d6fd5f7d374c4c30ba05d10eb8342fa5be`](https://github.com/b23bb1023/Manhwa-agent/commit/0b8568d6fd5f7d374c4c30ba05d10eb8342fa5be), rechecked on **27 October 2026**. The branch still matches the audit snapshot. All eight committed files were inspected for this documentation update; the tree contains no `AGENTS.md`, tests, or CI workflow. No containers, Flet session, external scraper target, or full n8n execution were run. The n8n runtime-contract findings below retain the supplied audit's verification; they were not independently rerun against an installed n8n release during this update.

## Order of work

| Priority | Work | Audit mapping | Completion evidence |
| --- | --- | --- | --- |
| P0, before network exposure | Restrict scraper callers and destinations | MAN-01 | Rejected requests never launch a browser |
| P1 | Repair checkout paths and pin a tested runtime | MAN-04, MAN-08 | Clean checkout builds and imports the workflow |
| P1 | Repair workflow execution and item preservation | MAN-02, MAN-03 | Two-item offline run processes each item once |
| P1 | Preserve state on scrape failures | MAN-05 | Failures retain previous availability |
| P1 | Give persistence a concurrency protocol | MAN-06 | Simultaneous progress and availability updates both survive |
| P2 | Bound thumbnail loading and surface errors | MAN-07 | Slow/oversized images do not block rendering |
| P2 | Establish schema, CI, and release documentation | Cross-cutting | Repeatable offline checks and honest support claims |

P0 denotes a prerequisite for exposing the service, not a claim that an Internet-facing deployment currently exists. The remaining tasks should be completed before advertising a working end-to-end installation.

## 1. Restrict scraper access and destinations

**Evidence:** [main.py](main.py) accepts a string `url` at `/scrape` and forwards it to `page.goto` without caller authentication or destination validation. [docker-compose.yml](docker-compose.yml) publishes `8000:8000`; [Dockerfile](Dockerfile) binds Uvicorn to `0.0.0.0`. Impact depends on who can reach that port and the container's network access.

**Implementation:**

- Remove the scraper host-port mapping if only n8n needs it. If host access is necessary, bind it to loopback. Review the n8n editor binding and session/transport configuration separately.
- Authenticate scraper calls and reject unauthorized requests before allocating Playwright resources. Keep credentials out of source control and URLs/logs.
- Allow only the required HTTPS hosts. Validate resolved addresses, every redirect, and browser subresource destinations; a check of the initial string alone is insufficient.
- Apply egress controls that deny private, loopback, link-local, and metadata destinations, including IPv6 equivalents. Design DNS handling to resist rebinding.
- Bound concurrent browsers, queue length, navigation and total request time, redirects, and resource consumption. Close browser resources reliably on failure and cancellation.

**Acceptance:** With mocked DNS/browser fixtures, reject unauthorized requests, forbidden schemes/hosts/addresses, forbidden redirects, and forbidden subresources before the corresponding request. Include one allowed synthetic host. Demonstrate bounded concurrency and cleanup after timeout. Do not probe real internal services to test the policy.

## 2. Make a clean checkout reproducible

**Evidence:** Compose requires `./scraper` and `./data`, while source and seed data are root-level files. [widget.py](widget.py) resolves `DATA_FILE` from the launch directory. Compose uses `n8nio/n8n:latest`; [requirements.txt](requirements.txt) pins only Playwright, while Flet is outside the manifest.

**Implementation:** Choose one committed layout: either move the scraper files into the expected directory or update the build context to the root. Provide a non-destructive data initializer that creates the data directory and copies a seed only when no user file exists. Resolve the dashboard path relative to its application/configured data root, not an arbitrary current directory. Keep mutable state outside the source files and exclude local state from commits.

Pin a tested n8n release or digest and Python/Flet dependencies, record supported Python and host environments, and keep Playwright's package/image/browser versions coherent. Re-export the workflow from that exact n8n release. Replace the `ExecuteCommand` file read with a supported data/file mechanism where practical; the supplied audit notes that n8n 2 disables that node by default. Do not broadly enable disabled nodes to make an untested export import.

**Acceptance:** From an empty checkout, validate Compose configuration, build the scraper, initialize the sample list, and import into the pinned n8n version. Confirm n8n and the widget resolve the same data store. A second initialization leaves existing data byte-for-byte intact. Commit exact commands and version results; a successful JSON parse is insufficient.

## 3. Repair the n8n execution contracts

**Evidence:** [n8n.json](n8n.json), nodes `Split Loop`, `Update Item`, `Keep Old Item`, `Collector`, `Finish Process`, and `Write to Disk`. The export connects Split Loop output 0 to the scraper and output 1 to finalization. Set v2 nodes contain `mode=raw`/`jsonOutput`; Code nodes call bare `getWorkflowStaticData`; the writer uses `fileSelector`. The supplied audit matched these to incompatible versioned node contracts.

**Implementation:** In the chosen n8n runtime, recreate and export the affected nodes using supported parameters. For Loop Over Items v3, connect loop output 1 to processing, return the processed item to the loop, and send done output 0 to finalization. Preserve complete original items, including `id`, `title`, `url`, and `last_read`. Prefer finalizing processed loop output over workflow-global aggregation. If static data remains necessary, use the supported `$getWorkflowStaticData` helper and isolate concurrent runs. Configure the file writer with the target parameter supported by the selected node version (`fileName` for the audited writeBinaryFile v1 contract).

**Acceptance:** Import the exported JSON into the pinned runtime and run two synthetic entries against a stub scraper. Assert exactly two scrape requests, both original IDs and progress values preserved, one finalization after processing, no helper `ReferenceError`, and exactly the intended persistence target. Exercise an empty list and repeat runs to detect stale aggregation. Capture the exported workflow and fixture output in the change.

## 4. Preserve availability when scraping fails

**Evidence:** [main.py](main.py) swallows navigation failures, returns success with `latest_chapter=0` when extraction finds nothing, and returns a normal error dictionary with zero on outer exceptions. In [n8n.json](n8n.json), `Keep Old Item` writes that number back, and the HTTP error output has no recovery connection. Downstream state loss is conditional on repairing the existing workflow blockers.

**Implementation:** Define separate results for successful extraction, a supported legitimate empty list, navigation failure, access challenge, and parse failure. Return typed results and appropriate HTTP errors. Update availability only after validated success. Preserve old values on failure, record `last_success_at` and visible error details, and route transport failures through a preservation path that continues the loop. Add browser cleanup in a guaranteed lifecycle block. Avoid logging credentials or complete sensitive URLs.

**Acceptance:** Offline fixtures cover timeout, browser launch error, challenge markup, selector mismatch, a valid empty source, successful chapters, and HTTP failure. Every failure retains the old item, progress, availability, and thumbnail as appropriate, records the error, and allows the next item to run. Successful extraction updates availability without reducing user progress.

## 5. Prevent competing writers from losing progress

**Evidence:** [widget.py](widget.py), `load_data`, `save_data`, and `mark_as_read`, reads and rewrites the full list. n8n reads an initial snapshot and later rewrites the same mounted JSON. There is no shared lock, revision, merge, or atomic write. The widget converts parse errors into an empty display.

**Implementation:** Prefer one persistence owner with an API, or a transactional SQLite store. Give user progress and scraper availability independent update operations keyed by stable ID; preserve both under concurrent updates. If JSON is retained, use cross-process locking, a revision-aware merge against current state, and temporary-file plus atomic replacement. Atomic replacement prevents partial reads but does not prevent stale-snapshot overwrites. Keep backups and report invalid data explicitly rather than treating corruption as an empty list.

**Acceptance:** Pause a scrape after it reads `last_read=5`, advance progress to 6 in the widget, then complete the scrape. Both `last_read=6` and new availability survive. Cover simultaneous refreshes, interrupted writes, malformed existing data, missing IDs, and duplicate IDs. Readers must see a complete previous or new state, never a silently emptied store.

## 6. Keep the dashboard responsive

**Evidence:** [widget.py](widget.py), `get_image_base64` and `create_card`, synchronously downloads each entire thumbnail without a timeout, MIME check, byte limit, or cache during UI refresh.

**Implementation:** Render placeholders immediately, fetch images in bounded background tasks with connect/read deadlines and maximum bytes, validate image type/decoding, and cache by URL with expiry and bounded size. Use Flet's supported UI-update mechanism for the pinned version. Apply destination restrictions to image URLs as appropriate and make errors visible without blocking list operations. Clarify the distinction between reloading the local view and requesting a remote refresh.

**Acceptance:** Fake stalled, oversized, invalid, and valid images. The list and controls remain responsive; each request has a deadline and byte budget; repeated reloads use the cache; failures retain placeholders. Verify both the Brave path and default-browser fallback on the documented platforms.

## 7. Define data contracts and a professional release gate

**Evidence:** The list has no enforced schema. Chapter parsing truncates fractions and excludes values at least `2000`. There is no test suite, CI, healthcheck, compatibility matrix, or separate license text.

**Implementation:**

- Validate unique stable IDs, required strings, permitted URLs, and nonnegative numeric fields at input boundaries. Decide explicitly whether fractional/high-number chapters are supported and test the representation.
- Add offline unit fixtures for parsing/results and an integration fixture for the pinned workflow and persistence layer. Run these with JSON/Python syntax checks and container smoke checks in CI without external scraping.
- Add a scraper readiness/health endpoint and test it before introducing Compose healthchecks that depend on it.
- Document exact supported versions, clean-checkout commands, configuration and secret handling, backup/restore, failure recovery, and observed limitations. Avoid uptime, access-bypass, data-integrity, or rate-limit guarantees that have not been demonstrated.
- Have the owner choose explicit reuse terms and commit an appropriate `LICENSE`; do not infer a standard open-source license from the existing personal/non-commercial statement.
- After checks exist, configure appropriate branch protections to require them. Repository administrative settings were not re-audited for this change.

**Release gate:** A fresh checkout builds and imports; a two-item offline workflow calls the scraper once per item and finalizes once; failures preserve the cache; simultaneous user progress survives; forbidden/unauthorized requests are denied before browser requests; the UI handles slow images without freezing. Record exact versions and results for each gate. Passing these checks supports the documented local use case, not an unqualified production-readiness claim.

## Suggested pull-request sequence

1. Reconcile layout and pin the runtime, with a non-destructive initializer and checkout smoke check.
2. Repair and re-export workflow nodes with a two-item offline fixture.
3. Add scraper access/resource controls and typed failure behavior.
4. Replace competing whole-file writes with a tested persistence protocol.
5. Add bounded image loading, visible errors, and the release documentation/CI gate.

Keep the scraper unexposed while steps 1–3 are in progress. Update this backlog with evidence and commit links as each task is completed; do not mark an audit item fixed solely because its documentation changed.
