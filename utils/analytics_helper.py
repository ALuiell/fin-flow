import re
import calendar
from datetime import datetime, date
from typing import List, Dict, Any
from database.db_manager import DBManager

def eval_expression(expr_str: str) -> float:
    """Safely evaluates a mathematical expression from a string."""
    if not expr_str:
        return 0.0
    # Clean the string
    expr_str = expr_str.replace(" ", "").replace(",", ".")
    # Allow only digits, dots, parentheses and basic operators
    if not re.match(r"^[\d.+\-*/()]+$", expr_str):
        raise ValueError("Недопустимые символы")
    try:
        # Limit namespace for safety
        result = float(eval(expr_str, {"__builtins__": None}, {}))
        return round(result, 2)
    except Exception:
        raise ValueError("Ошибка вычисления")

def get_days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]

def get_period_bounds(selected_date: date, mode: str) -> tuple[str, str]:
    """Returns inclusive YYYY-MM-DD bounds for analytics filters."""
    if mode == "day":
        day = selected_date.strftime("%Y-%m-%d")
        return day, day

    days_in_month = get_days_in_month(selected_date.year, selected_date.month)
    start = f"{selected_date.year}-{selected_date.month:02d}-01"
    end = f"{selected_date.year}-{selected_date.month:02d}-{days_in_month:02d}"
    return start, end

def build_cumulative_spend_series(
    transactions: List[Dict[str, Any]],
    subscriptions: List[Dict[str, Any]],
    year: int,
    month: int,
    planned_income: float,
    convert_amount,
    base_currency: str,
    today: date | None = None,
) -> Dict[str, List[float | None]]:
    days_in_month = get_days_in_month(year, month)
    days = list(range(1, days_in_month + 1))
    today = today or date.today()

    daily_spends = {d: 0.0 for d in days}
    for t in transactions:
        if t.get('category_type') != 'expense' or t.get('transfer_to_account_id') is not None:
            continue
        t_date = datetime.strptime(t['date'], "%Y-%m-%d").date()
        if t_date.year == year and t_date.month == month:
            daily_spends[t_date.day] += convert_amount(t['amount'], t['currency'], base_currency)

    if year < today.year or (year == today.year and month < today.month):
        actual_cutoff = days_in_month
    elif year == today.year and month == today.month:
        actual_cutoff = today.day
    else:
        actual_cutoff = 0

    actual_spend = []
    current_sum = 0.0
    for d in days:
        current_sum += daily_spends[d]
        actual_spend.append(current_sum if d <= actual_cutoff else None)

    ideal_spend = [(planned_income / days_in_month) * d for d in days]

    planned_daily = {d: 0.0 for d in days}
    for s in subscriptions:
        if not s.get('is_active'):
            continue
        next_pay = datetime.strptime(s['next_payment_date'], "%Y-%m-%d").date()
        if next_pay.year == year and next_pay.month == month:
            planned_daily[next_pay.day] += convert_amount(s['amount'], s['currency'], base_currency)

    planned_spend = []
    planned_sum = 0.0
    for d in days:
        planned_sum += planned_daily[d]
        planned_spend.append(planned_sum)

    return {
        "days": days,
        "actual_spend": actual_spend,
        "ideal_spend": ideal_spend,
        "planned_spend": planned_spend,
    }

def sort_transactions_by_selected_subcategories(
    transactions: List[Dict[str, Any]],
    selected_subcategory_ids: List[int],
) -> List[Dict[str, Any]]:
    if not selected_subcategory_ids:
        return transactions

    selected = set(selected_subcategory_ids)
    sorted_pairs = sorted(
        enumerate(transactions),
        key=lambda item: (0 if item[1].get('category_id') in selected else 1, item[0])
    )
    return [transaction for _, transaction in sorted_pairs]

