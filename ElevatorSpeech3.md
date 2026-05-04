# FAC-KV: Frequently Accessed Code KV Cache Reuse

> **코딩 에이전트를 위한 position-agnostic KV cache 재사용** — long-context agentic workflow에서 반복적인 prefill 비용을 제거합니다.

[![Status](https://img.shields.io/badge/status-research-blue?style=flat-square)](.)
[![Agent](https://img.shields.io/badge/agent-SWE--Agent-orange?style=flat-square)](https://github.com/princeton-nlp/SWE-agent)
[![Runtime](https://img.shields.io/badge/runtime-vLLM-green?style=flat-square)](https://github.com/vllm-project/vllm)
[![Hardware](https://img.shields.io/badge/GPU-RTX%205090%20×2-76b900?style=flat-square&logo=nvidia)](.)
[![Benchmark](https://img.shields.io/badge/eval-SWE--bench-purple?style=flat-square)](https://www.swebench.com)

---

## 문제

코딩 에이전트는 **Coding Agent → Serving Layer → LLM**, 이렇게 세 개의 레이어를 거쳐 동작합니다.

> **Serving Layer**: 모델을 효율적으로 돌려주는 중간 소프트웨어 (예: vLLM, Ollama)

코딩 에이전트가 파일을 읽을 때마다, Serving Layer는 그 내용을 LLM이 이해할 수 있는 형태로 매번 새로 계산합니다. 이 계산 결과가 바로 **KV cache**입니다. 문제는 같은 파일을 반복해서 읽으며 이 계산을 매번 처음부터 다시 한다는 겁니다. 이는 전체 토큰 소모의 대부분이 이 파일 읽기 작업에서 발생한다는 실험 결과로 입증할 수 있습니다.

---

## 해결 아이디어

자주 참조되는 KV cache 블록을 메모리에 고정해서, 같은 코드를 반복해서 prefill하지 않도록 합니다. 에이전트가 파일을 다시 읽더라도, Serving Layer에서 이미 계산된 결과를 재사용하는 방식입니다.

---

## 구현

저희는 자주 쓰이는 KV cache 블록을 메모리에서 지워지지 않도록 고정하는 **Pinning 정책**을 구현합니다.

에이전트나 모델 자체는 건드리지 않고, **Serving Layer만 수정**합니다. Serving Layer로는 오픈소스로 공개된 vLLM을 사용하는데, vLLM 내부의 Block Manager는 기본적으로 **LRU 정책**(가장 오랫동안 사용되지 않은 블록을 먼저 제거하는 방식)으로 캐시를 관리합니다. 저희는 여기에 **pin 플래그**를 추가해, 자주 쓰이는 블록이 제거(evict)되지 않도록 이 로직을 수정합니다.

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
vLLM Block Manager (커스터마이징)
    └── pin 플래그가 설정된 블록은 VRAM 상주, 나머지는 LRU eviction
```

| 구성 요소 | 기술 |
|---|---|
| 에이전트 프레임워크 | SWE-Agent |
| 추론 런타임 | vLLM (block manager 커스터마이징) |
| 타겟 하드웨어 | NVIDIA RTX 5090 × 2 (VRAM 31.84 GB each, Linux) |
| 프로파일링 | nvidia-smi, NVML, vLLM metrics endpoint |
| KV Cache 제어 | vLLM block manager 커스터마이징 + position-agnostic pinning 정책 |

---

## 기대 효과 (MVP)

최종 결과물은 **KV Cache Pinning 정책이 적용된 커스텀 vLLM 서빙 레이어**입니다.

이를 통해 코딩 에이전트 실행 시 **prefill latency 감소**와 **토큰 처리 비용 절감**을 달성하는 것이 목표입니다. SWE-bench를 기준으로 태스크 성능을 유지하면서 서빙 효율을 높이는 것을 검증합니다.

---

## 차별성

기존 KV cache 연구는 압축·양자화나 prefix 캐싱 확장에 머물렀습니다. 저희는 **serving layer의 block manager를 직접 커스터마이징**해, 같은 코드 블록이 context의 어느 위치에 등장하든 KV를 재사용할 수 있는 **position-agnostic pinning 정책**을 제안합니다.

### Coding Agent KV/Context 최적화 기법 비교

| 축 | CodeComp | SWE-Pruner | KVFlow | **FAC-KV (ours)** |
|---|---|---|---|---|
| **분류** | KV cache 압축 (eviction) | Context pruning (token-level 입력 압축) | KV cache 관리 (workflow-aware eviction + prefetch) | KV cache 재사용 (frequency-based pinning) |
| **타겟 문제** | 긴 코드베이스에서 KV cache가 추론 병목 — attention-only 압축은 구조적으로 중요한 토큰을 버림 | 긴 interaction context로 인한 API 비용·latency 문제 — PPL 기반 압축은 코드의 syntactic/logical 구조 깨뜨림 | LRU eviction이 미래 agent 호출을 예측 못해서 재사용 직전에 cache 버림 | 자주 접근되는 코드 블록의 반복적 prefill 비용 (token 소비) |
| **핵심 아이디어** | Joern으로 추출한 Code Property Graph prior로 구조적으로 중요한 토큰 보호 | 현재 task에 대한 explicit goal hint로 0.6B neural skimmer가 line 단위 선택 | Agent Step Graph + steps-to-execution 값으로 미래 활성화 시점 예측 | 접근 빈도(frequency) 기반으로 hot code block의 KV를 GPU에 핀, position-agnostic 재사용 |
| **개입 위치** | 추론 중 KV cache (attention 내부) | 입력 단계 (file read 결과 가공) | KV cache eviction policy + CPU↔GPU prefetch | KV cache 저장/재사용 레이어 |

---

## Related Work

- **SWE-Pruner**: Self-Adaptive Context Pruning for Coding Agents (arXiv:2601.16746)
- **KVFlow**: Efficient Prefix Caching for Accelerating LLM-Based Multi-Agent Workflows
- **CodeComp**: Structural KV Cache Compression for Agentic Coding (arXiv:2604.10235)

---

## 진행 현황

- [x] 문제 정의 및 선행 연구 조사
- [x] 가설 검증 실험 (toy repo — read/search 토큰 비중 확인)
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
