# CLI Agent Orchestrator

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/awslabs/cli-agent-orchestrator)

CLI Agent Orchestrator(CAO, pronounced as "kay-oh"), is a lightweight orchestration system for managing multiple AI agent sessions in tmux terminals. Enables Multi-agent collaboration via MCP server.

## Hierarchical Multi-Agent System

CLI Agent Orchestrator (CAO) implements a hierarchical multi-agent system that enables complex problem-solving through specialized division of CLI Developer Agents.

![CAO Architecture](./docs/assets/cao_architecture.png)

### Key Features

* **Hierarchical orchestration** – CAO's supervisor agent coordinates workflow management and task delegation to specialized worker agents. The supervisor maintains overall project context while agents focus on their domains of expertise.
* **Session-based isolation** – Each agent operates in isolated tmux sessions, ensuring proper context separation while enabling seamless communication through Model Context Protocol (MCP) servers. This provides both coordination and parallel processing capabilities.
* **Intelligent task delegation** – CAO automatically routes tasks to appropriate specialists based on project requirements, expertise matching, and workflow dependencies. The system adapts between individual agent work and coordinated team efforts through three orchestration patterns:
    - **Handoff** - Synchronous task transfer with wait-for-completion
    - **Assign** - Asynchronous task spawning for parallel execution  
    - **Send Message** - Direct communication with existing agents
