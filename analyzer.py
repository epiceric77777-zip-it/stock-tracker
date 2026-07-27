import os
import pandas as pd
import requests
from datetime import datetime

CSV_PATH = 'stock_rotation_20days.csv'
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

today_date = datetime.now().strftime('%Y-%m-%d')

if not os.path.exists(CSV_PATH): 
    print("CSV 파일이 존재하지 않습니다.")
    exit(0)

df = pd.read_csv(CSV_PATH)

def calculate_new_score(group):
    group['순위점수'] = (31 - group['순위']) * 2
    group['회전율등수'] = group['비율(%)'].rank(method='min', ascending=False)
    group['회전율점수'] = 31 - group['회전율등수']
    
    def apply_penalty(row):
        base_score = row['순위점수'] + row['회전율점수']
        if '등락률' in row and pd.notna(row['등락률']) and row['등락률'] < 0:
            return -(base_score / 2)
        return base_score
        
    group['일별점수'] = group.apply(apply_penalty, axis=1)
    return group

df = df.groupby('날짜', group_keys=False).apply(calculate_new_score)

summary = df.groupby('종목명').agg(
    총점수=('일별점수', 'sum'),
    출현횟수=('날짜', 'count'),
    최근거래대금=('거래대금', 'last'),
    최근비율=('비율(%)', 'last'),
    시가총액=('시가총액', 'last'),
    등락률=('등락률', 'last')
).reset_index()

top10 = summary.sort_values(by='총점수', ascending=False).head(10)
accumulated_days = len(df['날짜'].unique())

# 기존 포맷 완벽 복구 + 마지막에 등락률 추가
msg = f"📈 [{today_date}] 주도주 리포트 (TOP 10)\n"
msg += f"(총 {accumulated_days}일 누적)\n\n"

for idx, row in enumerate(top10.itertuples(), 1):
    trade_amt_billion = row.최근거래대금 / 100_000_000
    sign = "+" if row.등락률 > 0 else ""
    
    msg += f"{idx}. {row.종목명} ({row.총점수:.0f}점 | {row.출현횟수}회)\n"
    msg += f" - 거래대금 {trade_amt_billion:,.0f}억 | 시총 {row.시가총액:,.0f}억 | 회전율 {row.최근비율:.1f}% | 등락률 {sign}{row.등락률}%\n"

print("전송할 메시지 미리보기:\n", msg)

if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': msg}
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("✅ 본인 텔레그램 전송 성공!")
    else:
        print(f"❌ 전송 실패: {response.text}")
else:
    print("⚠️ 텔레그램 환경 변수 확인 필요")
