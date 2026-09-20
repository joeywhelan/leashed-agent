# Demo Plan: leashed-agent — Least Privilege for AI Agents, with the Elastic CLI

A Jupyter notebook that first shows a human using the Elastic CLI by hand, then hands a
read-only slice of the same CLI to an AI coding agent for a meaningful task, and shows the
three permission layers that give the agent exactly the access its task needs.

Article title: **Least Privilege for AI Agents, with the Elastic CLI**
One-line summary: *Three permission layers give an AI agent exactly the Elasticsearch access
its task needs, and the Elastic CLI is where you set them.*

## 1. Scenario

A product catalog index, `products`, in a Serverless project created for the demo. The data
has planted quality defects. The human loads and explores it with the CLI. The agent is then
asked to audit the catalog and fix what can be fixed mechanically. Its context permits reads
only, so the first write is refused; it records the refusal and turns every fix into a
proposed `elastic` command, verified against `--help`. The human reviews the report, checks
two receipts in the transcript, and applies the two mechanical fixes with the unrestricted
context. Duplicates and price defects are deliberately left for a data owner; the article
says so.

Planted defects (deterministic; `assets/data/products.ndjson` is checked in, produced once by
`assets/data/gen_products.py`, which the notebook does not run):

| Defect | Count | Outcome in the demo |
|---|---|---|
| Duplicate SKUs (same record emitted twice) | 40 | Reported; left for a human decision per pair |
| Missing `price` | 30 | Reported; no source of truth in the index |
| Negative `price` | 12 | Reported; intent cannot be inferred |
| Inconsistent `category` casing (`Audio`, `AUDIO`, `audio`) | 150 | Fixed by the human: `update-by-query` lowercasing the field |
| Leading/trailing whitespace in `name` | 60 | Fixed by the human: `update-by-query` trimming names matched by a regexp |

## 2. Three permission layers

Built from the inside out in Section 4, each proved with the same `indices delete`:

1. **Elasticsearch API key.** `assets/config/agent-key.json` grants `read`,
   `view_index_metadata`, `monitor` on `products*` and cluster `monitor` (needed for
   `elastic status`). Minted via `--use-context admin`, written into the `agent` context with
   `context add`. Proof: a delete as `agent` returns 403 from Elasticsearch. Verified
   2026-09-16 and again in the 2026-09-18 full run.
2. **CLI command allowlist.** `assets/config/agent-policy.yml` is attached to the `agent`
   context with `yq`; `agent` becomes the current context via `config current-context set`.
   Any command outside the list fails with `{"error":{"code":"command_blocked",...}}` on
   stderr and exit code 1 before a request is sent. Verified: paths are the full form
   (`stack.es.indices.delete`), a context's `allowed` list replaces the root list,
   `--use-context` selects the policy, `--help` is not subject to the policy, `--dry-run` is.
3. **Claude Code tool permission.** `--tools Bash --allowedTools "Bash(elastic *)"` plus
   deny rules `Bash(elastic * --use-context *)` and `Bash(elastic * --config-file *)`.
   Proved in the notebook by a `claude -p` probe asked to run the same delete with
   `--use-context admin`: the tool call is denied before the binary is invoked. Verified
   2026-09-19 (2 turns, ~12 s, ~$0.22).

Different parties enforce each layer: Elasticsearch, the `elastic` binary, the agent
runtime. Layer 1 never shows in an agent transcript because layer 2 refuses first; it is
proved directly in Section 4 and exists for the case where the CLI policy is wrong.

## 3. Design rules (learned from the first iteration)

- One Serverless project, created in Section 1, deleted in the last section.
- One config file at `out/elasticrc.yml`, selected with `ELASTIC_CLI_CONFIG_FILE`. The
  user's `~/.elasticrc.yml` is never read or written. No backup, no restore.
- Three contexts, written once: `cloud`, `admin` from `--save-as`, and `agent` with a
  read-only API key and the allowlist. `agent` is the current context from Section 4, so
  every bare `elastic` call is leashed. The human adds `--use-context admin` to act.
- The agent writes no files. Its final message is the report; the notebook saves it.
- Every cell is shell; the notebook runs no Python. Labels (`echo "--- ..."`) precede each
  display block, separated by blank lines.
- Notebook markdown cells are section headings only. The narrative lives in
  `assets/article.md`, which is the published piece; the notebook is its runnable spine.
- `yq` runs only on files inside the project, never on dotfiles (snap confinement). It has
  one job: attaching `commands` to the `agent` context, which no CLI command can do.
- Nothing in a cell uses `exit`; the Bash kernel shares one shell across cells.
- The agent model is pinned (`--model claude-sonnet-5`) and bounded (`--max-turns 30`) so
  runs are reproducible; the streaming `jq` is `--unbuffered` so prose appears as it arrives.

## 4. Sections

