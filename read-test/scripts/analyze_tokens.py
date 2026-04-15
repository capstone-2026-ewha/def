"""
SWE-agent trajectory 토큰 분류 분석기 (Qwen2.5-Coder tokenizer 사용).

두 관점에서 분석:
1. trajectory (step별) — action 카테고리별 observation 토큰 분포
2. history (LLM request별) — 실제 소비한 input 토큰을 카테고리별로
"""
import json
import sys
import os
from pathlib import Path
from collections import defaultdict
from transformers import AutoTokenizer

# ======== Config ========
TOKENIZER_PATH = os.path.expandvars(
    "$BASE_DIR/models/qwen2.5-coder-7b-instruct"
)

# 에이전트 action을 5개 카테고리로 분류
READ_CMDS = {"cat", "less", "more", "head", "tail", "nl", "view", "open", "file"}
SEARCH_CMDS = {"grep", "find", "locate", "ag", "rg", "which", "whereis"}
LIST_CMDS = {"ls", "tree", "pwd"}
EDIT_CMDS = {"sed", "awk", "echo", "tee", "cat", "vim", "nano"}  # 'cat >' 형태도
EXEC_CMDS = {"python", "python3", "pytest", "bash", "sh", "./", "make", "node", "npm", "pip"}

def categorize_action(action: str) -> str:
    """action 문자열을 카테고리로 분류."""
    if not action:
        return "empty"
    
    action_stripped = action.strip()
    if not action_stripped:
        return "empty"
    
    # 'submit' 특수 케이스
    if action_stripped.lower().startswith("submit"):
        return "submit"
    
    # 첫 토큰 추출
    first = action_stripped.split()[0].lower()
    # './script' 같은 경우
    first_clean = first.lstrip('./')
    
    # Edit 패턴 우선 체크 (redirection, heredoc)
    if ">" in action_stripped or "<<" in action_stripped:
        if "cat" in first or "echo" in first or "tee" in first:
            return "edit"
    
    # sed -i는 edit
    if "sed" in first and "-i" in action_stripped:
        return "edit"
    
    # 일반 카테고리
    if first_clean in READ_CMDS or first in READ_CMDS:
        return "read"
    if first_clean in SEARCH_CMDS or first in SEARCH_CMDS:
        return "search"
    if first_clean in LIST_CMDS or first in LIST_CMDS:
        return "list"
    if first_clean in EDIT_CMDS or first in EDIT_CMDS:
        return "edit"
    if first_clean in EXEC_CMDS or first in EXEC_CMDS:
        return "exec"
    # python filename.py 패턴
    if any(first_clean.startswith(p) for p in ("python", "pytest")):
        return "exec"
    
    return "other"


def analyze_trajectory(data, tokenizer):
    """trajectory 리스트 분석: action별 observation 토큰 분포."""
    trajectory = data.get("trajectory", [])
    
    by_category = defaultdict(lambda: {"count": 0, "obs_tokens": 0, "thought_tokens": 0, "action_tokens": 0})
    per_turn = []
    
    for i, step in enumerate(trajectory):
        action = step.get("action", "") or ""
        observation = step.get("observation", "") or ""
        thought = step.get("thought", "") or ""
        
        cat = categorize_action(action)
        
        obs_tokens = len(tokenizer.encode(observation, add_special_tokens=False)) if observation else 0
        thought_tokens = len(tokenizer.encode(thought, add_special_tokens=False)) if thought else 0
        action_tokens = len(tokenizer.encode(action, add_special_tokens=False)) if action else 0
        
        by_category[cat]["count"] += 1
        by_category[cat]["obs_tokens"] += obs_tokens
        by_category[cat]["thought_tokens"] += thought_tokens
        by_category[cat]["action_tokens"] += action_tokens
        
        per_turn.append({
            "turn": i,
            "category": cat,
            "action_preview": action[:80].replace("\n", " "),
            "obs_tokens": obs_tokens,
            "thought_tokens": thought_tokens,
            "action_tokens": action_tokens,
        })
    
    return dict(by_category), per_turn


