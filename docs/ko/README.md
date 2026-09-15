# Apply Scout

[English](../en/README.md) · **한국어**

**내 경력은 Markdown으로. 채용 탐색은 AI로. 지원 계획은 한눈에.**

프로필과 조사할 사이트 목록을 넣으면 Codex 또는 Claude Code가 공고를 조사하고,
지원 일정표와 공고별 적합성 분석을 Markdown으로 만듭니다.

```text
profile.md + portfolio.md (선택) + experience.md (선택) + sources.md
                             ↓
                      Codex / Claude Code
                             ↓
                 apply-tracker.md → jobs/*.md
```

**현재 버전: v0.1.0 / CLI MVP.** 실행 버튼이 있는 웹 화면은 후속 범위입니다.
AI의 공고 조사·판단과 프로그램의 검증·정렬·파일 생성을 분리했습니다.

영어·한국어 문서와 번역 예시를 제공합니다. 현재 CLI 안내와 자동 생성 보고서의 고정 문구는 한국어입니다.

## 결과 먼저 보기

- [지원 일정표 예시](examples/output/apply-tracker.md)
- [입력 프로필 예시](examples/inputs/profile.md)
- [조사 데이터 예시](../../examples/research.json)

예시는 모두 가상 회사·공고이며 실제 채용 정보가 아닙니다.

## 빠르게 시작하기

Python 3.10 이상이 필요합니다. 별도 Python 패키지는 설치하지 않습니다.
자동 조사에는 로그인된 Codex CLI 또는 Claude Code와 웹 검색 접근이 필요합니다.
AI 도구의 계정 사용량·과금 정책이 적용됩니다.

```sh
git clone https://github.com/sebnson/apply-scout.git
cd apply-scout
python3 -m apply_scout init
```

생성된 `inputs/profile.md`에 직무·경력·기술·희망 조건을 쓰고,
`inputs/sources.md`의 예시 주소를 실제 조사할 채용 사이트 주소로 바꾸세요.
포트폴리오와 상세 경력 파일은 선택입니다.

```sh
# 둘 중 설치·로그인한 도구 하나를 선택
python3 -m apply_scout run --agent codex
python3 -m apply_scout run --agent claude
```

완료되면 `output/apply-tracker.md`를 여세요. 회사명을 클릭하면 해당 공고 분석으로 이동합니다.
같은 회사의 다른 직무는 별도 파일로 생성합니다.

### AI 없이 출력 형식 체험

```sh
python3 -m apply_scout render examples/research.json --output output/demo --today 2026-09-15
```

### Codex·Claude 대화에서 직접 실행

이 저장소를 도구에서 열고 다음과 같이 요청해도 됩니다.

> AGENTS.md와 docs/research-instructions.md에 따라 inputs의 프로필과 사이트를 조사해 줘.
> output/research.json을 작성하고 apply_scout render로 지원 일정표를 만들어 줘.

완전한 입력·출력 규격을 담은 프롬프트는 다음 명령으로 확인합니다.

```sh
python3 -m apply_scout prompt
```

## 만들어지는 파일

```text
output/
  apply-tracker.md     # 마감일 순 목록, 지원 목표일, 상태·메모
  jobs/<공고 ID>.md    # 직무 요약, 요구사항↔경험 근거, 보완점, 지원 준비
  research.json       # 가장 최근 AI 조사 결과
  .state.json         # 이전 공고와 지원 상태를 유지하는 기록
```

- 공고 ID는 원문 URL에서 만듭니다. 추적용 URL 매개변수는 제거합니다.
- 마감된 공고, 이번 조사에서 재확인하지 못한 공고를 구분합니다.
- 날짜 없는 공고는 상시채용 / 미기재 / 확인 불가로 구분합니다.
- 권장 지원일은 마감일에서 기본 2일을 뺀 날짜이며, 이미 지났으면 오늘로 표시합니다.
- 마감 시각과 시간대는 개별 분석의 원문 안내를 함께 확인하세요.
- 주당 지원 가능량이나 항목별 소요 시간을 고려하는 자동 일정 배분은 아직 없습니다.

## 지원 기록 이어 쓰기

`apply-tracker.md` 표의 **상태·메모 열**을 직접 수정하세요. 다음 실행에도 보존됩니다.
상태가 `지원 완료`, `지원 안 함`, `합격`, `불합격`이면 준비 계획에서 제외합니다.
표의 열·공고 링크는 유지하고 메모 안의 `|` 문자는 `&#124;`로 적으세요.

지원표와 개별 분석의 **내 메모** 영역도 유지됩니다. HTML 주석 경계 사이에 작성하세요.
자동 생성 영역의 다른 수정은 다음 실행에서 갱신됩니다.
`output/.state.json`을 삭제하면 이전 공고 기록을 이어갈 수 없습니다.
한 출력 폴더에는 한 번에 한 실행만 사용하세요.

```sh
python3 -m apply_scout run --agent codex --limit 10 --buffer-days 3 --timeout 900
# 새 AI 조사 없이 기존 결과로 일정 다시 계산
python3 -m apply_scout render output/research.json
```

## 매칭 기준

| 평가 | 의미 |
|---|---|
| 높음 | 주요 필수요건과 관련된 구체적인 경험 근거가 충분함 |
| 보통 | 관련 경험은 있으나 일부 요건의 보완 또는 확인이 필요함 |
| 낮음 | 명시적인 필수 조건과 충돌하는 근거가 있음 |
| 판단 보류 | 공고·프로필의 정보가 부족함 |

프로필에 없는 내용은 ‘경험 없음’으로 단정하지 않습니다. 모든 평가에는 공고 원문과
프로필 파일·섹션에 기반한 설명을 요구합니다. 평가는 AI의 판단이며 합격 예측이 아닙니다.

## 조사 한계와 개인 정보

로그인이나 CAPTCHA가 필요한 사이트는 조사 기록에 제한 사유를 남깁니다.
지원 자동 제출은 하지 않습니다. 사이트 전체 공고 수집·평가의 정확성을 보장하지 않습니다.
AI에 전달하는 입력 문서는 해당 AI 제공자가 처리하므로 공개 가능한 정보만 넣으세요.
기본 `inputs/`, `output/`은 Git에서 제외됩니다. 사용자 지정 폴더는 직접 제외해야 합니다.
보고서의 형식·날짜·URL은 프로그램이 검증하지만, 사실 여부는 원문 확인과 사용자 검토가 필요합니다.

Codex는 읽기 전용 실행, Claude는 WebSearch·WebFetch 도구로 조사를 요청합니다.
인증과 제공자 사용 환경에 따라 실행 가능 여부가 달라집니다.
AI 실행 연결은 명령 구성·응답 처리 테스트를 통과했으며 실계정 웹 조사 전체 흐름은 아직 검증하지 않았습니다.

## 개발

```sh
python3 -m unittest discover -s tests -v
```

- [구조와 다음 단계](architecture.md)
- [기여 가이드](contributing.md)
- [공통 조사 지침](research-instructions.md)
- CLI 참고: [Codex 비대화형 실행](https://developers.openai.com/codex/noninteractive/),
  [Claude Code 프로그램 실행](https://code.claude.com/docs/en/headless)

## License

[MIT](../../LICENSE) © 2026 sebnson
