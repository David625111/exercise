# 논클 고독한 운동인증봇

## 프로젝트 개요

"논클 고독한 운동인증방" 텔레그램 그룹에서 사용하는 운동 인증 봇.
팀원들이 매일 운동 사진을 올려 인증하고, 주간/분기별 목표 달성 여부를 자동으로 추적하는 시스템이다.

## 핵심 규칙

### 운동 인증 조건
1. **하루 50분 이상** 운동해야 인증으로 인정
2. **당일 운동 증명 사진**을 반드시 업로드해야 기록으로 인정
3. 인증 마감은 **다음 날**까지 (그 이후 인증 불가)
4. 하루에 여러 번 나눠서 운동해도 합산 50분 이상이면 인정 (예: 요가 20분 + 산책 15분 + 홈트 15분)

### 주간 목표 시스템
- 각 팀원마다 **주간 운동 횟수 목표**가 다름 (주 3회, 4회, 5회 등)
- 한 주(월~일) 동안 목표 횟수만큼 인증하면 해당 주 **+1점** 획득
- 목표 미달성 시 점수 변동 없음 (감점 없음)
- 점수는 분기 내 누적

### 분기 시스템
- 분기마다 점수가 리셋되고 새로 시작
- 분기 시작 시 각 팀원이 해당 분기의 주간 목표를 설정
- 분기 종료 시 누적 점수 기준으로 순위 결정
- **현재 분기(Q2 2026)**: 2026-03-30 시작

### 주간 단위
- **월요일~일요일**을 한 주로 계산

## 팀원 정보

| 닉네임 | 한국이름 | 텔레그램 username | 비고 |
|---------|----------|-------------------|------|
| Robin   | 강유빈   | @youbinkang       | 주 5회 목표 (Q2 기준) |
| Kaido   | 카이도   | @kimkido          | 주 3~4회 목표 |
| Gemma   | 예지     | @nC_Gemma         | 기존 수동 점수 관리자 |
| Ben     | Ben      | @bambben          | 주 3회 목표 |
| Henry   | Henry    | @hskim6543        | |
| Yumi    | 유미     | @yumiiihong       | |
| Lulu    | 루시아   | @lucia744         | |

## 기술 스택

- **언어**: Python 3.11+
- **프레임워크**: python-telegram-bot (v20+, async)
- **데이터베이스**: SQLite (단일 파일, 서버리스)
- **배포**: Oracle Cloud Free Tier (Always Free ARM instance)
- **프로세스 관리**: systemd

## 프로젝트 구조

```
운동인증봇/
├── CLAUDE.md
├── requirements.txt
├── .env.example          # 환경변수 템플릿
├── .gitignore
├── bot/
│   ├── __init__.py
│   ├── main.py           # 봇 엔트리포인트
│   ├── config.py          # 설정 및 환경변수
│   ├── database.py        # SQLite DB 초기화 및 쿼리
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── verification.py  # 운동 인증 처리 (사진 수신)
│   │   ├── goals.py         # 분기 목표 설정
│   │   ├── status.py        # 현황 조회 (개인, 주간, 분기)
│   │   ├── admin.py         # 관리자 기능 (수동 인증 추가 등)
│   │   └── schedule.py      # 자동 리포트 (주간 점수 등)
│   └── utils.py           # 유틸리티 (날짜, 분기 계산 등)
└── deploy/
    └── exercise-bot.service  # systemd 서비스 파일
```

## 데이터베이스 스키마

### members 테이블
- `telegram_id` (INTEGER, PK): 텔레그램 사용자 ID
- `username` (TEXT): 텔레그램 username
- `display_name` (TEXT): 표시 이름 (Robin, Kaido 등)
- `created_at` (TIMESTAMP)

### quarter_goals 테이블
- `id` (INTEGER, PK)
- `telegram_id` (INTEGER, FK)
- `quarter_start` (DATE): 분기 시작일
- `weekly_target` (INTEGER): 주간 운동 목표 횟수
- `created_at` (TIMESTAMP)

### verifications 테이블
- `id` (INTEGER, PK)
- `telegram_id` (INTEGER, FK)
- `exercise_date` (DATE): 운동한 날짜
- `verified_at` (TIMESTAMP): 인증 시각
- `photo_file_id` (TEXT, NULLABLE): 텔레그램 사진 file_id
- `is_manual` (BOOLEAN): 수동 입력 여부
- `note` (TEXT, NULLABLE): 메모 (운동 종류 등)
- UNIQUE(telegram_id, exercise_date)