def analyze_history(data, tokenizer):
    """
    history 리스트 분석: 실제 LLM에 보낸 각 메시지의 토큰 수.
    
    history 각 항목은 message dict. {role, content} 형식일 것.
    """
    history = data.get("history", [])
    
    by_role = defaultdict(lambda: {"count": 0, "tokens": 0})
    per_message = []
    
    for i, msg in enumerate(history):
        if not isinstance(msg, dict):
            continue
        
        role = msg.get("role", "unknown")
        content = msg.get("content", "") or ""
        
        # content가 list (multimodal)일 수 있음
        if isinstance(content, list):
            content = " ".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in content
            )
        
        tokens = len(tokenizer.encode(content, add_special_tokens=False)) if content else 0
        
        by_role[role]["count"] += 1
        by_role[role]["tokens"] += tokens
        
        per_message.append({
            "msg": i,
            "role": role,
            "tokens": tokens,
            "preview": content[:100].replace("\n", " "),
        })
    
    return dict(by_role), per_message


def analyze_cumulative_consumption(data, tokenizer):
    """
    에이전트가 실제로 LLM에 지불한 누적 input 토큰.
    
    turn N의 input = system + task + (turn 1~N-1의 action, obs)
    즉 한 번 읽은 파일이 이후 모든 턴에 포함됨 (실제 API billing).
    """
    trajectory = data.get("trajectory", [])
    history = data.get("history", [])
    
    # history에서 system prompt + initial task 찾기
    base_tokens = 0
    base_category_tokens = defaultdict(int)
    for msg in history[:2]:  # 보통 첫 1-2개가 system + user task
        if isinstance(msg, dict):
            content = msg.get("content", "") or ""
            if isinstance(content, list):
                content = " ".join(item.get("text", "") if isinstance(item, dict) else str(item) for item in content)
            role = msg.get("role", "")
            t = len(tokenizer.encode(content, add_special_tokens=False)) if content else 0
            base_tokens += t
            if role == "system":
                base_category_tokens["system_prompt"] += t
            else:
                base_category_tokens["initial_task"] += t
    
    # 각 turn의 누적 input 추적
    running_category = defaultdict(int)
    for k, v in base_category_tokens.items():
        running_category[k] = v
    
    cumulative_total_input = 0
    cumulative_by_category = defaultdict(int)
    
    for step in trajectory:
        action = step.get("action", "") or ""
        observation = step.get("observation", "") or ""
        thought = step.get("thought", "") or ""
        response = step.get("response", "") or ""
        
        # 이 step의 LLM 호출 시점에서, input context = 지금까지 쌓인 모든 것
        current_input_tokens = sum(running_category.values())
        cumulative_total_input += current_input_tokens
        
        # 각 카테고리 누적 기여분도 합산
        for cat, tokens in running_category.items():
            cumulative_by_category[cat] += tokens
        
        # 이제 이 step이 끝나면 다음 턴의 context에 추가되는 것:
        cat = categorize_action(action)
        
        # assistant response (thought + action)
        resp_tokens = len(tokenizer.encode(response, add_special_tokens=False)) if response else 0
        running_category["assistant_response"] += resp_tokens
        
        # tool result (observation) - 이게 카테고리별
        obs_tokens = len(tokenizer.encode(observation, add_special_tokens=False)) if observation else 0
        running_category[f"tool_result_{cat}"] += obs_tokens
    
    return dict(cumulative_by_category), cumulative_total_input


