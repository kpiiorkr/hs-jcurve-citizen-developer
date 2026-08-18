# -*- coding: utf-8 -*-
"""
jcurve_hs_oulad.py — OULAD 기반 J-Curve 실증 및 Harmony Search(HS) 최적화 (v4)

원본: 260414_hs-jcurve-citizen-developer.ipynb (Google Colab, v3)
이 파일은 v3 코드 리뷰에서 발견된 방법론적 결함을 수정한 v4이다.

=====================================================================
변경 사항 요약 (v3 → v4) — 각 항목이 해결하는 결함을 1줄로 명시
=====================================================================
[G1] 그룹 정의를 studentInfo.highest_education(학력 수준) → studentRegistration
     기반 "STEM 도메인 선행 경험" 이력으로 전면 교체.
     해결 결함: OULAD에는 전공(학과) 필드가 없고 학력 수준은 도메인 전문성과
     무관하므로 "비전공자/전공자" 명명은 구성타당도(construct validity) 위반이었음.
[G2] 그룹 분류 단위를 (id_student, code_module, code_presentation) 조합으로 명시하고,
     이 조합을 analysis_cohort로 저장하여 이후 모든 VLE 조인의 유일한 기준으로 사용.
     해결 결함: 학생당 여러 학기 로그가 뒤섞여 분석 대상이 무엇인지 불명확했던 문제.
[B1] student_vle 필터링을 id_student 단독 → (id_student, code_module, code_presentation)
     조합 merge로 변경.
     해결 결함: 한 학생이 STEM 모듈을 여러 학기에 걸쳐 수강한 경우, 서로 다른 학기의
     클릭 로그가 하나의 시계열로 합산되던 "presentation 오염" 버그(v3의 신규 발견 결함).
[B2] week 정의를 date<0 → week=0(pre-course)으로 분리하고, week=1을 date 0~6일로
     정의, 1~30주 전체를 reindex(결측=0)하여 위치 인덱스가 아닌 "주차 라벨" 기준으로
     baseline/trough를 계산.
     해결 결함: 위치 인덱스 슬라이싱은 결측 주차가 있으면 실제 주차와 어긋남.
[E1] EI(참여도 지수)를 전체 기간 min-max 정규화 → 개인별 "초기 4주 평균" 기준 상대
     활동지수(Activity Index)로 변경.
     해결 결함: 전체 기간 min/max를 쓰면 미래(예: 중간고사 기간 급증)의 정보가 초기
     시점 정규화에 새어 들어가는 look-ahead bias가 발생.
[S1] Welch's t-test(equal_var=False), Mann-Whitney U, Cohen's d, rank-biserial
     correlation을 모두 계산하고, 전체표본 및 5주 이상 활동표본을 병행 산출.
     해결 결함: v3는 등분산 가정 t-검정만 사용했고 효과크기·비모수 검정이 없었으며,
     조기 이탈자 포함 여부에 따른 선택편향을 점검하지 않았음.
[H1] simulate_jcurve/fitness에 x1, x2 증가에 따른 이차 비용(cost) 항을 추가.
     해결 결함: v3는 x1, x2가 커질수록 J_depth/J_width가 단조 감소하기만 하는
     구조라 최적해가 코너값(x1=x2=1.0)에 자명하게 수렴하는 방법론적 결함이 있었음.
[H2] HS 계수(0.40, 0.10, 0.50 등 감소율과 cost 가중치)는 실증 데이터로 추정된 값이
     아니라 "가정 기반 시뮬레이션 계수"임을 코드 주석과 출력 문구에 명시.
     해결 결함: "OULAD 실측값 기준 모델링"이라는 표현이 계수 자체까지 실증적인
     것으로 오인되게 했음(실측인 것은 BASE_DEPTH, BASE_WIDTH뿐).
[V1] 그룹 분류(선행 경험 판정) 로직을 학생별 for-loop → merge_asof/groupby 기반
     벡터화로 변경.
     해결 결함: 학생 수만큼 반복하는 for-loop는 32,593명 규모에서 성능이 나쁨.
[N1] requests.get()에 timeout과 raise_for_status()를 추가.
     해결 결함: 네트워크 이상 시 무한 대기 및 실패를 조용히 넘어가는 문제.
[C1] weekly_ei_comparison.csv에 그룹별 n, sd, 95% CI 컬럼을 추가.
[C2] summary_revision_comparison.csv의 "변경 전" 수치는 v3 실행 로그 기반 하드코딩이며,
     각 값 옆에 출처 주석을 명시(재현 가능한 산출 스크립트가 없으므로 하드코딩 불가피).
[N2] (2026-08 신규) 공식 다운로드 URL(analyse.kmi.open.ac.uk)이 OU 사이트 이전으로 인해
     응답은 하되 zip이 아닌 HTML 랜딩 페이지로 리다이렉트되는 것을 실제로 확인함.
     download_oulad()에 Content-Type 검증을 추가해 이를 명시적 오류로 처리하고,
     검증 절차(verify_oulad_files, 원 논문 통계 대조)를 통과한 경우에만 비공식 대체
     미러(download_oulad_from_kaggle_mirror)를 쓸 수 있도록 안전장치를 추가함.
[B3] (2026-08, 실제 데이터로 최초 실행 중 발견) detect_jcurve()가 단일 패스로
     "현재까지 최소값 갱신"과 "회복 여부 판정"을 동시에 수행해, 실데이터처럼 EI가
     완전한 단조감소가 아닌 경우 전역 최저점(t_bottom) 이전에 t_recover가 잡히는
     모순이 실제로 발생함(Novice: t_start=6, t_bottom=27인데 t_recover=7로 계산됨).
     t_start 확정 → 전 구간에서 전역 최저점 확정 → 그 이후 구간에서만 회복 탐색,
     의 2단계 알고리즘으로 재작성.
[B4] (2026-08, 실제 실행 중 발견) matplotlib 3.11부터 Axes.boxplot()의 labels=
     인자가 제거되고 tick_labels=로 변경되어 STEP 10 시각화가 TypeError로 중단됨.
     tick_labels=로 수정.
[F1] (2026-08, 실제 실행 중 발견) 기본 폰트(DejaVu Sans)에 한글 글리프가 없어 저장된
     PNG의 한글 라벨이 깨지는 문제를 Malgun Gothic 폰트 지정으로 해결.

=====================================================================
실행 환경에 대한 안내
=====================================================================
[2026-08 갱신] 이 스크립트는 Windows 환경에 winget으로 설치한 실제 Python 3.12
런타임(pandas/numpy/scipy/matplotlib/requests/kagglehub)에서 실제로 실행되었다.
공식 OULAD 다운로드 엔드포인트(analyse.kmi.open.ac.uk)가 이 세션에서도 동일하게
HTML 랜딩 페이지로만 리다이렉트되어(§N2) 실패했으므로, download_oulad_from_kaggle_mirror()
경로로 전환해 Kaggle 미러(anlgrbz/student-demographics-online-education-dataoulad)를
사용했다. 이 미러는 verify_oulad_files()로 검증되었다: 필수 파일 7개가 모두 존재하고,
studentVle.csv의 행 수가 정확히 10,655,280행으로 Kuzilek et al.(2017)에 보고된 공식
통계와 완전히 일치함을 확인했다(허용오차 ±50,000행 대비 오차 0). 이 실행으로 생성된
jcurve_v4.png, hs_result_v4.png, weekly_ei_comparison.csv, group_stats_comparison.csv,
summary_revision_comparison.csv는 README.md §4.2~4.4에 반영된 실제 산출물이며, 더 이상
플레이스홀더가 아니다. 재현하려면: (1) 위 Kaggle 데이터셋(또는 공식 URL이 복구되면 공식
zip)을 구해 oulad/ 폴더에 7개 CSV를 배치, (2) `pip install pandas numpy scipy matplotlib
requests kagglehub`, (3) `python analysis/jcurve_hs_oulad.py` 실행.

[N2 관련 추가 안내] 2026-08 기준 OU 공식 다운로드 엔드포인트가 정상 동작하지 않는 것이
직접 확인되었다(리다이렉트만 발생, zip 미반환). download_oulad()가 이를 자동 감지해
실패하며, __main__ 블록은 실패 시 download_oulad_from_kaggle_mirror()로 자동 전환한
뒤 verify_oulad_files()로 검증한다. 검증 기준(필수 파일 7개, studentVle.csv 행 수
≈10,655,280 ± 50,000)을 통과하지 못하면 AssertionError로 중단되므로, 다른 소스로
바뀐 채 조용히 분석이 진행되는 일은 없다.
"""

