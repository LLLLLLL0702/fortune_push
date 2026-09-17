# -*- coding: utf-8 -*-
import os
import requests
from datetime import date, timedelta
from lunar_python import Solar

# ===== 配置区（本地测试直接改这里） =====
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
WXPUSHER_APP_TOKEN = os.environ.get("WXPUSHER_APP_TOKEN", "")
# 新增：支持两个接收者
WXPUSHER_UID = os.environ.get("WXPUSHER_UID", "")
WXPUSHER_UID_2 = os.environ.get("WXPUSHER_UID_2", "")

# ===== 固定信息 =====
FEMALE_BAZI = "辛巳 丙申 乙卯 戊寅"
FEMALE_DAYUN = "戊戌大运（2027年前）"

MALE_BAZI = "辛巳 辛丑 癸巳 丙辰"
MALE_DAYUN = "己亥大运（2028年前）"
LOCATION = "武汉"

def get_season(d: date) -> str:
    m = d.month
    if m in (3, 4, 5):
        return "春季"
    elif m in (6, 7, 8):
        return "夏季"
    elif m in (9, 10, 11):
        return "秋季"
    else:
        return "冬季"

def get_ganzhi(d: date) -> str:
    solar = Solar.fromYmd(d.year, d.month, d.day)
    lunar = solar.getLunar()
    return f"{lunar.getYearInGanZhi()}年 {lunar.getMonthInGanZhi()}月 {lunar.getDayInGanZhi()}日"

def build_prompt(today: date, today_ganzhi: str, season: str, days: list) -> str:
    prompt = f"""你是一个顶级命理高手，养生大师。请为以下情侣（均在武汉）生成今日精简运势与三餐规划。

【女方】八字：{FEMALE_BAZI}；当前大运：{FEMALE_DAYUN}
【男方】八字：{MALE_BAZI}；当前大运：{MALE_DAYUN}
【今日】{today}（{today_ganzhi}），{season}

请严格按以下格式输出，排版必须整齐。总字数≤800字，直接给结果，不要任何多余的客套话或分析过程。
重要：请完全使用纯文本格式，不要使用 Markdown 的 #、*、- 等符号，只需要用 Emoji、换行符和中文标点来排版。每部分之间留一个空行。

格式模板如下：

🌟【女方今日】
能量指数：XX/100
运势：XXX
宜：XXX、XXX
忌：XXX、XXX
幸运方位：XXX
适合做的事：XXX（结合病机与天赋）

🌟【男方今日】
状态：XXX
适合做的事：XXX（结合病机与天赋）

💑【双方共处】
1. XXX
2. XXX

🍱【三餐规划】
（每餐给出2个选项，用 / 隔开）

📅 今天（{days[0].strftime('%m-%d')}）
早：XXX / XXX
中：XXX / XXX
晚：XXX / XXX

📅 明天（{days[1].strftime('%m-%d')}）
早：XXX / XXX
中：XXX / XXX
晚：XXX / XXX

📅 后天（{days[2].strftime('%m-%d')}）
早：XXX / XXX
中：XXX / XXX
晚：XXX / XXX

📅 大后天（{days[3].strftime('%m-%d')}）
早：XXX / XXX
中：XXX / XXX
晚：XXX / XXX
"""
    return prompt

def call_deepseek(prompt: str) -> str:
    resp = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        },
        timeout=90
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

def push_to_wechat(title: str, content: str) -> None:
    """使用 WxPusher 推送到微信（支持多个 UID，并强制转换换行）"""
    api_url = "https://wxpusher.zjiecode.com/api/send/message"
    
    # 过滤有效 UID
    uids = [uid for uid in [WXPUSHER_UID, WXPUSHER_UID_2] if uid and not uid.startswith("对象的") and not uid.startswith("你的")]

    # 关键：将文本中的换行符 \n 替换为 HTML 的 <br>，确保在微信中正确分段
    html_content = content.replace("\n", "<br>")

    payload = {
        "appToken": WXPUSHER_APP_TOKEN,
        "content": html_content,
        "summary": title,
        "contentType": 2,
        "uids": uids
    }
    
    try:
        resp = requests.post(api_url, json=payload, timeout=15)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") == 1000:
            print(f"✅ 推送成功，共发送给 {len(uids)} 人")
        else:
            print(f"⚠️ 推送返回：{result}")
    except Exception as e:
        print(f"❌ 推送请求失败：{e}")

def main():
    today = date.today()
    days = [today + timedelta(days=i) for i in range(4)]
    season = get_season(today)
    today_ganzhi = get_ganzhi(today)

    print(f"📅 今日：{today}（{today_ganzhi}），季节：{season}")

    prompt = build_prompt(today, today_ganzhi, season, days)
    print("🤖 正在调用 DeepSeek 生成内容...")
    fortune_text = call_deepseek(prompt)

    print("📤 正在推送到微信...")
    title = f"今日运势与三餐规划 · {today.strftime('%m月%d日')}"
    push_to_wechat(title, fortune_text)

    print("🎉 完成")

if __name__ == "__main__":
    main()