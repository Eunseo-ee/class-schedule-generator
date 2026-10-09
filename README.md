# 시간표 조합 생성기 (Class Schedule Generator)

대학 시간표 **필터링 · 자동 조합 · TODO 연동**을 제공하는 Spring Boot 기반 웹 애플리케이션입니다.
[`time_table_maker`](https://github.com/Eunseo-ee/time_table_maker)(2024, 개인 프로젝트)를 그대로 옮기는 대신, **도메인 모델과 조합 알고리즘을 처음부터 다시 설계**하는 리메이크 프로젝트입니다.

<p align="left">
  <img alt="Java" src="https://img.shields.io/badge/Java-21-007396?logo=openjdk" />
  <img alt="Spring Boot" src="https://img.shields.io/badge/Spring%20Boot-3.5-6DB33F?logo=springboot" />
  <img alt="Gradle" src="https://img.shields.io/badge/Gradle-Kotlin%20DSL-02303A?logo=gradle" />
  <img alt="MySQL" src="https://img.shields.io/badge/MySQL-8.x-4479A1?logo=mysql" />
</p>

> 🚧 개발 진행 중입니다. 각 기능은 설계 의사결정과 함께 커밋으로 쌓아가고 있으며, 진행 상황은 커밋 로그를 참고해주세요.

---

## 📌 왜 다시 만들었나

기존 버전은 동작은 했지만 아래 문제가 있었습니다.

- 시간표 조합 로직이 재귀 안에서 관련 강의를 매번 DB로 재조회 (N+1)
- "같은 분반의 다른 시간대"를 FK가 아니라 강의명·교수명·강의실 **문자열 매칭**으로 묶는 구조
- 시간 겹침 판정이 문자열을 매번 파싱해서 비교
- 예외 처리·로깅이 거의 없어 실패 원인 추적 불가

이번 리메이크는 기능을 그대로 복제하는 게 아니라, **이 문제들을 어떤 구조로 풀었는지**에 초점을 맞춥니다.

---

## ✨ 핵심 기능 (스코프)

- **강의 필터링/검색**: 학과, 이수구분, 학점, 키워드 검색
- **시간표 자동 조합**: 필수 과목 + 조건(학점 범위, 요일/시간 회피)에 맞는 조합 생성
- **시간표 저장/관리**: 조합 결과 중 마음에 드는 시간표를 세트로 저장, 메인 지정
- **TODO 연동**: 확정한 시간표의 과목별로 할 일 관리 (간단한 CRUD)
- **API 문서**: Swagger UI

로그인/인증, Redis 캐싱, 레이트리밋, 배포 파이프라인은 이번 스코프에서 의도적으로 제외했습니다. (다른 포트폴리오 프로젝트에서 이미 다루고 있거나, 이 프로젝트의 핵심 스토리와 무관하다고 판단)

---

## 🧱 아키텍처

```
Spring Boot (REST)
 ├─ Validation / Global Exception Handler
 ├─ Domain: course / timetable / todo
 ├─ Algorithm: TimetableCombinationGenerator (순수 자바, 비트마스크 기반)
 └─ Persistence: JPA (MySQL)
```

Controller ↔ Service ↔ Repository 계층 분리를 기본으로 하되, 기존 버전처럼 Service 하나에 조회·조합·검증 로직이 몰리지 않도록 알고리즘 부분은 별도 컴포넌트로 분리합니다.

---

## 🗄️ 도메인 모델

기존 버전은 강의 하나가 여러 시간대를 가지면 row가 여러 개로 쪼개지고, 이를 강의명·교수명·강의실 문자열로 다시 묶었습니다. 이번 버전은 관계를 명시적인 FK로 표현합니다.

```
courses           (id, code, name, credit, division, ...)
 └─ course_sections   (id, course_id, professor, classroom, capacity)
     └─ section_meetings (id, section_id, day, start_min, end_min)

timetable_sets     (id, title, is_main)
 └─ timetable_items (id, set_id, section_id)

todos              (id, course_id, title, due_date, status)
```

시간 겹침 판정은 문자열 파싱 대신, 요일×교시를 비트마스크(`long`)로 표현해 `(mask1 & mask2) != 0` 연산으로 처리합니다.

---

## 🔌 API 개요

Swagger: `/swagger-ui/index.html`

### 조합 생성 예시

**POST** `/api/timetables/generate`

```json
{
  "requiredCourseCodes": ["101068", "161004"],
  "minCredit": 12,
  "maxCredit": 18,
  "avoidTimes": [{ "day": "FRI", "startPeriod": 7, "endPeriod": 9 }]
}
```

```json
{
  "success": true,
  "data": [
    {
      "totalCredit": 15,
      "sections": [
        { "courseCode": "101068", "day": "MON", "startPeriod": 3, "endPeriod": 4 }
      ]
    }
  ]
}
```

---

## ⚙️ 기술적 의사결정 하이라이트

- **문자열 파싱 → 비트마스크**: 시간 겹침 판정을 `String.split()` 반복에서 비트 연산으로 바꿔 조합 생성 성능 개선 (수치는 벤치마크 후 갱신 예정)
- **개별 시간블록 단위 → 분반(Section) 단위 탐색**: 재귀 조합 생성 안에서 발생하던 DB N+1 조회 제거
- **강의 단위 조합 → 과목 단위 CSP**: "과목마다 분반 하나씩 선택"하는 구조로 재구성해 탐색 공간 축소

자세한 설계 고민과 트러블슈팅은 별도 기록으로 정리하고 있습니다. (진행하며 링크 추가 예정)

---

## 🧪 테스트

- 조합 생성 로직, 시간 충돌 판정 로직 위주로 단위 테스트 작성
```bash
./gradlew test
```

---

## 🚀 로컬 실행

```bash
# MySQL 준비 후
./gradlew bootRun
```

Swagger: `http://localhost:8080/swagger-ui/index.html`

## 로컬 개발 환경 (MySQL / Docker)

### 처음 한 번
1. Docker Desktop 실행
2. `.env.example`을 복사해 `.env` 생성 후 비밀번호 수정
```powershell
   Copy-Item .env.example .env
```
3. 3306 포트를 이미 쓰고 있다면 `.env`의 `MYSQL_PORT`를 `3307` 등으로 변경
   - 확인: `netstat -ano | findstr :3306`

### 자주 쓰는 명령어 (프로젝트 루트에서 실행)
| 명령어 | 설명 |
|---|---|
| `docker compose up -d` | DB 시작 (백그라운드) |
| `docker compose ps` | 상태 확인 (`healthy`면 준비 완료) |
| `docker compose logs db` | 로그 확인 |
| `docker compose exec db mysql -u<유저> -p <DB명>` | MySQL 접속 |
| `docker compose down` | 중지 (데이터 유지) |
| `docker compose down -v` | 중지 + 데이터 삭제 (DB 초기화) |

### 주의
- DB 데이터는 컴퓨터마다 따로 저장된다. 다른 컴퓨터에서는 스키마 생성과 데이터 적재를 다시 해야 한다.
- 호스트에서 접속할 때(Spring, DB 클라이언트)는 `.env`의 `MYSQL_PORT`를 사용한다.

---

## 🗺️ 로드맵

도메인 모델 → 데이터 마이그레이션 → 필터링 API → 조합 알고리즘(비트마스크/CSP) → 성능 비교 → 시간표 저장 → TODO 순으로 진행 중입니다.
배포, 로그인, 캐싱은 필요해지면 그때 추가합니다.

---

## 📜 라이선스

MIT
