# AirBooking — Update Log

## Final Demonstration Refactor — 2026-05-23

This update addresses the five feedback items from the *Implementation of Core
Operations* presentation, and incorporates the second advanced feature
(Indexing & Query Optimization) for the *Final Demonstration*.

---

### English

#### 1. Real-world sample data — `03_seed_sample_data.sql`
Replaced the original toy seed (5 airports, 3 airlines, 3 aircraft, 4
schedules) with a curated real-world dataset drawn from openflights-family
IATA codes:

- **40 airports** spanning East Asia, SE Asia, Oceania, Middle East,
  Europe, and North America (ICN, GMP, NRT, HND, KIX, PEK, PVG, HKG, TPE,
  SIN, BKK, KUL, CGK, MNL, DEL, BOM, SYD, MEL, DXB, DOH, IST, LHR, LGW,
  CDG, AMS, FRA, MUC, MAD, BCN, FCO, ZRH, VIE, JFK, LAX, ORD, ATL, SFO,
  SEA, YYZ, YVR).
- **14 airlines** (KE, OZ, JL, NH, CX, SQ, EK, QR, LH, BA, AF, DL, AA, UA).
- **18 aircraft** with realistic fleet assignments — KE B777-300ER + A380,
  EK A380 + B777, SQ A350 + A380, LH 747-8 + A350, etc.
- **20 schedules** of real intercontinental routes (KE001 ICN→JFK,
  KE017 ICN→LAX, NH106 HND→LHR, SQ322 SIN→LHR, EK202 DXB→JFK,
  LH400 FRA→JFK, BA15 LHR→SIN, AF272 CDG→ICN, DL159 ATL→ICN, UA853
  SFO→NRT, etc.).
- **6 stopover schedules** — EK350 (ICN→DXB→LHR), QR858 (SIN→DOH→CDG),
  LH716 (HND→FRA→MAD), SQ12 (SIN→NRT→LAX), BA284 (LHR→SFO→SEA→YVR;
  2 stops), AF7755 (BOM→CDG→JFK).
- Seat counts scaled per aircraft class (A380/747-8 → First 4, Business 8,
  Economy 30; B777-300ER → 2/6/24; B787/A350 → 2/4/18). Trigger
  auto-generates ~530 physical seats total.
- Added a third customer account (`charlie@example.com`) for richer demos.

#### 2. Stopover discount pricing — `01_schema.sql`, `02_functions.sql`, `app.py`
Stopover flights are now automatically cheaper than direct flights:

- **`FLIGHT_AVAILABILITY_VIEW`** gained two columns:
  - `stop_count` — number of stopovers on the schedule (0 for direct).
  - `effective_price` — `ROUND(base_price * GREATEST(1 − 0.15 *
    stop_count, 0.40), 2)`. A 1-stop flight is 15% cheaper, 2-stop is
    30% cheaper; the floor caps the discount at 60% off.
- **`search_flights()`** now returns `effective_price` and `stop_count`,
  ordered by `effective_price` ascending so stopover deals surface first.
- **Customer booking flow** uses `effective_price` for the actual charge.

#### 3. Search-result configuration — `app.py` (customer portal)
Cleaned up the search-result table:

- Hidden columns: `flight_id`, `class_id`, `schedule_id`, and any other
  UUID-like fields. Users never see internal IDs.
- Displayed columns (in order): Flight, Airline, Route, Departure,
  Arrival, Class, Stops, Base Price, Price (USD), Avail. Seats.
- Dates/times reformatted as `YYYY-MM-DD HH:MM`.
- Route built via `build_route()` showing `DEP → [stops] → DEST`.
- Results sorted by `effective_price` ascending.

#### 4. Direct book / cancel — no more copy-paste — `app.py`
Both booking and cancellation now use selectboxes pre-populated from
real data — no UUID copy-pasting:

- **Search → Book:** search results are cached in `st.session_state`.
  The booking selectbox shows entries like
  `KE001 — ICN → DXB → LHR — 2026-05-15 23:00 — Economy — $297.50 • 1 stop`.
  Selecting a row auto-loads available seats for that flight + class.
  A metrics strip shows class, stop count, and effective price (with the
  delta vs the direct fare when applicable).