* **Flexible workflow patterns** – CAO supports both sequential coordination for dependent tasks and parallel processing for independent work streams. This allows optimization of both development speed and quality assurance processes.
* **Flow - Scheduled runs** – Automated execution of workflows at specified intervals using cron-like scheduling, enabling routine tasks and monitoring workflows to run unattended.
* **Context preservation** – The supervisor agent provides only necessary context to each worker agent, avoiding context pollution while maintaining workflow coherence.
* **Direct worker interaction and steering** – Users can interact directly with worker agents to provide additional steering, distinguishing from sub-agents features by allowing real-time guidance and course correction.
* **Advanced CLI integration** – CAO agents have full access to advanced features of the developer CLI, such as the [sub-agents](https://docs.claude.com/en/docs/claude-code/sub-agents) feature of Claude Code, [Custom Agent](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line-custom-agents.html) of Amazon Q Developer for CLI, [Codex CLI](https://github.com/openai/codex) from OpenAI, and [Gemini CLI](https://geminicli.com/docs/) from Google.

For detailed project structure and architecture, see [CODEBASE.md](CODEBASE.md).

## Installation

1. Install tmux (version 3.3 or higher required)

```bash
bash <(curl -s https://raw.githubusercontent.com/awslabs/cli-agent-orchestrator/refs/heads/main/tmux-install.sh)
```

2. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Install CLI Agent Orchestrator:

```bash
uv tool install git+https://github.com/awslabs/cli-agent-orchestrator.git@main --upgrade
```

## Quick Start

### Installing Agents

CAO supports installing agents from multiple sources:

**1. Install built-in agents (bundled with CAO):**

```bash
# Core agents
cao install code_supervisor
cao install developer
cao install reviewer

# Specialized developers
cao install frontend_developer   # Web UI, React, Vue, CSS
cao install backend_developer    # APIs, databases, cloud
cao install mobile_developer     # Flutter, Swift, Kotlin
```

**2. Install from a local file:**

```bash
cao install ./my-custom-agent.md
cao install /absolute/path/to/agent.md
```

**3. Install from a URL:**

```bash
cao install https://example.com/agents/custom-agent.md
```

When installing from a file or URL, the agent is saved to your local agent store (`~/.aws/cli-agent-orchestrator/agent-store/`) and can be referenced by name in future installations.

**Provider Selection:**

CAO supports multiple CLI providers. By default, agents are installed for the `q_cli` provider (Amazon Q CLI). You can specify a different provider:

```bash
# Install for Amazon Q CLI (default)
cao install developer --provider q_cli

# Install for Kiro CLI
cao install developer --provider kiro_cli
```

**Supported Providers:**

| Provider | Command | Description |
|----------|---------|-------------|
| `q_cli` | Amazon Q CLI | AWS's AI coding assistant (default) |
| `kiro_cli` | Kiro CLI | Kiro AI assistant |
| `claude_code` | Claude Code | Anthropic's Claude Code CLI |
| `codex_cli` | Codex CLI | OpenAI's Codex CLI |
| `gemini_cli` | Gemini CLI | Google's Gemini CLI |

Note: The `claude_code`, `codex_cli`, and `gemini_cli` providers do not require agent installation - they use their native configuration systems (CLAUDE.md, AGENTS.md, etc.).

**Built-in Agent Profiles:**

| Agent | Specialization |
|-------|---------------|
| `code_supervisor` | Orchestrates tasks and delegates to specialists |
| `developer` | General-purpose development |
| `reviewer` | Code review and quality assurance |
| `frontend_developer` | Web UI, React, Vue, Angular, CSS, accessibility |
| `backend_developer` | APIs, databases, cloud, security, microservices |
| `mobile_developer` | Flutter, Swift, Kotlin, React Native |

**Check Available Providers:**

To see which CLI tools are installed on your machine:

```bash
cao providers

# With verbose output (shows installation paths)
cao providers --verbose
```

For details on creating custom agent profiles, see [docs/agent-profile.md](docs/agent-profile.md).

### Launching Agents

Start the cao server:

```bash
cao-server
```

In another terminal, launch a terminal with an agent profile:

```bash
cao launch --agents code_supervisor

# Or specify a provider
cao launch --agents code_supervisor --provider kiro_cli

# Launch with Codex CLI
cao launch --agents code_supervisor --provider codex_cli

# Launch with Gemini CLI
cao launch --agents code_supervisor --provider gemini_cli
```

**Working Directory (VS Code Workspaces):**

Agents launch in a working directory to access project files. Use `--cwd` to specify:

```bash
# Launch in current directory (default)
cao launch --agents developer

# Launch in a specific project folder
cao launch --agents developer --cwd /path/to/my-project

# Launch in current VS Code workspace (from integrated terminal)
cao launch --agents developer --cwd .

# Short form
cao launch --agents developer -C ~/projects/my-app
```

**Note:** CAO validates that the required CLI tool is installed before launching. If the CLI is not found, you'll receive helpful installation instructions.

### Configuration

CAO stores configuration in `~/.aws/cli-agent-orchestrator/config.json`.

**Set Default Provider:**

```bash
# View current configuration
cao config show

# Set default provider for all agents
cao config set-provider claude_code

# Set provider for specific agent (overrides default)
cao config set-provider claude_code --agent frontend_developer
cao config set-provider codex_cli --agent backend_developer
cao config set-provider gemini_cli --agent mobile_developer

# Reset agent to use default provider
cao config reset-agent frontend_developer
```

### Agent Teams (cao.config.json)

Define your project's agent team in a `cao.config.json` file:

```bash
# Create cao.config.json in your project
cao team init

# View current config
cao team show

# Start all agents defined in config
cao team start
```

**Example cao.config.json:**

```json
{
  "name": "my-project",
  "agents": [
    { "agent": "code_supervisor", "provider": "claude_code" },
    { "agent": "frontend_developer", "provider": "claude_code" },
    { "agent": "backend_developer", "provider": "codex_cli" },
    { "agent": "reviewer", "provider": "claude_code" }
  ]
}
```

**Simple format (uses default provider):**

```json
{
  "name": "my-project",
  "default_provider": "claude_code",
  "agents": ["code_supervisor", "developer", "reviewer"]
}
```

**Start team from any directory:**

```bash
# Start team in current directory (reads cao.config.json)
cao team start

# Start team in specific project
cao team start --cwd /path/to/project

# Start in headless mode (detached)
cao team start --headless
```

Shutdown sessions:

```bash
# Shutdown all cao sessions
cao shutdown --all

# Shutdown specific session
cao shutdown --session cao-my-session
```

### Working with tmux Sessions

All agent sessions run in tmux. Useful commands:

```bash
# List all sessions
tmux list-sessions

# Attach to a session
tmux attach -t <session-name>

# Detach from session (inside tmux)
Ctrl+b, then d

# Switch between windows (inside tmux)
Ctrl+b, then n          # Next window
Ctrl+b, then p          # Previous window
Ctrl+b, then <number>   # Go to window number (0-9)
Ctrl+b, then w          # List all windows (interactive selector)

# Delete a session
cao shutdown --session <session-name>
```

**List all windows (Ctrl+b, w):**

![Tmux Window Selector](./docs/assets/tmux_all_windows.png)

## MCP Server Tools and Orchestration Modes

CAO provides a local HTTP server that processes orchestration requests. CLI agents can interact with this server through MCP tools to coordinate multi-agent workflows.

### How It Works

Each agent terminal is assigned a unique `CAO_TERMINAL_ID` environment variable. The server uses this ID to:

- Route messages between agents
- Track terminal status (IDLE, BUSY, COMPLETED, ERROR)
- Manage terminal-to-terminal communication via inbox
- Coordinate orchestration operations

When an agent calls an MCP tool, the server identifies the caller by their `CAO_TERMINAL_ID` and orchestrates accordingly.

### Orchestration Modes

CAO supports three orchestration patterns:

**1. Handoff** - Transfer control to another agent and wait for completion

- Creates a new terminal with the specified agent profile
- Sends the task message and waits for the agent to finish
- Returns the agent's output to the caller
- Automatically exits the agent after completion
- Use when you need **synchronous** task execution with results

Example: Sequential code review workflow

![Handoff Workflow](./docs/assets/handoff-workflow.png)

**2. Assign** - Spawn an agent to work independently (async)

- Creates a new terminal with the specified agent profile
- Sends the task message with callback instructions
- Returns immediately with the terminal ID
- Agent continues working in the background
- Assigned agent sends results back to supervisor via `send_message` when complete
- Messages are queued for delivery if the supervisor is busy (common in parallel workflows)
- Use for **asynchronous** task execution or fire-and-forget operations

Example: A supervisor assigns parallel data analysis tasks to multiple analysts while using handoff to sequentially generate a report template, then combines all results.

See [examples/assign](examples/assign) for the complete working example.

![Parallel Data Analysis](./docs/assets/parallel-data-analysis.png)

**3. Send Message** - Communicate with an existing agent

- Sends a message to a specific terminal's inbox
- Messages are queued and delivered when the terminal is idle
- Enables ongoing collaboration between agents
- Common for **swarm** operations where multiple agents coordinate dynamically
- Use for iterative feedback or multi-turn conversations

Example: Multi-role feature development

![Multi-role Feature Development](./docs/assets/multi-role-feature-development.png)

### Custom Orchestration

The `cao-server` runs on `http://localhost:9889` by default and exposes REST APIs for session management, terminal control, and messaging. The CLI commands (`cao launch`, `cao shutdown`) and MCP server tools (`handoff`, `assign`, `send_message`) are just examples of how these APIs can be packaged together.

You can combine the three orchestration modes above into custom workflows, or create entirely new orchestration patterns using the underlying APIs to fit your specific needs.

For complete API documentation, see [docs/api.md](docs/api.md).

## Flows - Scheduled Agent Sessions

Flows allow you to schedule agent sessions to run automatically based on cron expressions.

### Prerequisites

Install the agent profile you want to use:

```bash
cao install developer
```

### Quick Start

The example flow asks a simple world trivia question every morning at 7:30 AM.

```bash
# 1. Start the cao server
cao-server

# 2. In another terminal, add a flow
cao flow add examples/flow/morning-trivia.md

# 3. List flows to see schedule and status
cao flow list

# 4. Manually run a flow (optional - for testing)
cao flow run morning-trivia

# 5. View flow execution (after it runs)
tmux list-sessions
tmux attach -t <session-name>

# 6. Cleanup session when done
cao shutdown --session <session-name>
```

**IMPORTANT:** The `cao-server` must be running for flows to execute on schedule.

### Example 1: Simple Scheduled Task

A flow that runs at regular intervals with a static prompt (no script needed):

**File: `daily-standup.md`**

```yaml
---
name: daily-standup
schedule: "0 9 * * 1-5"  # 9am weekdays
agent_profile: developer
provider: q_cli  # Optional, defaults to q_cli
---

Review yesterday's commits and create a standup summary.
```

### Example 2: Conditional Execution with Health Check

A flow that monitors a service and only executes when there's an issue:

**File: `monitor-service.md`**

```yaml
---
name: monitor-service
schedule: "*/5 * * * *"  # Every 5 minutes
agent_profile: developer
script: ./health-check.sh
---

The service at [[url]] is down (status: [[status_code]]).
Please investigate and triage the issue:
1. Check recent deployments
2. Review error logs
3. Identify root cause
4. Suggest remediation steps
```

**Script: `health-check.sh`**

```bash
#!/bin/bash
URL="https://api.example.com/health"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$URL")

if [ "$STATUS" != "200" ]; then
  # Service is down - execute flow
  echo "{\"execute\": true, \"output\": {\"url\": \"$URL\", \"status_code\": \"$STATUS\"}}"
else
  # Service is healthy - skip execution
  echo "{\"execute\": false, \"output\": {}}"
fi
```

### Flow Commands

```bash
# Add a flow
cao flow add daily-standup.md

# List all flows (shows schedule, next run time, enabled status)
cao flow list

# Enable/disable a flow
cao flow enable daily-standup
cao flow disable daily-standup

# Manually run a flow (ignores schedule)
cao flow run daily-standup

# Remove a flow
cao flow remove daily-standup
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `cao launch --agents <name>` | Launch single agent |
| `cao launch --agents <name> --cwd <path>` | Launch agent in specific directory |
| `cao launch --agents <name> --provider <provider>` | Launch with specific provider |
| `cao team init` | Create cao.config.json in current directory |
| `cao team show` | Show project's agent configuration |
| `cao team start` | Start all agents from cao.config.json |
| `cao team start --cwd <path>` | Start team in specific directory |
| `cao install <agent>` | Install built-in agent profile |
| `cao install <file.md>` | Install agent from file |
| `cao providers` | List installed CLI tools |
| `cao config show` | Show global configuration |
| `cao config set-provider <provider>` | Set default provider |
| `cao config set-provider <provider> --agent <name>` | Set provider for specific agent |
| `cao shutdown --all` | Shutdown all sessions |
| `cao shutdown --session <name>` | Shutdown specific session |
| `cao flow add <file.md>` | Add scheduled flow |
| `cao flow list` | List all flows |
| `cao flow run <name>` | Manually run flow |
| `cao-server` | Start CAO server |

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.