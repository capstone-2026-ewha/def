"""
토큰 분석 결과를 시각화.
3가지 플롯 생성:
1. 카테고리별 observation 토큰 (파이 + 바)
2. 누적 consumption 브레이크다운
3. Turn별 토큰 증가 흐름 (선 그래프)
"""
import json
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# 카테고리별 색상 (일관성)
COLOR_MAP = {
    "read": "#e74c3c",           # 빨강 - 핵심
    "search": "#e67e22",         # 주황 - 핵심
    "list": "#f39c12",           # 노랑
    "exec": "#3498db",           # 파랑
    "edit": "#9b59b6",           # 보라
    "submit": "#95a5a6",         # 회색
    "empty": "#bdc3c7",          # 연회색
    "other": "#7f8c8d",          # 짙은회색
    # 누적 분석용
    "tool_result_read": "#e74c3c",
    "tool_result_search": "#e67e22",
    "tool_result_list": "#f39c12",
    "tool_result_exec": "#3498db",
    "tool_result_edit": "#9b59b6",
    "tool_result_submit": "#95a5a6",
    "tool_result_empty": "#bdc3c7",
    "tool_result_other": "#7f8c8d",
    "assistant_response": "#2ecc71",  # 녹색
    "system_prompt": "#34495e",       # 남색
    "initial_task": "#16a085",        # 청록
}

def get_color(cat):
    return COLOR_MAP.get(cat, "#ecf0f1")


def plot_trajectory_breakdown(data, out_dir):
    """플롯 1: trajectory (per-step) observation 카테고리별 분포."""
    by_cat = data["trajectory_analysis"]["by_category"]
    
    # obs_tokens 기준 정렬
    items = sorted(by_cat.items(), key=lambda x: -x[1]["obs_tokens"])
    items = [(cat, s) for cat, s in items if s["obs_tokens"] > 0]  # 0 제거
    
    cats = [c for c, _ in items]
    values = [s["obs_tokens"] for _, s in items]
    colors = [get_color(c) for c in cats]
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # 좌: 파이차트
    total = sum(values)
    pct = [100 * v / total for v in values]
    # 5% 미만은 라벨 숨김 (겹침 방지)
    labels = [f"{c}\n{v:,} ({p:.1f}%)" if p >= 5 else "" for c, v, p in zip(cats, values, pct)]
    
    axes[0].pie(values, labels=labels, colors=colors, startangle=90,
                wedgeprops={'edgecolor': 'white', 'linewidth': 2})
    axes[0].set_title("Observation Tokens by Action Category\n(per-step, trajectory)", fontsize=12)
    
    # 우: 수평 바차트 (정렬된 순서)
    y_pos = range(len(cats))
    axes[1].barh(y_pos, values, color=colors)
    axes[1].set_yticks(y_pos)
    axes[1].set_yticklabels(cats)
    axes[1].invert_yaxis()
    axes[1].set_xlabel("Tokens")
    axes[1].set_title("Observation Tokens by Category (Bar)", fontsize=12)
    
    # 각 바에 숫자 표시
    for i, v in enumerate(values):
        axes[1].text(v + max(values) * 0.01, i, f"{v:,} ({100*v/total:.1f}%)",
                     va='center', fontsize=9)
    
    # Read+Search 강조 박스
    read_search = sum(by_cat.get(c, {}).get("obs_tokens", 0) for c in ["read", "search"])
    read_pct = 100 * read_search / total if total else 0
    fig.suptitle(
        f"READ + SEARCH = {read_search:,} tokens ({read_pct:.1f}% of observations)",
        fontsize=14, fontweight='bold', y=1.02
    )
    
    plt.tight_layout()
    out = out_dir / "01_trajectory_breakdown.png"
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f"Saved: {out}")
    plt.close()


def plot_cumulative_consumption(data, out_dir):
    """플롯 2: 누적 consumption (실제 API billing 관점)."""
    cum = data["cumulative_consumption"]["by_category"]
    total = data["cumulative_consumption"]["total_input_tokens"]
    
    items = sorted(cum.items(), key=lambda x: -x[1])
    items = [(c, v) for c, v in items if v > 0]
    
    cats = [c for c, _ in items]
    values = [v for _, v in items]
    colors = [get_color(c) for c in cats]
    
    # 카테고리 이름 단순화 (tool_result_X → X)
    display_cats = [c.replace("tool_result_", "obs_") for c in cats]
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # 좌: 파이차트
    pct = [100 * v / total for v in values]
    labels = [f"{c}\n{p:.1f}%" if p >= 5 else "" for c, p in zip(display_cats, pct)]
    axes[0].pie(values, labels=labels, colors=colors, startangle=90,
                wedgeprops={'edgecolor': 'white', 'linewidth': 2})
    axes[0].set_title("Cumulative Input Tokens by Source\n(what agent 'paid' across all LLM calls)", fontsize=12)
    
    # 우: 수평 바
    y_pos = range(len(cats))
    axes[1].barh(y_pos, values, color=colors)
    axes[1].set_yticks(y_pos)
    axes[1].set_yticklabels(display_cats)
    axes[1].invert_yaxis()
    axes[1].set_xlabel("Cumulative Input Tokens")
    axes[1].set_title("Cumulative Consumption (Bar)", fontsize=12)
    
    for i, v in enumerate(values):
        axes[1].text(v + max(values) * 0.01, i, f"{v:,} ({100*v/total:.1f}%)",
                     va='center', fontsize=9)
    
    # Read-heavy 강조
    read_cum = cum.get("tool_result_read", 0) + cum.get("tool_result_search", 0)
    read_pct = 100 * read_cum / total if total else 0
    fig.suptitle(
        f"READ+SEARCH cumulative = {read_cum:,} tokens ({read_pct:.1f}% of total consumption)",
        fontsize=14, fontweight='bold', y=1.02
    )
    
    plt.tight_layout()
    out = out_dir / "02_cumulative_consumption.png"
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f"Saved: {out}")
    plt.close()


