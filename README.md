# def
2026-spring capstone project
# FAC-KV: Frequently Accessed Code KV Cache Reuse

> **코딩 에이전트를 위한 position-agnostic KV cache 재사용** — long-context agentic workflow에서 반복적인 prefill 비용을 제거합니다.

[![Status](https://img.shields.io/badge/status-research-blue?style=flat-square)](.)
[![Agent](https://img.shields.io/badge/agent-SWE--Agent-orange?style=flat-square)](https://github.com/princeton-nlp/SWE-agent)
[![Runtime](https://img.shields.io/badge/runtime-vLLM-green?style=flat-square)](https://github.com/vllm-project/vllm)
[![Hardware](https://img.shields.io/badge/GPU-RTX%205090%20×2-76b900?style=flat-square&logo=nvidia)](.)
[![Benchmark](https://img.shields.io/badge/eval-SWE--bench-purple?style=flat-square)](https://www.swebench.com)

---

## 개요

코딩 에이전트는 token 사용량의 대부분을 **파일 읽기(read operation)**에 소비합니다. 대화 기록이 쌓일수록 같은 파일을 반복해서 읽게 되고, 매번 전체 prefill이 재실행됩니다. vLLM의 기본 prefix caching은 앞부분이 완전히 일치해야만 동작하기 때문에, 기록이 누적될수록 cache miss가 계속 발생합니다.

**FAC-KV**는 코드 블록별 접근 빈도를 추적하고, 자주 읽히는 블록의 KV tensor를 GPU 메모리에 고정(pin)합니다. context 내 위치가 바뀌어도 cache hit를 유지하는 **position-agnostic** 캐시 레이어입니다.

```
Turn 1:  [system] + [file_A] + [query_1]               → file_A 전체 prefill 실행
Turn 2:  [system] + [history_1] + [file_A] + [query_2] → prefix 불일치; cache miss 발생
Turn N:  [system] + [history_1..N] + [file_A] + ...

                         ┌─────────────────────────┐
                         │     FAC-KV Cache Layer  │
                         │                         │
                         │  file_A  →  KV pinned ✓ │
                         │  file_B  →  KV pinned ✓ │
                         │  file_C  →  evicted     │
                         └─────────────────────────┘
                                      ↓
                     Turn 2..N에서 file_A prefill 생략
```

---

## 문제 의식

SWE-bench에서 SWE-Agent의 실행 궤적을 분석하면, **전체 token 소비의 대부분이 input token**이며 그 주된 원인은 repository 탐색 과정의 반복적인 파일 읽기입니다. 파일 내용이 바뀌지 않아도 앞에 대화 기록이 추가될 때마다 full prefill이 재실행됩니다.

vLLM의 내장 prefix caching은 요청 간 앞부분이 완전히 동일한 경우에만 동작합니다. multi-turn agentic 환경에서는 매 턴마다 이 조건이 깨집니다. FAC-KV는 이 공백을 해결합니다.

---

## 핵심 아이디어

| | vLLM Prefix Caching | **FAC-KV** |
|---|---|---|
| Cache 조건 | 앞부분 완전 일치 | 턴 간 접근 빈도 |
| 대화 기록 누적 시 | Cache miss | Cache hit 유지 |
| Context 내 위치 | 의존적 | **Position-agnostic** |
| 대상 workload | 단일 요청 | Long-horizon agentic task |

---

## 기술 스택

| 구성 요소 | 기술 |
|---|---|
| Coding Agent | [SWE-Agent](https://github.com/princeton-nlp/SWE-agent) |
| Inference Runtime | [vLLM](https://github.com/vllm-project/vllm) |
| 하드웨어 | NVIDIA RTX 5090 × 2 (VRAM 31.84 GB each) |
| 프로파일링 | `nvidia-smi`, NVML, vLLM metrics endpoint |
| 평가 | SWE-bench (repository 수준 코딩 태스크) |
| OS | Linux |

---

## 동작 방식

```
SWE-Agent
    │  tool_call: read_file("src/utils.py")
    ▼
FAC-KV Interceptor
    ├── access_count("src/utils.py") 증가
    ├── access_count > threshold?
    │       YES → 저장된 KV tensor 재사용 → prefill 생략
    │       NO  → 일반 prefill 실행 → KV tensor 저장
    ▼
vLLM Block Manager
    └── 자주 접근된 블록은 VRAM 상주, 나머지는 eviction 정책에 따라 제거
```

**Pinning 정책** 결정 기준:
- 접근 빈도 (주 신호)
- 최근성 (LRU decay)
- 블록 크기 대비 VRAM 압박 균형

---

## 기대 효과

- **Prefill latency 감소** — 반복 파일 읽기에서 재계산 제거
- **VRAM 대역폭 절약** — 중복 KV 연산 제거
- **Input token 비용 감소** — long-horizon task 전반
- 정량 지표: prefill time, memory bandwidth 사용률, end-to-end task latency

---

## 진행 현황

- [x] 문제 정의 및 선행 연구 조사
- [ ] 접근 빈도 프로파일러 구현 (SWE-Agent trajectory 분석)
- [ ] Hot block 탐지 및 pinning 정책 설계
- [ ] vLLM block manager 통합
- [ ] SWE-bench baseline 측정
- [ ] 평가 및 ablation study
- [ ] 논문 작성

---

## References
 
- Kwon et al. *Efficient Memory Management for Large Language Model Serving with PagedAttention.* SOSP, 2023.
- Yao et al. *ReAct: Synergizing Reasoning and Acting in Language Models.* ICLR, 2023.
- Vaswani et al. *Attention Is All You Need.* NeurIPS, 2017.
