import requests
from database.db_manager import DBManager

def update_exchange_rates(db: DBManager) -> bool:
    """
    Loads fresh currency rates relative to USD
    and saves them in the database as rate_to_usd.
    1 unit of currency = X USD (e.g., 1 RUB = 0.011 USD).
    """
    url = "https://open.er-api.com/v6/latest/USD"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("result") == "success":
                rates = data.get("rates", {})
                
                # We support major currencies, but can update any
                supported_currencies = ["USD", "EUR", "RUB", "BYN", "KZT", "UAH", "GBP"]
                
                for code in supported_currencies:
                    if code in rates:
                        rate_to_usd = 1.0 / rates[code]
                        db.update_rate(code, rate_to_usd)
                return True
    except Exception as e:
        print(f"Error updating currency rates: {e}")
    return False