## 봇 명령어

### 일반 사용자
- **사진 전송**: 사진을 보내면 당일 운동 인증으로 처리. 사진과 함께 메모를 첨부할 수 있음 (예: "크로스핏 1시간")
- `/status` 또는 `/현황`: 이번 주 개인 인증 현황 및 분기 누적 점수 확인
- `/주간` 또는 `/weekly`: 이번 주 전체 팀원 인증 현황
- `/점수` 또는 `/score`: 현재 분기 누적 점수 랭킹
- `/목표설정 N` 또는 `/setgoal N`: 현재 분기 주간 목표 설정 (예: `/목표설정 5` = 주 5회)

### 관리자 (Gemma, Robin)
- `/수동인증 @username YYYY-MM-DD` 또는 `/addlog @username YYYY-MM-DD`: 과거 운동 기록 수동 추가
- `/수동인증삭제 @username YYYY-MM-DD` 또는 `/dellog @username YYYY-MM-DD`: 잘못된 기록 삭제
- `/분기설정 YYYY-MM-DD` 또는 `/setquarter YYYY-MM-DD`: 분기 시작일 설정
- `/리포트` 또는 `/report`: 주간 점수 리포트 즉시 생성

### 자동 스케줄
- **매주 월요일 오전 10시 (KST)**: 지난 주 점수 자동 집계 및 전송
- **매일 밤 11시 (KST)**: 당일 인증 현황 요약 전송

## 점수 계산 로직

1. 한 주(월~일) 동안의 인증 횟수를 카운트
2. 인증 횟수 >= 해당 멤버의 주간 목표 → 분기 점수 +1
3. 인증 횟수 < 주간 목표 → 점수 변동 없음
4. 점수는 분기 시작부터 현재까지 누적

### 주간 리포트 형식 (기존 채팅방 스타일 유지)
```
🍀 April Week 2 Scores

Robin +2 ⬆️
Kaido +2 ⬆️
Gemma +2 ⬆️
Henry 0
Ben 0
Lulu 0
```
- ⬆️: 이번 주 점수가 올라간 멤버
- 🥇: 분기 종료 시 1등
- 🥈: 분기 종료 시 2등

## 개발 규칙

- 모든 시간은 **KST (Asia/Seoul, UTC+9)** 기준으로 처리
- 봇 메시지는 한국어로 작성
- 에러 로깅은 영어로 작성
- 환경변수:
  - `TELEGRAM_BOT_TOKEN`: 텔레그램 봇 토큰
  - `ADMIN_IDS`: 관리자 텔레그램 ID 목록 (쉼표 구분)
  - `GROUP_CHAT_ID`: 봇이 동작할 그룹 채팅 ID
  - `DATABASE_PATH`: SQLite DB 파일 경로 (기본값: `data/exercise.db`)
  - `TZ`: `Asia/Seoul`

## Oracle Cloud 배포

### Free Tier 인스턴스 사양
- Shape: VM.Standard.A1.Flex (ARM)
- OCPU: 1, RAM: 6GB
- OS: Ubuntu 22.04+

### 배포 절차
1. 인스턴스 SSH 접속
2. Python 3.11+ 및 pip 설치
3. 프로젝트 클론 및 가상환경 세팅
4. `.env` 파일 생성 (봇 토큰 등)
5. systemd 서비스 등록 및 시작

### systemd 서비스
- 서비스명: `exercise-bot`
- 자동 재시작: `Restart=always`
- 로그 확인: `journalctl -u exercise-bot -f`

## 수동 인증 반영 (봇 이전 기록)

봇 배포 이전(2026-03-30 ~ 봇 시작 전) 운동 기록을 반영하기 위해:
1. 관리자가 `/수동인증` 명령어로 개별 추가
2. 또는 봇 최초 실행 시 초기 데이터를 seed할 수 있는 스크립트 제공

### Q2 2026 기존 인증 기록 (채팅 기반 파악)
대화 내용 기반으로 파악된 Q2(3/30~) 기존 기록:
- **Robin (강유빈)**: Week 1 (3/30~4/5) 5회, Week 2 (4/6~4/12) 5회 → 현재 +2
- **Kaido (카이도)**: Week 1 3회, Week 2 4회 → 현재 +2
- **Gemma (예지)**: Week 1 3회+, Week 2 3회+ → 현재 +2
- 나머지: 0
