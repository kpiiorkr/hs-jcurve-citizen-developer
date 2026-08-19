# ktcloud TECH UP 정적 사이트

## 실행

```bash
python -m http.server 8000
```

브라우저에서 `http://localhost:8000`으로 접속하세요.

## 배포

GitHub Pages 기준:

1. 변경사항을 `main` 또는 배포 브랜치에 반영
2. Repository Settings > Pages
3. Source를 `Deploy from a branch`로 선택
4. 브랜치와 루트를 지정 후 저장

## 수정 프로세스

1. 기능별 브랜치 생성
2. 수정 후 커밋
3. Pull Request 생성
4. 리뷰 후 머지

## 변경 이력

- 공통 떠다니는 채널 버튼 제거
- 인스타그램 연결 및 인스타 이미지 제거
- 메인페이지의 지원 확인 버튼 제거
- 모든 지원 CTA를 동일한 신청 폼으로 통일
- `/frontend` 직접 접근 가능한 정적 페이지 추가
