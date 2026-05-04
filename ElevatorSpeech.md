# FAC-KV Elevator Speech
> Team 14 def | 서혜원, 신은서, 이재린 | 지도교수: 심재형 교수님

---

## 1. 문제 — 고객과 Pain Point (20초)

**고객:** 로컬 GPU 환경(온디바이스)에서 LLM 기반 코딩 에이전트를 운용하는 개발자·연구자.  
API 비용 대신 자체 인프라를 선택한 팀(스타트업, 보안 민감 조직 포함).

**Pain Point:**  
코딩 에이전트는 레포지토리를 탐색하면서 같은 파일을 반복해서 읽는다.  
파일 내용이 바뀌지 않아도, 대화 기록이 앞에 쌓일 때마다 기존 prefix caching 조건이 깨져 **매번 full prefill이 재실행**된다.  
로컬 환경에서 이는 곧 **지연 시간 증가 + VRAM 대역폭 낭비**로 직결된다.

---

## 2. 해결 아이디어 (20초)

**"자주 읽히는 코드 블록의 KV Cache를 위치에 상관없이 GPU에 고정해두자."**

코드 블록별 접근 빈도를 추적하고, 일정 임계치를 넘은 블록의 KV tensor를 VRAM에 pin한다.  
대화 기록이 누적되어 context 내 위치가 바뀌어도 cache hit를 유지하는 **position-agnostic KV cache 재사용 레이어** — 이것이 FAC-KV다.

---

## 3. 기술 및 구현 (30초)

SWE-Agent가 `read_file("src/utils.py")`를 호출하면, FAC-KV interceptor가 해당 블록의 접근 횟수를 증가시킨다.  
임계치를 초과하면 저장된 KV tensor를 바로 재사용해 prefill을 생략하고, 미달이면 일반 prefill 후 KV를 저장한다.  
vLLM block manager를 커스터마이징해 hot block을 VRAM에 상주시키고, 나머지는 접근 빈도·최근성·블록 크기를 고려한 eviction 정책으로 관리한다.

| 구성 요소 | 기술 |
|---|---|
| 코딩 에이전트 | SWE-Agent |
| 추론 런타임 | vLLM (block manager 커스터마이징) |
| 하드웨어 | NVIDIA RTX 5090 × 2 (VRAM 31.84 GB each) |
| 프로파일링 | nvidia-smi, NVML, vLLM metrics endpoint |
| 평가 | SWE-bench |

---

## 4. MVP 및 배포 (20초)

**만들어질 것:**
- 코드 블록 접근 빈도 프로파일러 (SWE-Agent trajectory 분석)
- Hot block 탐지 및 KV pinning 정책 모듈
- vLLM block manager 통합 레이어
- SWE-bench 기반 성능 측정: prefill latency, VRAM 대역폭, end-to-end task latency

**배포 방식:** 로컬 vLLM 환경에 플러그인 형태로 통합. RTX 5090 듀얼 서버에서 SWE-bench 태스크를 기준으로 baseline 대비 성능 비교 실험.

---

## 5. 차별성 (10초)

기존 연구들은 모두 **"무엇을 지울까"(압축·선택)** 를 묻는다.  
FAC-KV는 **"무엇이 반복적으로 읽히는가"** 를 묻는다.  
압축률이나 선택 정확도 경쟁이 아닌, **재계산 자체를 없애는** 방향의 접근이다.

| | 기존 방법 | FAC-KV |
|---|---|---|
| 핵심 질문 | 무엇을 지울까 | 무엇이 반복 읽히는가 |
| Cache 조건 | prefix 완전 일치 | 접근 빈도 기반 |
| 대화 기록 누적 시 | cache miss | cache hit 유지 |
| 접근 방식 | 압축·선택 | **position-agnostic pinning** |

---

## (발표 외 기재 항목) Related Work

### 참고 논문 3편

**1. SWE-Pruner** (arXiv:2601.16746, 2026)  
전체 토큰의 76%가 파일 읽기에서 발생한다는 실증에서 출발. Goal Hint 기반 neural skimmer로 관련 라인만 선별해 23~54% 토큰 절감. → **"더 잘 골라 넣자"** 는 방향.

**2. SWE-ContextBench** (arXiv:2602.08316, 2026)  
기존 벤치마크가 경험 재사용 능력을 평가하지 않는다는 문제 제기. GitHub 이슈·PR 의존 관계 기반 1,100개 태스크 + 376개 연관 태스크 벤치마크 제안. → **평가 프레임워크** 제시.

**3. CodeComp** (arXiv:2604.10235, 2026)  
attention 기반 압축이 call site, branch condition 등 구조적 토큰을 손실시킨다는 문제 분석. Code Property Graph(CPG) prior를 활용한 training-free KV 압축. → **"구조를 보존하며 지우자"** 는 방향.

### 우리 팀 연구의 차별성·독특성·우수성

세 논문 모두 문제의 원인을 **"컨텍스트 안에 불필요한 내용이 너무 많다"** 로 정의한다.  
FAC-KV는 원인을 **"position 변화로 인해 캐시가 매번 무효화된다"** 로 다르게 정의한다.

vLLM의 기본 prefix caching은 앞부분이 완전히 일치해야만 동작하는데, multi-turn agentic 환경에서는 매 턴마다 대화 기록이 추가되며 이 조건이 깨진다. 압축을 아무리 잘 해도 이 구조적 문제는 해결되지 않는다.

FAC-KV는 접근 빈도라는 **에이전트 행동 패턴** 을 신호로 삼아, 위치 변화에 독립적인 캐시 레이어를 추가함으로써 기존 연구들이 건드리지 않은 공백을 메운다. 이 접근은 압축 방법과 상호 배타적이지 않으며, 기존 최적화 위에 추가로 적용 가능한 레이어다.

---

*GitHub Repo: https://github.com/capstone-2026-ewha/def*
