import os
from datetime import datetime
import pandas as pd
import requests

SAVE_PATH_20DAYS = 'stock_rotation_20days.csv'
SAVE_PATH_INFINITE = 'stock_rotation_infinite.csv' # 영구 보존용 파일 추가
MAX_DAYS = 20
today_date = datetime.now().strftime('%Y-%m-%d')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

all_dfs = []

# 코스피(sosok=0), 코스닥(sosok=1) 1~10페이지 수집
for sosok in [0, 1]:
    for page in range(1, 11):
        url = f'https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page={page}'
        response = requests.get(url, headers=headers)
        response.encoding = 'euc-kr'
        try:
            tables = pd.read_html(response.text)
            df_page = tables[1].dropna(subset=['종목명']).copy()
            df_page = df_page[df_page['종목명'] != '종목명']
            all_dfs.append(df_page)
        except Exception as e:
            print(f'수집 오류: {e}')

df = pd.concat(all_dfs, ignore_index=True)

def is_not_etf(row):
    name = str(row['종목명'])
    keywords = ['ETF', 'ETN', 'KODEX', 'TIGER', 'RISE', 'SOL', 'ACE', 'KBSTAR', 'HANARO', 'KOSEF', 'ARIRANG', 'TIMEFOLIO', 'WOORI', 'PLUS', '스팩', '제X호']
    return not any(k in name for k in keywords)

df_filtered = df[df.apply(is_not_etf, axis=1)].copy()

# 등락률 기호(+, %, -) 처리 및 숫자로 변환
if '등락률' in df_filtered.columns:
    df_filtered['등락률'] = df_filtered['등락률'].astype(str).str.replace('%', '').str.replace('+', '').apply(pd.to_numeric, errors='coerce')
else:
    df_filtered['등락률'] = 0.0

for col in ['현재가', '거래량', '시가총액']:
    df_filtered[col] = df_filtered[col].astype(str).str.replace(',', '').apply(pd.to_numeric, errors='coerce')

df_filtered = df_filtered.dropna(subset=['현재가', '거래량', '시가총액'])
df_filtered['거래대금'] = df_filtered['현재가'] * df_filtered['거래량']
top30_df = df_filtered.sort_values(by='거래대금', ascending=False).head(30).reset_index(drop=True)

top30_df['비율(%)'] = (top30_df['거래대금'] / (top30_df['시가총액'] * 100_000_000)) * 100
top30_df['날짜'] = today_date
top30_df['순위'] = top30_df.index + 1

final_df = top30_df[['날짜', '순위', '종목명', '현재가', '거래대금', '시가총액', '비율(%)', '등락률']]

# [1] 20일 유지용 파일 저장 (기존 로직)
if os.path.exists(SAVE_PATH_20DAYS):
    existing_df = pd.read_csv(SAVE_PATH_20DAYS)
    existing_df = existing_df[existing_df['날짜'] != today_date]
    updated_df = pd.concat([existing_df, final_df], ignore_index=True)
    
    unique_dates = sorted(updated_df['날짜'].unique())
    if len(unique_dates) > MAX_DAYS:
        updated_df = updated_df[updated_df['날짜'].isin(unique_dates[-MAX_DAYS:])]
        
    updated_df.to_csv(SAVE_PATH_20DAYS, index=False, encoding='utf-8-sig')
else:
    final_df.to_csv(SAVE_PATH_20DAYS, index=False, encoding='utf-8-sig')

# [2] 영구 보존(무한 누적)용 파일 저장 (새로운 로직)
if os.path.exists(SAVE_PATH_INFINITE):
    infinite_df = pd.read_csv(SAVE_PATH_INFINITE)
    # 하루에 여러 번 돌리더라도 오늘 날짜는 중복되지 않게 한 번 지워줌
    infinite_df = infinite_df[infinite_df['날짜'] != today_date]
    updated_infinite_df = pd.concat([infinite_df, final_df], ignore_index=True)
    updated_infinite_df.to_csv(SAVE_PATH_INFINITE, index=False, encoding='utf-8-sig')
else:
    final_df.to_csv(SAVE_PATH_INFINITE, index=False, encoding='utf-8-sig')
