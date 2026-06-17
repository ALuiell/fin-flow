import requests
from database.db_manager import DBManager

def update_exchange_rates(db: DBManager) -> bool:
    """
    Загружает свежие курсы валют относительно USD
    и сохраняет их в базу данных как rate_to_usd.
    1 ед. валюты = X USD (например, 1 RUB = 0.011 USD).
    """
    url = "https://open.er-api.com/v6/latest/USD"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("result") == "success":
                rates = data.get("rates", {})
                
                # Мы поддерживаем основные валюты, но можем обновить любые
                supported_currencies = ["USD", "EUR", "RUB", "BYN", "KZT", "UAH", "GBP"]
                
                for code in supported_currencies:
                    if code in rates:
                        rate_to_usd = 1.0 / rates[code]
                        db.update_rate(code, rate_to_usd)
                return True
    except Exception as e:
        print(f"Error updating currency rates: {e}")
    return False
