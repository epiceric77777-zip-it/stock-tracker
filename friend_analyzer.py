import os
import pandas as pd
import requests

CSV_PATH = 'stock_rotation_20days.csv'
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
FRIEND_CHAT_ID = os.environ.get('FRIEND_CHAT_ID')

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
    등락률=('등락률', 'last')
).reset_index()

top10 = summary.sort_values(by='총점수', ascending=False).head(10)

# 친구들 채널용: 시총을 빼고 등락률만 표시
msg = "📈 한지혁의 HOT 종목 검색기 🔥\n\n"
for idx, row in enumerate(top10.itertuples(), 1):
    sign = "+" if row.등락률 > 0 else ""
    msg += f"{idx}. {row.종목명} ({sign}{row.등락률}%)\n"

if TELEGRAM_TOKEN and FRIEND_CHAT_ID:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': FRIEND_CHAT_ID, 'text': msg}
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("✅ 친구들 채널 전송 성공!")
    else:
        print(f"❌ 전송 실패: {response.text}")
else:
    print("⚠️ 텔레그램 환경 변수 확인 필요")
