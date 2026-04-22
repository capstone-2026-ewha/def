# FAC-KV: 관련 연구 및 차별점

> 2026 Spring Capstone Project — 연구트랙 중간 과제  
> **PMF 사전적 정의 / Related Work 3편 / 우리 팀 연구의 차별점**

---

## 1. PMF(Product-Market Fit)의 사전적 정의

**PMF**란 Marc Andreessen이 2007년에 처음 정형화한 개념으로,  
**"좋은 시장에서 그 시장을 만족시킬 수 있는 제품을 보유한 상태(being in a good market with a product that can satisfy that market)"** 를 의미한다.

보다 구체적으로는, 타겟 고객이 제품이 해결해주는 문제를 실제로 중요하게 여기고, 그 해결 방식에 충분히 만족하여 반복 사용하고 타인에게 추천까지 하는 상태를 가리킨다. PMF는 단순한 사용자 수나 매출 숫자가 아닌, **제품이 시장의 진짜 수요와 맞물려 있는가**를 나타내는 개념이다.

PMF를 정량적으로 측정하는 대표적인 방법으로는 Sean Ellis의 **"40% Rule"** 이 있다. "이 제품이 없어진다면 얼마나 실망하겠습니까?"라는 질문에 "매우 실망할 것이다"라고 응답하는 사용자가 40% 이상이면 PMF에 도달했다고 판단하는 기준이다. 이 외에도 코호트 리텐션율, NPS(Net Promoter Score), CAC 대비 LTV 비율 등 여러 지표가 PMF 달성 여부를 판단하는 데 활용된다.

PMF는 정적인 상태가 아니라 **지속적으로 검증하고 조정해야 하는 과정(iterative process)** 이며, 달성 이후에도 시장 변화에 따라 다시 흔들릴 수 있다. 스타트업에서는 "PMF 이전"과 "PMF 이후"가 전략의 근본적 전환점이 되는 만큼, 이를 조기에 정확히 측정하는 것이 매우 중요하다.

---

## 2. Related Work: 참고 논문 3편

### 논문 1. SWE-Pruner: Self-Adaptive Context Pruning for Coding Agents
> Wang et al., *arXiv:2601.16746*, 2026

코딩 에이전트의 SWE-Bench 실행 궤적을 분석했더니 전체 토큰 소비의 **76% 이상이 파일 읽기(read operation)** 에서 발생한다는 실증적 관찰에서 출발한 연구다. 기존 컨텍스트 압축 방법들이 perplexity 같은 고정 지표를 사용하거나 자연어 위주로 설계되어 코드의 구문적·논리적 구조를 손상시키는 문제를 지적한다.

해결책으로 에이전트가 파일을 읽기 전에 현재 목적(Goal Hint, 예: "focus on error handling")을 자연어로 명시하면, 0.6B 파라미터의 경량 neural skimmer가 해당 목표에 관련된 라인만 선별하여 에이전트에게 전달하는 **목표 기반 적응형 pruning** 방식을 제안한다. SWE-Bench Verified 기준 23~54%의 토큰 절감을 달성하면서 성공률을 유지하거나 오히려 개선하는 결과를 보였다.

**핵심 기여:** 에이전트의 현재 목적에 따라 동적으로 컨텍스트를 필터링하여 정보 밀도를 높이는 task-aware pruning 프레임워크.

---

### 논문 2. SWE-ContextBench: A Benchmark for Context Learning in Coding
> Zhu, Hu, Wu, *arXiv:2602.08316*, 2026

기존 코딩 에이전트 벤치마크(SWE-Bench 등)는 각 태스크를 독립적으로 평가하여 **에이전트가 이전 경험이나 컨텍스트를 얼마나 재활용(reuse)할 수 있는지를 전혀 측정하지 않는다**는 문제를 제기한다. 즉, "맞았느냐 틀렸느냐"만 보고, "어떻게 정보를 탐색하고 축적했느냐"는 보지 않는다.

이를 위해 GitHub 이슈와 PR 간의 실제 의존 관계를 기반으로 "연관 태스크 쌍"을 구성한 새 벤치마크를 제안한다. SWE-Bench Lite, Multilingual, Verified를 기반으로 1,100개 기본 태스크 + 376개 연관 태스크로 구성되며, 51개 저장소·9개 언어를 포함한다. 실험 결과 경험 검색과 요약이 성능과 효율성을 동시에 향상시킴을 보였다.

**핵심 기여:** 컨텍스트를 단순히 "잘 검색"하는 능력이 아닌, 과거 경험을 축적하고 재사용하는 능력을 분리해서 평가하는 프레임워크를 최초로 제시.

---

### 논문 3. CodeComp: Structural KV Cache Compression for Agentic Coding
> Chen et al., *arXiv:2604.10235*, 2026

코딩 에이전트가 긴 코드베이스를 처리할 때 KV 캐시가 주요 메모리 병목이 되는데, 기존의 attention score 기반 압축 방법들은 코드에서 의미적으로 중요한 구조적 토큰들(call site, branch condition, assignment 등)을 체계적으로 손실시킨다는 문제를 분석한다.