def calculate_safe_to_spend(db: DBManager) -> Dict[str, Any]:
    """
    Calculates the dynamic spending limit for today.
    Formula: (Planned income - Actual expenses this month - Upcoming subscriptions this month) / Remaining days in the month
    """
    base_currency = db.get_setting("base_currency", "RUB")
    try:
        planned_income = float(db.get_setting("planned_monthly_income", "50000"))
    except ValueError:
        planned_income = 50000.0

    today = date.today()
    year, month = today.year, today.month
    days_in_month = get_days_in_month(year, month)
    passed_days = today.day
    remaining_days = days_in_month - passed_days + 1  # Including today

    # Extract all transactions for the current month
    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year}-{month:02d}-{days_in_month:02d}"
    
    transactions = db.get_transactions(start_date=start_date, end_date=end_date)
    
    # Calculate actual expenses and actual incomes
    actual_expenses = 0.0
    actual_incomes = 0.0
    
    for t in transactions:
        # Skip transfers
        if t['transfer_to_account_id'] is not None:
            continue
        
        amount_base = db.convert_amount(t['amount'], t['currency'], base_currency)
        if t['category_type'] == 'expense':
            actual_expenses += amount_base
        elif t['category_type'] == 'income':
            actual_incomes += amount_base

    # Find upcoming (not yet paid this month) subscriptions
    subscriptions = db.get_subscriptions()
    upcoming_subs_total = 0.0
    
    for s in subscriptions:
        if not s['is_active']:
            continue
        # If the next payment date is in this month and is >= today
        next_pay = datetime.strptime(s['next_payment_date'], "%Y-%m-%d").date()
        if next_pay.year == year and next_pay.month == month and next_pay >= today:
            sub_amount_base = db.convert_amount(s['amount'], s['currency'], base_currency)
            upcoming_subs_total += sub_amount_base

    # Calculate remaining budget
    # Base logic: we focus on the planned income (or real income, if it's larger)
    effective_income = max(planned_income, actual_incomes)
    remaining_budget = effective_income - actual_expenses - upcoming_subs_total

    safe_today = remaining_budget / remaining_days if remaining_days > 0 else remaining_budget
    safe_today = max(0.0, round(safe_today, 2))

    return {
        "safe_today": safe_today,
        "remaining_budget": round(remaining_budget, 2),
        "actual_expenses": round(actual_expenses, 2),
        "actual_incomes": round(actual_incomes, 2),
        "remaining_days": remaining_days,
        "upcoming_subs": round(upcoming_subs_total, 2)
    }

def get_analytics_summary(
    db: DBManager,
    selected_date: date | None = None,
    mode: str = "month",
    transactions: List[Dict[str, Any]] | None = None,
    base_currency: str | None = None,
) -> Dict[str, Any]:
    """Returns forecasts, average check, most expensive day of the week, and other insights."""
    base_currency = base_currency or db.get_setting("base_currency", "RUB")
    selected_date = selected_date or date.today()
    year, month = selected_date.year, selected_date.month
    days_in_month = get_days_in_month(year, month)
    
    start_date, end_date = get_period_bounds(selected_date, mode)
    
    if transactions is None:
        transactions = db.get_transactions(start_date=start_date, end_date=end_date)
    
    expense_txs = [t for t in transactions if t['category_type'] == 'expense' and t['transfer_to_account_id'] is None]
    
    # 1. Average check
    total_expense = sum(db.convert_amount(t['amount'], t['currency'], base_currency) for t in expense_txs)
    avg_check = round(total_expense / len(expense_txs), 2) if expense_txs else 0.0

    # 2. Most expensive day of the week
    weekday_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    weekday_expenses = {i: 0.0 for i in range(7)}
    for t in expense_txs:
        t_date = datetime.strptime(t['date'], "%Y-%m-%d").date()
        amount_base = db.convert_amount(t['amount'], t['currency'], base_currency)
        weekday_expenses[t_date.weekday()] += amount_base
        
    top_weekday_idx = max(weekday_expenses, key=weekday_expenses.get)
    top_weekday_sum = weekday_expenses[top_weekday_idx]
    top_weekday = weekday_names[top_weekday_idx] if top_weekday_sum > 0 else "Нет данных"

    # 3. Spend forecast for the end of the month
    if mode == "day":
        passed_days = selected_date.day
    elif year == date.today().year and month == date.today().month:
        passed_days = date.today().day
    else:
        passed_days = days_in_month
    # If this is the first day of the month, divide by 1.
    days_divisor = passed_days if passed_days > 0 else 1
    projected_expense = (total_expense / days_divisor) * days_in_month
    projected_expense = round(projected_expense, 2)

    # 4. Comparison with the previous month
    # Get expenses for the previous month
    prev_expense = 0.0
    diff_percent = 0.0
    if mode != "day":
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        prev_days = get_days_in_month(prev_year, prev_month)
        prev_start = f"{prev_year}-{prev_month:02d}-01"
        prev_end = f"{prev_year}-{prev_month:02d}-{prev_days:02d}"

        prev_txs = db.get_transactions(start_date=prev_start, end_date=prev_end)
        prev_expense = sum(db.convert_amount(t['amount'], t['currency'], base_currency) for t in prev_txs if t['category_type'] == 'expense' and t['transfer_to_account_id'] is None)

        if prev_expense > 0:
            diff_percent = round(((total_expense - prev_expense) / prev_expense) * 100, 1)

    return {
        "total_expense": round(total_expense, 2),
        "avg_check": avg_check,
        "top_weekday": top_weekday,
        "top_weekday_sum": round(top_weekday_sum, 2),
        "projected_expense": projected_expense,
        "prev_month_expense": round(prev_expense, 2),
        "diff_percent": diff_percent,
        "transaction_count": len(expense_txs),
    }
