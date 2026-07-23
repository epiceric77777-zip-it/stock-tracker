import os
import pandas as pd
import requests
from datetime import datetime

CSV_PATH = 'stock_rotation_20days.csv'
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

today_date = datetime.now().strftime('%Y-%m-%d')

if not os.path.exists(CSV_PATH):
    print("분석할 CSV 파일이 존재하지 않습니다.")
    exit(0)

df = pd.read_csv(CSV_PATH)

# 새로운 커스텀 점수 로직
def calculate_new_score(group):
    # 1. 거래대금 순위 점수: (31 - 등수) * 2
    group['순위점수'] = (31 - group['순위']) * 2
    
    # 2. 당일 30종목 내에서 회전율(비율) 등수 계산 (1등=30점, 30등=1점)
    group['회전율등수'] = group['비율(%)'].rank(method='min', ascending=False)
    group['회전율점수'] = 31 - group['회전율등수']
    
    # 3. 일별 종합 점수 = 거래대금 점수 + 회전율 점수
    group['일별점수'] = group['순위점수'] + group['회전율점수']
    return group

df = df.groupby('날짜', group_keys=False).apply(calculate_new_score)

# 종목별 20일 총합
summary = df.groupby('종목명').agg(
    총점수=('일별점수', 'sum'),
    출현횟수=('날짜', 'count'),
    최근현재가=('현재가', 'last'),
    최근비율=('비율(%)', 'last'),
    시가총액=('시가총액', 'last')
).reset_index()

# 20위까지 추출
top20 = summary.sort_values(by='총점수', ascending=False).head(20)
accumulated_days = len(df['날짜'].unique())

msg = f"📈 [{today_date}] 주도주 리포트\n"
msg += f"(총 {accumulated_days}일 누적 / 거래대금+회전율 커스텀 점수)\n\n"

# 핸드폰 화면에 쏙 들어오게 가독성 압축 포맷
for idx, row in enumerate(top20.itertuples(), 1):
    msg += f"{idx}. {row.종목명} ({row.총점수:.0f}점 | {row.출현횟수}회)\n"
    msg += f" - {row.최근현재가:,.0f}원 | 시총 {row.시가총액:,.0f}억 | 회전율 {row.최근비율:.1f}%\n"

print("전송할 메시지 미리보기:\n", msg)

# 텔레그램 전송 및 상세 디버깅
if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': msg}
    
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print("✅ 텔레그램 메시지 전송 성공!")
        else:
            print(f"❌ 텔레그램 전송 실패: {response.status_code}")
            print(f"상세 이유: {response.text}")
    except Exception as e:
        print(f"❌ 텔레그램 요청 중 에러 발생: {e}")
else:
    print("⚠️ 텔레그램 토큰을 찾을 수 없습니다. GitHub Secrets 연동을 확인하세요.")
