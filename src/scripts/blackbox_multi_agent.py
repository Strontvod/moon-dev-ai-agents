"""
Blackbox AI Multi-Agent Task Runner

Dispatches coding tasks to multiple AI agents (Blackbox, Claude Code, Codex, Gemini)
running in parallel on Blackbox AI Cloud. An AI judge picks the best implementation.

API Docs: https://docs.blackbox.ai/api-reference/multi-agent-task

Usage:
    # Multi-agent task (2+ agents, AI judge picks best)
    python src/scripts/blackbox_multi_agent.py "Add unit tests for risk_agent" --repo https://github.com/user/repo

    # Single agent task
    python src/scripts/blackbox_multi_agent.py "Fix the login bug" --repo https://github.com/user/repo --agent claude

    # List available agents/models
    python src/scripts/blackbox_multi_agent.py --list

    # Check task status
    python src/scripts/blackbox_multi_agent.py --status TASK_ID
"""

import os
import sys
import json
import time
import argparse
import requests
from pathlib import Path
from termcolor import cprint
from dotenv import load_dotenv

# Load .env from src/ directory (same as other agents)
src_dir = Path(__file__).parent.parent
load_dotenv(dotenv_path=src_dir / ".env")

# ─── Configuration ────────────────────────────────────────────────────────────

BLACKBOX_API_KEY = os.getenv("BLACKBOX_API_KEY", "")
BLACKBOX_API_URL = "https://cloud.blackbox.ai/api/tasks"

# Available agents and their recommended models
AGENTS = {
    "blackbox": {
        "recommended": "blackboxai/blackbox-pro",
        "models": [
            "blackboxai/blackbox-pro",
            "blackboxai/anthropic/claude-sonnet-4.5",
            "blackboxai/openai/gpt-5.2-codex",
            "blackboxai/anthropic/claude-opus-4.5",
            "blackboxai/x-ai/grok-code-fast-1:free",
            "blackboxai/google/gemini-2.5-pro",
        ]
    },
    "claude": {
        "recommended": "blackboxai/anthropic/claude-opus-4.6",
        "models": [
            "blackboxai/anthropic/claude-opus-4.6",
            "blackboxai/anthropic/claude-sonnet-4.5",
            "blackboxai/anthropic/claude-sonnet-4",
            "blackboxai/anthropic/claude-opus-4.5",
        ]
    },
    "codex": {
        "recommended": "gpt-5.2-codex",
        "models": [
            "gpt-5.2-codex",
            "openai/gpt-5",
            "openai/gpt-5-mini",
            "openai/gpt-5-nano",
            "openai/gpt-4.1",
        ]
    },
    "gemini": {
        "recommended": "gemini-3-pro",
        "models": [
            "gemini-3-pro",
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.0-flash-exp",
        ]
    },
}

# Default multi-agent combo: your 3 active agents
DEFAULT_MULTI_AGENTS = [
    {"agent": "claude",   "model": "blackboxai/anthropic/claude-opus-4.6"},
    {"agent": "blackbox", "model": "blackboxai/blackbox-pro"},
    {"agent": "gemini",   "model": "gemini-3-pro"},
]

# ─── API Functions ────────────────────────────────────────────────────────────

def _headers():
    if not BLACKBOX_API_KEY:
        cprint("❌ BLACKBOX_API_KEY not set in .env", "red")
        cprint("   Get your key at https://cloud.blackbox.ai → API Keys", "yellow")
        sys.exit(1)
    return {
        "Authorization": f"Bearer {BLACKBOX_API_KEY}",
        "Content-Type": "application/json",
    }


def create_task(prompt, repo_url=None, branch="main", agent="blackbox", model=None):
    """Create a single-agent task on Blackbox Cloud.

    Args:
        prompt:   Task description for the agent
        repo_url: GitHub repo URL (optional)
        branch:   Branch to work on (default: main)
        agent:    Agent name: blackbox, claude, codex, gemini
        model:    Model ID (None = use recommended for agent)

    Returns:
        dict: Task response with id, status, taskUrl
    """
    if model is None:
        model = AGENTS[agent]["recommended"]

    payload = {
        "prompt": prompt,
        "selectedAgent": agent,
        "selectedModel": model,
    }
    if repo_url:
        payload["repoUrl"] = repo_url
        payload["selectedBranch"] = branch

    cprint(f"\n🚀 Creating single-agent task...", "cyan")
    cprint(f"  ├─ Agent: {agent}", "cyan")
    cprint(f"  ├─ Model: {model}", "cyan")
    cprint(f"  ├─ Repo:  {repo_url or '(none)'}", "cyan")
    cprint(f"  └─ Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}", "cyan")

    resp = requests.post(BLACKBOX_API_URL, headers=_headers(), json=payload)
    if not resp.ok:
        cprint(f"\n❌ API error {resp.status_code}: {resp.text[:500]}", "red")
        sys.exit(1)
    data = resp.json()

    task = data.get("task", data)
    task_id = task.get("id", "unknown")
    task_url = data.get("taskUrl", task.get("taskUrl", ""))

    cprint(f"\n✅ Task created!", "green")
    cprint(f"  ├─ ID:  {task_id}", "green")
    cprint(f"  └─ URL: {task_url}", "green")

    return data


