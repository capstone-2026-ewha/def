"""
vLLM prefix caching replay 스크립트
- 48개 trace JSON을 턴별로 replay
- 턴별 TTFT 측정
- prefix cache hit rate 확인
"""

"""
vLLM prefix caching replay 스크립트
- 48개 trace JSON을 턴별로 replay
- 턴별 TTFT 측정
- prefix cache hit rate 확인
"""

import json
import os
import glob
import time
import requests
from pathlib import Path

TRACES_DIR    = '/home/hellkitty/local-proj/ast-kv/data/traces/30b_direct_run01'
RESULTS_DIR   = '/home/hellkitty/local-proj/ast-kv/results/0.5b'
VLLM_BASE_URL = 'http://localhost:8002'
MODEL_NAME    = 'Qwen2.5-Coder-0.5B-Instruct'

os.makedirs(RESULTS_DIR, exist_ok=True)

EXCLUDE = {
    'django__django-11019_run1.json',
    'matplotlib__matplotlib-23563_run0.json',
}

def get_prefix_cache_hits():
    try:
        resp = requests.get(f"{VLLM_BASE_URL}/metrics", timeout=10)
        for line in resp.text.splitlines():
            if line.startswith('#'):
                continue
            if 'vllm:prefix_cache_hits_total' in line and 'created' not in line:
                return float(line.split()[-1])
    except Exception as e:
        print(f"  metrics 조회 실패: {e}")
    return None

def get_prefix_cache_hit_rate():
    """hits / queries 비율로 현재 누적 hit rate 반환 (0.0~1.0)"""
    try:
        resp = requests.get(f"{VLLM_BASE_URL}/metrics", timeout=10)
        hits, queries = None, None
        for line in resp.text.splitlines():
            if line.startswith('#'):
                continue
            if 'vllm:prefix_cache_hits_total' in line and 'created' not in line:
                hits = float(line.split()[-1])
            if 'vllm:prefix_cache_queries_total' in line and 'created' not in line:
                queries = float(line.split()[-1])
        if hits is not None and queries is not None and queries > 0:
            return hits / queries
    except Exception as e:
        print(f"  metrics 조회 실패: {e}")
    return None

def measure_ttft(messages):
    url = f"{VLLM_BASE_URL}/v1/chat/completions"
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "max_tokens": 1,
        "stream": True,
        "temperature": 0,
    }
    start = time.time()
    first_token_time = None
    try:
        with requests.post(url, json=payload, stream=True, timeout=120) as resp:
            for line in resp.iter_lines():
                if line and line != b'data: [DONE]':
                    first_token_time = time.time()
                    break
    except Exception as e:
        print(f"  요청 실패: {e}")
        return None
    if first_token_time is None:
        return None
    return (first_token_time - start) * 1000

def extract_text_from_content(content):
    """content 필드에서 텍스트 추출"""
    if isinstance(content, str):
        return content
    if isinstance(content, list) and content:
        item = content[0]
        if isinstance(item, dict):
            return item.get('text', '')
    return ''

def extract_turns(events):
    """trace events에서 턴별 누적 메시지 컨텍스트 추출"""
    turns = []
    current_messages = []

    for e in events:
        kind = e.get('kind', '')

        if kind == 'SystemPromptEvent':
            sp = e.get('system_prompt', {})
            if isinstance(sp, dict):
                text = sp.get('text', '')
            elif isinstance(sp, list) and sp:
                text = sp[0].get('text', '') if isinstance(sp[0], dict) else str(sp[0])
            else:
                text = str(sp)
            if text:
                current_messages = [{'role': 'system', 'content': text}]

        elif kind == 'MessageEvent' and e.get('source') == 'user':
            llm_msg = e.get('llm_message', {})
            if isinstance(llm_msg, dict):
                text = extract_text_from_content(llm_msg.get('content', ''))
                if text:
                    current_messages = current_messages + [{'role': 'user', 'content': text}]

        elif kind == 'ActionEvent' and e.get('source') == 'agent':
            thought = e.get('thought', [])
            if isinstance(thought, list) and thought:
                text = thought[0].get('text', '') if isinstance(thought[0], dict) else ''
            else:
                text = str(thought) if thought else ''

            tool_call = e.get('tool_call', {})

            if text or tool_call:
                # 현재 컨텍스트를 턴으로 저장
                turns.append(list(current_messages))

                # assistant 메시지 구성
                assistant_msg = {'role': 'assistant', 'content': text}
                if tool_call and isinstance(tool_call, dict):
                    assistant_msg['tool_calls'] = [{
                        'id': tool_call.get('id', ''),
                        'type': 'function',
                        'function': {
                            'name': tool_call.get('name', ''),
                            'arguments': tool_call.get('arguments', '{}'),
                        }
                    }]
                current_messages = current_messages + [assistant_msg]

        elif kind == 'ObservationEvent':
            obs = e.get('observation', {})
            if isinstance(obs, dict):
                content = obs.get('content', [])
                text = extract_text_from_content(content)
            else:
                text = str(obs)
            if text:
                # tool result 메시지로 추가
                tool_call_id = e.get('tool_call_id', '')
                if tool_call_id:
                    current_messages = current_messages + [{
                        'role': 'tool',
                        'tool_call_id': tool_call_id,
                        'content': text,
                    }]
                else:
                    current_messages = current_messages + [{'role': 'user', 'content': text}]

    return turns

