import re
import calendar
from datetime import datetime, date
from typing import List, Dict, Any
from database.db_manager import DBManager

def eval_expression(expr_str: str) -> float:
    """Безопасно вычисляет математическое выражение из строки."""
    if not expr_str:
        return 0.0
    # Очищаем строку
    expr_str = expr_str.replace(" ", "").replace(",", ".")
    # Разрешаем только цифры, точки, круглые скобки и базовые операторы
    if not re.match(r"^[\d.+\-*/()]+$", expr_str):
        raise ValueError("Недопустимые символы")
    try:
        # Ограничиваем пространство имен для безопасности
        result = float(eval(expr_str, {"__builtins__": None}, {}))
        return round(result, 2)
    except Exception:
        raise ValueError("Ошибка вычисления")

def get_days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]

def calculate_safe_to_spend(db: DBManager) -> Dict[str, Any]:
    """
    Рассчитывает динамический лимит трат на сегодня.
    Формула: (Плановый доход - Фактические расходы этого месяца - Предстоящие подписки этого месяца) / Оставшиеся дни в месяце
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
    remaining_days = days_in_month - passed_days + 1  # Включая сегодняшний день

    # Вытаскиваем все транзакции текущего месяца
    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year}-{month:02d}-{days_in_month:02d}"
    
    transactions = db.get_transactions(start_date=start_date, end_date=end_date)
    
    # Считаем фактические расходы и фактические доходы
    actual_expenses = 0.0
    actual_incomes = 0.0
    
    for t in transactions:
        # Пропускаем переводы
        if t['transfer_to_account_id'] is not None:
            continue
        
        amount_base = db.convert_amount(t['amount'], t['currency'], base_currency)
        if t['category_type'] == 'expense':
            actual_expenses += amount_base
        elif t['category_type'] == 'income':
            actual_incomes += amount_base

    # Находим предстоящие (еще не оплаченные в этом месяце) подписки
    subscriptions = db.get_subscriptions()
    upcoming_subs_total = 0.0
    
    for s in subscriptions:
        if not s['is_active']:
            continue
        # Если дата следующего списания в этом месяце и она >= сегодня
        next_pay = datetime.strptime(s['next_payment_date'], "%Y-%m-%d").date()
        if next_pay.year == year and next_pay.month == month and next_pay >= today:
            sub_amount_base = db.convert_amount(s['amount'], s['currency'], base_currency)
            upcoming_subs_total += sub_amount_base

    # Считаем остаток бюджета
    # Базовая логика: мы ориентируемся на планируемый доход (или реальный доход, если он больше)
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

def get_analytics_summary(db: DBManager) -> Dict[str, Any]:
    """Возвращает прогнозы, средний чек, самый затратный день недели и другие инсайты."""
    base_currency = db.get_setting("base_currency", "RUB")
    today = date.today()
    year, month = today.year, today.month
    days_in_month = get_days_in_month(year, month)
    
    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year}-{month:02d}-{days_in_month:02d}"
    
    transactions = db.get_transactions(start_date=start_date, end_date=end_date)
    
    expense_txs = [t for t in transactions if t['category_type'] == 'expense' and t['transfer_to_account_id'] is None]
    
    # 1. Средний чек
    total_expense = sum(db.convert_amount(t['amount'], t['currency'], base_currency) for t in expense_txs)
    avg_check = round(total_expense / len(expense_txs), 2) if expense_txs else 0.0

    # 2. Самый затратный день недели
    weekday_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    weekday_expenses = {i: 0.0 for i in range(7)}
    for t in expense_txs:
        t_date = datetime.strptime(t['date'], "%Y-%m-%d").date()
        amount_base = db.convert_amount(t['amount'], t['currency'], base_currency)
        weekday_expenses[t_date.weekday()] += amount_base
        
    top_weekday_idx = max(weekday_expenses, key=weekday_expenses.get)
    top_weekday_sum = weekday_expenses[top_weekday_idx]
    top_weekday = weekday_names[top_weekday_idx] if top_weekday_sum > 0 else "Нет данных"

    # 3. Прогноз трат на конец месяца
    passed_days = today.day
    # Если это первый день месяца, делим на 1.
    days_divisor = passed_days if passed_days > 0 else 1
    projected_expense = (total_expense / days_divisor) * days_in_month
    projected_expense = round(projected_expense, 2)

    # 4. Сравнение с прошлым месяцем
    # Получаем траты за прошлый месяц
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    prev_days = get_days_in_month(prev_year, prev_month)
    prev_start = f"{prev_year}-{prev_month:02d}-01"
    prev_end = f"{prev_year}-{prev_month:02d}-{prev_days:02d}"
    
    prev_txs = db.get_transactions(start_date=prev_start, end_date=prev_end)
    prev_expense = sum(db.convert_amount(t['amount'], t['currency'], base_currency) for t in prev_txs if t['category_type'] == 'expense' and t['transfer_to_account_id'] is None)
    
    diff_percent = 0.0
    if prev_expense > 0:
        diff_percent = round(((total_expense - prev_expense) / prev_expense) * 100, 1)

    return {
        "total_expense": round(total_expense, 2),
        "avg_check": avg_check,
        "top_weekday": top_weekday,
        "top_weekday_sum": round(top_weekday_sum, 2),
        "projected_expense": projected_expense,
        "prev_month_expense": round(prev_expense, 2),
        "diff_percent": diff_percent
    }
