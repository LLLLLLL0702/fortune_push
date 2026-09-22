# -*- coding: utf-8 -*-
import os
import requests
from datetime import date, timedelta, datetime, timezone
from lunar_python import Solar
import chinese_calendar

# ===== 配置区 =====
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
WXPUSHER_APP_TOKEN = os.environ.get("WXPUSHER_APP_TOKEN", "")
WXPUSHER_UID = os.environ.get("WXPUSHER_UID", "")
WXPUSHER_UID_2 = os.environ.get("WXPUSHER_UID_2", "")

FEMALE_BAZI = "辛巳 丙申 乙卯 戊寅"
FEMALE_DAYUN = "戊戌大运（2027年前）"
MALE_BAZI = "辛巳 辛丑 癸巳 丙辰"
MALE_DAYUN = "己亥大运（2028年前）"
LOCATION = "武汉"

BJ = timezone(timedelta(hours=8))


def get_season(d: date) -> str:
    m = d.month
    if m in (3, 4, 5):
        return "春季"
    if m in (6, 7, 8):
        return "夏季"
    if m in (9, 10, 11):
        return "秋季"
    return "冬季"


def get_ganzhi(d: date) -> str:
    solar = Solar.fromYmd(d.year, d.month, d.day)
    lunar = solar.getLunar()
    return f"{lunar.getYearInGanZhi()}年 {lunar.getMonthInGanZhi()}月 {lunar.getDayInGanZhi()}日"


def calc_energy(bazi: str, today_ganzhi: str, d: date) -> int:
    """
    根据今日日干与八字日主的生克关系 + 日期扰动，算出能量指数。
    范围 45~95，保证每天不同。
    """
    wuxing = {
        "甲": "木", "乙": "木", "丙": "火", "丁": "火",
        "戊": "土", "己": "土", "庚": "金", "辛": "金",
        "壬": "水", "癸": "水",
    }
    sheng = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
    ke = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

    base = 70

    day_master = bazi.split()[2][0]
    dm_wx = wuxing.get(day_master, "土")

    day_part = [p for p in today_ganzhi.split() if p.endswith("日")]
    today_gan = day_part[0][0] if day_part else ""
    tg_wx = wuxing.get(today_gan, "")

    if tg_wx == dm_wx:
        base += 10
    elif sheng.get(tg_wx) == dm_wx:
        base += 15
    elif sheng.get(dm_wx) == tg_wx:
        base += 5
    elif ke.get(tg_wx) == dm_wx:
        base -= 12
    elif ke.get(dm_wx) == tg_wx:
        base -= 8

    base += (d.day * 7 + d.month * 3) % 15 - 7

    return max(45, min(95, base))


def build_meals_female(days: list) -> str:
    """只规划女方三餐，每餐 3 个选项"""
    labels = ["今天", "明天", "后天", "大后天", "大大后天"]
    block = ""
    for i, d in enumerate(days):
        label = labels[i] if i < len(labels) else f"{i + 1}天后"
        block += (
            f"\n📅 {label}（{d.strftime('%m-%d')}）\n"
            f"早：XXX / XXX / XXX\n"
            f"中：XXX / XXX / XXX\n"
            f"晚：XXX / XXX / XXX\n"
        )
    return block


