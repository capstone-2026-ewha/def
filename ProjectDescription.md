<a id="team-14"></a>
## Team 14 def

| 항목 | 내용 |
|------|------|
| 프로젝트명 | 로컬 LLM 기반 Coding Agent에서 Frequently Accessed Code 블록의 KV Cache 재사용을 통한 Token 소비 최적화 |
| 서비스명(브랜드) | |
| 트랙 | 연구 |
| 팀명 | def |
| 팀구성 | 서혜원, 신은서, 이재린 |
| 팀지도교수 | 심재형 교수님 |
| 무엇을 만들고자 하는가 | 코딩 에이전트가 레포지토리를 탐색하는 과정에서 반복적으로 읽히는 코드 블록을 추적하고, 해당 블록의 KV Cache를 context 내 위치에 무관하게 메모리에 상주시켜 재사용함으로써 prefill 비용을 줄이는 최적화 레이어를 vLLM 기반 로컬 환경에 구현한다.
- 코드 블록별 read frequency 프로파일러<br>
- Hot block 판별 및 KV Cache pinning 정책<br>
- 로컬 LLM 추론 파이프라인과의 통합<br>|
| 고객 (누구를 위해) | - 로컬 LLM으로 코딩 에이전트를 운용하는 개인 개발자 / 연구자<br> - API 비용 대신 온디바이스 추론을 선택한 팀 (스타트업, 보안 민감 조직)<br> - NVIDIA GPU 기반 자체 인프라 운용 조직<br>|
| Pain Point (해결할 문제) | - 코딩 에이전트의 토큰 소비에서 input token이 압도적으로 지배적이며, 토큰 캐싱을 적용해도 그 구조는 유지된다. 핵심 원인은 코드 탐색 패턴에 있다.<br>- SWE-Agent를 포함한 코딩 에이전트는 파일 접근 시 전체 파일 내용을 읽는 whole-file reading 방식을 채택하는데, 매 스텝마다 대화 히스토리가 누적되면서 같은 파일을 반복 읽어도 prefix가 달라져 기존 prefix caching이 무력화된다.<br>->에이전트가 같은 파일을 반복 탐색할 때마다 full prefill이 재발생하고, 로컬 환경에서는 이것이 직접적인 지연 시간 + VRAM 대역폭 낭비로 이어짐 |
| 사용 기술 | - 에이전트 프레임워크 : SWE-Agent<br> - 추론 런타임 : vLLM<br>- 타겟 하드웨어 : NVDIA RTX 5090X2(VRAM 31.84GBX2, Linux)<br>- 프로파일링 : nvida-smi, nvml, vLLM metrics endpoint<br>- KV Cache 제어 : vLLM block manager 커스터마이징+위치에 종속되지 않는 pinning 정책<br>|
| 기대 효과 | - Prefill latency 감소 : 자주 읽히는 코드 블록의 KV Cache를 재계산 없이 재사용<br>- VRAM 대역폭 절약 — RTX 5090 듀얼 환경에서 중복 prefill로 인한 메모리 낭비 제거<br>- 총 토큰 소비 감소 : 반복 read에서 발생하는 input token 중복 제거<br> -Long context 환경 대응 : 히스토리가 누적되어도 캐시 hit 유지<br>|
| GitHub Repo | [https://github.com/capstone-2026-ewha/def](https://github.com/capstone-2026-ewha/def) |
| Team Ground Rule | [https://github.com/capstone-2026-ewha/def/blob/main/Team_Ground_Rule.md](https://github.com/capstone-2026-ewha/def/blob/main/Team_Ground_Rule.md) |
| 최종수정일 | 2026-4-15 |
