# Oracle Cloud 서버 현황 분석

## 서버 기본 정보

| 항목 | 값 |
|------|-----|
| OS | Ubuntu 22.04.5 LTS |
| Python | 3.10.12 |
| Shape | VM.Standard.A1.Flex (ARM) — Free Tier |
| 호스트명 | usdt-alert-bot |
| 사용자 | ubuntu |

## 현재 실행 중인 봇

### usdt-alert-bot (1개 확인됨)

| 항목 | 값 |
|------|-----|
| 경로 | `/home/ubuntu/usdt-alert-bot/` |
| 실행 방식 | systemd (`usdt-alert-bot.service`) |
| 프로세스 | `/home/ubuntu/usdt-alert-bot/venv/bin/python main.py` |
| PID | 27421 |
| 가상환경 | `venv/` (프로젝트 내부) |
| 가동 시작 | Apr 12 |

> 참고: 사용자는 봇 2개가 돌아간다고 했으나, systemd 서비스와 ps 결과에서는 1개만 확인됨.
> 다른 1개는 다른 서버에 있거나, 현재 중지 상태일 수 있음.

## 디렉토리 구조

```
/home/ubuntu/
├── usdt-alert-bot/        # 기존 봇 (건드리지 않음)
│   ├── venv/
│   └── main.py
└── (운동인증봇을 여기에 추가 예정)
```

## 안전한 배포 계획

### 원칙
- 기존 `usdt-alert-bot` 디렉토리, 서비스, 프로세스에 **일절 접근하지 않음**
- 완전히 별도의 디렉토리, 별도의 venv, 별도의 systemd 서비스로 운영
- 시스템 Python(`/usr/bin/python3`)에 패키지 설치하지 않음

### 배포 단계

```
1. 프로젝트 업로드
   scp 또는 git clone → /home/ubuntu/exercise-bot/

2. 가상환경 생성 및 의존성 설치
   cd /home/ubuntu/exercise-bot
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

3. .env 파일 생성
   cp .env.example .env
   nano .env  # 실제 값 입력

4. 수동 실행 테스트 (기존 봇에 영향 없음)
   python -m bot.main
   # Ctrl+C로 종료

5. systemd 서비스 등록
   sudo cp deploy/exercise-bot.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable exercise-bot
   sudo systemctl start exercise-bot

6. 정상 확인
   sudo systemctl status exercise-bot
   journalctl -u exercise-bot -f
```

### 최종 상태 (배포 후)

```
/home/ubuntu/
├── usdt-alert-bot/       # 기존 — 그대로 유지
└── exercise-bot/         # 신규 — 독립 운영

systemd 서비스:
  usdt-alert-bot.service  ← 기존 (running)
  exercise-bot.service    ← 신규 (running)
```

### 리소스 영향

- Free Tier ARM 인스턴스 (1 OCPU, 6GB RAM)
- 기존 usdt-alert-bot 메모리 사용: ~80MB
- exercise-bot 예상 메모리: ~50-80MB
- 합계 ~160MB — 6GB 중 2.7% 수준. 문제 없음.