import os
import zipfile
import random

import numpy as np
import pandas as pd
import requests
from scipy import stats
import matplotlib.pyplot as plt

# [F1] (2026-08, 실제 실행 중 발견) 기본 폰트(DejaVu Sans)는 한글 글리프가 없어
# 저장된 PNG에서 한글 라벨이 빈 사각형(missing glyph)으로 표시되는 문제가 있었다.
# Windows에 기본 포함된 한글 지원 폰트(Malgun Gothic)로 전환해 이를 해결한다.
# 해당 폰트가 없는 환경(Linux CI 등)에서는 예외를 무시하고 기본 폰트로 진행한다
# (한글이 깨져 보일 수 있으나 스크립트 실행 자체는 계속된다).
try:
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
except Exception:
    pass

# =====================================================================
# STEP 0: OULAD 다운로드 및 압축 해제  [N1: timeout/raise_for_status 추가]
# =====================================================================
OULAD_URL = "https://analyse.kmi.open.ac.uk/open-dataset/download"
DATA_DIR = "oulad"


# [N2] 2026년 기준 OU 사이트 이전(analyse.kmi.open.ac.uk -> research.stem.open.ac.uk/ouanalyse/)
# 이후 공식 다운로드 버튼/엔드포인트 자체가 응답 없이 랜딩 페이지로 리다이렉트되는 것이
# 실제로 확인되었다(2026-08 기준, requests로 상태코드/Content-Type/최종 URL 직접 검증).
# 즉 OULAD_URL이 살아있다는 보장이 없으므로, Content-Type이 zip이 아니면 즉시 실패시키고
# (조용히 HTML 에러 페이지를 zip으로 오인하지 않도록) 대체 경로 안내 메시지를 출력한다.
KAGGLE_MIRROR_SLUG = "anlgrbz/student-demographics-online-education-dataoulad"  # 비공식 미러, 검증 후 사용
EXPECTED_VLE_ROWS = 10_655_280  # Kuzilek et al.(2017) 논문에 보고된 studentVle.csv 행 수(검증 기준)
EXPECTED_VLE_TOLERANCE = 50_000