def plot_per_turn_flow(data, out_dir):
    """플롯 3: turn별 토큰 흐름 (누적)."""
    per_turn = data["trajectory_analysis"]["per_turn"]
    
    if not per_turn:
        print("No per_turn data, skipping plot 3")
        return
    
    turns = [t["turn"] for t in per_turn]
    obs_tokens = [t["obs_tokens"] for t in per_turn]
    categories = [t["category"] for t in per_turn]
    
    # 누적
    cumulative = []
    running = 0
    for t in obs_tokens:
        running += t
        cumulative.append(running)
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # 상단: turn별 observation 토큰 (카테고리별 색)
    bar_colors = [get_color(c) for c in categories]
    ax1.bar(turns, obs_tokens, color=bar_colors, edgecolor='white', linewidth=0.8)
    ax1.set_xlabel("Turn")
    ax1.set_ylabel("Observation Tokens (this turn)")
    ax1.set_title("Tokens added by each step's observation", fontsize=12)
    ax1.grid(True, alpha=0.3, axis='y')
    
    # 각 바 위에 카테고리 라벨
    for i, (t, v, c) in enumerate(zip(turns, obs_tokens, categories)):
        if v > 0:
            ax1.text(t, v + max(obs_tokens) * 0.02, c,
                     ha='center', fontsize=8, rotation=45)
    
    # 카테고리 범례
    unique_cats = list(set(categories))
    patches = [mpatches.Patch(color=get_color(c), label=c) for c in unique_cats]
    ax1.legend(handles=patches, loc='upper right', fontsize=9)
    
    # 하단: 누적
    ax2.fill_between(turns, cumulative, alpha=0.3, color="#e74c3c")
    ax2.plot(turns, cumulative, 'o-', color="#c0392b", linewidth=2, markersize=6)
    ax2.set_xlabel("Turn")
    ax2.set_ylabel("Cumulative Observation Tokens")
    ax2.set_title("Cumulative observation tokens over turns\n(every past read stays in context)", fontsize=12)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    out = out_dir / "03_per_turn_flow.png"
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f"Saved: {out}")
    plt.close()


def plot_headline_summary(data, out_dir):
    """플롯 4: 한눈에 보이는 요약 (논문 figure 1 후보)."""
    by_cat = data["trajectory_analysis"]["by_category"]
    cum = data["cumulative_consumption"]["by_category"]
    cum_total = data["cumulative_consumption"]["total_input_tokens"]
    
    # Read+Search vs Others (누적 기준)
    read_cum = cum.get("tool_result_read", 0) + cum.get("tool_result_search", 0)
    other_cum = cum_total - read_cum
    
    fig, ax = plt.subplots(figsize=(10, 4))
    
    # 스택 바 (하나의 긴 바)
    ax.barh([""], [read_cum], color="#e74c3c", 
            label=f"Read + Search: {read_cum:,} tokens ({100*read_cum/cum_total:.1f}%)")
    ax.barh([""], [other_cum], left=[read_cum], color="#95a5a6",
            label=f"Other: {other_cum:,} tokens ({100*other_cum/cum_total:.1f}%)")
    
    # 중간에 비율 표시
    ax.text(read_cum / 2, 0, f"{100*read_cum/cum_total:.1f}%",
            ha='center', va='center', fontsize=20, fontweight='bold', color='white')
    ax.text(read_cum + other_cum / 2, 0, f"{100*other_cum/cum_total:.1f}%",
            ha='center', va='center', fontsize=20, fontweight='bold', color='white')
    
    ax.set_xlabel("Cumulative Input Tokens", fontsize=11)
    ax.set_title("Most of a coding agent's token consumption comes from code exploration",
                 fontsize=14, fontweight='bold', pad=15)
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.35), ncol=2, fontsize=11)
    
    # y축 장식 제거
    ax.set_yticks([])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    
    plt.tight_layout()
    out = out_dir / "04_headline_summary.png"
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f"Saved: {out}")
    plt.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: python plot_breakdown.py <token_analysis.json>")
        sys.exit(1)
    
    json_path = Path(sys.argv[1])
    out_dir = json_path.parent
    
    with open(json_path) as f:
        data = json.load(f)
    
    print(f"Creating plots in {out_dir}/...")
    print()
    
    plot_trajectory_breakdown(data, out_dir)
    plot_cumulative_consumption(data, out_dir)
    plot_per_turn_flow(data, out_dir)
    plot_headline_summary(data, out_dir)
    
    print()
    print("=" * 50)
    print("Done. 4 plots generated:")
    print("  01_trajectory_breakdown.png   (per-step observation by category)")
    print("  02_cumulative_consumption.png (API billing perspective)")
    print("  03_per_turn_flow.png          (turn-by-turn evolution)")
    print("  04_headline_summary.png       (Paper's Figure 1 candidate)")
    print("=" * 50)


if __name__ == "__main__":
    main()