"""
Google Scholar 프로필에서 논문 목록을 가져와 docs/publications.json으로 저장합니다.

로컬 실행:
    pip install -r requirements.txt
    python fetch_publications.py

GitHub Actions에서는 .github/workflows/update-publications.yml 이 이 스크립트를
주기적으로 실행하고, 결과를 자동으로 커밋합니다.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from scholarly import scholarly, ProxyGenerator

# ── 설정 ──────────────────────────────────────────────────────────────
# Google Scholar 프로필 URL에서 user=XXXXXXXX 부분이 SCHOLAR_ID 입니다.
# 예: https://scholar.google.com/citations?user=JHrp3gcAAAAJ -> JHrp3gcAAAAJ
#
# 아래 ID는 웹 검색으로 찾은 강미숙(Misook Kang) 교수님의 Google Scholar
# 프로필입니다. 본인 개인 프로필로 바꾸고 싶다면 이 값만 교체하면 됩니다.
SCHOLAR_ID = "JHrp3gcAAAAJ"

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "publications.json"


def build_scholar_url(scholar_id: str, author_pub_id: str) -> str:
    """개별 논문의 Google Scholar 상세 페이지 링크를 생성합니다."""
    return (
        "https://scholar.google.com/citations?"
        f"view_op=view_citation&hl=en&user={scholar_id}&citation_for_view={author_pub_id}"
    )


def setup_proxy() -> None:
    """GitHub Actions 서버 IP는 Google Scholar에 자주 차단당하기 때문에,
    무료 프록시를 거쳐 우회를 시도합니다. (몇 분 걸릴 수 있고, 100% 보장되진 않습니다.)
    """
    print("프록시 준비 중... (최대 몇 분 걸릴 수 있어요)")
    try:
        pg = ProxyGenerator()
        pg.FreeProxies()
        scholarly.use_proxy(pg)
        print("프록시 연결 성공, 이어서 진행합니다.")
    except Exception as e:  # 프록시를 못 구해도 일단 직접 연결로 시도는 해봅니다.
        print(f"프록시 설정 실패({e}) — 직접 연결로 시도합니다.")


def fetch() -> dict:
    setup_proxy()
    print(f"[1/2] {SCHOLAR_ID} 저자 정보를 가져오는 중...")
    author = scholarly.search_author_id(SCHOLAR_ID)
    # sections=['publications']만 채우면 논문마다 추가 요청을 보내지 않고
    # 저자 페이지 목록에서 바로 제목/저널/연도/피인용수를 가져옵니다.
    # (개별 논문 fill()은 요청 수가 급격히 늘어나 차단 위험이 커서 사용하지 않습니다.)
    author = scholarly.fill(
        author,
        sections=["basics", "indices", "publications"],
        sortby="year",
    )

    pubs_raw = author.get("publications", [])
    print(f"[2/2] 논문 {len(pubs_raw)}건 정리 중...")

    publications = []
    for pub in pubs_raw:
        bib = pub.get("bib", {})
        author_pub_id = pub.get("author_pub_id", "")
        publications.append(
            {
                "title": bib.get("title", ""),
                "authors": bib.get("author", ""),
                "year": bib.get("pub_year", ""),
                "venue": bib.get("citation", bib.get("journal", "")),
                "num_citations": pub.get("num_citations", 0),
                "link": build_scholar_url(SCHOLAR_ID, author_pub_id) if author_pub_id else "",
            }
        )

    # 연도 내림차순 정렬 (연도 정보 없는 항목은 맨 뒤로)
    publications.sort(key=lambda p: p["year"] or "0", reverse=True)

    return {
        "name": author.get("name", ""),
        "affiliation": author.get("affiliation", ""),
        "citedby": author.get("citedby", 0),
        "hindex": author.get("hindex", 0),
        "i10index": author.get("i10index", 0),
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "publications": publications,
    }


def main():
    data = fetch()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"저장 완료 → {OUTPUT_PATH} ({len(data['publications'])}건)")


if __name__ == "__main__":
    main()