- **My Bookings → Cancel:** selectbox now shows
  `KE001 — ICN→JFK — 2026-05-15 — Seat 1A — $1500.00` so a customer can
  identify the booking at a glance.

#### 5. Revenue statistics audit & fix — `01_schema.sql`, `02_functions.sql`, `app.py`
Found and fixed an ambiguity in the load-factor metric:

- **`REVENUE_STATS_VIEW`** now exposes two distinct load-factor columns:
  - `class_load_factor_pct` — bookings in this class / seats in this class.
  - `flight_load_factor_pct` — bookings on this flight / total seats on
    the aircraft (computed from new CTEs `flight_totals` and
    `aircraft_totals`).
- **`get_revenue_report()`** returns both metrics with unambiguous names
  and drops the misleading single `load_factor_percentage`.
- **`class_revenue_pct`** confirmed correct: partitions by `flight_id`
  (UUID; unique per (schedule, date)). Percentages now sum to 100 per
  flight.
- **App revenue tab** improvements:
  - Totals strip (total revenue, flights with bookings, routes sold).
  - Quarter formatting via explicit `f"{year}-Q{q}"` string (replaced
    the fragile `dt.to_period("Q")` call).
  - Added a Revenue-by-Quarter chart alongside Revenue-by-Month.
  - Revenue-by-Route chart sorted in ranked order.
  - Seat-class breakdown now shows the share percentage in a small table
    next to the chart.

#### 6. Advanced feature #2 — Indexing & Query Optimization — `02_functions.sql`, `app.py`
The project brief allows selecting either or both advanced features. We
were already showcasing *Triggers & Stored Procedures*; this revision adds
*Indexing & Query Optimization* alongside.

- **`bulk_generate_test_bookings(p_count, p_seed)`** — new stored
  procedure that inserts `p_count` random confirmed bookings (with paired
  PAYMENT and TICKET) across existing scheduled flights, respecting the
  partial unique index. `setseed()` makes it reproducible.
- **`explain_search_flights(...)`** and **`explain_revenue_report()`** —
  return `EXPLAIN (ANALYZE, BUFFERS, TIMING)` output as `SETOF text` so the
  app can render the executor plan directly.
- **Staff Dashboard → Advanced Features tab** (formerly "Triggers Demo")
  now has an **Indexing & Query Optimization** section with:
  - A catalog of every index defined in `01_schema.sql`.
  - A bulk-generator panel (size + seed inputs) and live row counts for
    FLIGHT / BOOKING / SEAT_INVENTORY.
  - Interactive `EXPLAIN ANALYZE` panels for `search_flights` and
    `get_revenue_report` — paste the airport pair / date / class and see
    the live plan, including index scan / sequential scan choices.

#### 7. Documentation sync — `README.md`
Updated the README's "Sample routes" line, documented the
15%-per-stopover discount rule, replaced the single `load_factor_percentage`
mention with the two new metrics, and added a section describing the
Advanced Feature #2 (Indexing & Query Optimization) workflow.

#### 8. Setup hardening — `04_grants.sql`
Fixed a recurring "Invalid email or password" login failure caused by
Supabase re-arming RLS every time `01_schema.sql` drops and recreates
the tables. `04_grants.sql` now:

- Adds explicit `GRANT EXECUTE` on every stored procedure (including the
  three new ones: `bulk_generate_test_bookings`, `explain_search_flights`,
  `explain_revenue_report`).
- Runs `ALTER TABLE ... DISABLE ROW LEVEL SECURITY` for all 14 tables as
  its final step, so any full reset (`01 → 02 → 03 → 04`) ends in a
  queryable state without manual steps.
- README updated: setup is now a single 4-file sequence, and the
  previous "Step 4: Disable RLS" manual block is gone.

---

### 한국어

#### 1. 실제 데이터 기반 샘플 데이터 — `03_seed_sample_data.sql`
기존의 작은 시드(공항 5, 항공사 3, 항공기 3, 스케줄 4)를 openflights
계열의 실제 IATA 코드를 기반으로 한 데이터셋으로 전면 교체:

