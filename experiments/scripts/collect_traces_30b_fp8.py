import json
import os
import asyncio
from pathlib import Path
from openhands.sdk import LLM, Agent, Conversation, Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool

os.environ["OPENHANDS_SUPPRESS_BANNER"] = "1"

ISSUES_PATH = '/home/hellkitty/local-proj/ast-kv/data/swe_bench_25.json'
REPO_BASE   = '/home/hellkitty/local-proj/ast-kv/data/repos'
TRACES_DIR  = '/home/hellkitty/local-proj/ast-kv/data/traces/30b_direct_run01'

os.makedirs(TRACES_DIR, exist_ok=True)

with open(ISSUES_PATH) as f:
    issues = json.load(f)

llm = LLM(
    model="openai/Qwen3-Coder-30B-A3B-Instruct-FP8",
    api_key="dummy",
    base_url="http://localhost:8002/v1",
)

for i, issue in enumerate(issues):
    instance_id = issue['instance_id']
    repo        = issue['repo']
    problem     = issue['problem_statement']
    cwd         = os.path.join(REPO_BASE, instance_id)

    print(f"[{i+1}/25] {instance_id} 시작...")

    for run_idx in range(2):
        trace_path = os.path.join(TRACES_DIR, f"{instance_id}_run{run_idx}.json")
        if os.path.exists(trace_path):
            print(f"  run {run_idx+1} 이미 존재, 스킵 → {trace_path}")
            continue
        print(f"  run {run_idx+1}/2")

        # repo 초기화
        import subprocess
        subprocess.run(['git', 'checkout', '.'], cwd=cwd, check=True)
        subprocess.run(['git', 'clean', '-fd'], cwd=cwd, check=True)

        agent = Agent(
            llm=llm,
            tools=[
                Tool(name=TerminalTool.name),
                Tool(name=FileEditorTool.name),
            ],
        )

        task = (
            f"Repository: {repo}\n"
            f"The repository is already cloned at: {cwd}\n\n"
            f"Issue to fix:\n{problem}\n\n"
            f"Please:\n"
            f"1. Explore the repository structure to understand the codebase\n"
            f"2. Identify the root cause of the issue\n"
            f"3. Implement a fix\n"
            f"4. Verify your fix is correct\n\n"
            f"Use the available tools to navigate and modify the codebase."
        )

        conversation = Conversation(agent=agent, workspace=cwd)
        conversation.send_message(task)
        conversation.run()

        trace = {
            'instance_id': instance_id,
            'repo': repo,
            'run_idx': run_idx,
            'events': [e.model_dump() for e in conversation.state.events],
        }

        trace_path = os.path.join(TRACES_DIR, f"{instance_id}_run{run_idx}.json")
        with open(trace_path, 'w') as f:
            json.dump(trace, f, indent=2, default=str)

        print(f"  run {run_idx+1} 완료 ({len(trace['events'])} events) → {trace_path}")

print("\n전체 완료!")