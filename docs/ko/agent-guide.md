# 에이전트 가이드

[English](../en/agent-guide.md) · **한국어**

저장소 루트의 `AGENTS.md`와 `CLAUDE.md`는 Codex·Claude Code가 읽는 진입점입니다.
이 문서는 같은 작업 흐름을 사용자와 기여자를 위해 설명합니다.

## 개발

Python 3.10 이상과 표준 라이브러리를 사용합니다. 동작을 변경하면 다음 검증을 실행합니다.

```sh
python3 -m unittest discover -s tests -v
```

## 채용 공고 조사

조사를 요청받으면 [공통 조사 지침](research-instructions.md)을 따릅니다.
`inputs/profile.md`, `inputs/sources.md`와 선택 사항인 포트폴리오·상세 경력 파일을 읽습니다.

```sh
# 전체 프롬프트와 출력 규격 확인
python3 -m apply_scout prompt
# 유효한 조사 결과를 output/research.json에 저장한 다음 실행
python3 -m apply_scout render output/research.json
```

공고를 만들어 내거나 웹 탐색 없이 실제 조사를 했다고 주장하지 않습니다.
사용자 메모와 기존 출력 규격을 보존합니다. 기본 비공개 폴더의 개인 입력과 조사 결과를
Git에 커밋하지 않습니다.
