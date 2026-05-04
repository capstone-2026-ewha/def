# FAC-KV: Frequently Accessed Code KV Cache Reuse

> **프로젝트 한 줄 요약**
> 코딩 에이전트가 자주 참조하는 코드 블록의 KV cache를 vLLM 메모리에 고정(pinning)하여, 반복적인 prefill 비용을 제거하기 위해, vLLM block manager를 커스터마이징한 position-agnostic pinning 정책을 제안합니다.

[![Status](https://img.shields.io/badge/status-research-blue?style=flat-square)](.)
[![Agent](https://img.shields.io/badge/agent-SWE--Agent-orange?style=flat-square)](https://github.com/princeton-nlp/SWE-agent)
[![Runtime](https://img.shields.io/badge/runtime-vLLM-green?style=flat-square)](https://github.com/vllm-project/vllm)
[![Hardware](https://img.shields.io/badge/GPU-RTX%205090%20×2-76b900?style=flat-square&logo=nvidia)](.)
[![Benchmark](https://img.shields.io/badge/eval-SWE--bench-purple?style=flat-square)](https://www.swebench.com)

---

## 1. 문제 — Pain Point

코딩 에이전트는 일반적으로 **Coding Agent → Serving Layer → LLM**, 세 개의 레이어를 거쳐 동작합니다.

에이전트가 파일을 읽을 때마다, Serving Layer는 그 내용을 LLM이 이해할 수 있는 형태로 매번 새로 계산합니다. 이 계산 결과가 바로 **KV cache** 입니다.

문제는 **같은 파일을 반복해서 읽으며 이 계산을 매번 처음부터 다시 한다**는 점이며, 코딩 에이전트 워크로드에서 전체 토큰 소모의 상당 부분이 이 반복적인 파일 읽기 단계에서 발생합니다.

> **Serving Layer** = 모델을 효율적으로 돌려주는 중간 소프트웨어 (예: vLLM, Ollama 등)

---

## 2. 해결 아이디어

자주 참조되는 KV cache 블록을 메모리에 **고정(pin)** 하여, 같은 코드를 반복적으로 prefill하지 않도록 합니다.

에이전트가 동일 파일을 다시 읽더라도, serving layer에 이미 저장된 KV cache를 **위치에 종속되지 않고(position-agnostic)** 재사용하는 방식입니다.

---

## 3. 기술 / 구현

자주 쓰이는 KV cache 블록을 메모리에서 지워지지 않도록 고정하는 **Pinning 정책**을 구현합니다.

이때 세 레이어 중 **에이전트나 모델 자체는 건드리지 않고, serving layer만 수정**합니다. Serving layer로는 오픈소스 vLLM을 사용합니다.

vLLM 내부의 **Block Manager**는 기본적으로 **LRU 정책**(가장 오랫동안 사용되지 않은 블록을 먼저 제거)으로 캐시를 관리합니다. 저희는 여기에 **`pin` 플래그**를 추가하여, 자주 쓰이는 블록이 evict되지 않도록 로직을 수정합니다.

### 스택 구성

| 구분 | 사용 기술 |
|---|---|
| 에이전트 프레임워크 | **SWE-Agent** |
| 추론 런타임 | **vLLM** (block manager 커스터마이징) |
| 타겟 하드웨어 | **NVIDIA RTX 5090 × 2** (VRAM 31.84GB × 2, Linux) |
| 프로파일링 | `nvidia-smi`, NVML, vLLM metrics endpoint |
| KV Cache 제어 | vLLM block manager 커스터마이징 + position-agnostic pinning 정책 |

---

## 4. MVP / 배포

최종 결과물은 **KV Cache Pinning 정책이 적용된 커스텀 vLLM 서빙 레이어**입니다.

이를 통해 코딩 에이전트 실행 시,

- **Prefill latency 감소**
- **토큰 처리 비용 절감**

을 달성하는 것이 목표이며, **SWE-bench**를 기준으로 태스크 성능을 유지하면서 서빙 효율을 높이는 것을 검증합니다.

---

## 5. 차별성 

기존 KV cache 연구는 **압축·양자화**나 **prefix caching 확장**에 머물러 있었습니다.

저희는 serving layer의 **block manager를 직접 커스터마이징**하여, **같은 코드 블록이 context의 어느 위치에 등장하든 KV를 재사용할 수 있는 pinning 정책**을 제안합니다.

| 축 | CodeComp | SWE-Pruner | KVFlow | **FAC-KV (네 거)** |
|---|---|---|---|---|
| **분류** | KV cache 압축 (eviction) | Context pruning (token-level 입력 압축) | KV cache 관리 (workflow-aware eviction + prefetch) | **KV cache 재사용 (frequency-based pinning)** |
| **타겟 문제** | 긴 코드베이스에서 KV cache가 추론 병목 — attention-only 압축은 구조적으로 중요한 토큰을 버림 | 긴 interaction context로 인한 API 비용·latency 문제 — PPL 기반 압축은 코드의 syntactic/logical 구조를 깨뜨림 | LRU eviction이 미래 agent 호출을 예측 못해서 재사용 직전에 cache를 버림 | **자주 접근되는 코드 블록의 반복적 prefill 비용 (token 소비)** |
| **핵심 아이디어** | Joern으로 추출한 Code Property Graph prior로 구조적으로 중요한 토큰 보호 | 현재 task에 대한 explicit goal hint로 0.6B neural skimmer가 line 단위 선택 | Agent Step Graph + steps-to-execution 값으로 미래 활성화 시점 예측 | **접근 빈도(frequency) 기반으로 hot code block의 KV를 GPU에 pin, position-agnostic 재사용** |
| **개입 위치** | 추론 중 KV cache (attention 내부) | 입력 단계 (file read 결과 가공) | KV cache eviction policy + CPU↔GPU prefetch | **KV cache 저장/재사용 레이어** |

---

## 6. Related Work

- **SWE-Pruner**: Self-Adaptive Context Pruning for Coding Agents
- **KVFlow**: Efficient Prefix Caching for Accelerating LLM-Based Multi-Agent Workflows
- **CodeComp**: Structural KV Cache Compression for Agentic Coding
