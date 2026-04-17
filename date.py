import requests


def get_internet_time():
    try:
        response = requests.get("https://time.now/bishkek/", timeout=5)
        data = response.json()
        datetime_str = data['datetime']
        date_part = datetime_str[:10]
        time_part = datetime_str[11:16]

        return date_part, time_part
    except Exception:
        import datetime
        now = datetime.datetime.now()
        return now.strftime("%Y-%m-%d"), now.strftime("%H:%M")