def download_oulad(url: str = OULAD_URL, out_dir: str = DATA_DIR, timeout: int = 60) -> None:
    """OULAD zip을 내려받아 out_dir에 압축 해제한다.

    [N1] v3는 requests.get(url, stream=True)에 timeout이 없어 네트워크 장애 시
    무한 대기했고, 상태 코드를 확인하지 않아 실패 응답(HTML 에러 페이지 등)을
    zip으로 오인하고 넘어가는 문제가 있었다. timeout과 raise_for_status()를 추가한다.

    [N2] 공식 URL이 응답은 200을 반환하되 실제로는 zip이 아닌 HTML 랜딩 페이지로
    리다이렉트되는 경우(현재 OU 사이트 이전으로 인한 실제 상황)를 Content-Type 검사로
    탐지하여 명시적으로 실패시킨다. 이 경우 download_oulad_from_kaggle_mirror()로
    대체하되, 반드시 verify_oulad_files()로 검증한 뒤 사용해야 한다.
    """
    print("다운로드 중...")
    resp = requests.get(url, stream=True, timeout=timeout, allow_redirects=True)
    resp.raise_for_status()
    content_type = resp.headers.get("Content-Type", "")
    if "zip" not in content_type and not resp.url.endswith(".zip"):
        raise RuntimeError(
            f"[N2] 공식 URL({url})이 zip이 아닌 응답을 반환했습니다 "
            f"(Content-Type={content_type!r}, 최종 URL={resp.url!r}). "
            "OU 사이트 이전으로 다운로드 엔드포인트가 깨졌을 가능성이 높습니다. "
            "download_oulad_from_kaggle_mirror()를 사용하고 verify_oulad_files()로 "
            "검증한 뒤 진행하세요."
        )
    with open("oulad.zip", "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    print("다운로드 완료")

    with zipfile.ZipFile("oulad.zip", "r") as z:
        z.extractall(out_dir)
        print(f"압축 해제 완료: {z.namelist()}")


def download_oulad_from_kaggle_mirror(out_dir: str = DATA_DIR, slug: str = KAGGLE_MIRROR_SLUG) -> None:
    """[N2] 공식 사이트가 응답하지 않을 때 사용하는 비공식 대체 경로.

    kagglehub 패키지가 필요하다(pip install kagglehub). 이 미러는 OU가 직접 관리하는
    출처가 아니므로, 반드시 verify_oulad_files()로 파일 구성과 행 수를 검증한 뒤에만
    분석에 사용해야 한다. 검증 없이 사용하지 말 것.
    """
    import shutil

    import kagglehub

    path = kagglehub.dataset_download(slug)
    os.makedirs(out_dir, exist_ok=True)
    for filename in os.listdir(path):
        src = os.path.join(path, filename)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(out_dir, filename))
    print(f"[N2] Kaggle 미러({slug})에서 '{out_dir}' 폴더로 복사 완료. verify_oulad_files() 필수 실행.")


def verify_oulad_files(data_dir: str = DATA_DIR) -> None:
    """[N2] 다운로드된 OULAD 파일이 원 논문 통계와 합치하는지 검증한다.

    공식 출처가 아닌 미러를 사용할 경우 이 검증을 통과해야만 분석에 사용해도 된다.
    검증 실패 시 AssertionError를 발생시켜 잘못된 데이터로 분석이 진행되지 않도록 한다.
    """
    required = [
        "courses.csv", "assessments.csv", "vle.csv", "studentInfo.csv",
        "studentRegistration.csv", "studentVle.csv", "studentAssessment.csv",
    ]
    missing = [f for f in required if not os.path.isfile(os.path.join(data_dir, f))]
    if missing:
        raise AssertionError(f"[N2] 필수 파일 누락: {missing}")

    vle_rows = sum(1 for _ in open(os.path.join(data_dir, "studentVle.csv"), encoding="utf-8")) - 1
    if abs(vle_rows - EXPECTED_VLE_ROWS) > EXPECTED_VLE_TOLERANCE:
        raise AssertionError(
            f"[N2] studentVle.csv 행 수({vle_rows:,})가 원 논문 보고치"
            f"({EXPECTED_VLE_ROWS:,} ± {EXPECTED_VLE_TOLERANCE:,})와 크게 다릅니다. "
            "이 소스를 신뢰할 수 없으니 다른 미러를 확인하세요."
        )
    print(f"[N2] 검증 통과: 필수 파일 7개 존재, studentVle.csv 행 수 {vle_rows:,}건 (기대치 근접).")


if __name__ == "__main__" and not os.path.isdir(DATA_DIR):
    try:
        download_oulad()
    except (requests.RequestException, RuntimeError) as e:
        print(f"공식 URL 다운로드 실패: {e}")
        print("대체 경로(Kaggle 미러)로 전환합니다. 이는 비공식 출처이므로 검증을 거칩니다.")
        download_oulad_from_kaggle_mirror()
    verify_oulad_files()

BASE = DATA_DIR + "/"