def create_multi_agent_task(prompt, repo_url=None, branch="main", agents=None):
    """Create a multi-agent task (2-5 agents run in parallel, AI judge picks best).

    Args:
        prompt:   Task description
        repo_url: GitHub repo URL (optional)
        branch:   Branch to work on
        agents:   List of {"agent": str, "model": str} dicts (min 2, max 5)

    Returns:
        dict: Task response with id, status, agentExecutions
    """
    if agents is None:
        agents = DEFAULT_MULTI_AGENTS

    if len(agents) < 2:
        cprint("❌ Multi-agent tasks need at least 2 agents", "red")
        sys.exit(1)
    if len(agents) > 5:
        cprint("⚠️  Max 5 agents — trimming to first 5", "yellow")
        agents = agents[:5]

    payload = {
        "prompt": prompt,
        "selectedAgents": agents,
    }
    if repo_url:
        payload["repoUrl"] = repo_url
        payload["selectedBranch"] = branch

    cprint(f"\n🚀 Creating multi-agent task ({len(agents)} agents)...", "cyan")
    for i, a in enumerate(agents):
        prefix = "├─" if i < len(agents) - 1 else "└─"
        cprint(f"  {prefix} {a['agent']}: {a['model']}", "cyan")
    cprint(f"  Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}", "cyan")

    resp = requests.post(BLACKBOX_API_URL, headers=_headers(), json=payload)
    if not resp.ok:
        cprint(f"\n❌ API error {resp.status_code}: {resp.text[:500]}", "red")
        sys.exit(1)
    data = resp.json()

    task = data.get("task", data)
    task_id = task.get("id", "unknown")
    task_url = data.get("taskUrl", task.get("taskUrl", ""))

    cprint(f"\n✅ Multi-agent task created!", "green")
    cprint(f"  ├─ ID:  {task_id}", "green")
    cprint(f"  └─ URL: {task_url}", "green")

    return data


def get_task_status(task_id):
    """Check task status via GET /api/tasks/{taskId}.

    Returns:
        dict: Task object with status, agentExecutions, etc.
    """
    url = f"{BLACKBOX_API_URL}/{task_id}"
    resp = requests.get(url, headers=_headers())
    resp.raise_for_status()
    return resp.json()


def poll_until_complete(task_id, interval=10, timeout=600):
    """Poll task status until all agents complete or timeout.

    Args:
        task_id:  Task ID to poll
        interval: Seconds between polls (default 10)
        timeout:  Max seconds to wait (default 600 = 10 min)

    Returns:
        dict: Final task status
    """
    cprint(f"\n⏳ Polling task {task_id} (every {interval}s, timeout {timeout}s)...", "cyan")
    start = time.time()

    while time.time() - start < timeout:
        data = get_task_status(task_id)
        task = data.get("task", data)
        status = task.get("status", "unknown")

        # Check agent executions
        executions = task.get("agentExecutions") or []
        completed = sum(1 for e in executions if e.get("status") in ("completed", "failed"))
        total = len(executions) if executions else "?"

        elapsed = int(time.time() - start)
        cprint(f"  [{elapsed}s] status={status}  agents={completed}/{total}", "cyan")

        if status in ("completed", "failed", "cancelled"):
            cprint(f"\n{'✅' if status == 'completed' else '❌'} Task {status}!", "green" if status == "completed" else "red")
            _print_results(task)
            return data

        time.sleep(interval)

    cprint(f"\n⚠️  Timeout after {timeout}s — task still running", "yellow")
    cprint(f"   Check manually: https://cloud.blackbox.ai/tasks/{task_id}", "yellow")
    return get_task_status(task_id)