이를 해결하기 위해 **정적 프로그램 분석(static program analysis)** 을 LLM 추론 과정에 결합한다. Joern이 추출하는 Code Property Graph(CPG)를 prior로 활용하여, 코드 구조적으로 중요한 토큰을 보호하면서 KV 캐시를 압축한다. 추가 학습 없이(training-free) 동작하며, bug localization 및 code generation 벤치마크에서 attention-only 압축 방법들을 일관되게 능가했다.

**핵심 기여:** 코드의 구조(AST, 제어 흐름, 데이터 흐름)를 컨텍스트 압축 기준으로 직접 활용하는 최초의 KV 캐시 압축 프레임워크.

---

### 추가 참고 논문

| 논문 | 핵심 내용 |
|---|---|
| **SideQuest** (arXiv:2602.22603) | 장기 추론 에이전트에서 KV 캐시가 외부 검색 결과로 급격히 늘어나는 문제를, LRM 자신이 "보조 태스크(side quest)"로 KV 중요도를 판단하여 압축. 모델 자신의 추론 능력을 메모리 관리에 활용. |
| **Code Retrieval Survey** (preprints.org) | 렉시컬 검색(grep/ripgrep), 시맨틱 검색(RAG), LSP 통합, 에이전틱 검색, 멀티에이전트 등 코딩 에이전트의 코드 검색 기법 전반을 체계적으로 비교·분석한 탐색적 연구. |

---

## 3. 우리 팀 연구(FAC-KV)의 차별점

### 문제를 바라보는 시각 자체가 다르다

위 세 논문을 포함한 기존 연구들은 모두 **"어떤 토큰/라인/블록이 지금 덜 중요한가"** 라는 관점으로 접근한다. 현재 컨텍스트에서 무엇을 지울지 결정하는 것이 핵심이다.

- SWE-Pruner: goal hint 기반 라인 필터링 (더 잘 골라 넣자)
- CodeComp: 코드 구조 기반 KV 압축 (덜 중요한 것을 지우자)
- SideQuest: LRM 자신이 KV 중요도를 판단 (모델이 스스로 관리하자)

**FAC-KV는 다른 질문에서 출발한다.**  
"무엇을 지울까"가 아니라, **"무엇이 반복적으로 읽히는가"** 다.

코딩 에이전트가 실제로 낭비하는 비용의 본질은, 파일 내용이 전혀 바뀌지 않았는데도 대화 기록이 앞에 추가될 때마다 full prefill이 재실행된다는 점이다. 이는 압축이나 선택의 문제가 아니라, **위치(position) 의존성으로 인한 캐시 무효화** 문제다.

### 기존 prefix caching이 해결하지 못하는 지점

vLLM을 포함한 기존 시스템의 prefix caching은 요청 간 앞부분이 완전히 일치할 때만 동작한다. multi-turn agentic 환경에서는 매 턴마다 앞에 대화 기록이 추가되면서 이 조건이 깨진다.

기존 연구들도 이 문제를 인식하고 있지만, 해결 방향은 "더 적은 토큰을 넣자"(압축) 또는 "더 잘 골라 넣자"(선택)에 머문다.

| | 기존 연구 방향 | **FAC-KV** |
|---|---|---|
| 핵심 질문 | 무엇을 지울까 / 골라 넣을까 | 무엇이 반복적으로 읽히는가 |
| 접근 방식 | 압축 · 선택 | 접근 빈도 기반 KV pinning |
| Cache 조건 | 앞부분 완전 일치 (prefix) | 턴 간 접근 빈도 |
| 대화 기록 누적 시 | Cache miss | Cache hit 유지 |
| Context 내 위치 | 의존적 | **Position-agnostic** |
| 목표 | 토큰 수 감소 | **재계산 자체를 제거** |

FAC-KV는 **접근 빈도를 추적하여 자주 읽히는 코드 블록의 KV tensor를 GPU 메모리에 고정(pin)** 함으로써, context 내 위치가 바뀌어도 캐시 hit를 유지하는 **position-agnostic** 캐시 레이어를 제안한다.

### 우리 팀의 해석과 계획

> ✏️ **이 섹션은 팀이 직접 작성해야 합니다.**  
> 논문들을 읽으면서 직접 느낀 "이 연구의 아쉬운 점", 실험 과정에서 맞닥뜨린 고민, FAC-KV가 옳은 방향이라고 확신하게 된 계기, 그리고 PMF 관점에서 이 연구의 실제 수요를 어떻게 정의할 것인지를 팀 고유의 언어로 채워주세요.

아래 질문이 작성에 도움이 될 수 있습니다:
- FAC-KV가 해결하는 고통을 실제로 느끼는 사용자는 누구인가?
- 기존 압축/선택 방법 대신 FAC-KV를 선택해야 할 이유는 충분히 설득력 있는가?
- 실험적으로 검증하고자 하는 핵심 가설은 무엇인가?

---

*참고 논문 링크*
- [arXiv:2601.16746](https://arxiv.org/pdf/2601.16746) — SWE-Pruner
- [arXiv:2602.08316](https://arxiv.org/pdf/2602.08316) — SWE-ContextBench
- [arXiv:2604.10235](https://arxiv.org/pdf/2604.10235) — CodeComp
- [arXiv:2602.22603](https://arxiv.org/pdf/2602.22603) — SideQuest
- [preprints.org](https://www.preprints.org/frontend/manuscript/161dfc371faa1178c5426838021ec200/download_pub) — Code Retrieval Survey
