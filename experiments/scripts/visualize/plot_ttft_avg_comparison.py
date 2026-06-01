"""
Vanilla vs Prefix Caching 턴별 평균 TTFT 비교 그래프
- 두 JSON 결과 파일에서 턴별 TTFT를 읽어
- 턴 번호 기준으로 평균을 계산한 뒤
- 한 plot에 겹쳐서 표시
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from collections import defaultdict

# ── 경로 설정 ──────────────────────────────────────────────
VANILLA_PATH  = '/home/hellkitty/local-proj/ast-kv/results/0.5b/vanilla_replay_results.json'
PREFIX_PATH   = '/home/hellkitty/local-proj/ast-kv/results/0.5b/prefix_caching_results.json'
OUTPUT_PATH   = '/home/hellkitty/local-proj/ast-kv/results/figures/ttft_avg_comparison_0.5b.png'

# ── 데이터 로드 ────────────────────────────────────────────
def load_ttft_by_turn(path):
    """JSON에서 턴 번호별 TTFT 목록을 반환 {turn_idx: [ttft, ...]}"""
    with open(path) as f:
        data = json.load(f)

    by_turn = defaultdict(list)
    for trace in data['per_trace']:
        for i, ttft in enumerate(trace['ttfts_ms'], start=1):
            by_turn[i].append(ttft)
    return by_turn

vanilla_by_turn = load_ttft_by_turn(VANILLA_PATH)
prefix_by_turn  = load_ttft_by_turn(PREFIX_PATH)

# ── 턴별 평균 계산 ─────────────────────────────────────────
def compute_mean_series(by_turn, min_traces=3):
    """
    각 턴에 데이터가 min_traces개 이상 있을 때만 포함
    (후반 턴은 긴 세션만 남아 편향될 수 있으므로)
    """
    turns = sorted(k for k, v in by_turn.items() if len(v) >= min_traces)
    means = [np.mean(by_turn[t]) for t in turns]
    return turns, means

van_turns, van_means = compute_mean_series(vanilla_by_turn)
pre_turns, pre_means = compute_mean_series(prefix_by_turn)

van_avg = np.mean(van_means)
pre_avg = np.mean(pre_means)

# ── 그래프 ─────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5.5))

ax.plot(van_turns, van_means,
        color='#2563EB', linewidth=2.2, linestyle='--',
        label=f'Vanilla Decode  (overall avg {van_avg:.0f} ms)')

ax.plot(pre_turns, pre_means,
        color='#DC2626', linewidth=2.2, linestyle='-',
        label=f'vLLM Prefix Caching  (overall avg {pre_avg:.0f} ms)')

# 전체 평균 수평선
ax.axhline(van_avg, color='#2563EB', linewidth=0.8, linestyle=':', alpha=0.6)
ax.axhline(pre_avg, color='#DC2626', linewidth=0.8, linestyle=':', alpha=0.6)

# 축 설정
ax.set_xlabel('Turn', fontsize=12)
ax.set_ylabel('TTFT (ms)', fontsize=12)
ax.set_title('Mean TTFT per Turn — Vanilla vs vLLM Prefix Caching\n'
             '(Qwen2.5-Coder-0.5B-Instruct, 48 traces)',
             fontsize=13, pad=14)

ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
ax.set_xlim(left=1)
ax.set_ylim(bottom=0)
ax.grid(axis='y', linewidth=0.5, alpha=0.4)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

ax.legend(fontsize=11, framealpha=0.9, loc='upper left')

plt.tight_layout()
plt.savefig(OUTPUT_PATH, dpi=180, bbox_inches='tight')
print(f'저장 완료: {OUTPUT_PATH}')
plt.show()
