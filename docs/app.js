// publications.json 을 불러와 통계 · 연도별 논문 목록을 렌더링합니다.
// 이 파일 자체는 데이터를 만들지 않습니다 — 실제 데이터는
// scripts/fetch_publications.py 가 GitHub Actions로 주기적으로 갱신합니다.

const listEl = document.getElementById("pubs-list");
const yearFilterEl = document.getElementById("year-filter");
const updatedLineEl = document.getElementById("updated-line");
const scholarLinkEl = document.getElementById("scholar-link");

let allPublications = [];

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

function renderStats(data) {
  document.getElementById("stat-citedby").textContent = data.citedby ?? "—";
  document.getElementById("stat-hindex").textContent = data.hindex ?? "—";
  document.getElementById("stat-i10index").textContent = data.i10index ?? "—";
}

function renderPublications(publications) {
  if (!publications.length) {
    listEl.innerHTML = `<p class="pubs__empty">표시할 논문이 없습니다.</p>`;
    return;
  }

  const groups = new Map();
  for (const pub of publications) {
    const key = pub.year || "연도 미상";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(pub);
  }

  const years = [...groups.keys()].sort((a, b) => (b > a ? 1 : -1));

  listEl.innerHTML = years
    .map((year) => {
      const items = groups
        .get(year)
        .map((pub) => {
          const citations = Number(pub.num_citations) || 0;
          const titleHtml = pub.link
            ? `<a href="${escapeHtml(pub.link)}" target="_blank" rel="noopener">${escapeHtml(pub.title)}</a>`
            : escapeHtml(pub.title);
          return `
            <div class="pub">
              <div>
                <p class="pub__title">${titleHtml}</p>
                <p class="pub__meta">${escapeHtml(pub.venue)}${pub.venue && pub.authors ? " · " : ""}${escapeHtml(pub.authors)}</p>
              </div>
              <span class="pub__badge" data-zero="${citations === 0}" title="피인용 ${citations}회">${citations}</span>
            </div>`;
        })
        .join("");

      return `
        <div class="year-group" data-year="${escapeHtml(year)}">
          <p class="year-group__label">${escapeHtml(year)}</p>
          ${items}
        </div>`;
    })
    .join("");
}

function populateYearFilter(publications) {
  const years = [...new Set(publications.map((p) => p.year).filter(Boolean))].sort((a, b) =>
    b > a ? 1 : -1
  );
  for (const year of years) {
    const opt = document.createElement("option");
    opt.value = year;
    opt.textContent = year;
    yearFilterEl.appendChild(opt);
  }
}

yearFilterEl.addEventListener("change", () => {
  const value = yearFilterEl.value;
  const filtered =
    value === "all" ? allPublications : allPublications.filter((p) => p.year === value);
  renderPublications(filtered);
});

async function init() {
  try {
    const res = await fetch("publications.json", { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    allPublications = data.publications || [];
    renderStats(data);
    populateYearFilter(allPublications);
    renderPublications(allPublications);

    updatedLineEl.textContent = data.updated
      ? `마지막 업데이트 ${data.updated} · 매일 자동 갱신`
      : "";
    if (data.name) {
      scholarLinkEl.textContent = `${data.name}의 Google Scholar 프로필 전체 보기 →`;
    }
  } catch (err) {
    listEl.innerHTML = `<p class="pubs__empty">논문 목록을 불러오지 못했습니다. (${escapeHtml(
      err.message
    )})</p>`;
    updatedLineEl.textContent = "";
    console.error(err);
  }
}

init();