def build_prompt(today, today_ganzhi, season, days, fe, me, is_together: bool) -> str:
    meals_block = build_meals_female(days)

    if is_together:
        together_section = """💑【双方共处】
1. XXX
2. XXX
3. XXX"""
        together_note = "今天在一起，可安排共同活动。"
    else:
        together_section = """💌【双方互动】
1. XXX
2. XXX
3. XXX"""
        together_note = "今天不在一起，但离得不远，注意沟通关心。"

    prompt = f"""你是一个顶级命理高手，养生大师。请为以下情侣（均在武汉）生成今日精简运势与女方三餐规划。

【女方】八字：{FEMALE_BAZI}；当前大运：{FEMALE_DAYUN}。日主乙木，秋季金旺木弱，宜养肝润肺，少辛辣，适当酸味。
【男方】八字：{MALE_BAZI}；当前大运：{MALE_DAYUN}。日主癸水，秋季金旺水相，宜养肾润燥，少熬夜。
【今日】{today}（{today_ganzhi}），{season}，{LOCATION}
【今日是否在一起】{"是，周末/节假日在一起" if is_together else "否，工作日各自忙碌，但离得不远"}
{together_note}

请严格按以下格式输出，排版必须整齐。总字数≤1500字，直接给结果，不要任何多余的客套话或分析过程。
重要：请完全使用纯文本格式，不要使用 Markdown 的 #、*、- 等符号，只需要用 Emoji、换行符和中文标点来排版。每部分之间留一个空行。

运势按由大到小展开，规则如下：
- 大运、流年：各一句话带过，不超过20字，要结合具体事项，不要模板话
- 流月：一句话，不超过25字，结合具体事项
- 流日：重点，2~3句话，不超过80字
- 流时：只讲今日剩余时辰的吉凶，1句话，没有就省略
- 能量指数：给出后，用一句话解释依据，不超过15字

女方今日能量指数固定为 {fe}，男方今日能量指数固定为 {me}，不要改动这两个数字，直接使用。

三餐只规划女方，男方不需要三餐规划。
三餐要求：
- 每餐给出3个选项，用 / 隔开
- 结合武汉本地当季食材，优先本地
- 结合女方乙木日主，秋季养肝润肺，少辛辣，适当酸味
- 食物自由度放宽，不必严格限制重复，但要尽量多样化

幸运方位请结合女方喜用神（乙木喜水木）给出，并注明原因，不超过10字。

适合做的事必须结合今日干支与日主关系，写出具体动作，禁止通用套话。

格式模板如下：

📋 今日总览：XXX（不超过30字）

🌟【女方今日】
运势：
大运：XXX
流年：XXX
流月：XXX
流日：XXX
流时：XXX
能量指数：{fe}/100（依据：XXX）
宜：XXX、XXX
忌：XXX、XXX
幸运方位：XXX（原因：XXX）
适合做的事：XXX（结合病机与天赋）

🌟【男方今日】
运势：
大运：XXX
流年：XXX
流月：XXX
流日：XXX
流时：XXX
能量指数：{me}/100（依据：XXX）
宜：XXX、XXX
忌：XXX、XXX
幸运方位：XXX（原因：XXX）
适合做的事：XXX（结合病机与天赋）

{together_section}

🍱【女方三餐规划】
（每餐3个选项，用 / 隔开，结合武汉本地当季，只规划女方，男方无需三餐）

{meals_block}
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
            "temperature": 0.8
        },
        timeout=90
    )
    if resp.status_code != 200:
        print("DeepSeek 错误：", resp.status_code, resp.text)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def push_to_wechat(title: str, content: str) -> None:
    api_url = "https://wxpusher.zjiecode.com/api/send/message"

    uids = [
        uid for uid in [WXPUSHER_UID, WXPUSHER_UID_2]
        if uid and not uid.startswith("对象的") and not uid.startswith("你的")
    ]
    print("准备推送给 UID:", uids)
    if not uids:
        raise RuntimeError("没有有效的 WxPusher UID")

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
        print("WxPusher 返回：", result)
        if result.get("code") == 1000:
            print(f"✅ 推送成功，共发送给 {len(uids)} 人")
        else:
            print(f"⚠️ 推送返回异常：{result}")
    except Exception as e:
        print(f"❌ 推送请求失败：{e}")
        raise


def main():
    if not DEEPSEEK_API_KEY:
        raise SystemExit("缺少 DEEPSEEK_API_KEY")
    if not WXPUSHER_APP_TOKEN:
        raise SystemExit("缺少 WXPUSHER_APP_TOKEN")
    if not WXPUSHER_UID and not WXPUSHER_UID_2:
        raise SystemExit("缺少 WXPUSHER_UID 或 WXPUSHER_UID_2")

    today = datetime.now(BJ).date()
    days = [today + timedelta(days=i) for i in range(4)]
    season = get_season(today)
    today_ganzhi = get_ganzhi(today)

    is_together = chinese_calendar.is_holiday(today)
    print(f"📅 今日：{today}（{today_ganzhi}），季节：{season}，是否在一起：{is_together}")

    fe = calc_energy(FEMALE_BAZI, today_ganzhi, today)
    me = calc_energy(MALE_BAZI, today_ganzhi, today)
    print(f"🔢 女方能量：{fe}，男方能量：{me}")

    prompt = build_prompt(today, today_ganzhi, season, days, fe, me, is_together)
    print("🤖 正在调用 DeepSeek 生成内容...")
    fortune_text = call_deepseek(prompt)

    print("📤 正在推送到微信...")
    title = f"今日运势与女方三餐 · {today.strftime('%m月%d日')}"
    push_to_wechat(title, fortune_text)

    print("🎉 完成")


if __name__ == "__main__":
    main()