# 분석 시작
files = sorted([
    f for f in glob.glob(os.path.join(TRACES_DIR, '*.json'))
    if Path(f).name not in EXCLUDE
])
print(f"총 {len(files)}개 trace replay 시작\n")

print("[시작 전 prefix cache hits]")
hits_before = get_prefix_cache_hits()
print(f"  hits: {hits_before}\n")

all_results = []
total_ttfts = []

for f in files:
    name = Path(f).stem
    d = json.load(open(f))
    events = d.get('events', [])

    turns = extract_turns(events)
    if not turns:
        print(f"{name}: 턴 없음, 스킵")
        continue

    print(f"\n====== {name} ({len(turns)}턴) ======")
    trace_ttfts = []
    trace_hit_rates = []

    for i, messages in enumerate(turns):
        ttft = measure_ttft(messages)
        hit_rate = get_prefix_cache_hit_rate()
        if ttft is not None:
            trace_ttfts.append(ttft)
            total_ttfts.append(ttft)
            hr_str = f", hit rate = {hit_rate*100:.1f}%" if hit_rate is not None else ""
            print(f"  Turn {i+1}: TTFT = {ttft:.1f} ms{hr_str}")
        else:
            print(f"  Turn {i+1}: 측정 실패")
        if hit_rate is not None:
            trace_hit_rates.append(round(hit_rate, 4))

    if trace_ttfts:
        avg = sum(trace_ttfts) / len(trace_ttfts)
        final_hr = trace_hit_rates[-1] if trace_hit_rates else None
        hr_str = f", 최종 hit rate = {final_hr*100:.1f}%" if final_hr is not None else ""
        print(f"  세션 평균 TTFT: {avg:.1f} ms{hr_str}")
        all_results.append({
            'name': name,
            'turns': len(turns),
            'ttfts_ms': [round(t, 2) for t in trace_ttfts],
            'avg_ttft_ms': round(avg, 2),
            'hit_rates': trace_hit_rates,
            'final_hit_rate': final_hr,
        })

print(f"\n{'='*60}")
print(f"전체 결과 요약")
print(f"{'='*60}")
overall_avg = sum(total_ttfts) / len(total_ttfts) if total_ttfts else 0
print(f"총 턴 수: {len(total_ttfts)}")
print(f"전체 평균 TTFT: {overall_avg:.1f} ms")

print("\n[종료 후 prefix cache hits]")
hits_after = get_prefix_cache_hits()
final_hit_rate = get_prefix_cache_hit_rate()
print(f"  hits: {hits_after}")
if hits_before is not None and hits_after is not None:
    print(f"  증가량: {hits_after - hits_before:.0f}")
if final_hit_rate is not None:
    print(f"  최종 전체 hit rate: {final_hit_rate*100:.1f}%")

output = {
    'model': MODEL_NAME,
    'total_traces': len(all_results),
    'total_turns': len(total_ttfts),
    'overall_avg_ttft_ms': round(overall_avg, 2),
    'overall_hit_rate': round(final_hit_rate, 4) if final_hit_rate is not None else None,
    'prefix_cache_hits_before': hits_before,
    'prefix_cache_hits_after': hits_after,
    'per_trace': all_results,
}
out_path = os.path.join(RESULTS_DIR, 'prefix_caching_results.json')
with open(out_path, 'w') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
print(f"\n결과 저장 완료: {out_path}")