def print_report(traj_cats, per_turn, hist_roles, cum_by_cat, cum_total):
    print("=" * 70)
    print("TRAJECTORY ANALYSIS (per-step observation tokens by action category)")
    print("=" * 70)
    
    total_obs = sum(c["obs_tokens"] for c in traj_cats.values())
    total_steps = sum(c["count"] for c in traj_cats.values())
    
    print(f"\nTotal steps: {total_steps}")
    print(f"Total observation tokens: {total_obs:,}")
    print()
    print(f"{'Category':<15} {'Count':>6} {'ObsTokens':>12} {'% of Obs':>10}")
    print("-" * 50)
    for cat, stats in sorted(traj_cats.items(), key=lambda x: -x[1]["obs_tokens"]):
        pct = 100 * stats["obs_tokens"] / total_obs if total_obs else 0
        print(f"{cat:<15} {stats['count']:>6} {stats['obs_tokens']:>12,} {pct:>9.1f}%")
    
    read_search = traj_cats.get("read", {}).get("obs_tokens", 0) + traj_cats.get("search", {}).get("obs_tokens", 0)
    read_pct = 100 * read_search / total_obs if total_obs else 0
    print()
    print(f"READ + SEARCH obs tokens: {read_search:,} ({read_pct:.1f}% of total observation)")
    
    print()
    print("=" * 70)
    print("HISTORY ANALYSIS (LLM messages by role)")
    print("=" * 70)
    total_hist = sum(r["tokens"] for r in hist_roles.values())
    print(f"\nTotal message tokens: {total_hist:,}")
    print()
    print(f"{'Role':<15} {'Count':>6} {'Tokens':>12} {'% Total':>10}")
    print("-" * 50)
    for role, stats in sorted(hist_roles.items(), key=lambda x: -x[1]["tokens"]):
        pct = 100 * stats["tokens"] / total_hist if total_hist else 0
        print(f"{role:<15} {stats['count']:>6} {stats['tokens']:>12,} {pct:>9.1f}%")
    
    print()
    print("=" * 70)
    print("CUMULATIVE CONSUMPTION (API billing perspective)")
    print("What the agent actually *paid* in input tokens across all LLM calls")
    print("=" * 70)
    print(f"\nTotal cumulative input tokens: {cum_total:,}")
    print()
    print(f"{'Category':<25} {'Tokens':>12} {'% Total':>10}")
    print("-" * 50)
    for cat, tokens in sorted(cum_by_cat.items(), key=lambda x: -x[1]):
        pct = 100 * tokens / cum_total if cum_total else 0
        print(f"{cat:<25} {tokens:>12,} {pct:>9.1f}%")
    
    # Read-heavy 증거 (누적 관점)
    read_cum = cum_by_cat.get("tool_result_read", 0) + cum_by_cat.get("tool_result_search", 0)
    read_cum_pct = 100 * read_cum / cum_total if cum_total else 0
    print()
    print(f"READ + SEARCH cumulative tokens: {read_cum:,} ({read_cum_pct:.1f}% of consumption)")
    print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_tokens.py <trajectory.traj>")
        sys.exit(1)
    
    traj_path = sys.argv[1]
    
    print(f"Loading tokenizer from {TOKENIZER_PATH}...")
    tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_PATH)
    
    print(f"Loading trajectory from {traj_path}...")
    with open(traj_path) as f:
        data = json.load(f)
    
    print("\n[1/3] Analyzing trajectory (per-step)...")
    traj_cats, per_turn = analyze_trajectory(data, tokenizer)
    
    print("[2/3] Analyzing history (LLM messages)...")
    hist_roles, per_message = analyze_history(data, tokenizer)
    
    print("[3/3] Computing cumulative consumption...")
    cum_by_cat, cum_total = analyze_cumulative_consumption(data, tokenizer)
    
    print()
    print_report(traj_cats, per_turn, hist_roles, cum_by_cat, cum_total)
    
    # JSON 저장
    out_path = Path(traj_path).parent / "token_analysis.json"
    out = {
        "source": traj_path,
        "trajectory_analysis": {
            "by_category": traj_cats,
            "per_turn": per_turn,
        },
        "history_analysis": {
            "by_role": hist_roles,
            # per_message는 용량 커서 제외, 필요시 주석 해제
            # "per_message": per_message,
        },
        "cumulative_consumption": {
            "total_input_tokens": cum_total,
            "by_category": cum_by_cat,
        },
    }
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()