1. **Preflight and provision.** Tool versions, skills count, load `.env`, create `out/`,
   export `ELASTIC_CLI_CONFIG_FILE=$PWD/out/elasticrc.yml`; `cloud` context from
   `EC_API_KEY` (this first write creates the config file); `status` on `cloud`; create the
   project with `--wait --save-as admin --yes`; save id and endpoints to `out/project.json`;
   context list; `status` on `admin`. About 75 s, dominated by `--wait`.
2. **Load the catalog.** Line count and two documents from `assets/data/products.ndjson`;
   delete any leftover `products` (silenced); create from `assets/config/mapping.json`;
   `helpers bulk-ingest`; refresh (silenced); count.
3. **Explore by hand.** All `--use-context admin`: `status`; ES|QL summary (min price is
   negative); `search` with `--output-fields` (top three audio products); `search` with
   `--output-template` ("30 products have no price"); ES|QL count by category (eighteen
   rows where there should be six).
4. **Leash the agent.** Four cells. (a) Mint the read-only key, create the `agent` context,
   `status` as `agent`, prove the 403. (b) Attach the allowlist with `yq`, set `agent`
   current, print the list, prove `command_blocked`, show a bare read still works. (c) Probe:
   `claude -p` asked to run the same delete with `--use-context admin`; print the denial.
   (d) `claude -p` with `assets/prompts/audit.md`: the agent audits, verifies flags with
   `--help`, attempts `update-by-query`, hits `command_blocked`, and re-plans into proposals.
   Stream-json to `out/transcript.jsonl`; prose to the cell; final result to
   `out/report.md`; turn count, duration, and cost printed. Typical run: 23–26 turns,
   100–165 s, $0.40–0.65.
5. **Apply the fixes.** Two receipts from the transcript first: the `command_blocked` tool
   result, and a grep proving none of the three credentials appears. Then the report's
   headings; before-counts for the two mechanical defects; the two `update-by-query` fixes as
   `admin`; after-counts at zero; the category breakdown back to six rows.
6. **Teardown.** Delete the project through the `cloud` context; list projects; `rm -rf out/`;
   unset the config variable. The checked-in data file is kept.

## 5. Files

```
demo.ipynb                          # the runnable spine; headings only in markdown cells
README.md                           # summary, features, prerequisites, platform and kernel notes
CLAUDE.md                           # repo guidance + the demo agent's rules (read by claude -p)
assets/article.md                   # the published article; narrative, excerpts, real output
assets/plan.md                      # this file
assets/config/project.json          # Serverless project spec (name, region_id)
assets/config/mapping.json          # products index mapping
assets/config/agent-key.json        # read-only API key role for the agent context
assets/config/agent-policy.yml      # commands.allowed for the agent context
assets/data/products.ndjson         # the catalog, checked in (5,040 docs, planted defects)
assets/data/gen_products.py         # produced it; provenance only, not run by the notebook
assets/prompts/audit.md             # the agent's task
assets/prompts/prompt_cover.txt     # LinkedIn cover spec (aperture metaphor)
assets/prompts/prompt_arch.txt      # README architecture diagram spec
assets/prompts/prompt_section1-5.txt# one 900×300 section image spec per article section
assets/images/cover.png             # 1672×941, accepted as-is on LinkedIn
assets/images/arch.png              # 1600×1000, 256-colour PNG under 1 MB
assets/images/section1-5.png        # 900×300, proofread against their prompts
assets/images/resize.sh             # presets: cover 1920×1080, arch 1600×1000, section 900×300
out/                                # runtime artifacts (gitignored): elasticrc.yml, project.json,
                                    #   transcript.jsonl, report.md
```

## 6. Verification history

- 2026-09-16: policy engine semantics, deny-rule wildcards, env-var inheritance, 403 with a
  read-only key, secret-tool probe bug in `@elastic/cli` 0.5.0 (Linux stores fall back to
  inline; issue write-up drafted).
- 2026-09-17: Sections 1–3 end to end; agent run with the "fix what you can" task hit the
  wall as intended; second run 24 turns, 127 s.
- 2026-09-18: full notebook run by the author; agent 23 turns, 163 s, $0.63; fixes applied,
  counts to zero; project deleted.
- 2026-09-19: layer 3 probe cell added and run (denied before the binary); section images
  generated, resized, proofread; section 4 image regenerated once for a misspelling.

## 7. Open items

- [ ] `Bash(elastic *)` permits pipes: the agent appends `2>&1 | head -N`, which runs.
      Harmless here; decide whether the article should mention it.
- [ ] Whether the agent should get `.agents/skills` (ES|QL skill). Not used so far; the
      agent's ES|QL has been correct without it.
- [ ] Duplicates are never fixed. Deliberate, and stated in the article. Revisit only if the
      demo should show a third fix (reindex by SKU as `_id`).
- [x] `--help` works under the allowlist, `--dry-run` does not; agent rules use `--help`.
- [x] Default model in `claude -p` was `claude-sonnet-4-6`; now pinned to `claude-sonnet-5`.
- [x] Image generators misspell "Elasticsearch"; the section 4 label is "Elastic API key".