# =====================================================================
# STEP 1: CSV 로드 (studentRegistration 추가 로드 — [G1] 그룹 재정의에 필요)
# =====================================================================
student_info    = pd.read_csv(BASE + "studentInfo.csv")
student_reg     = pd.read_csv(BASE + "studentRegistration.csv")
student_vle     = pd.read_csv(BASE + "studentVle.csv")
student_assess  = pd.read_csv(BASE + "studentAssessment.csv")
assessments     = pd.read_csv(BASE + "assessments.csv")
vle             = pd.read_csv(BASE + "vle.csv")

STEM_MODULES = ["CCC", "DDD", "EEE", "FFF"]
VALID_ATTEMPT_MIN_DAYS = 56  # 8주 * 7일 — "유효 이수 시도"의 최소 등록 유지 기간

# =====================================================================
# STEP 2: 그룹 정의 재설계 [G1][G2][V1]
# =====================================================================
# 2-1. code_presentation을 정렬 가능한 순서 키로 변환
#      예: "2013B" → 2013*2+0=4026 (2월 학기), "2013J" → 2013*2+1=4027 (10월 학기)
def presentation_order(code_presentation: str) -> int:
    year = int(code_presentation[:4])
    season = 0 if code_presentation[4] == "B" else 1  # B=Feb, J=Oct
    return year * 2 + season


reg = student_reg.copy()
reg["presentation_order"] = reg["code_presentation"].map(presentation_order)

# 2-2. "유효 이수 시도" 판정: 등록 취소일이 결측(끝까지 유지) 이거나
#      등록~취소 기간이 8주(56일) 이상인 경우
reg["is_stem_module"] = reg["code_module"].isin(STEM_MODULES)
reg["valid_attempt"] = (
    reg["date_unregistration"].isna()
    | ((reg["date_unregistration"] - reg["date_registration"].fillna(0)) >= VALID_ATTEMPT_MIN_DAYS)
)
reg["stem_valid_attempt"] = reg["is_stem_module"] & reg["valid_attempt"]

# 2-3. [V1] 벡터화: 학생×presentation 단위로 "이 presentation에 STEM 유효 이수 시도가
#      있었는가"를 집계한 뒤, presentation_order 오름차순 cummax를 한 칸 shift하여
#      "그 이전 presentation에 유효 STEM 경험이 있었는가"를 구한다. (for-loop 없음)
level = (
    reg.groupby(["id_student", "presentation_order"])["stem_valid_attempt"]
    .any()
    .reset_index(name="has_stem_valid_this_presentation")
    .sort_values(["id_student", "presentation_order"])
)
level["cummax_incl_current"] = (
    level.groupby("id_student")["has_stem_valid_this_presentation"].cummax()
)
level["prior_stem_experience"] = (
    level.groupby("id_student")["cummax_incl_current"].shift(1).fillna(False).astype(bool)
)

# 2-4. STEM 모듈 등록 건 각각에 "직전까지의 선행 경험 여부"를 라벨링
stem_reg = reg[reg["is_stem_module"]].merge(
    level[["id_student", "presentation_order", "prior_stem_experience"]],
    on=["id_student", "presentation_order"],
    how="left",
)
stem_reg["group"] = np.where(
    stem_reg["prior_stem_experience"], "Experienced", "Novice"
)

# 2-5. 학생당 하나의 대표 (id_student, code_module, code_presentation)만 선택하여
#      analysis_cohort를 구성한다. [G2][B1의 전제]
#      - Novice: 그 학생의 가장 이른 STEM presentation (정의상 항상 Novice로 라벨됨)
#      - Experienced: 그 학생이 처음으로 "Experienced"로 라벨된 가장 이른 presentation
#      규칙: 한 학생이 Novice/Experienced 라벨을 모두 가질 수 있는 경우(여러 학기에
#      걸쳐 STEM을 재수강) Experienced를 우선 할당한다(중복 제거).
stem_reg_sorted = stem_reg.sort_values(["id_student", "presentation_order"])

experienced_rows = (
    stem_reg_sorted[stem_reg_sorted["group"] == "Experienced"]
    .groupby("id_student", as_index=False)
    .first()
)
students_experienced = set(experienced_rows["id_student"])

novice_rows = (
    stem_reg_sorted[~stem_reg_sorted["id_student"].isin(students_experienced)]
    .groupby("id_student", as_index=False)
    .first()
)

analysis_cohort = pd.concat([experienced_rows, novice_rows], ignore_index=True)
analysis_cohort = analysis_cohort[
    ["id_student", "code_module", "code_presentation", "group"]
].drop_duplicates(subset=["id_student"])

EXPERIENCED_KEYS = set(
    map(tuple, analysis_cohort.loc[analysis_cohort["group"] == "Experienced",
                                    ["id_student", "code_module", "code_presentation"]].values)
)
NOVICE_KEYS = set(
    map(tuple, analysis_cohort.loc[analysis_cohort["group"] == "Novice",
                                    ["id_student", "code_module", "code_presentation"]].values)
)
ALL_ANALYSIS_KEYS = EXPERIENCED_KEYS | NOVICE_KEYS

print(f"분석 대상 학생 수: {len(analysis_cohort):,}명")
print(f"  - STEM 도메인 경험군(Experienced): {len(EXPERIENCED_KEYS):,}명")
print(f"  - 초심자군(Novice):                {len(NOVICE_KEYS):,}명")

