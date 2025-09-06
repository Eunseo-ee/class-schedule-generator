# Spring Campus Timetable

대학 시간표 **조합 생성 + 관리 + TODO 연동**을 제공하는 Spring Boot 기반 웹앱입니다.
HTML/CSS/JS 정적 프론트로 가볍게 동작하며, 공개 배포/에브리타임 공유를 염두에 둔 구조와 운영 가드레일을 포함합니다.

<p align="left">
  <img alt="Java" src="https://img.shields.io/badge/Java-21-007396?logo=openjdk" />
  <img alt="Spring Boot" src="https://img.shields.io/badge/Spring%20Boot-3.x-6DB33F?logo=springboot" />
  <img alt="Gradle" src="https://img.shields.io/badge/Gradle-Kotlin%20DSL-02303A?logo=gradle" />
  <img alt="MySQL" src="https://img.shields.io/badge/MySQL-8.x-4479A1?logo=mysql" />
  <img alt="Redis" src="https://img.shields.io/badge/Redis-optional-DC382D?logo=redis" />
  <img alt="CI" src="https://img.shields.io/badge/GitHub%20Actions-CI-2088FF?logo=githubactions" />
</p>

> 📌 **레포 이름**: `class-schedule-generator` / 루트 패키지: `io.github.Eunseo-ee.class-schedule-generator`

---

## ✨ 주요 기능

* **시간표 자동 조합**: 필수(required) + **클릭 1회 포함 과목만** 조합 대상, 그 외 과목 **배제**

    * 학점 범위, 요일/시간 충돌 금지, 회피 시간대 제외
    * 타임박스(예: 1500ms), 최대 결과 상한(N≤50)
    * 결과 정렬: 공강/아침회피/총학점 가중치 스코어
* **시간표 저장/메인 지정**: Timetable Set 관리, 직접 과목 추가/삭제
* **TODO 연동**: 확정 시간표 → 과목별 TODO 시드 생성
* **CSV 임포트**: 공개 강의 목록을 표준 스키마로 업로드(관리자)
* **API 문서**: Swagger UI
* **운영 가드레일**: 레이트리밋(Bucket4j), Redis 캐시(선택), Actuator 헬스체크

---

## 🧱 아키텍처 개요

```
Spring Boot (REST)
 ├─ Security(JWT) / Validation / Global Exception
 ├─ Domain: auth / course / timetable / todo
 ├─ Algorithm: CombinationGenerator (순수 자바)
 └─ Persistence: JPA(MySQL) + (옵션) Redis 캐시
Static Frontend (HTML/CSS/JS) → fetch('/api/**')
```

* **프론트**: `src/main/resources/static/{index.html, app.js, styles.css}`
* **백엔드**: Controller ↔ Service ↔ Repository (DDD-lite 계층)

> 다이어그램: `docs/architecture.png`로 첨부 예정

---

## 🗄️ ERD(핵심)

* users(id, email\*, password\_hash, name, created\_at)
* courses(id, code\*, name, professor, credit)
* course\_sections(id, course\_id, day, start\_min, end\_min, room)
* timetable\_sets(id, user\_id, title, is\_main)
* timetable\_items(id, set\_id, course\_section\_id, **unique(set\_id, course\_section\_id)**)
* todos(id, user\_id, course\_id, title, due\_at, done)

> ERD 이미지: `docs/erd.png`로 넣고 링크 예정

---

## 🔌 API 요약

* Swagger: `/swagger-ui/index.html`

### 조합 생성 예시

**POST** `/api/timetable/generate`

```json
{
  "requiredCourseCodes": ["CS101", "MATH201"],
  "clickedOnceCourseCodes": ["PE101"],
  "days": ["MON","TUE","WED","THU","FRI"],
  "minCredit": 12, "maxCredit": 18,
  "avoidTimes": [{"day":"FRI","startMin":540,"endMin":600}],
  "maxResults": 30,
  "sort": "GAP_DESC|MORNING_AVOID|CREDIT_DESC"
}
```

응답(요약)

```json
{
  "success": true,
  "data": [
    {
      "totalCredit": 15, "score": 0.83,
      "sections": [
        {"courseCode":"CS101","day":"MON","startMin":540,"endMin":630}
      ]
    }
  ],
  "error": null
}
```

