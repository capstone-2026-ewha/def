# def
2026-spring capstone project
# SynTree KV : 코딩 에이전트를 위한 AST 기반 KV 재사용 추론 최적화

> **코딩 에이전트를 위한 AST 기반 KV cache 재사용** — long-context agentic workflow에서 반복되는 코드 구조를 AST 지문으로 탐지하고, 중복 prefill 비용을 제거합니다.

[![Status](https://img.shields.io/badge/status-research-blue?style=flat-square)](.)
[![Agent](https://img.shields.io/badge/agent-OpenHands-orange?style=flat-square)](https://github.com/All-Hands-AI/OpenHands)
[![Runtime](https://img.shields.io/badge/runtime-vLLM-green?style=flat-square)](https://github.com/vllm-project/vllm)
[![Hardware](https://img.shields.io/badge/GPU-RTX%205090%20×2-76b900?style=flat-square&logo=nvidia)](.)
[![Benchmark](https://img.shields.io/badge/eval-SWE--bench%20Lite-purple?style=flat-square)](https://www.swebench.com)

---

## 팀 정보

| 항목 | 내용 |
|------|------|
| 팀명 | capstone-2026-ewha |
| 소속 | 이화여자대학교 |
| 지도교수 | 심재형 교수님 |
| 팀원 | 서혜원, 신은서, 이재린 |

---

## 개요

코딩 에이전트는 다중 턴 작업 과정에서 **같은 코드 파일을 반복적으로 읽습니다**. 대화 기록이 쌓일수록 동일한 코드 구조가 context에 반복 등장하지만, vLLM의 기존 prefix caching은 앞부분이 완전히 일치해야만 동작하기 때문에 매 턴마다 cache miss가 발생합니다.

**TreeHit**은 코드 토큰에 AST(Abstract Syntax Tree) 구조 레이블을 부여하고, **BLAKE3 해시 기반 AST 지문**으로 context 내 중복 코드 블록을 탐지합니다. 동일 지문의 KV cache를 재사용함으로써 반복 prefill 비용을 제거하고 **TTFT(Time-To-First-Token)**를 단축합니다.

```
Turn 1:  [system] + [obs: file_A] + [action]               → file_A prefill 실행 + KV 저장
Turn 2:  [system] + [history_1] + [obs: file_A] + [action] → AST 지문 일치 → KV 재사용 ✓
Turn N:  [system] + [history_1..N] + [obs: file_A] + ...

                    ┌──────────────────────────────────────┐
                    │         TreeHit Cache Layer          │
                    │                                      │
                    │  AST fingerprint(file_A) → KV hit ✓ │
                    │  AST fingerprint(file_B) → KV hit ✓ │
                    │  AST fingerprint(file_C) → miss      │
                    └──────────────────────────────────────┘
                                       ↓
                     Turn 2..N에서 중복 코드 블록 prefill 생략
```

---

## 문제 의식

SWE-bench Lite 기준으로 OpenHands 에이전트의 실행 궤적을 분석하면, **관찰(ObservationEvent) content의 대부분이 파일 읽기 결과**입니다. 파일 내용이 바뀌지 않아도 대화 기록이 앞에 추가될 때마다 full prefill이 재실행됩니다.

vLLM의 내장 prefix caching은 앞부분의 **토큰 시퀀스가 완전히 동일**한 경우에만 동작합니다. multi-turn agentic 환경에서는 매 턴마다 이 조건이 깨집니다. TreeHit은 **AST 구조 동일성**을 기준으로 삼아 이 공백을 해결합니다.

---

## 핵심 아이디어

| | vLLM Prefix Caching | **TreeHit** |
|---|---|---|
| Cache 조건 | 앞부분 토큰 시퀀스 완전 일치 | AST 지문(BLAKE3 해시) 일치 |
| 대화 기록 누적 시 | Cache miss | Cache hit 유지 |
| α-rename 적용 | 없음 | 변수명 정규화 → 더 높은 hit rate |
| 대상 workload | 단일 요청 | Long-horizon agentic task |
| 실측 hit rate | 4% TTFT 개선 | **36.2% hit rate (목표: 30%+ TTFT 개선)** |

---

## 기술 스택

| 구성 요소 | 기술 |
|---|---|
| Coding Agent | [OpenHands](https://github.com/All-Hands-AI/OpenHands) |
| Inference Runtime | [vLLM](https://github.com/vllm-project/vllm) |
| 모델 | Qwen3-Coder-30B-A3B-Instruct-FP8 |
| AST 파싱 | Tree-sitter (증분 파싱, Python) |
| 지문 생성 | BLAKE3 해시 (16자리) |
| 하드웨어 | NVIDIA RTX 5090 × 2 (VRAM 31.84 GB each) |
| 평가 | SWE-bench Lite (25개 이슈, 12개 레포) |
| OS | Linux |

---

## 아키텍처

```
새 턴 프롬프트 도착
    │
    ▼
텍스트 정제 (cat -n 줄 번호 등 제거)
    │
    ▼
Tree-sitter 증분 파싱 → AST 생성
    │
    ▼
자격 조건 필터링
    ├── 노드 타입 ∈ {FunctionDef, ClassDef, ImportStmt, CallExpr, AssignStmt}
    ├── AST 깊이 ≥ 2
    └── 토큰 수 ≥ 8
    │
    ▼
α-rename 정규화
    ├── vars_only: 변수·로컬 함수명 → VAR_0, VAR_1 ...  (보수적)
    └── all:       모든 identifier → VAR_n              (공격적)
    │
    ▼
BLAKE3 지문 생성 → SessionCacheTable 조회
    ├── Hit:  RoPE re-positioning → KV splice → prefill 생략
    └── Miss: 정상 prefill 실행 → KV tensor 저장
    │
    ▼
응답 생성
```

---

## 설치 및 실행 방법

### 사전 요구 사항

- CUDA 12.x 이상
- Python 3.10+
- NVIDIA GPU (VRAM 31GB+ 권장)

### 환경 구성

```bash
# 레포 클론
git clone https://github.com/capstone-2026-ewha/def.git
cd def

# conda 환경 생성 (vLLM 서빙용)
conda create -n treehit-vllm python=3.10
conda activate treehit-vllm
pip install vllm==0.8.x humming-kernels[cu13]

# conda 환경 생성 (trace 수집 및 분석용)
conda create -n treehit-openhands python=3.10
conda activate treehit-openhands
pip install open-hands-ai tree-sitter transformers blake3
```

### 모델 다운로드

```bash
# Qwen3-Coder-30B-A3B-FP8 모델 다운로드
huggingface-cli download Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 \
    --local-dir ./models/Qwen3-Coder-30B-A3B-Instruct-FP8
```

### vLLM 서버 실행

```bash
conda activate treehit-vllm
vllm serve ./models/Qwen3-Coder-30B-A3B-Instruct-FP8 \
    --tool-call-parser qwen3_coder \
    --enable-expert-parallel \
    --tensor-parallel-size 2 \
    --max-model-len 131072 \
    --port 8000
```

### SWE-bench Trace 수집

```bash
conda activate treehit-openhands
python scripts/collect_traces.py \
    --model-url http://localhost:8000/v1 \
    --output-dir ./traces/30b_run01 \
    --n-tasks 50
```

### AST Hit Rate 분석

```bash
# 4가지 조건 hit rate 분석 실행
python scripts/analyze_hitrate.py \
    --trace-dir ./traces/30b_run01 \
    --mode all          # all | vars_only
    --scope top_level   # top_level | all_nodes
```

---

## 실험 결과

### Hit Rate 분석 (48개 유효 trace 기준)

GO 기준: hit rate ≥ 25% **AND** token ratio ≥ 30%

| 조건 | Hit Rate | Token Ratio | 판정 |
|---|---|---|---|
| obs 단독 / vars_only / 최상위만 | **36.2%** | 36.9% | ✅ GO |
| obs 단독 / all / 최상위만 | 46.0% | 36.9% | ✅ GO |
| obs+action / vars_only / 최상위만 | 41.5% | 42.4% | ✅ GO |
| obs+action / all / 최상위만 | 51.1% | 42.4% | ✅ GO |

- **α-rename 순수 기여: +9.8%p** — exact-match 대비 변수명이 달라도 동일 구조 포착
- 권장 보수 수치: obs 단독 / vars_only / 최상위만 → **36.2% / 36.9%**

### TTFT Baseline 비교

| 조건 | 평균 TTFT |
|---|---|
| Vanilla (prefix caching 없음) | 31.2 ms |
| vLLM prefix caching | 29.9 ms (+4% 개선) |
| **TreeHit (구현 목표)** | **목표: 30%+ 개선** |

---

## 진행 현황

- [x] 문제 정의 및 선행 연구 조사
- [x] Qwen3-Coder-30B-A3B-FP8로 SWE-bench Lite trace 48개 수집
- [x] AST 지문 파이프라인 구현 (Tree-sitter + α-rename + BLAKE3)
- [x] Hit rate 분석 (4가지 조건) → **GO 판정**
- [x] Vanilla / vLLM prefix caching TTFT baseline 측정
- [ ] SessionCacheTable 구현 (PyTorch KV splice 훅)
- [ ] RoPE re-positioning 모듈 구현
- [ ] AST 인식 KV 재사용 통합 실험
- [ ] 최종 TTFT 비교 (vanilla / prefix caching / TreeHit)
- [ ] 논문 작성

---

## 레포 구조

```
def/
├── README.md
├── scripts/
│   ├── collect_traces.py     # SWE-bench trace 수집
│   ├── analyze_hitrate.py    # AST hit rate 분석 (v3_5)
│   └── measure_ttft.py       # TTFT 측정 (vanilla / prefix caching)
├── src/
│   ├── ast_fingerprint.py    # Tree-sitter 파싱 + α-rename + BLAKE3
│   ├── session_cache.py      # SessionCacheTable (구현 중)
│   └── rope_reposition.py    # RoPE re-positioning (구현 중)
├── traces/                   # SWE-bench 실행 궤적 (gitignore)
├── models/                   # 모델 가중치 (gitignore)
└── results/
    ├── hitrate_v3_5.json
    └── ttft_baseline.json
```

---

## 라이선스

본 프로젝트는 연구 목적으로 작성되었습니다. 코드는 [MIT License](LICENSE) 하에 배포됩니다.

---

## References

- Kwon et al. *Efficient Memory Management for Large Language Model Serving with PagedAttention.* SOSP, 2023.
- Gim et al. *PromptCache: Modular Attention Reuse for Low-Latency Inference.* MLSys, 2024.
- Yao et al. *CacheBlend: Fast Large Language Model Serving for RAG with Cached Knowledge Fusion.* EuroSys, 2025.
- Li et al. *SnapKV: LLM Knows What You are Looking for Before Generation.* NeurIPS, 2024.
- Yao et al. *DeFT: Decoding with Flash Tree-attention for Efficient Tree-structured LLM Inference.* ICLR, 2024.

