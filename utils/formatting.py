def format_amount(value, decimals: int = 2) -> str:
    amount = float(value or 0)
    if amount.is_integer():
        return f"{int(amount):,}"
    return f"{amount:,.{decimals}f}".rstrip("0").rstrip(".")


def format_money(value, currency: str, decimals: int = 2) -> str:
    return f"{format_amount(value, decimals)} {currency}"
