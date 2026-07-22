from datetime import datetime
import os
import pandas as pd
import requests

SAVE_PATH = 'stock_rotation_20days.csv'
MAX_DAYS = 20  # 최근 20일 데이터 유지를 위한 설정

# 환경 변수에서 텔레그램 정보 가져오기
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

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

# 3. 데이터 변환 및 상위 30개 추출
df_filtered['거래대금'] = (
    df_filtered['거래대금'].astype(str).str.replace(',', '').astype(float)
)
df_filtered['시가총액'] = (
    df_filtered['시가총액'].astype(str).str.replace(',', '').astype(float)
)

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

# 4. 20일 슬라이딩 저장 로직
if os.path.exists(SAVE_PATH):
  existing_df = pd.read_csv(SAVE_PATH)
  existing_df = existing_df[existing_df['날짜'] != today_date]
  updated_df = pd.concat([existing_df, final_df], ignore_index=True)

  unique_dates = sorted(updated_df['날짜'].unique())
  if len(unique_dates) > MAX_DAYS:
    keep_dates = unique_dates[-MAX_DAYS:]
    updated_df = updated_df[updated_df['날짜'].isin(keep_dates)]

  updated_df.to_csv(SAVE_PATH, index=False, encoding='utf-8-sig')
else:
  updated_df = final_df.copy()
  updated_df.to_csv(SAVE_PATH, index=False, encoding='utf-8-sig')

# 5. [점수 산정 및 텔레그램 발송 로직]
# 순위 점수 + (비율 * 2)
updated_df['순위점수'] = 31 - updated_df['순위']
updated_df['일별점수'] = updated_df['순위점수'] + (updated_df['비율(%)'] * 2)

# 종목별 집계
summary = (
    updated_df.groupby('종목명')
    .agg(
        총점수=('일별점수', 'sum'),
        출현횟수=('날짜', 'count'),
        최근현재가=('현재가', 'last'),
        최근비율=('비율(%)', 'last'),
    )
    .reset_index()
)

# 총점수 상위 5개 선정
top5 = summary.sort_values(by='총점수', ascending=False).head(5)
accumulated_days = len(updated_df['날짜'].unique())

# 텔레그램 메시지 생성
msg = f'📈 [{today_date}] 주도주 분석 리포트\n'
msg += f'(누적 분석 데이터: {accumulated_days}일치)\n\n'
msg += '🔥 [최우수 추천 종목 TOP 5]\n'

for idx, row in enumerate(top5.itertuples(), 1):
  msg += (
      f'{idx}. {row.종목명}\n'
      f'   • 총점수: {row.총점수:.1f}점 (출현 {row.출현횟수}회)\n'
      f'   • 현재가: {row.최근현재가:,.0f}원 | 당일비율: {row.최근비율:.2f}%\n\n'
  )

# 텔레그램 전송 함수
if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
  telegram_url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
  payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': msg}
  requests.post(telegram_url, data=payload)
  print('텔레그램 메시지 발송 완료!')
