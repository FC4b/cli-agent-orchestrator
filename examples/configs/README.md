# Example cao.config.json Files

Copy one of these to your project root as `cao.config.json` and customize as needed.

## Available Configurations

| File | Use Case |
|------|----------|
| `fullstack-team.json` | Web apps with frontend + backend |
| `mobile-team.json` | Mobile apps (Flutter/Swift/Kotlin) + backend API |
| `backend-only.json` | API services, microservices |
| `solo-developer.json` | Simple projects, scripts, utilities |
| `mixed-providers.json` | Use different CLI tools for different agents |

## Quick Start

```bash
# Copy to your project
cp examples/configs/fullstack-team.json ~/my-project/cao.config.json

# Edit project name
# Then start the team
cd ~/my-project
cao team start
```

## Configuration Format

```json
{
  "name": "project-name",
  "agents": [
    { "agent": "agent_profile_name", "provider": "provider_type" }
  ]
}
```

## Available Agents

| Agent | Specialization |
|-------|---------------|
| `code_supervisor` | Orchestrates tasks, manages workflow |
| `frontend_developer` | Web UI, React, Vue, CSS |
| `backend_developer` | APIs, databases, cloud |
| `mobile_developer` | Flutter, Swift, Kotlin |
| `developer` | General-purpose development |
| `reviewer` | Code review, quality assurance |

## Available Providers

| Provider | CLI Tool |
|----------|----------|
| `claude_code` | Claude Code (Anthropic) |
| `codex_cli` | Codex CLI (OpenAI) |
| `gemini_cli` | Gemini CLI (Google) |
| `q_cli` | Amazon Q Developer CLI |
| `kiro_cli` | Kiro CLI |

## Tips

1. **Always include `code_supervisor`** - It orchestrates the other agents
2. **Always include `reviewer`** - All code should be reviewed
3. **Match providers to strengths** - Some CLIs are better for certain tasks
4. **Start simple** - Begin with `solo-developer.json` and add agents as needed