- **공항 40개** — 동아시아·동남아·오세아니아·중동·유럽·북미를 망라
  (ICN, GMP, NRT, HND, KIX, PEK, PVG, HKG, TPE, SIN, BKK, KUL, CGK, MNL,
  DEL, BOM, SYD, MEL, DXB, DOH, IST, LHR, LGW, CDG, AMS, FRA, MUC, MAD,
  BCN, FCO, ZRH, VIE, JFK, LAX, ORD, ATL, SFO, SEA, YYZ, YVR).
- **항공사 14개** (KE, OZ, JL, NH, CX, SQ, EK, QR, LH, BA, AF, DL, AA, UA).
- **항공기 18대** — 실제 운영 기종 매칭 (KE의 B777-300ER + A380, EK의
  A380 + B777, SQ의 A350 + A380, LH의 747-8 + A350 등).
- **스케줄 20개** — 실제 국제선 노선 (KE001 ICN→JFK, KE017 ICN→LAX,
  NH106 HND→LHR, SQ322 SIN→LHR, EK202 DXB→JFK, LH400 FRA→JFK, BA15
  LHR→SIN, AF272 CDG→ICN, DL159 ATL→ICN, UA853 SFO→NRT 등).
- **경유 스케줄 6개** — EK350 (ICN→DXB→LHR), QR858 (SIN→DOH→CDG),
  LH716 (HND→FRA→MAD), SQ12 (SIN→NRT→LAX), BA284 (LHR→SFO→SEA→YVR,
  2회 경유), AF7755 (BOM→CDG→JFK).
- 좌석 수도 기종별 차등 적용 (A380/747-8 → First 4·Business 8·Economy
  30; B777-300ER → 2/6/24; B787/A350 → 2/4/18). 트리거가 총 530석
  내외의 물리 좌석을 자동 생성.
- 데모용 고객 계정 1개 추가 (`charlie@example.com`).

#### 2. 경유 항공편 할인 가격 정책 — `01_schema.sql`, `02_functions.sql`, `app.py`
경유 항공편이 자동으로 직항보다 저렴해지도록 변경:

- **`FLIGHT_AVAILABILITY_VIEW`**에 두 컬럼 추가:
  - `stop_count` — 해당 스케줄의 경유지 개수 (직항이면 0).
  - `effective_price` — `ROUND(base_price * GREATEST(1 − 0.15 *
    stop_count, 0.40), 2)`. 1회 경유 = 15% 할인, 2회 경유 = 30% 할인,
    최대 60% 할인까지로 캡.
- **`search_flights()`**가 `effective_price`, `stop_count`를 반환하며
  `effective_price` 오름차순 정렬 — 경유 할인 항공편이 위로 노출.
- **고객 예약 흐름**도 `effective_price`로 결제.

#### 3. 검색 결과 화면 개선 — `app.py` (Customer Portal)
검색 결과 테이블을 정리:

- 숨김 컬럼: `flight_id`, `class_id`, `schedule_id` 등 모든 UUID.
- 표시 순서: Flight, Airline, Route, Departure, Arrival, Class, Stops,
  Base Price, Price (USD), Avail. Seats.
- 날짜/시간을 `YYYY-MM-DD HH:MM`으로 포맷.
- Route는 `build_route()`로 `출발 → [경유지] → 도착` 형태.
- 결과는 `effective_price` 오름차순 정렬.

#### 4. 직접 예약/취소 — UUID 복붙 제거 — `app.py`
예약·취소 모두 selectbox 기반으로 변경, ID 직접 입력 불필요:

- **검색 → 예약:** 검색 결과를 `st.session_state`에 캐싱.
  예약 selectbox는 `KE001 — ICN → DXB → LHR — 2026-05-15 23:00 —
  Economy — $297.50 • 1 stop` 형태. 선택 시 해당 항공편/클래스의
  잔여 좌석이 자동 로딩. 클래스·경유 수·실결제가(직항 대비 할인폭
  포함)를 metric으로 표시.
- **My Bookings → 취소:** selectbox에
  `KE001 — ICN→JFK — 2026-05-15 — Seat 1A — $1500.00` 형태로
  표시되어 한눈에 식별 가능.

#### 5. 매출 통계 검증 및 수정 — `01_schema.sql`, `02_functions.sql`, `app.py`
load factor 지표의 모호함을 발견하고 수정:

- **`REVENUE_STATS_VIEW`**가 두 종류의 load factor 컬럼 노출:
  - `class_load_factor_pct` — 해당 클래스 예약 수 / 해당 클래스 좌석 수.
  - `flight_load_factor_pct` — 해당 항공편 예약 수 / 항공기 전체
    좌석 수 (CTE `flight_totals`, `aircraft_totals`로 계산).
- **`get_revenue_report()`**는 두 지표 모두 명확한 이름으로 반환하며
  기존의 모호한 `load_factor_percentage`는 제거.
- **`class_revenue_pct`** 정확성 검증 완료: `flight_id` 기준 윈도우
  파티션 (UUID·(schedule, date) 유일). 클래스 비중 합계는 항공편당
  100%로 일치.
- **App 매출 탭** 개선:
  - 총 매출·예약 항공편 수·운항 노선 수의 metric strip.
  - 분기 포맷을 `f"{year}-Q{q}"` 문자열로 변경 (불안정한
    `dt.to_period("Q")` 호출 대체).
  - Revenue-by-Quarter 차트 추가.
  - Revenue-by-Route 차트는 매출 내림차순 정렬.
  - 좌석 클래스별 매출 비중을 별도 테이블로 표시.

#### 6. Advanced Feature #2 추가 — 인덱싱 & 쿼리 최적화 — `02_functions.sql`, `app.py`
프로젝트 요구사항(Advanced Features)에서 두 가지 모두 적용 가능하므로,
기존 *Triggers & Stored Procedures*에 더해 *Indexing & Query
Optimization*도 데모에 포함:

- **`bulk_generate_test_bookings(p_count, p_seed)`** — 신규
  저장 프로시저. 기존 예정 항공편을 대상으로 무작위 좌석에 N건의
  확정 예약(+ PAYMENT, TICKET)을 일괄 생성. 파셜 유니크 인덱스를
  준수. `setseed()`로 재현 가능.
- **`explain_search_flights(...)`** 와 **`explain_revenue_report()`** —
  `EXPLAIN (ANALYZE, BUFFERS, TIMING)` 결과를 `SETOF text`로 반환하여
  앱이 실행 계획을 직접 렌더링.
- **Staff Dashboard → Advanced Features 탭** (구 "Triggers Demo")에
  **Indexing & Query Optimization** 섹션 추가:
  - `01_schema.sql`에 정의된 모든 인덱스 카탈로그.
  - Bulk 생성기 패널 (개수·시드 입력) + FLIGHT/BOOKING/SEAT_INVENTORY
    실시간 행수.
  - `search_flights`, `get_revenue_report`에 대한 인터랙티브 EXPLAIN
    ANALYZE 패널 — 인덱스 스캔/순차 스캔 여부를 라이브로 확인.

#### 7. 문서 동기화 — `README.md`
README의 "Sample routes" 문구, 15%/경유 할인 규칙, load factor 두
지표 설명, Advanced Feature #2 사용법 섹션을 추가/갱신.

#### 8. 설치 절차 보강 — `04_grants.sql`
`01_schema.sql`이 테이블을 DROP/CREATE할 때마다 Supabase가 RLS를
자동 활성화시켜 `STAFF`·`CUSTOMER` 로그인이 "Invalid email or
password"로 실패하던 문제를 수정. `04_grants.sql`을 다음과 같이
확장:

- 모든 저장 프로시저(`generate_flights`, `search_flights`,
  `create_booking`, `cancel_booking`, `get_revenue_report`,
  신규 추가된 `bulk_generate_test_bookings`,
  `explain_search_flights`, `explain_revenue_report`)에 대해
  명시적 `GRANT EXECUTE` 추가.
- 14개 테이블 전체에 `ALTER TABLE ... DISABLE ROW LEVEL SECURITY`
  실행을 마지막 단계로 포함. `01 → 02 → 03 → 04` 순서로 한 번에
  리셋해도 추가 수동 작업 없이 즉시 사용 가능.
- README 업데이트: 설치는 이제 4개 SQL 파일 순차 실행만 하면 되며
  기존 "Step 4: Disable RLS" 수동 블록은 삭제.

---

## CSV-First Data Replacement — 2026-05-30

