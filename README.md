# 우아경비율 (wooagyeongbi.wooahouse.com)

국세청 고시 제2026-14호(2025년 귀속 경비율)의 업종코드 1,542개 단순경비율(기본율·초과율)·기준경비율을 업종별로 정리한 정적 사이트.

- 데이터: `data/rates_2025.json` ([업종코드, 업종명, 단순경비율 기본율, 초과율, 기준경비율]). 원본은 nts.go.kr 고시 첨부(hwpx, section0.xml의 표)이며 공공데이터포털 15036323은 다운로드가 막혀 있어 NTS 공지에서 직접 받음.
- 빌드: `python scripts/build_site.py`
- 갱신: 매년 3월 전후 새 고시(다음 귀속연도)가 나오면 hwpx 표를 다시 파싱해 rates 파일 교체, `YEAR`/NOTE 문구 수정
