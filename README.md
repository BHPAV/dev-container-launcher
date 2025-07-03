# Dev-Container Launcher

A Docker-based development environment manager with seamless Cursor IDE integration.  Version 2 introduces a collaborative *agent* pipeline for rapid, automated feature delivery.

---

## ✨ Key Features

• One-click **Cursor** access to containerised workspaces
• **Textual** TUI & CLI for container lifecycle
• Pre-built images: **Python 3.12**, **Node 20**, **Go 1.22** (add your own!)
• Persistent volumes – your code survives rebuilds
• SSH-based access with automatic `~/.ssh/config` entries
• Agent framework (Planner → Coder → Tester → …​) for hands-off feature delivery

---

## 🚀 Quick Start

```bash
# Clone & install deps
cd dev-container-launcher
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Build the base image
python scripts/devctl.py build

# Launch the TUI
python app.py
```

1. Press `c` to create a container (choose `python-3.12`, `node-20`, or `go-1.22`).
2. Highlight the new entry and hit **Enter** – Cursor opens automatically!

Need an end-to-end setup? Use the helper script:

```bash
bash scripts/bootstrap.sh
```

---

## 🛠  CLI Cheat-Sheet

```bash
# Container lifecycle
python scripts/devctl.py new mybox          # create
python scripts/devctl.py ls                 # list
python scripts/devctl.py code mybox         # open in Cursor
python scripts/devctl.py stop|start mybox   # stop / start
python scripts/devctl.py rm mybox --force   # delete

# Image tasks
python scripts/devctl.py build                             # base image
make build-all                                             # all language images
```

---

## 🐳 Building Language Images

```bash
for f in docker/images/*.Dockerfile; do
  tag=$(basename "$f" .Dockerfile)
  docker build -f "$f" -t "$tag" .
done
```

---

## 🤖 Agent-Based Development (v2)

The V2 architecture introduces specialised agents that collaborate to ship features:

| Agent | Role |
|-------|------|
| **Planner** | Breaks epics into tasks & stores roadmap in Neo4j |
| **Coder**   | Generates / refactors code, writes tests |
| **Tester**  | Executes unit / integration / perf tests |
| _(Planned)_ **Reviewer** | Static analysis, security scans |
| _(Planned)_ **Doc-Gen**  | Updates docs & API specs |
| _(Planned)_ **Integrator** | Manages PRs, deploys, updates Neo4j |

Agents communicate via the local repo and the Neo4j graph, enabling an automated, measurable delivery flow.

### Running Example Tasks

```bash
python -m agents.roadmap show                 # view roadmap
python -m agents.coder execute-task T-101     # run a Coder task
python -m agents.tester execute-task T-103    # run tests
```

---

## 📚 Project Layout

```
dev-container-launcher/
├── app.py                # Textual UI
├── scripts/
│   ├── devctl.py         # Core Docker logic (CLI-friendly)
│   ├── bootstrap.sh      # One-shot environment setup
│   └── initialize_v2.py  # Demo data & hooks
├── docker/
│   ├── Dockerfile        # Base image
│   └── images/           # Language images
├── agents/               # Autonomous agents
├── docs/                 # Extended docs & specs
└── tests/                # Unit / integration / perf
```

---

## 🏗  Contributing & Roadmap

Milestones live in `docs/milestones.md`.  Pick a task, create a branch, ensure **tests + linters pass**, then open a PR.

### Success Metrics

• 95 % of container launches < 5 s  • 80 %+ test coverage  • 0 critical CVEs

---

## 📝 License

MIT