---

## 🚀 빠른 시작(로컬)

### 요구 사항

* JDK 21, Docker(Compose), Gradle Wrapper

### 1) 환경 변수

`src/main/resources/application-local.yml`

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/timetable?useSSL=false&characterEncoding=UTF-8&serverTimezone=Asia/Seoul
    username: root
    password: root
  jpa:
    hibernate:
      ddl-auto: update
    properties:
      hibernate.format_sql: true
jwt:
  secret: change-me
  expiration-seconds: 3600
```

### 2) Docker로 MySQL(옵션 Redis)

`docker-compose.yml`

```yaml
services:
  mysql:
    image: mysql:8.3
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: timetable
    ports: ["3306:3306"]
    healthcheck: { test: ["CMD", "mysqladmin", "ping", "-h", "localhost"], interval: 5s, timeout: 3s, retries: 20 }
  redis:
    image: redis:7
    ports: ["6379:6379"]
```

실행: `docker compose up -d`

### 3) 애플리케이션 실행

```bash
./gradlew bootRun --args='--spring.profiles.active=local'
# 또는
./gradlew bootJar && java -jar build/libs/*.jar --spring.profiles.active=local
```

### 4) 정적 프런트 진입

* `http://localhost:8080/` (정적 `index.html`)
* Swagger: `http://localhost:8080/swagger-ui/index.html`

---

## 📥 CSV 임포트(관리자)

* 엔드포인트: `POST /api/courses/import` (multipart/form-data)
* 스키마: `code,name,professor,credit,section_day,section_start_min,section_end_min,room`

```csv
CS101,컴퓨터개론,홍길동,3,MON,540,630,101호
MATH201,이산수학,이교수,3,TUE,600,690,202호
```

* 서버 측 검증: 학점 0..6, 시간 0..1440, end>start, 요일 enum

---

## 🧪 테스트 & 품질

* **Unit**(60%): `CombinationGenerator`, `TimeConflictUtils`, `Scorer`
* **Integration**(30%): `@DataJpaTest` + Testcontainers(MySQL)
* **E2E**(10%): `@SpringBootTest` + MockMvc

명령어:

```bash
./gradlew test
```

리포트: `build/reports/tests/test/index.html`

---

## ⚙️ CI/CD

* GitHub Actions: PR/메인 푸시에 `spotlessCheck` + `test` + `bootJar`
* (옵션) 메인 푸시 시 Docker 이미지 GHCR 푸시 → 서버 배포

워크플로 예시는 `.github/workflows/ci.yml` 참고

---

## 🛡️ 운영 가드레일

* 레이트리밋: `/api/timetable/generate` 익명 10req/분/IP, 로그인 30req/분
* 캐시: 동일 요청 파라미터 해시 → Redis 5\~15분 캐싱
* 보안: JWT(BCrypt 12\~14), 로그 민감정보 마스킹, Actuator `/health`
* 모니터링: (선택) Sentry/GA4, `X-Request-ID` 트레이싱

---

## ⏱️ 성능 가이드(목표)

* 검색 API P95 < **400ms**
* 조합 생성 P95 < **1200ms** (50 VUs / 1분, k6 리포트)

> `k6/` 스크립트를 제공하고, 결과 그래프 `docs/perf.png`로 첨부 예정

---

## 🗺️ 로드맵(4주)

* W1: Auth/CRUD/Swagger/도커 & 정적 프론트 최소 연결
* W2: Timetable Set/Item + CSV 임포트 + 프론트 편집 UI
* W3: 조합 엔진(타임박스/상한/스코어) + 캐시/레이트리밋
* W4: TODO 연동 + 배포 + k6 + README/시연 GIF/약관

---

## 🔀 브랜치 & 커밋 규칙

* 전략: Trunk-based (`main` 보호) + 짧은 기능 브랜치(`feat/*`, `fix/*`)
* PR은 **Draft → Ready → Squash merge**
* Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`

---

## 📸 스크린샷

* `docs/overview.png`, `docs/generate.gif`, `docs/mobile.png`

---

## 📜 라이선스

MIT (또는 원하는 라이선스 명시)

---

## 🙋‍♀️ 문의

* Maintainer: \Eunseo-ee (GitHub: `@Eunseo-ee`)
* 버그/제안: GitHub Issues
