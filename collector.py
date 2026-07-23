import os
from datetime import datetime
import pandas as pd
import requests

SAVE_PATH = 'stock_rotation_20days.csv'
MAX_DAYS = 20
today_date = datetime.now().strftime('%Y-%m-%d')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

all_dfs = []

# 코스피(sosok=0) 10페이지, 코스닥(sosok=1) 10페이지 (총 1000개 종목) 수집
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
            print(f'수집 오류: sosok={sosok}, page={page} - {e}')

# 전체 데이터 병합
df = pd.concat(all_dfs, ignore_index=True)

# ETF, 스팩 등 잡주 필터링
def is_not_etf(row):
    name = str(row['종목명'])
    keywords = ['ETF', 'ETN', 'KODEX', 'TIGER', 'RISE', 'SOL', 'ACE', 'KBSTAR', 'HANARO', 'KOSEF', 'ARIRANG', 'TIMEFOLIO', 'WOORI', 'PLUS', '스팩', '제X호']
    return not any(k in name for k in keywords)

df_filtered = df[df.apply(is_not_etf, axis=1)].copy()

# 콤마(,) 제거 후 숫자로 변환
for col in ['현재가', '거래량', '시가총액']:
    df_filtered[col] = df_filtered[col].astype(str).str.replace(',', '').apply(pd.to_numeric, errors='coerce')

df_filtered = df_filtered.dropna(subset=['현재가', '거래량', '시가총액'])

# 시총 페이지에는 거래대금이 없으므로 직접 계산 (현재가 * 거래량)
df_filtered['거래대금'] = df_filtered['현재가'] * df_filtered['거래량']

# 거래대금 상위 30개 추출
top30_df = df_filtered.sort_values(by='거래대금', ascending=False).head(30).reset_index(drop=True)

# 시총(억원)과 거래대금(원) 단위 맞추어 비율 계산
top30_df['비율(%)'] = (top30_df['거래대금'] / (top30_df['시가총액'] * 100_000_000)) * 100
top30_df['날짜'] = today_date
top30_df['순위'] = top30_df.index + 1  # 거래대금 1~30위

final_df = top30_df[['날짜', '순위', '종목명', '현재가', '거래대금', '시가총액', '비율(%)']]

# 누적 저장 로직
if os.path.exists(SAVE_PATH):
    existing_df = pd.read_csv(SAVE_PATH)
    existing_df = existing_df[existing_df['날짜'] != today_date]
    updated_df = pd.concat([existing_df, final_df], ignore_index=True)
    
    unique_dates = sorted(updated_df['날짜'].unique())
    if len(unique_dates) > MAX_DAYS:
        keep_dates = unique_dates[-MAX_DAYS:]
        updated_df = updated_df[updated_df['날짜'].isin(keep_dates)]
        
    updated_df.to_csv(SAVE_PATH, index=False, encoding='utf-8-sig')
    print(f"[{today_date}] 기존 CSV 파일에 누적 저장 완료!")
else:
    final_df.to_csv(SAVE_PATH, index=False, encoding='utf-8-sig')
    print(f"[{today_date}] 최초 CSV 파일 생성 완료!")
