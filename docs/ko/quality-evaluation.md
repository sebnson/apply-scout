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
