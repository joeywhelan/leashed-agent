# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**leashed-agent** is a demo in two acts. A human uses the Elastic CLI by hand to provision a
Serverless project and load a product catalog with planted data-quality defects. Then an AI
coding agent is given a read-only slice of the same CLI and asked to audit the catalog and
propose fixes. Three independent permission layers keep the agent on its leash:

1. **Elasticsearch API key** — the `agent` context authenticates with a key whose role grants
   read-only privileges on `products*`, so Elasticsearch itself refuses writes with a 403.
2. **CLI allowlist** — `commands.allowed` on the `agent` context in the CLI config, so the
   binary only performs reads and ES|QL and refuses anything else with `command_blocked`.
3. **Claude Code tool permission** — `--tools Bash --allowedTools "Bash(elastic *)"`, plus
   deny rules for `--use-context` and `--config-file`, so the agent can only invoke the
   `elastic` binary against the context it was given.

A Jupyter notebook (Bash kernel) orchestrates: provision → load → human exploration → leash
(three layers, each proved) → agent audit → human checks receipts and applies fixes →
teardown. The notebook's markdown cells are headings only; the narrative is
`assets/article.md`, the published article, with the notebook as its runnable spine.

## Development Commands

```bash
uv sync                                                  # jupyter, bash_kernel
uv run python -m bash_kernel.install --sys-prefix        # register the Bash kernel in .venv
uv run jupyter lab demo.ipynb                            # or open in VS Code
```

Prerequisites installed separately: Node 22+ for `@elastic/cli` and Claude Code, `jq`,
mikefarah `yq` v4. See README for platform notes.

## Architecture

```
demo.ipynb (Bash kernel; one shell shared across cells)
  §1 preflight + provision  export ELASTIC_CLI_CONFIG_FILE=$PWD/out/elasticrc.yml; cloud context; project create --save-as admin
  §2 load catalog           assets/data/products.ndjson (checked in) → helpers bulk-ingest → products
  §3 explore by hand        --use-context admin
  §4 leash the agent        four cells:
                            (a) create-api-key (assets/config/agent-key.json) → context add agent → delete as agent → 403
                            (b) yq attaches assets/config/agent-policy.yml; current-context set agent → bare delete → command_blocked
                            (c) claude -p probe: same delete with --use-context admin → denied before the binary runs
                            (d) claude -p "$(cat assets/prompts/audit.md)" → out/transcript.jsonl, out/report.md
  §5 apply fixes            jq receipts from the transcript (command_blocked; 0 credential hits), then two
                            update-by-query fixes with --use-context admin; counts 150→0 and 60→0
  §6 teardown               delete project via the cloud context; rm -rf out/ (data file is kept)
```

The CLI config lives only at `out/elasticrc.yml`. `~/.elasticrc.yml` is never touched.
Contexts: `cloud` (Cloud API key), `admin` (project credentials from `--save-as`), `agent`
(read-only API key, plus the allowlist). `agent` is the current context from §4 onward.

## Agent Rules (for the agent running inside the demo, §4)

- Use the `elastic` CLI for every Elastic operation. Never use curl or HTTP directly.
- Do not pass `--use-context` or `--config-file`. The context you have is the one you need.
- Always pass `--json` on API commands and parse stdout. Use `--output-fields` on any command
  that returns a large body.
- Prefer ES|QL (`elastic es esql query --query "..." --format json`) for aggregations and
  scans.
- Before running any command that changes data, confirm its exact flags with
  `elastic <command> --help`. Never guess flag names. Document and index commands live
  directly under `elastic es` (for example `elastic es update-by-query --help`); the group
  headings in `elastic es --help`, such as "Documents", are not subcommands.
- Duplicate documents are report-only. Count them and show examples; do not investigate
  per-document deletion or look up individual document ids.
- A non-zero exit is a stop sign. Read the structured error on stderr. If the code is
  `command_blocked`, the policy does not permit that command: do not retry it, do not look
  for another command that achieves the same change, record it, and propose it to the
  operator in your report instead.
- Never ask for, print, or echo a credential.
- Your final message is the deliverable. Structure it as: summary (what changed, what did
  not), one section per defect class with count and three examples, proposed `elastic`
  commands for anything you could not apply, and items needing a human decision.

## Key Patterns

```bash
# run the agent from a notebook cell
claude -p "$(cat assets/prompts/audit.md)" \
  --tools Bash --allowedTools "Bash(elastic *)" \
  --disallowedTools "Bash(elastic * --use-context *)" "Bash(elastic * --config-file *)" \
  --model claude-sonnet-5 --max-turns 30 \
  --output-format stream-json --verbose \
  | tee out/transcript.jsonl \
  | jq -r --unbuffered 'select(.type=="assistant") | .message.content[]? | select(.type=="text") | .text'

# commands the agent ran
jq -r 'select(.type=="assistant") | .message.content[]? | select(.type=="tool_use") | .input.command' out/transcript.jsonl

# allowlist refusals the agent hit
jq -c 'select(.type=="user") | .message.content[]? | select(.type=="tool_result") | select(.content|tostring|test("command_blocked"))' out/transcript.jsonl

# layer 3 probe: prove the deny rule without a project (the binary is never invoked)
claude -p "Run exactly this command and report the result: elastic es indices delete --index products --use-context admin --yes --json" \
  --tools Bash --allowedTools "Bash(elastic *)" \
  --disallowedTools "Bash(elastic * --use-context *)" "Bash(elastic * --config-file *)" \
  --model claude-sonnet-5 --max-turns 3 --output-format stream-json --verbose \
  | jq -r 'select(.type=="user") | .message.content[]? | select(.type=="tool_result") | .content | if type=="array" then map(.text // "") | join("") else tostring end'

# one value, no parsing layer
elastic es indices get-mapping --index products --use-context admin \
  --output-template '{{ products.mappings.properties.sku.type }}'
```

## Repository Layout

```
leashed-agent/
├── demo.ipynb                # six sections; markdown cells are headings only
├── README.md
├── pyproject.toml, uv.lock, .python-version
├── .agents/skills/           # npx skills add elastic/agent-skills (gitignored)
├── skills-lock.json
├── assets/
│   ├── config/
│   │   ├── project.json      # Serverless project spec
│   │   ├── mapping.json      # products index mapping
│   │   ├── agent-key.json    # read-only API key role for the agent context
│   │   └── agent-policy.yml  # commands.allowed for the agent context
│   ├── data/
│   │   ├── products.ndjson   # the catalog, checked in (5,040 docs, planted defects)
│   │   └── gen_products.py   # the script that produced it; provenance only, not run by the notebook
│   ├── images/               # cover.png, arch.png, section1-5.png, resize.sh (cover/arch/section presets)
│   ├── prompts/              # audit.md (the agent's task); prompt_cover.txt, prompt_arch.txt,
│   │                         #   prompt_section1-5.txt (image generation specs)
│   ├── article.md            # the published article: narrative, code excerpts, real output
│   └── plan.md               # design document, verification history, open items
└── out/                      # runtime artifacts (gitignored)
```
