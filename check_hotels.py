from datetime import datetime
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests

# 1. 設定日期變數 (優先讀取環境變數，若無則使用預設值)
CHECK_IN_DATE = os.environ.get("CHECK_IN_DATE", "2026-09-22")
CHECK_OUT_DATE = os.environ.get("CHECK_OUT_DATE", "2026-09-24")

# 2. 自動計算入住天數 (晚數)
d1 = datetime.strptime(CHECK_IN_DATE, "%Y-%m-%d")
d2 = datetime.strptime(CHECK_OUT_DATE, "%Y-%m-%d")
NIGHTS = (d2 - d1).days

# 3. 從 GitHub Secrets 讀取設定的環境變數
SEARCHAPI_KEY = os.environ.get("SEARCHAPI_KEY")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_PASS = os.environ.get("GMAIL_PASS")  # 必須是 Gmail 的「應用程式專用密碼」
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", GMAIL_USER)

SEARCH_URL = "https://www.searchapi.io/api/v1/search"

# 4. 設定 SearchApi.io 查詢參數
params = {
    "engine": "google_hotels",
    "q": "新潟站 飯店",
    "check_in_date": CHECK_IN_DATE,
    "check_out_date": CHECK_OUT_DATE,
    "adults": "2",
    "currency": "JPY",
    "gl": "jp",
    "hl": "zh-TW",
    "api_key": SEARCHAPI_KEY,
}


def send_email(subject, body_html):
    """透過 SMTP 傳送 Email"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = RECIPIENT_EMAIL

    msg.attach(MIMEText(body_html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_PASS)
        server.sendmail(GMAIL_USER, RECIPIENT_EMAIL, msg.as_string())


def main():
    if not SEARCHAPI_KEY or not GMAIL_USER or not GMAIL_PASS:
        print(
            "❌ 錯誤：缺少必要的 Secrets 環境變數，請確認 GitHub Secrets 設定。"
        )
        return

    print(
        f"🔍 正在向 SearchApi 查詢 {CHECK_IN_DATE} ~ {CHECK_OUT_DATE}（共 {NIGHTS} 晚）的飯店資訊..."
    )
    response = requests.get(SEARCH_URL, params=params)

    if response.status_code != 200:
        print(f"❌ API 查詢失敗，狀態碼：{response.status_code}")
        print(response.text)
        return

    data = response.json()
    properties = data.get("properties", [])

    # 動態產生對應入住日期與晚數的 Google Maps 連結
    google_maps_url = f"https://www.google.com/maps/place/%E6%96%B0%E6%BD%9F%E5%A4%A7%E5%80%89%E9%85%92%E5%BA%97/@37.9178791,139.0466195,15.5z/data=!3m1!5s0x5ff4c9f29bbb22c5:0xa8cceab01ad7c4f4!4m18!1m8!2m7!1z5paw5r2f56uZIOmjr-W6lw!5m4!5m3!1s{CHECK_IN_DATE}!4m1!1i{NIGHTS}!6e3!3m8!1s0x5ff4c8e44d0e77bb:0x260596fc90a25936!5m2!4m1!1i{NIGHTS}!8m2!3d37.9198561!4d139.0510225!16s%2Fg%2F1yl48dcvv?authuser=0&entry=ttu"

    # 5. 判斷是否有開放預訂的飯店
    if properties:
        print(
            f"🎉 成功找到 {len(properties)} 間開放預訂的飯店！發送通知信..."
        )
        subject = f"【有房了！】{CHECK_IN_DATE}（{NIGHTS}晚）JR新潟站飯店搜尋結果（共 {len(properties)} 間）"

        content_lines = [
            f"<h2>{CHECK_IN_DATE} ~ {CHECK_OUT_DATE}（共 {NIGHTS} 晚）JR新潟站飯店已開放預訂：</h2>",
            "<table border='1' cellpadding='8' style='border-collapse: collapse;'>",
            "<tr style='background-color: #f2f2f2;'><th>飯店名稱</th><th>每晚價格</th><th>評分</th><th>預訂連結</th></tr>",
        ]

        for hotel in properties[:15]:  # 列出前 15 間
            name = hotel.get("name", "未知飯店")
            rate = hotel.get("rate_per_night", {}).get(
                "extracted", "未公開價格"
            )
            rating = hotel.get("overall_rating", "無評分")
            link = hotel.get("link", "#")

            content_lines.append(
                f"<tr>"
                f"<td><b>{name}</b></td>"
                f"<td>{rate} JPY</td>"
                f"<td>{rating} ⭐</td>"
                f"<td><a href='{link}' target='_blank'>查看預訂</a></td>"
                f"</tr>"
            )

        content_lines.append("</table><br>")
        content_lines.append(
            f"<p>Google Maps 搜尋結果：<a href='{google_maps_url}' target='_blank'>點此開啟 Google Maps 查看</a></p>"
        )
        html_body = "".join(content_lines)
    else:
        print("ℹ️ 目前尚無房源開放預訂。發送每日平靜報告...")
        subject = f"【每日回報】{CHECK_IN_DATE}（{NIGHTS}晚）JR新潟站飯店尚未開放預訂"
        html_body = f"<p>今日查詢結果：系統尚未釋出 {CHECK_IN_DATE} ~ {CHECK_OUT_DATE}（共 {NIGHTS} 晚）的飯店房源，將於明天同一時間繼續監測。</p>"

    send_email(subject, html_body)
    print("✅ Email 發送成功！")


if __name__ == "__main__":
    main()
