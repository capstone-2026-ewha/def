import json
import matplotlib.pyplot as plt
import numpy as np
import os

RESULTS_DIR = '/home/hellkitty/local-proj/ast-kv/results'

vanilla_path = os.path.join(RESULTS_DIR, '0.5b/vanilla_replay_results.json')
prefix_path  = os.path.join(RESULTS_DIR, '0.5b/prefix_caching_results.json')

with open(vanilla_path) as f:
    vanilla = json.load(f)
with open(prefix_path) as f:
    prefix = json.load(f)

fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)

for ax, data, title, color in zip(
    axes,
    [vanilla, prefix],
    ['Vanilla Decode', 'vLLM Prefix Caching'],
    ['steelblue', 'tomato']
):
    all_ttfts = []
    for trace in data['per_trace']:
        ttfts = trace['ttfts_ms']
        turns = list(range(1, len(ttfts) + 1))
        ax.plot(turns, ttfts, color=color, alpha=0.2, linewidth=0.8)
        all_ttfts.append(ttfts)

    # 평균선
    max_turns = max(len(t) for t in all_ttfts)
    avg_by_turn = []
    for i in range(max_turns):
        vals = [t[i] for t in all_ttfts if i < len(t)]
        avg_by_turn.append(np.mean(vals))

    ax.plot(range(1, max_turns + 1), avg_by_turn,
            color='black', linewidth=2, linestyle='--', label='Mean')

    ax.set_title(title, fontsize=13)
    ax.set_xlabel('Turn', fontsize=11)
    ax.set_ylabel('TTFT (ms)', fontsize=11)
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 전체 평균 TTFT 표시
    avg = data['overall_avg_ttft_ms']
    ax.axhline(y=avg, color=color, linewidth=1.5, linestyle=':', alpha=0.8,
               label=f'Overall Avg: {avg:.1f}ms')
    ax.legend()

plt.suptitle('Vanilla vs Prefix Caching TTFT (Qwen2.5-Coder-0.5B-Instruct)', fontsize=14)
plt.tight_layout()

out_path = os.path.join(RESULTS_DIR, 'figures/ttft_comparison_0.5b.png')
plt.savefig(out_path, dpi=150, bbox_inches='tight')
print(f'저장 완료: {out_path}')