# =====================================================================
# STEP 3: VLE 로그 조인 — presentation 오염 버그 수정 [B1][B2]
# =====================================================================
# [B1] id_student만으로 필터링하지 않고, analysis_cohort의
#      (id_student, code_module, code_presentation) 조합으로 inner merge한다.
#      → 학생당 정확히 하나의 지정된 presentation 로그만 사용됨을 보장.
vle_cohort = student_vle.merge(
    analysis_cohort, on=["id_student", "code_module", "code_presentation"], how="inner"
)

# [B2] week 정의: date < 0 → week 0(pre-course, 분석에서 제외),
#      date 0~6 → week 1, 이후 7일 단위로 증가.
vle_cohort = vle_cohort[vle_cohort["date"] >= 0].copy()
vle_cohort["week"] = (vle_cohort["date"] // 7 + 1).astype(int)
vle_cohort = vle_cohort[vle_cohort["week"].between(1, 30)]

# =====================================================================
# STEP 4: 참여도 지수(EI) 산출 — look-ahead bias 제거 [E1]
# =====================================================================
weekly_clicks = (
    vle_cohort.groupby(["id_student", "group", "week"])["sum_click"].sum().reset_index()
)


def reindex_weeks(df: pd.DataFrame) -> pd.DataFrame:
    """1~30주 전체로 reindex하여 결측 주=0으로 채운다. (위치 인덱스 슬라이싱 금지)"""
    full_weeks = pd.DataFrame({"week": range(1, 31)})
    out = full_weeks.merge(df, on="week", how="left")
    out["sum_click"] = out["sum_click"].fillna(0)
    return out


def compute_activity_index(group_df: pd.DataFrame) -> pd.DataFrame:
    """[E1] 개인별 초기 4주(week 1~4) 평균 클릭 수를 baseline으로 삼아
    상대 활동지수(Activity Index) = click_t / baseline_individual 을 계산한다.
    baseline이 0인 학생(초기 4주 무활동)은 분석에서 제외한다(0/0 방지).
    """
    reindexed = reindex_weeks(group_df[["week", "sum_click"]])
    baseline_individual = reindexed.loc[reindexed["week"] <= 4, "sum_click"].mean()
    if baseline_individual == 0:
        return None
    reindexed["EI"] = reindexed["sum_click"] / baseline_individual
    return reindexed


records = []
for (sid, grp), g in weekly_clicks.groupby(["id_student", "group"]):
    ei_df = compute_activity_index(g)
    if ei_df is None:
        continue
    ei_df["id_student"] = sid
    ei_df["group"] = grp
    records.append(ei_df)

ei_long = pd.concat(records, ignore_index=True) if records else pd.DataFrame(
    columns=["week", "sum_click", "EI", "id_student", "group"]
)

# =====================================================================
# STEP 5: J-커브 탐지 (그룹별) — baseline은 population mean(EI)=1.0으로 수렴
# =====================================================================
def detect_jcurve(mean_ei: np.ndarray, weeks: np.ndarray):
    """population-averaged EI 곡선에서 J-curve 시작/최저/회복 시점을 찾는다.
    EI는 개인별 초기 4주 평균으로 정규화되었으므로 population baseline은
    이론상 1.0에 근접한다(각 개인의 최초 4주 평균 EI가 정의상 1.0이기 때문).

    [BUGFIX 2026-08, 실제 OULAD 데이터로 최초 실행 중 발견] 이전 구현은 "현재까지의
    최소값"을 갱신하는 매 시점마다 회복 여부를 함께 검사했기 때문에, 실제 데이터처럼
    EI가 단조 감소하지 않고 노이즈가 있는 경우 전역 최저점(t_bottom)에 도달하기 전에
    일시적으로 baseline을 넘는 구간을 "회복"으로 오판하여 t_recover < t_bottom이 되는
    모순이 발생했다(예: t_start=6, t_bottom=27인데 t_recover=7로 계산됨). 이를 2단계로
    분리하여 수정한다: (1) t_start 이후 구간에서 전역 최저점을 먼저 확정한 뒤,
    (2) 그 이후 구간에서만 회복 시점을 탐색한다.
    """
    baseline = 1.0
    threshold = baseline * 0.85
    partial_threshold = baseline * 0.70

    weeks = np.asarray(weeks)
    mean_ei = np.asarray(mean_ei, dtype=float)

    below_mask = mean_ei < threshold
    if not below_mask.any():
        return {
            "baseline": baseline, "t_start": None, "t_bottom": None,
            "bottom_val": mean_ei.min() if len(mean_ei) else None,
            "t_recover": None, "J_depth": None, "J_width": None,
            "recovery_type": "J-커브 미관측(임계값 미달)",
        }
    t_start = int(weeks[below_mask][0])

    # 1단계: t_start 이후 구간에서 전역 최저점을 확정한다.
    post_start_mask = weeks >= t_start
    post_weeks = weeks[post_start_mask]
    post_ei = mean_ei[post_start_mask]
    bottom_idx = int(np.argmin(post_ei))
    t_bottom = int(post_weeks[bottom_idx])
    bottom_val = float(post_ei[bottom_idx])

    # 2단계: 전역 최저점 이후 구간에서만 회복 시점을 탐색한다.
    post_bottom_mask = post_weeks > t_bottom
    after_weeks = post_weeks[post_bottom_mask]
    after_ei = post_ei[post_bottom_mask]

    t_recover = None
    t_recover_partial = None
    for w, ei in zip(after_weeks, after_ei):
        if ei >= baseline and t_recover is None:
            t_recover = int(w)
            break
        if ei >= partial_threshold and t_recover_partial is None:
            t_recover_partial = int(w)

    if t_recover is not None:
        recovery_type = "완전 회복"
        t_recover_final = t_recover
    elif t_recover_partial is not None:
        recovery_type = "부분 회복 (70% 기준)"
        t_recover_final = t_recover_partial
    else:
        recovery_type = "측정기간 내 미회복"
        t_recover_final = None

    j_depth = round(baseline - bottom_val, 4)
    j_width = int(t_recover_final - t_start) if t_recover_final is not None else int(weeks[-1] - t_start)

    return {
        "baseline": baseline,
        "t_start": t_start,
        "t_bottom": t_bottom,
        "bottom_val": bottom_val,
        "t_recover": t_recover_final,
        "J_depth": j_depth,
        "J_width": j_width,
        "recovery_type": recovery_type,
    }


jcurve_results = {}
for grp in ["Novice", "Experienced"]:
    sub = ei_long[ei_long["group"] == grp]
    mean_ei = sub.groupby("week")["EI"].mean().reindex(range(1, 31), fill_value=0)
    jcurve_results[grp] = detect_jcurve(mean_ei.values, mean_ei.index.values)
    print(f"[{grp}] {jcurve_results[grp]}")

# 논문 표1의 주 실증 대상은 Novice(초심자군)
BASE_DEPTH = jcurve_results["Novice"]["J_depth"]
BASE_WIDTH = jcurve_results["Novice"]["J_width"]

# =====================================================================
# STEP 6: 통계 검정 — Welch t-test, Mann-Whitney U, 효과크기 [S1]
# =====================================================================
def per_student_jdepth(ei_long_df: pd.DataFrame, group_name: str, min_weeks: int = 0) -> np.ndarray:
    """학생별 J_depth(1.0 - 개인 최저 EI)를 계산한다.
    min_weeks: 조기 이탈자 제외 기준(활동 주차 수). 0이면 전체표본.
    """
    out = []
    for sid, g in ei_long_df[ei_long_df["group"] == group_name].groupby("id_student"):
        active_weeks = (g["sum_click"] > 0).sum()
        if active_weeks < min_weeks:
            continue
        out.append(1.0 - g["EI"].min())
    return np.array(out)


def welch_and_effect_sizes(a: np.ndarray, b: np.ndarray) -> dict:
    """[S1] Welch's t-test + Mann-Whitney U + Cohen's d + rank-biserial correlation."""
    t_stat, p_t = stats.ttest_ind(a, b, equal_var=False)
    u_stat, p_u = stats.mannwhitneyu(a, b, alternative="two-sided")

    n1, n2 = len(a), len(b)
    pooled_sd = np.sqrt(((n1 - 1) * a.var(ddof=1) + (n2 - 1) * b.var(ddof=1)) / (n1 + n2 - 2))
    cohens_d = (a.mean() - b.mean()) / pooled_sd if pooled_sd > 0 else np.nan

    rank_biserial = 1 - (2 * u_stat) / (n1 * n2) if (n1 * n2) > 0 else np.nan

    return {
        "n1": n1, "n2": n2,
        "mean1": a.mean(), "mean2": b.mean(),
        "sd1": a.std(ddof=1), "sd2": b.std(ddof=1),
        "welch_t": t_stat, "welch_p": p_t,
        "mannwhitney_u": u_stat, "mannwhitney_p": p_u,
        "cohens_d": cohens_d,
        "rank_biserial": rank_biserial,
    }


jd_novice_all = per_student_jdepth(ei_long, "Novice", min_weeks=0)
jd_exp_all = per_student_jdepth(ei_long, "Experienced", min_weeks=0)
jd_novice_5w = per_student_jdepth(ei_long, "Novice", min_weeks=5)
jd_exp_5w = per_student_jdepth(ei_long, "Experienced", min_weeks=5)

stats_all_sample = welch_and_effect_sizes(jd_novice_all, jd_exp_all)
stats_5w_sample = welch_and_effect_sizes(jd_novice_5w, jd_exp_5w)

print("\n[통계 검정 — 전체표본]")
print(stats_all_sample)
print("\n[통계 검정 — 5주 이상 활동표본 (조기 이탈자 제외)]")
print(stats_5w_sample)

# =====================================================================
# STEP 7: 산출 CSV — 그룹별 n/sd/95% CI 포함 [C1]
# =====================================================================
def ci95(mean: float, sd: float, n: int) -> tuple:
    if n <= 1:
        return (np.nan, np.nan)
    se = sd / np.sqrt(n)
    margin = 1.96 * se
    return (mean - margin, mean + margin)


weekly_summary_rows = []
for grp in ["Novice", "Experienced"]:
    sub = ei_long[ei_long["group"] == grp]
    for week, g in sub.groupby("week"):
        n = g["id_student"].nunique()
        mean_ei = g["EI"].mean()
        sd_ei = g["EI"].std(ddof=1)
        lo, hi = ci95(mean_ei, sd_ei, n)
        weekly_summary_rows.append({
            "group": grp, "week": week, "n": n,
            "mean_EI": mean_ei, "sd_EI": sd_ei,
            "ci95_low": lo, "ci95_high": hi,
        })

weekly_ei_comparison = pd.DataFrame(weekly_summary_rows).sort_values(["group", "week"])
weekly_ei_comparison.to_csv("weekly_ei_comparison.csv", index=False)

group_stats_comparison = pd.DataFrame([
    {"sample": "all", **stats_all_sample},
    {"sample": "active_5w_plus", **stats_5w_sample},
])
group_stats_comparison.to_csv("group_stats_comparison.csv", index=False)

# [C2] "변경 전(v3)" 수치는 재현 스크립트가 없어 v3 실행 로그를 하드코딩한다.
# 출처: 260414_hs-jcurve-citizen-developer.ipynb 실행 로그 (highest_education 기반
# "비전공자" 정의, 13,936명, J_depth=0.2878, J_width=27주).
summary_revision_comparison = pd.DataFrame([
    {
        "지표": "그룹 정의",
        "변경 전(v3, 하드코딩 — 출처: v3 실행 로그)": "highest_education 기반 비전공자 (13,936명)",
        "변경 후(v4)": f"studentRegistration 기반 STEM 초심자군(Novice) ({len(NOVICE_KEYS):,}명)",
    },
    {
        "지표": "J_depth",
        "변경 전(v3, 하드코딩 — 출처: v3 실행 로그)": 0.2878,
        "변경 후(v4)": BASE_DEPTH,
    },
    {
        "지표": "J_width(주)",
        "변경 전(v3, 하드코딩 — 출처: v3 실행 로그)": 27,
        "변경 후(v4)": BASE_WIDTH,
    },
])
summary_revision_comparison.to_csv("summary_revision_comparison.csv", index=False, encoding="utf-8-sig")

# =====================================================================
# STEP 8: 시각화 (그룹 비교 J-커브)
# =====================================================================
plt.rcParams["axes.unicode_minus"] = False
plt.figure(figsize=(10, 4))
for grp, color in [("Novice", "#2c7bb6"), ("Experienced", "#1a9641")]:
    mean_ei = ei_long[ei_long["group"] == grp].groupby("week")["EI"].mean().reindex(
        range(1, 31), fill_value=0
    )
    plt.plot(mean_ei.index, mean_ei.values, "o-", lw=2, color=color, label=f"{grp} 평균 활동지수")
plt.axhline(1.0, color="gray", ls="--", alpha=0.7, label="개인별 초기 4주 평균 기준선(=1.0)")
plt.xlabel("학습 주차")
plt.ylabel("상대 활동지수 (Activity Index)")
plt.title("STEM 도메인 경험군/초심자군 J-커브 비교 (v4, presentation 오염 수정)")
plt.legend(fontsize=8)
plt.tight_layout()
plt.savefig("jcurve_v4.png", dpi=120)

# =====================================================================
# STEP 9: Harmony Search 최적화 — cost 항 추가 [H1][H2]
# =====================================================================
# HS 파라미터 (선행 연구 권고 범위 참고, 실증 추정값 아님)
HMS, HMCR, PAR, BW = 10, 0.85, 0.35, 0.1
MAX_ITER, ALPHA, BETA = 1000, 0.6, 0.4

# [H2] 아래 감소율 계수(0.40, 0.10, 0.50)와 cost 가중치(COST_WEIGHT, GAMMA1, GAMMA2)는
# OULAD로부터 실증 추정된 값이 아니라 "가정 기반 시뮬레이션 계수"이다.
# 실증값은 BASE_DEPTH, BASE_WIDTH(위 STEP 5에서 산출) 뿐이다.
COST_WEIGHT = 6.0   # 모듈 재설계·개입 체계 구축의 운영/설계 비용 가중치 (가정치)
GAMMA1, GAMMA2 = 1.0, 1.0  # x1, x2 각각에 대한 비용의 볼록성(이차) 계수 (가정치)


def simulate_jcurve(x1: float, x2: float) -> tuple:
    """x1: 모듈 순서 최적화(0~1), x2: 개입 시점 최적화(0~1).
    [H1] 이전 버전은 cost 항이 없어 x1, x2가 커질수록 J_depth/J_width가 단조
    감소하기만 했다. 이 경우 목적함수도 단조 감소이므로 최적해가 항상
    코너값(x1=x2=1.0)에 자명하게 수렴하는 결함이 있었다.
    """
    depth = BASE_DEPTH * (1 - 0.40 * x1 - 0.10 * x1 * x2)
    width = BASE_WIDTH * (1 - 0.50 * x2 - 0.10 * x1 * x2)
    depth += np.random.normal(0, 0.005)
    width += np.random.normal(0, 0.3)
    return max(depth, 0.0), max(width, 0.0)


def implementation_cost(x1: float, x2: float) -> float:
    """[H1] 모듈 재설계(x1) 및 개입 시스템 구축(x2)에 따르는 이차(볼록) 비용.
    x가 커질수록(더 급진적인 재설계/더 촘촘한 개입) 비용이 가속적으로 증가하도록
    설계하여, 목적함수가 x1=x2=1.0에서 자명하게 최소가 되지 않도록 한다.
    """
    return COST_WEIGHT * (GAMMA1 * x1 ** 2 + GAMMA2 * x2 ** 2)


def fitness(x: list) -> float:
    d, w = simulate_jcurve(x[0], x[1])
    return ALPHA * d + BETA * w + implementation_cost(x[0], x[1])


random.seed(42)
np.random.seed(42)

HM = [[random.uniform(0, 1) for _ in range(2)] for _ in range(HMS)]
HM_fitness = [fitness(h) for h in HM]
best_hist = []

for _ in range(MAX_ITER):
    new_h = []
    for j in range(2):
        if random.random() < HMCR:
            val = random.choice(HM)[j]
            if random.random() < PAR:
                val = max(0.0, min(1.0, val + random.uniform(-BW, BW)))
        else:
            val = random.uniform(0, 1)
        new_h.append(val)
    nf = fitness(new_h)
    wi = HM_fitness.index(max(HM_fitness))
    if nf < HM_fitness[wi]:
        HM[wi], HM_fitness[wi] = new_h, nf
    best_hist.append(min(HM_fitness))

best_idx = HM_fitness.index(min(HM_fitness))
best_x = HM[best_idx]
# 노이즈 없는 확정값 + cost 포함 목적함수값
best_d = BASE_DEPTH * (1 - 0.40 * best_x[0] - 0.10 * best_x[0] * best_x[1])
best_w = BASE_WIDTH * (1 - 0.50 * best_x[1] - 0.10 * best_x[0] * best_x[1])
best_cost = implementation_cost(best_x[0], best_x[1])
best_f = ALPHA * best_d + BETA * best_w + best_cost

print(f"\n[ HS 최적화 결과 (cost 항 포함) ]")
print(f"x1 (모듈 순서)  = {best_x[0]:.4f}")
print(f"x2 (개입 시점)  = {best_x[1]:.4f}")
print(f"최적 J_depth    = {best_d:.4f}  (개선: {(1 - best_d / BASE_DEPTH) * 100:.1f}%)")
print(f"최적 J_width    = {best_w:.2f}주  (개선: {(1 - best_w / BASE_WIDTH) * 100:.1f}%)")
print(f"implementation_cost = {best_cost:.4f}")
print(f"f(x) = {best_f:.4f}")
print("주의: 위 x1,x2 감소율 계수 및 cost 계수는 가정 기반 시뮬레이션 값이다 [H2].")

print(f"\n[ Sensitivity Analysis: α/β 조합 (cost 항 포함) ]")
for a in [0.3, 0.5, 0.6, 0.7]:
    b = round(1 - a, 1)
    f_val = a * best_d + b * best_w + best_cost
    print(f"alpha={a:.1f} beta={b:.1f} f(x)={f_val:.4f}")

# =====================================================================
# STEP 10: 시각화 (HS 수렴 곡선 + 비교 boxplot)
# =====================================================================
fig, axes = plt.subplots(1, 3, figsize=(15, 4))

axes[0].plot(best_hist, color="#d7191c", lw=1.5)
axes[0].set_xlabel("반복 횟수")
axes[0].set_ylabel("목적함수 f(x) (cost 포함)")
axes[0].set_title("HS 수렴 곡선 (v4)")

w_sim = np.linspace(0, 30, 300)


def jcurve_shape(w, depth, width, start=3):
    center = start + width / 2
    sigma = max(width / 3, 0.5)
    dip = depth * np.exp(-0.5 * ((w - center) / sigma) ** 2)
    return 1.0 - dip


orig = jcurve_shape(w_sim, BASE_DEPTH, BASE_WIDTH)
opt = jcurve_shape(w_sim, best_d, best_w)

axes[1].plot(w_sim, orig, "--", color="#d7191c", lw=2,
             label=f"기존 (depth={BASE_DEPTH:.3f}, width={BASE_WIDTH}주)")
axes[1].plot(w_sim, opt, "-", color="#1a9641", lw=2,
             label=f"HS최적, cost 포함 (depth={best_d:.3f}, width={best_w:.1f}주)")
axes[1].fill_between(w_sim, opt, orig, alpha=0.12, color="#1a9641", label="개선 영역")
axes[1].set_xlabel("학습 주차")
axes[1].set_ylabel("상대 활동지수")
axes[1].set_title("기존 vs HS 최적화(cost 포함) J-커브 비교")
axes[1].legend(fontsize=7)

axes[2].boxplot([jd_novice_all, jd_exp_all], tick_labels=["초심자군(Novice)", "경험군(Experienced)"],
                patch_artist=True, boxprops=dict(facecolor="#b2d8f7"),
                medianprops=dict(color="#d7191c", lw=2))
axes[2].set_ylabel("개인별 J_depth")
axes[2].set_title(
    f"J_depth 분포 비교\n(Welch t={stats_all_sample['welch_t']:.3f}, "
    f"p={stats_all_sample['welch_p']:.4f}, d={stats_all_sample['cohens_d']:.3f})"
)

plt.suptitle("HS 기반 J-커브 최적화 분석 결과 (v4)", fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig("hs_result_v4.png", dpi=120, bbox_inches="tight")
