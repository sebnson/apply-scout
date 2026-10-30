# 품질 평가

[English](../en/quality-evaluation.md) · **한국어**

제공자를 호출하지 않고 가상 사례 6개를 실행한다.

```sh
python3 -m apply_scout evaluate
python3 -m unittest discover -s tests -v
```

사례는 `tests/fixtures/quality/`에 있다. 각각 `profile.md`, `sources.md`, 추출된 `posting.json`,
별도 조건 파일 `expected.json`, 오프라인 응답 `response.json`을 포함한다. 인물·회사·경험·공고는
모두 가상이며 URL은 `example.com`을 사용한다.

| 사례 | 제약 |
|---|---|
| required-gap | 명시적인 출근 조건 충돌이 있으면 높은 평가를 금지 |
| missing-experience | 기재되지 않은 Kubernetes 경험은 확인 필요로 유지 |
| preferred-gap | 명시적으로 없는 우대 기술을 필수요건 충돌로 해석하지 않음 |
| partial-evidence | 프로토타입은 부분 충족의 근거이며 실제 운영 경험을 증명하지 않음 |
| unsupported-claims | 근거에 기술·숫자·리더십 책임을 만들어 넣지 않음 |
| unclassified | 중요도 미분류는 보이는 경고를 생성 |

평가기는 v2 스키마의 사용 키워드와 런타임 일관성, 요구사항 누락, 중요도, 허용 평가와 전체 매칭,
공고 인용, 입력 파일·섹션의 인용, 금지 주장을 검사한다. 사례의 요구사항 이름은 식별용이므로 응답
생성 시 보존한다. 통제된 사례에서는 근거 상세를 짧은 원문 인용으로 작성해야 한다. 이는 근거 없는
추가를 찾기 위한 규칙이며, 임의의 의역이나 실제 적합성을 문자열 비교로 판단한다는 뜻이 아니다.
응답 전체를 고정 정답으로 비교하지 않으므로 요약과 설명은 달라도 된다. 별도 렌더러 회귀 테스트는
Markdown 출력, 기존 v1 데이터, 지원 상태, 사용자 메모를 검증한다.

저장된 응답은 다음과 같이 평가한다.

```sh
python3 -m apply_scout evaluate --responses output/quality-responses
```

파일명은 `partial-evidence.1.json`처럼 `<fixture>.json` 또는 `<fixture>.<run>.json`으로 쓴다.
모든 사례에 응답이 있어야 한다. 보고서에는 정확한 사례명, 실패 규칙, JSON 경로, 설명이 나온다.
전체 통과 시 종료 코드는 0, 실패 시 1이다. 반복 응답은 유효한 요구사항 구조(이름·중요도·평가·근거 수)의
서로 다른 개수를 기록한다. 차이 자체를 품질 실패로 단정하지 않는다. 누락되거나 잘못된 JSON 응답은 실패한다.

[조사 규격](research-contract.md)도 참고한다. 오프라인 테스트는 유료 제공자를 호출하지 않는다.

## 변경 전후 결과 기록

```sh
python3 -m apply_scout evaluate --result output/quality-before.json
# 런타임 지침이나 스키마를 바꾼 후 새로 생성해 저장한 응답을 평가한다.
python3 -m apply_scout evaluate --responses output/quality-after-responses --result output/quality-after.json
```

보고서는 평가 시각, `evaluator_instruction_hash`, 유효한 각 응답의 `run` 메타데이터를 기록한다.
평가기 해시는 현재 지침·스키마의 값이며 응답은 이전 해시로 생성되었을 수 있다. PR에서는 두 보고서의
실패와 구조 차이를 비교한다. 포함된 오프라인 응답을 재검사하는 것은 평가기와 회귀 검증이며,
새 프롬프트가 모델에 미친 영향을 측정하는 것은 아니다. 그 비교에는 새로 생성한 응답을 사용한다.
개인 `inputs/` 또는 `output/` 폴더를 커밋하지 않는다.

## 명시적인 제공자 평가

```sh
python3 -m apply_scout evaluate-live --agent codex --runs 2 --output output/quality-before
python3 -m apply_scout evaluate-live --agent claude --runs 2 --output output/quality-after
```

이 명령은 제공자 비용을 발생시킬 수 있다. 반복마다 각 사례에 대해 선택한 CLI를 한 번 호출한다
(기본 6회). 프롬프트 변경 효과를 비교할 때는 제공자·설정 모델·반복 횟수·사례를 동일하게 유지한다.
위 명령의 두 제공자는 선택 가능한 대안을 보여 준다. `--runs`는 1~10이며, `--timeout`은 기본
900초로 **호출별** 제한이다. 전체 평가의 제한 시간이 아니다. 재시도 없이 순차 실행한다.
CLI에 설정된 모델을 사용하므로 모델명과 CLI 버전은 PR에 별도로 기록한다.

가상 문서와 추출된 공고만 제공하며 `expected.json`과 저장된 응답은 프롬프트에서 제외한다.
제공자 명령의 웹 검색을 끄고 프롬프트에서도 현재 공고 조사가 아닌 제공된 가상 데이터임을 밝힌다.
결과 폴더는 새 폴더여야 한다. 각 파싱 응답, 반환된 제공자 원문, `evaluation.json`을 저장한다.
잘못된 JSON·규격 오류·제공자 실패는 실패 사례로 기록하며 호출이 끝날 때마다 완료된 사례를 저장한다.
일반 조사는 모든 보고서를 쓰기 전에 검증한다. 단위 테스트는 실제 유료 호출 없이 모의 응답으로 이 경로를 검증한다.

Codex는 [설정 오버라이드](https://developers.openai.com/codex/config-reference/)로 `web_search="disabled"`를 명시하고, Claude에는 빈 기본 도구 목록을 전달한다.
