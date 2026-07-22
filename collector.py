from datetime import datetime
import os
import pandas as pd
import requests

SAVE_PATH = 'stock_rotation_20days.csv'
MAX_DAYS = 20  # 유지할 최대 일수 (20일)

today_date = datetime.now().strftime('%Y-%m-%d')

# 1. 네이버 금융 수집
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


# 2. ETF 제외 필터
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

# 3. 데이터 수치 변환
df_filtered['거래대금'] = (
    df_filtered['거래대금'].astype(str).str.replace(',', '').astype(float)
)
df_filtered['시가총액'] = (
    df_filtered['시가총액'].astype(str).str.replace(',', '').astype(float)
)

# 4. [핵심] 시가총액 상위 50% (중위값 이상) 종목만 자동 필터링 (잡주 제거)
market_cap_median = df_filtered['시가총액'].median()  # 매일 실시간 중앙값 구함
df_filtered = df_filtered[
    df_filtered['시가총액'] >= market_cap_median
].copy()

# 5. 거래대금 상위 30개 추출
top30_df = (
    df_filtered.sort_values(by='거래대금', ascending=False).head(30).copy()
)

top30_df['비율(%)'] = (
    (top30_df['거래대금'] * 1_000_000)
    / (top30_df['시가총액'] * 100_000_000)
) * 100

result_df = top30_df.sort_values(by='비율(%)', ascending=False).reset_index(
    drop=True
)
result_df['날짜'] = today_date
result_df['순위'] = result_df.index + 1

final_df = result_df[
    ['날짜', '순위', '종목명', '현재가', '거래대금', '시가총액', '비율(%)']
]

# 6. 20일 슬라이딩 저장 로직
if os.path.exists(SAVE_PATH):
  existing_df = pd.read_csv(SAVE_PATH)
  existing_df = existing_df[existing_df['날짜'] != today_date]
  updated_df = pd.concat([existing_df, final_df], ignore_index=True)

  unique_dates = sorted(updated_df['날짜'].unique())
  if len(unique_dates) > MAX_DAYS:
    keep_dates = unique_dates[-MAX_DAYS:]
    updated_df = updated_df[updated_df['날짜'].isin(keep_dates)]

  updated_df.to_csv(SAVE_PATH, index=False, encoding='utf-8-sig')
  print(
      f'[{today_date}] (시총 상위 50% 반영) 기존 CSV 파일에 누적 저장 완료!'
  )
else:
  final_df.to_csv(SAVE_PATH, index=False, encoding='utf-8-sig')
  print(f'[{today_date}] (시총 상위 50% 반영) 최초 CSV 파일 생성 완료!')
