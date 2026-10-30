# 조사 규격 v2

[English](../en/research-contract.md) · **한국어**

`apply_scout/schema.py`의 딕셔너리 규격과 런타임 검증은 같은 열거형 상수를 사용한다.
새 제공자 출력은 v2를 사용하며 렌더링은 v1과 v2를 모두 지원한다. [조사 지침](research-instructions.md)을 참고한다.

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

## 검증과 호환성

`met`, `partial`, `unmet`에는 프로필 근거가 필요하다. 정보가 없으면 `unknown`을 쓰고
`rationale`에 질문이나 설명을 남긴다. 근거 파일명은 `run.input_files`에 있어야 하며, 실제 실행에서는
포함한 파일명도 전달해 임의로 만든 목록을 거부한다. 오프라인 렌더링은 저장된 목록을 신뢰하며
개인 파일을 읽지 않는다. 공고 근거는 해당 공고 URL 또는 그 공고에 선언된 확인 완료 공식 링크여야 한다.

필수요건이 `unmet`이면 `높음`을 거부한다. 모든 필수요건이 `unknown`이면 `높음`과 `보통`을
거부한다. 요구사항이 비어 있거나 모든 중요도 분류가 `unknown`이면 경고한다.
오류는 JSON 경로와 수정 방법을 포함한다. 의미상의 적합성이나 합격 확률을 채점하지 않는다.

버전이 없거나 `"1"`인 결과의 평가와 근거는 보존한다. 메모리 내 변환은 v2 요구사항 배치를 쓰되
`schema_version="1"`과 원본 `legacy` 필드를 유지한다. 파일·섹션 참조, 공고 인용, 메타데이터,
중요도를 만들어 내지 않는다. 알려진 한국어 평가만 대응하는 열거형으로 바꾸고 사용자 정의 평가는
그대로 둔다. 이 내부 표현은 새로운 v2 조사 결과로 내보내지 않는다. v1 지원 제거는 별도 메이저 버전에서 결정한다.
