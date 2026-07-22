from datetime import datetime
import os
import pandas as pd
import requests

SAVE_PATH = 'stock_rotation_20days.csv'
MAX_DAYS = 20  # 유지할 최대 일수 (20일)

# 1. 오늘 날짜 (YYYY-MM-DD)
today_date = datetime.now().strftime('%Y-%m-%d')

# 2. 네이버 금융 거래량/거래대금 상위 페이지 요청
url = 'https://finance.naver.com/sise/sise_quant.naver'
headers = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )
}

response = requests.get(url, headers=headers)
response.encoding = 'euc-kr'

tables = pd.read_html(response.text)
df = tables[1].dropna(subset=['종목명']).copy()
df = df[df['N'] != 'N']


# 3. ETF 제외 필터
def is_not_etf(row):
  name = str(row['종목명'])
  etf_keywords = [
      'ETF',
      'ETN',
      'KODEX',
      'TIGER',
      'RISE',
      'SOL',
      'ACE',
      'KBSTAR',
      'HANARO',
      'KOSEF',
      'ARIRANG',
      'TIMEFOLIO',
      'WOORI',
      'PLUS',
  ]
  return not any(keyword in name for keyword in etf_keywords)


df_filtered = df[df.apply(is_not_etf, axis=1)].copy()

# 4. 숫자 변환
df_filtered['거래대금'] = (
    df_filtered['거래대금'].astype(str).str.replace(',', '').astype(float)
)
df_filtered['시가총액'] = (
    df_filtered['시가총액'].astype(str).str.replace(',', '').astype(float)
)

# 5. 거래대금 상위 30개 추출
top30_df = (
    df_filtered.sort_values(by='거래대금', ascending=False).head(30).copy()
)

# 6. 거래대금 / 시가총액 비율(%) 계산
top30_df['비율(%)'] = (
    (top30_df['거래대금'] * 1_000_000)
    / (top30_df['시가총액'] * 100_000_000)
) * 100

# 7. 비율 순 내림차순 정렬
result_df = top30_df.sort_values(by='비율(%)', ascending=False).reset_index(
    drop=True
)

result_df['날짜'] = today_date
result_df['순위'] = result_df.index + 1

final_df = result_df[
    ['날짜', '순위', '종목명', '현재가', '거래대금', '시가총액', '비율(%)']
]

# 8. [핵심] 최근 20일 데이터만 유지하는 저장 로직
if os.path.exists(SAVE_PATH):
  existing_df = pd.read_csv(SAVE_PATH)

  # 오늘 이미 실행된 기록이 있다면 삭제 후 새로 덮어씀 (당일 중복 방지)
  existing_df = existing_df[existing_df['날짜'] != today_date]

  # 기존 데이터와 오늘 데이터 합치기
  updated_df = pd.concat([existing_df, final_df], ignore_index=True)

  # 저장된 Unique 날짜 목록 가져오기 (오래된 순)
  unique_dates = sorted(updated_df['날짜'].unique())

  # 저장된 날짜가 20일을 초과하면 가장 오래된 날짜 제거
  if len(unique_dates) > MAX_DAYS:
    # 뒤에서부터 20개 날짜만 선택 (가장 최신 20일)
    keep_dates = unique_dates[-MAX_DAYS:]
    updated_df = updated_df[updated_df['날짜'].isin(keep_dates)]
    print(f'20일 초과 데이터 삭제 완료. (현재 유지 중인 날짜: {len(keep_dates)}일치)')

  updated_df.to_csv(SAVE_PATH, index=False, encoding='utf-8-sig')
  print(f'[{today_date}] 성공적으로 저장 및 업데이트되었습니다.')
else:
  final_df.to_csv(SAVE_PATH, index=False, encoding='utf-8-sig')
  print(f'[{today_date}] 최초 CSV 파일이 생성되었습니다.')
