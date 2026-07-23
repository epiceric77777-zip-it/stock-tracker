name: Daily Stock Data Collector & Analyzer

on:
  schedule:
    # 한국 시간 매주 월~금 오후 3시 38분 실행 (대기열 지연 방지)
    - cron: '38 6 * * 1-5'
  workflow_dispatch: # 수동 실행 버튼 활성화

permissions:
  contents: write

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout Repository
      uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pandas requests lxml html5lib

    # 1. 수집 스크립트 먼저 실행 (stock_rotation_20days.csv 생성/누적)
    - name: Run Collector Script
      run: python collector.py

    # 2. 누적된 CSV 파일 깃허브 저장소에 Commit & Push
    - name: Commit & Push Changes
      run: |
        git config --local user.email "action@github.com"
        git config --local user.name "GitHub Action"
        git add stock_rotation_20days.csv
        git commit -m "Auto update stock data" || exit 0
        git push

    # 3. 점수 분석 및 텔레그램 발송 스크립트 실행
    - name: Run Analyzer Script
      env:
        TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
        TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
      run: python analyzer.py
