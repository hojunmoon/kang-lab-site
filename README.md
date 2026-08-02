# Kang Lab 홈페이지 — Google Scholar 자동 연동

Google Scholar 프로필에서 논문 목록을 매일 자동으로 가져와 정적 홈페이지에
표시하는 프로젝트입니다. GitHub Actions가 스크래핑 → `docs/publications.json`
갱신 → 커밋까지 처리하고, GitHub Pages가 `docs/` 폴더를 그대로 배포합니다.

```
Google Scholar  →  scripts/fetch_publications.py  →  docs/publications.json  →  GitHub Pages
                    (GitHub Actions, 매일 1회 자동 실행)
```

## 폴더 구조

```
.github/workflows/update-publications.yml   # 매일 자동 실행되는 워크플로
scripts/fetch_publications.py               # Scholar 스크래핑 스크립트
scripts/requirements.txt
docs/index.html                             # 홈페이지 본문
docs/styles.css
docs/app.js                                  # publications.json을 읽어 렌더링
docs/publications.json                       # 데이터 (자동 갱신됨, 지금은 placeholder)
```

## 배포 방법 (최초 1회)

1. **GitHub에 새 리포지토리 생성** 후, 이 폴더 전체 내용을 그대로 push 합니다.

   ```bash
   git init
   git add .
   git commit -m "init: lab site"
   git branch -M main
   git remote add origin <본인 리포지토리 URL>
   git push -u origin main
   ```

2. **Actions 쓰기 권한 켜기** (자동 커밋을 위해 필요합니다)
   리포지토리 → **Settings → Actions → General → Workflow permissions**
   → **Read and write permissions** 선택 → 저장

3. **GitHub Pages 켜기**
   리포지토리 → **Settings → Pages** → Source: **Deploy from a branch**
   → Branch: `main`, 폴더: `/docs` 선택 → 저장
   (몇 분 후 `https://<계정>.github.io/<리포지토리>/` 로 접속 가능)

4. **첫 데이터 채우기**
   리포지토리 → **Actions** 탭 → `Update publications` 워크플로 선택 →
   **Run workflow** 버튼으로 수동 1회 실행 → `docs/publications.json`이
   실제 논문 목록으로 자동 커밋되는지 확인합니다.
   (다음부터는 매일 자동으로 실행됩니다.)

## 본인 프로필로 바꾸기

`scripts/fetch_publications.py` 상단의 `SCHOLAR_ID` 값을 원하는 Google
Scholar 프로필 ID로 바꾸면 됩니다.

```python
SCHOLAR_ID = "JHrp3gcAAAAJ"  # 프로필 URL의 user=XXXXXXXX 부분
```

지금 기본값은 웹 검색으로 찾은 강미숙 교수님의 Scholar 프로필입니다 —
연구실 전체 논문 목록을 보여줄지, 본인 개인 프로필을 보여줄지에 맞게
바꿔서 사용하세요.

## 참고 / 주의사항

- Google Scholar는 공식 API를 제공하지 않아 `scholarly` 라이브러리가
  페이지를 직접 파싱합니다. 요청이 너무 잦으면 일시적으로 차단될 수 있어
  기본 스케줄을 **하루 1회**로 설정해 두었습니다 (필요하면
  `.github/workflows/update-publications.yml`의 `cron` 값을 조정하세요).
- 워크플로가 실패하면 **Actions 탭 → 실패한 실행 → 로그**에서 원인을
  확인할 수 있습니다 (대개 일시적인 차단이며, 다음 스케줄 실행 시
  자동으로 복구됩니다).
- `docs/publications.json`은 지금 placeholder(예시) 데이터입니다.
  워크플로를 한 번 실행하면 실제 데이터로 교체됩니다.
