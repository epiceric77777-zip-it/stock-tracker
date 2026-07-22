from datetime import datetime
import os
import pandas as pd
import requests

CSV_PATH = 'stock_rotation_20days.csv'

# 환경 변수에서 텔레그램 정보 읽기
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

today_date = datetime.now().strftime('%Y-%m-%d')

if not os.path.exists(CSV_PATH):
  print('분석할 CSV 파일이 존재하지 않습니다.')
  exit(0)

# 1. 누적 데이터 읽기
df = pd.read_csv(CSV_PATH)

# 2. 점수 계산 로직
# 순위 점수 (1위=30점, 30위=1점) + (비율 * 2)
df['순위점수'] = 31 - df['순위']
df['일별점수'] = df['순위점수'] + (df['비율(%)'] * 2)

# 3. 종목별 점수 집계
summary = (
    df.groupby('종목명')
    .agg(
        총점수=('일별점수', 'sum'),
        출현횟수=('날짜', 'count'),
        최근현재가=('현재가', 'last'),
        최근비율=('비율(%)', 'last'),
        시가총액=('시가총액', 'last'),
    )
    .reset_index()
)

# 총점수 기준 상위 10개 추출
top10 = summary.sort_values(by='총점수', ascending=False).head(10)
accumulated_days = len(df['날짜'].unique())

# 4. 텔레그램 메시지 생성
msg = f'📈 [{today_date}] 주도주 분석 리포트\n'
msg += f'(시총 상위 50% 이내 | 누적 {accumulated_days}일치 데이터)\n\n'
msg += '🔥 [최우수 추천 종목 TOP 10]\n'

for idx, row in enumerate(top10.itertuples(), 1):
  # 시가총액 억원 단위 표시 정제
  cap_billion = int(row.시가총액)
  msg += (
      f'{idx}. {row.종목명} (시총 {cap_billion:,}억)\n'
      f'   • 총점수: {row.총점수:.1f}점 (출현 {row.출현횟수}회)\n'
      f'   • 현재가: {row.최근현재가:,.0f}원 | 당일비율: {row.최근비율:.2f}%\n\n'
  )

# 5. 텔레그램 메시지 전송
if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
  telegram_url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
  payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': msg}
  response = requests.post(telegram_url, data=payload)
  if response.status_code == 200:
    print('텔레그램 TOP 10 전송 성공!')
  else:
    print(f'텔레그램 전송 실패: {response.text}')
else:
  print('텔레그램 토큰 또는 Chat ID가 설정되지 않았습니다.')
