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
import scholarly.publication_parser as publication_parser

# ── 설정 ──────────────────────────────────────────────────────────────
# Google Scholar 프로필 URL에서 user=XXXXXXXX 부분이 SCHOLAR_ID 입니다.
# 예: https://scholar.google.com/citations?user=JHrp3gcAAAAJ -> JHrp3gcAAAAJ
#
# 아래 ID는 웹 검색으로 찾은 강미숙(Misook Kang) 교수님의 Google Scholar
# 프로필입니다. 본인 개인 프로필로 바꾸고 싶다면 이 값만 교체하면 됩니다.
SCHOLAR_ID = "JHrp3gcAAAAJ"

# 저자 이름이 잘린 논문을 개별 페이지로 보강하는 시도 횟수 상한.
# 논문 수가 많은 저자는 이 기능 하나 때문에 전체 실행 시간이 너무 길어질
# 수 있어서, 최대 이만큼만 시도하고 나머지는 잘린 이름 그대로 둡니다.
MAX_AUTHOR_EXPANSIONS = 40

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "publications.json"


def build_scholar_url(scholar_id: str, author_pub_id: str) -> str:
    """개별 논문의 Google Scholar 상세 페이지 링크를 생성합니다."""
    return (
        "https://scholar.google.com/citations?"
        f"view_op=view_citation&hl=en&user={scholar_id}&citation_for_view={author_pub_id}"
    )


def patch_author_names() -> None:
    """scholarly는 논문 목록 페이지를 가져올 때 제목/연도/저널만 파싱하고
    저자 이름은 버립니다 (개별 논문 페이지를 또 열어야 얻을 수 있는 구조라서).
    이미 받아온 같은 HTML 안에 저자 이름 줄이 그대로 들어있으므로,
    추가 요청 없이 그 줄만 더 읽어오도록 파서를 살짝 보강합니다.
    """
    original = publication_parser.PublicationParser._citation_pub

    def patched(self, __data, publication):
        publication = original(self, __data, publication)
        gray_lines = __data.find_all("div", class_="gs_gray")
        if gray_lines:
            publication["bib"]["author"] = gray_lines[0].text.strip()
        return publication

    publication_parser.PublicationParser._citation_pub = patched


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


def expand_truncated_authors(pub: dict, authors_text: str, expanded_so_far: int) -> str:
    """목록 페이지에서 저자 이름이 '…' 로 잘려있는 논문만, 그 논문의 개별
    페이지를 한 번 더 열어 전체 저자 목록을 가져옵니다. (실패해도 스크립트가
    멈추지 않고 잘린 이름을 그대로 씁니다. MAX_AUTHOR_EXPANSIONS를 넘으면
    더 이상 시도하지 않습니다.)
    """
    if not authors_text.rstrip().endswith(("…", "...")):
        return authors_text
    if expanded_so_far >= MAX_AUTHOR_EXPANSIONS:
        return authors_text
    try:
        filled = scholarly.fill(pub)
        full_author = filled.get("bib", {}).get("author", "")
        if full_author:
            return full_author.replace(" and ", ", ")
    except Exception as e:
        print(f"  ↳ 저자 전체 목록 가져오기 실패, 잘린 목록 유지: {e}")
    return authors_text


def fetch() -> dict:
    patch_author_names()
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

    # 여기부터는 부가 기능(저자 보강)이라, 막힌 논문 하나 때문에 오래
    # 기다리지 않도록 재시도 횟수와 타임아웃을 줄입니다.
    scholarly.set_retries(2)
    scholarly.set_timeout(10)

    publications = []
    expanded_count = 0
    for pub in pubs_raw:
        bib = pub.get("bib", {})
        author_pub_id = pub.get("author_pub_id", "")
        authors_text = bib.get("author", "")
        expanded = expand_truncated_authors(pub, authors_text, expanded_count)
        if expanded != authors_text:
            expanded_count += 1
        publications.append(
            {
                "title": bib.get("title", ""),
                "authors": expanded,
                "year": str(bib.get("pub_year") or ""),
                "venue": bib.get("citation", bib.get("journal", "")),
                "num_citations": pub.get("num_citations", 0),
                "link": build_scholar_url(SCHOLAR_ID, author_pub_id) if author_pub_id else "",
            }
        )
    if expanded_count:
        print(f"  ↳ 저자 목록이 잘려있던 논문 중 {expanded_count}건, 전체 이름으로 보강함 (상한 {MAX_AUTHOR_EXPANSIONS}건)")

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
