import requests
from ddgs import DDGS


def get_web_info(query):
    results = []
    with DDGS() as ddgs:
        # Берем первые 3-5 результатов поиска
        for r in ddgs.text(query, max_results=5):
            results.append(f"Источник: {r['href']}\nТекст: {r['body']}")
    return "\n\n".join(results)


def get_currency():
    response = requests.get("https://www.nbkr.kg/XML/daily.xml")
    response.raise_for_status()
    return response.text