This update replaces the manually curated international seed data with the
real-world **nycflights13** dataset (336,776 US-domestic flights, 2013) to
provide a large, authentic dataset for the Final Demonstration — especially
for the Indexing & Query Optimization advanced feature.

---

### English

#### 1. Slim seed file — `03_seed_sample_data.sql`
Removed all manually curated international airlines, airports, aircraft,
seat classes, and 20 flight schedules from the seed file. The file now
contains only:
- **Demo accounts**: CUSTOMER × 3 (alice, bob, charlie) + STAFF × 1 (admin).
- **Two stopover demo schedules**: EK350 (ICN→DXB→LHR, 1 stop) and BA284
  (LHR→SFO→SEA→YVR, 2 stops) — retained because the nycflights13 dataset
  has no stopover routes, so these schedules are the only way to demonstrate
  the 15%-per-stop discount feature live.
- Only the 6 airports needed by those two schedules (ICN, DXB, LHR, SFO,
  SEA, YVR) and 2 airlines (EK, BA).

#### 2. New ETL script — `seed_from_csv.py`
A Python command-line script that reads `flights.csv` (nycflights13) and
loads the data into Supabase in 8 sequential phases:

| Phase | Action |
|---|---|
| A | 16 US carriers → AIRLINE |
| B | ~108 airports (3 origins + 105 destinations, curated names) → AIRPORT |
| C | Distance-tiered fleet (short/medium/long per carrier) → AIRCRAFT |
| D | 3 SEAT_CLASS rows per aircraft → trigger auto-creates SEAT_INVENTORY |
| E | One FLIGHT_SCHEDULE per distinct (carrier, flight#, origin, dest) |
| F | One FLIGHT per (schedule, date); dates shifted 2013→2026, all `scheduled` |
| G | Historical BOOKING + PAYMENT + TICKET on past-dated flights |
| H | Past flights (before 2026-05-30) → `arrived` |

Key design choices:
- **Date shift**: 2013 → 2026 (year + 13), preserving month/day.
- **Status hybrid**: flights before today (`2026-05-30`) = `arrived` (populates
  revenue/load-factor history); flights on/after = `scheduled` (bookable).
- **Trigger ordering**: all flights inserted as `scheduled` first so
  `trg_validate_booking` allows historical bookings to be created; status
  flipped to `arrived` only in Phase H.
- **Distance-tiered pricing**: Economy base $120 (short < 700 mi) / $200
  (medium) / $380 (long). Business ≈ 2.5× Economy; First ≈ 5× Economy.
  Price is stored on `SEAT_CLASS` (per-aircraft, not per-route), consistent
  with the physical-asset schema model.
- **No schema changes**: the existing `01_schema.sql` is used as-is.
- **CLI flags**: `--limit N` (smoke test), `--with-history N` (historical
  bookings), `--batch 500`, `--truncate` (clear flights/bookings, keep rest).
- **Service-role key required** in `.env` as `SUPABASE_SERVICE_ROLE_KEY` to
  bypass RLS for the bulk inserts.

#### 3. README update — `README.md`
- Added `SUPABASE_SERVICE_ROLE_KEY` to the `.env` template.
- Replaced step 3 description (updated to reflect slim seed).
- Added new step 4 (ETL script usage with smoke-test and full-load commands).
- Documented the pricing model, date-shift rule, and stopover demo retention.
- Updated the Project Structure tree to include `seed_from_csv.py` and
  `flights.csv`.

---

### 한국어

#### 1. 시드 파일 간소화 — `03_seed_sample_data.sql`
기존의 직접 작성한 국제선 항공사·공항·항공기·좌석 클래스·20개 스케줄을
시드 파일에서 모두 제거. 이제 이 파일에는 다음만 포함됨:
- **데모 계정**: 고객 3명(alice, bob, charlie) + 스태프 1명(admin).
- **두 경유 데모 스케줄**: EK350(ICN→DXB→LHR, 1회 경유)와 BA284
  (LHR→SFO→SEA→YVR, 2회 경유) — nycflights13은 경유 노선이 없으므로 경유
  할인 기능(15%/stop)을 시연하려면 이 스케줄이 반드시 필요함.
- 두 스케줄에 필요한 공항 6개(ICN, DXB, LHR, SFO, SEA, YVR)와 항공사 2개
  (EK, BA)만 삽입.

#### 2. 신규 ETL 스크립트 — `seed_from_csv.py`
`flights.csv`(nycflights13)를 읽어 Supabase에 데이터를 로드하는 Python
커맨드라인 스크립트. 8단계로 구성:

| 단계 | 작업 |
|---|---|
| A | 16개 미국 항공사 → AIRLINE |
| B | ~108개 공항(출발 3 + 도착 105, 주요 공항명 사전 포함) → AIRPORT |
| C | 거리 기반 기종 구분(단/중/장거리, 항공사별 최대 3종) → AIRCRAFT |
| D | 항공기당 SEAT_CLASS 3행 삽입 → 트리거가 SEAT_INVENTORY 자동 생성 |
| E | (항공사, 편명, 출발지, 목적지) 고유 조합 → FLIGHT_SCHEDULE |
| F | (스케줄, 날짜)별 FLIGHT 삽입; 연도 2013→2026 변환, 전부 `scheduled` |
| G | 과거 날짜 항공편에 BOOKING + PAYMENT + TICKET 생성(히스토리) |
| H | 2026-05-30 이전 항공편 → `arrived` 로 상태 변경 |

주요 설계 결정:
- **날짜 변환**: 2013→2026(연도 +13), 월/일 유지.
- **상태 하이브리드**: 오늘(2026-05-30) 이전 = `arrived`(매출/탑승률 히스토리
  데모용); 이후 = `scheduled`(예약 가능).
- **트리거 순서 준수**: 히스토리 예약 생성 전까지 모든 편을 `scheduled`로 유지
  (trg_validate_booking이 non-scheduled 편에 예약 차단) → Phase H에서 일괄
  `arrived` 전환.
- **거리 기반 가격 정책**: Economy 기본가 $120(단거리) / $200(중거리) / $380
  (장거리). Business ≈ 2.5배, First ≈ 5배. SEAT_CLASS(항공기 단위)에 저장
  — 스키마의 물리 자산 모델 그대로 사용, 노선별 요금 없음.
- **스키마 변경 없음**: 기존 `01_schema.sql`을 그대로 사용.
- **CLI 플래그**: `--limit N`(소규모 테스트), `--with-history N`(히스토리
  예약 건수), `--batch 500`, `--truncate`(항공편/예약 초기화 후 재로드).
- `.env`에 `SUPABASE_SERVICE_ROLE_KEY` 추가 필요(대량 INSERT 시 RLS 우회).

#### 3. README 업데이트 — `README.md`
- `.env` 템플릿에 `SUPABASE_SERVICE_ROLE_KEY` 추가 및 취득 방법 설명.
- 3단계 설명을 간소화된 시드 파일 기준으로 수정.
- 4단계(ETL 스크립트 실행 — 소규모 테스트·전체 로드 명령) 신규 추가.
- 가격 정책, 날짜 변환 규칙, 경유 데모 스케줄 유지 이유 문서화.
- 프로젝트 구조 트리에 `seed_from_csv.py`·`flights.csv` 추가.

---

## Source feedback (preserved for traceability)

- plan with opus, work with sonnet (switch model required)
- ask questions if unclear
- After the entire execution, update in @DOCS.md

@airBooking-s26.md 에서 Final Demonstration and Final Report를 위해 코드 작업을 하자.
Implementation of Core Operations에서 피드백을 받았는데:

1. Must need more sample data, real data perhaps… https://openflights.org/data.php#airport
2. Need for stopover flights (Stopover flights might need to be cheaper compared to direct flights)
3. Configure search result
4. Directly book, refund etc. without copy and pasting the actual ID
5. Check revenue result correctness

모든 sql 파일과 @app.py 를 수정할거야. 수정하면서 다음 발표 때, 어떤 부분이 업데이트 되었고
수정되었는지 기록도 해야 되니, 수정 이후 @update_log.md 에 어떤 부분이 바뀌었는지 영어로,
그리고 한국어로 나누어서 정리해줘.

Final Demonstration에서는 ### Advanced Features 이 로직도 적용해야 된다는 점을 잊지마.
