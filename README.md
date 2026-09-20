# Least Privilege for AI Agents, with the Elastic CLI

## Contents
1. [Summary](#summary)
2. [Presentation](#presentation)
3. [Architecture](#architecture)
4. [Features](#features)
5. [Prerequisites](#prerequisites)
6. [Installation](#installation)
7. [Usage](#usage)
8. [Bash Kernel Notes](#bash-kernel)

## Summary <a name="summary"></a>
This demo explores usage of the Elastic CLI both from human and agent standpoints.  The human is given admin-level access to commands while the agent is restricted to essentially read-only access.


## Presentation <a name="presentation"></a>
[Slide deck](https://joeywhelan.github.io/leashed-agent/)

## Architecture <a name="architecture"></a>
![architecture](assets/images/arch.png)

## Features <a name="features"></a>
- Jupyter notebook (Bash kernel) with linear, top-to-bottom execution; every cell is a real `elastic`, `claude`, or `jq` invocation
- Human-use showcase: `status`, ES|QL, `search` with `--output-fields` and `--output-template`
- Three independent permission layers for the agent: a read-only Elasticsearch API key, CLI `commands.allowed` per context, and Claude Code `--allowedTools` + deny rules
- Agent output is a report with proposed `elastic` commands; the human decides and executes
- Full teardown removes the project and all runtime artifacts

## Prerequisites <a name="prerequisites"></a>
- [`uv`](https://docs.astral.sh/uv/) — Python toolchain (manages Python 3.12)
- [Node.js 22+](https://nodejs.org/) — required by the Elastic CLI and Claude Code
- [`@elastic/cli`](https://www.elastic.co/guide/en/elasticsearch/client/elastic-cli/current/index.html) — `npm install -g @elastic/cli` (technical preview; pin the version used)
- [`claude`](https://claude.ai/claude-code) — `npm install -g @anthropic-ai/claude-code`
- [`jq`](https://jqlang.org/) — install via your OS package manager
- [`yq`](https://github.com/mikefarah/yq) v4+ — **must be the Go implementation by mikefarah**, not the Python `yq` that Debian/Ubuntu `apt` installs (that one is a jq wrapper with different syntax and reports version `0.0.0`). Install with one of:
  - Ubuntu/Debian: `sudo snap install yq` (note: snap confinement hides dotfiles in your home directory from `yq`, so the notebook edits `~/.elasticrc.yml` through a copy in `out/`; the direct-download binary below has no such limit)
  - macOS: `brew install yq`
  - Any Linux: `sudo wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 && sudo chmod +x /usr/local/bin/yq`

  Verify with `yq --version`; it should print `yq (https://github.com/mikefarah/yq/) version v4.x.x`.
- Elastic Cloud API key with Serverless project create/delete permissions

## Installation <a name="installation"></a>
- Install Python dependencies: `uv sync`
- Register the Bash kernel inside the project venv: `uv run python -m bash_kernel.install --sys-prefix` (see [Bash Kernel Notes](#bash-kernel))
- Install Elastic Agent Skills: `npx skills add elastic/agent-skills` (installs to `.agents/skills/`; `skills-lock.json` is committed)
- Copy `.env.sample` to `.env` and set your Elastic Cloud API key:
  ```
  EC_API_KEY=<your-key>
  ```

## Usage <a name="usage"></a>
- Launch the notebook: `uv run jupyter lab demo.ipynb` (or open `demo.ipynb` in VS Code)
- Make sure the **Bash** kernel is selected, not a Python kernel (see [Bash Kernel Notes](#bash-kernel))
- Run the cells top to bottom; each section depends on the one before it
- Section 5 applies the agent's proposed fixes; read `out/report.md` first and decide which to run

## Bash Kernel Notes <a name="bash-kernel"></a>
- Register the kernel in the venv: `uv run python -m bash_kernel.install --sys-prefix`
- Select the **Bash** kernel in the notebook UI. In VS Code: kernel picker → `Select Another Kernel…` → `Jupyter Kernel…` → `Bash` (reload the window if it is not listed)
- VS Code only: if cells run with no output and no error, or a cell's language shows as `bash`, pin every code cell to `shellscript` and reopen the notebook:
  ```
  jq --indent 1 '.cells |= map(if .cell_type == "code" then .metadata.vscode.languageId = "shellscript" else . end)' demo.ipynb > demo.tmp && mv demo.tmp demo.ipynb
  ```
  New cells added in VS Code inherit `bash` from the kernel, so re-run this after adding cells.
- Do not use `exit` in a cell; it kills the shared shell for all later cells
