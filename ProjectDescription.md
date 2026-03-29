<a id="team-14"></a>
## Team 14 def

| 항목 | 내용 |
|------|------|
| 프로젝트명 | 로컬 환경에서의 Agentic AI 병목 분석 및 성능 최적화: Apple silicon 온디바이스를 중심으로 |
| 서비스명(브랜드) | |
| 트랙 | 연구 |
| 팀명 | def |
| 팀구성 | 서혜원, 신은서, 이재린 |
| 팀지도교수 | 심재형 교수님 |
| 무엇을 만들고자 하는가 | - 로컬 워크로드를 분석하고 병목을 스스로 해결하는 에이전트 기반 최적화 프레임워크 설계 및 구현<br>- Experimental Evaluation (논문 핵심): 최적화 적용 전/후의 성능(TPS, Latency, Energy Efficiency) 비교 데이터와 다양한 워크로드 시나리오(단일 추론 vs 멀티태스킹)에서의 자원 효율성 검증 보고서 |
| 고객 (누구를 위해) | - Agent AI 시스템 설계자 및 연구자: 클라우드 의존도를 낮추고 로컬 기기(Edge Device)의 하드웨어 잠재력을 끝까지 끌어올려야 하는 엔지니어<br>- Agent AI 사용자: 외부 클라우드 서버에 데이터를 보내지 않고, Mac mini 같은 로컬 기기에서 개인화된 AI 모델을 안전하게 돌리고 싶은 개인 및 기업 |
| Pain Point (해결할 문제) | - 리소스 고갈:LLM(거대언어모델) 실행 시 메모리 점유율이 급증하여 시스템이 멈추거나 느려지는 현상<br>- 예측 불가능한 병목(Dynamic Bottleneck):워크로드의 성격(연산 중심 vs 메모리 중심)에 따라 시스템의 어느 부분에서 병목이 생길지 실시간으로 파악하기 어려움<br>- 메모리 고갈(Memory Issue):특히 LLM 구동 시 제한된 통합 메모리(Unified Memory) 용량을 초과할 때 생기는 다양한 문제점 |
| 사용 기술 | - Agentic Monitoring Loop : 에이전트가 시스템 API를 통해 CPU/GPU 등 점유율 및 전력 소모량을 실시간 관찰하고 대응 전략을 결정<br>- 현재 실행 중인 워크로드에 대한 실시간으로 분류하는 분석 알고리즘 |
| 기대 효과 | - 효율성 극대화:동일 하드웨어 대비 AI 추론 성능(Throughput) 및 응답 속도(Latency)의 유의미한 향상.<br>- 시스템 안정성:메모리 이슈로 인한 시스템 다운 방지 및 멀티태스킹 환경에서의 부드러운 사용자 경험 유지.<br>- 에너지 효율: 불필요한 연산 낭비를 줄여 전력 소모 최적화 및 발열 제어 |
| GitHub Repo | [https://github.com/capstone-2026-ewha/def](https://github.com/capstone-2026-ewha/def) |
| Team Ground Rule | [https://github.com/capstone-2026-ewha/def/blob/main/Team_Ground_Rule.md](https://github.com/capstone-2026-ewha/def/blob/main/Team_Ground_Rule.md) |
| 최종수정일 | 2026-3-12 |
