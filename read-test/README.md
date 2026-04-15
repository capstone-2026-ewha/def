# Coding Agent Token Consumption Analysis

코딩 에이전트가 소비하는 토큰 중 "코드 탐색(read)" 비중을 분석하는 연구.

## 목적

코딩 에이전트의 token consumption 패턴을 분석하여, KV cache 재사용 최적화의 motivation을 제공한다.

가설 H1: **코딩 에이전트가 소비하는 input 토큰의 대부분은 코드 read에서 온다.**

## 환경

- Agent: SWE-agent 1.1.0
- Model: Qwen2.5-Coder-7B-Instruct
- Serving: vLLM (OpenAI-compatible API)
- GPU: NVIDIA RTX 5090
- OS: Ubuntu

## 디렉토리 구조

- `scripts/`: trajectory 분석 & 시각화 스크립트
- `experiments/toy_repo/`: 에이전트가 고칠 버그 있는 toy 코드
- `results/run_simple_01/`: 첫 실행 결과
  - `token_analysis.json`: 분류 결과
  - `*.png`: 플롯 4개
  - `*.patch`: 에이전트 출력 patch
  - `*.traj`: 원본 trajectory
  - `config.yaml`: SWE-agent 실행 설정

## 실행 방법

### 1. 환경 준비
- vLLM 서버 (Qwen2.5-Coder-7B, port 8002)
- SWE-agent: https://github.com/SWE-agent/SWE-agent

### 2. 실험 실행
```bash
sweagent run \
    --config config/bash_only.yaml \
    --agent.model.name="hosted_vllm/qwen2.5-coder-7b" \
    --agent.model.api_base="http://localhost:8002/v1" \
    --env.repo.type=local \
    --env.repo.path=<experiments/toy_repo 경로> \
    --problem_statement.type=text \
    --problem_statement.id="toy_simple_01" \
    --problem_statement.text="..." \
    --output_dir=<결과 경로>
```

### 3. 분석
```bash
python scripts/analyze_tokens.py <trajectory.traj>
python scripts/plot_breakdown.py <token_analysis.json>
```

## 결과 (toy task)

`results/run_simple_01/04_headline_summary.png` 참고.
