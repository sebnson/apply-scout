# 조사 규격 v2

[English](../en/research-contract.md) · **한국어**

`apply_scout/schema.py`의 딕셔너리 규격과 런타임 검증은 같은 열거형 상수를 사용한다.
제공자 출력을 전환하기 전에 v2 규격을 도입하며 v1 지원은 유지한다.

- `schema_version`: `"2"`.
- `run`: `agent`, `instruction_hash` (`sha256:` 뒤에 16진수 64자리), `input_files`
  (실제로 이번 실행에 포함된 문서의 파일명이며 문서 내용은 저장하지 않음).
- 요구사항: `requirement`, `importance` (`required`, `preferred`, `responsibility`, `unknown`),
  `assessment` (`met`, `partial`, `unmet`, `unknown`), 비어 있지 않은 `rationale`.
- `job_evidence`: 공고에서 확인한 `source_url`과 `detail`.
- `profile_evidence`: `file`, `section`, `detail` 객체의 배열.
- 공고별 `official_source_urls`: 실제 조사한 공식 연결 페이지. `sources`에도 `checked`로
  기록한다. 공고 URL만 근거로 사용했다면 빈 배열을 쓴다.
- 전체 `match`: `높음`, `보통`, `낮음`, `판단 보류`를 유지한다.

지침 해시는 런타임 조사 지침과 JSON Schema만 포함하며 개인정보 문서나 전체 프롬프트는
포함하지 않는다. 코드는 구조와 내부 일관성을 검증하지만 공식 출처라는 주장이나 경험 서술의
진위를 판단하지 못한다. 사용자가 근거를 검토해야 한다.
