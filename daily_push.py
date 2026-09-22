name: Daily Fortune Push

on:
  schedule:
    # UTC 20:00 = 北京时间 4:00，提前触发，留足排队缓冲
    - cron: '0 20 * * *'
  workflow_dispatch:

jobs:
  push:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - name: 拉取代码
        uses: actions/checkout@v4

      - name: 安装 Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: 安装依赖
        run: pip install -r requirements.txt

      - name: 显示时间
        run: |
          echo "UTC 时间: $(date -u)"
          echo "北京时间: $(TZ=Asia/Shanghai date)"

      - name: 运行推送脚本
        run: python daily_push.py
        env:
          TZ: Asia/Shanghai
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
          WXPUSHER_APP_TOKEN: ${{ secrets.WXPUSHER_APP_TOKEN }}
          WXPUSHER_UID: ${{ secrets.WXPUSHER_UID }}
          WXPUSHER_UID_2: ${{ secrets.WXPUSHER_UID_2 }}