def _print_results(task):
    """Pretty-print task results."""
    executions = task.get("agentExecutions") or []
    if not executions:
        cprint("  No agent executions found yet", "yellow")
        return

    cprint(f"\n📊 Results ({len(executions)} agents):", "cyan")
    cprint("─" * 60, "cyan")

    for ex in executions:
        agent = ex.get("agent", "?")
        model = ex.get("model", "?")
        status = ex.get("status", "?")
        files_changed = ex.get("filesChanged", 0)
        lines_added = ex.get("linesAdded", 0)
        lines_removed = ex.get("linesRemoved", 0)
        error = ex.get("error")

        color = "green" if status == "completed" else "red" if status == "failed" else "yellow"
        cprint(f"\n  🤖 {agent} ({model})", color)
        cprint(f"     Status: {status}", color)

        if status == "completed":
            cprint(f"     Files changed: {files_changed}  (+{lines_added} / -{lines_removed})", "green")
            commits = ex.get("commits") or []
            for c in commits[:3]:
                cprint(f"     Commit: {c.get('message', '?')[:60]}", "green")
            result = ex.get("result") or {}
            if result.get("summary"):
                cprint(f"     Summary: {result['summary'][:120]}", "green")
        elif error:
            cprint(f"     Error: {error}", "red")

    cprint("─" * 60, "cyan")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def list_agents():
    """Print all available agents and models."""
    cprint("\n🤖 Blackbox AI Cloud — Available Agents & Models", "cyan", attrs=["bold"])
    cprint("═" * 55, "cyan")
    for agent_name, info in AGENTS.items():
        cprint(f"\n  {agent_name}:", "green", attrs=["bold"])
        for m in info["models"]:
            rec = " (recommended)" if m == info["recommended"] else ""
            cprint(f"    • {m}{rec}", "white")
    cprint(f"\n💡 Default multi-agent combo uses all 4 recommended models", "yellow")
    cprint(f"   Get your API key at https://cloud.blackbox.ai → API Keys\n", "yellow")


def main():
    parser = argparse.ArgumentParser(
        description="Blackbox AI Multi-Agent Task Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Multi-agent (all 4 agents, AI judge picks best)
  python src/scripts/blackbox_multi_agent.py "Add dark mode" --repo https://github.com/user/repo

  # Single agent
  python src/scripts/blackbox_multi_agent.py "Fix login bug" --repo https://github.com/user/repo --agent claude

  # Custom agents
  python src/scripts/blackbox_multi_agent.py "Refactor auth" --repo https://github.com/user/repo --agents blackbox claude

  # Check status
  python src/scripts/blackbox_multi_agent.py --status abc123

  # List agents
  python src/scripts/blackbox_multi_agent.py --list
        """
    )
    parser.add_argument("prompt", nargs="?", help="Task description for the agent(s)")
    parser.add_argument("--repo", help="GitHub repository URL")
    parser.add_argument("--branch", default="main", help="Branch to work on (default: main)")
    parser.add_argument("--agent", help="Single agent: blackbox, claude, codex, gemini")
    parser.add_argument("--agents", nargs="+", help="Multiple agents for multi-agent task")
    parser.add_argument("--status", metavar="TASK_ID", help="Check status of existing task")
    parser.add_argument("--poll", metavar="TASK_ID", help="Poll task until complete")
    parser.add_argument("--list", action="store_true", help="List available agents and models")
    parser.add_argument("--no-poll", action="store_true", help="Don't auto-poll after creating task")

    args = parser.parse_args()

    cprint("\nBlackbox AI Multi-Agent Runner\n", "cyan", attrs=["bold"])

    # List agents
    if args.list:
        list_agents()
        return

    # Check status
    if args.status:
        data = get_task_status(args.status)
        task = data.get("task", data)
        cprint(f"\nTask {args.status}:", "cyan")
        cprint(json.dumps(task, indent=2, default=str), "white")
        _print_results(task)
        return

    # Poll existing task
    if args.poll:
        poll_until_complete(args.poll)
        return

    # Create task
    if not args.prompt:
        parser.print_help()
        return

    if args.agent:
        # Single agent
        if args.agent not in AGENTS:
            cprint(f"❌ Unknown agent: {args.agent}. Use --list to see options.", "red")
            return
        data = create_task(args.prompt, args.repo, args.branch, args.agent)
        task = data.get("task", data)
        task_id = task.get("id")
    elif args.agents:
        # Custom multi-agent
        agent_list = []
        for a in args.agents:
            if a not in AGENTS:
                cprint(f"❌ Unknown agent: {a}. Use --list to see options.", "red")
                return
            agent_list.append({"agent": a, "model": AGENTS[a]["recommended"]})
        data = create_multi_agent_task(args.prompt, args.repo, args.branch, agent_list)
        task = data.get("task", data)
        task_id = task.get("id")
    else:
        # Default: all 4 agents
        data = create_multi_agent_task(args.prompt, args.repo, args.branch)
        task = data.get("task", data)
        task_id = task.get("id")

    # Auto-poll unless --no-poll
    if task_id and not args.no_poll:
        poll_until_complete(task_id)


if __name__ == "__main__":
    main()
