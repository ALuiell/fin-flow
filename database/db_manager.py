import sqlite3
import os
import contextlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from models import Account, Category, Transaction, Budget, Goal, Subscription

class DBManager:
    def __init__(self, db_path: str = "finflow.db"):
        self.db_path = db_path
        self.init_db()

    @contextlib.contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()


    def init_db(self):
        """Создает таблицы и инициализирует дефолтные значения, если база пустая."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Таблица настроек
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """)

            # 2. Таблица курсов валют к USD (1 ед. валюты = X USD)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS currency_rates (
                code TEXT PRIMARY KEY,
                rate_to_usd REAL NOT NULL,
                last_updated TEXT
            )
            """)

            # 3. Таблица счетов
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                balance REAL DEFAULT 0,
                currency TEXT NOT NULL,
                color TEXT
            )
            """)

            # 4. Таблица категорий
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                icon TEXT,
                color TEXT
            )
            """)

            # 5. Таблица транзакций
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                category_id INTEGER,
                account_id INTEGER NOT NULL,
                transfer_to_account_id INTEGER,
                date TEXT NOT NULL,
                description TEXT,
                tags TEXT,
                FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE SET NULL,
                FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE,
                FOREIGN KEY(transfer_to_account_id) REFERENCES accounts(id) ON DELETE CASCADE
            )
            """)

            # 6. Таблица бюджетов
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER UNIQUE,
                amount_limit REAL NOT NULL,
                currency TEXT NOT NULL,
                month TEXT NOT NULL,
                FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE
            )
            """)

            # 7. Таблица целей накопления
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                target_amount REAL NOT NULL,
                current_amount REAL DEFAULT 0,
                currency TEXT NOT NULL,
                deadline TEXT,
                status TEXT DEFAULT 'active' CHECK(status IN ('active', 'completed', 'failed'))
            )
            """)

            # 8. Таблица подписок
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                category_id INTEGER,
                period TEXT NOT NULL CHECK(period IN ('monthly', 'yearly')),
                next_payment_date TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE SET NULL
            )
            """)

            # Заполнение настроек по умолчанию
            cursor.execute("SELECT COUNT(*) FROM settings")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO settings (key, value) VALUES ('base_currency', 'USD')")
                cursor.execute("INSERT INTO settings (key, value) VALUES ('planned_monthly_income', '2000')")

            # Заполнение курсов валют по умолчанию (1 ед. валюты = X USD)
            cursor.execute("SELECT COUNT(*) FROM currency_rates")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO currency_rates (code, rate_to_usd, last_updated) VALUES ('USD', 1.0, ?)", (datetime.now().isoformat(),))
                cursor.execute("INSERT INTO currency_rates (code, rate_to_usd, last_updated) VALUES ('EUR', 1.08, ?)", (datetime.now().isoformat(),))
                cursor.execute("INSERT INTO currency_rates (code, rate_to_usd, last_updated) VALUES ('UAH', 0.025, ?)", (datetime.now().isoformat(),))
                cursor.execute("INSERT INTO currency_rates (code, rate_to_usd, last_updated) VALUES ('RUB', 0.011, ?)", (datetime.now().isoformat(),))

            # Заполнение категорий по умолчанию
            cursor.execute("SELECT COUNT(*) FROM categories")
            if cursor.fetchone()[0] == 0:
                default_categories = [
                    # Расходы
                    ('Продукты', 'expense', '🍏', '#4CAF50'),
                    ('Транспорт', 'expense', '🚗', '#2196F3'),
                    ('Жилье и ЖКХ', 'expense', '🏠', '#FF9800'),
                    ('Кафе и Рестораны', 'expense', '☕', '#E91E63'),
                    ('Развлечения', 'expense', '🎬', '#9C27B0'),
                    ('Одежда и Покупки', 'expense', '🛍️', '#00BCD4'),
                    ('Здоровье', 'expense', '💊', '#F44336'),
                    ('Другое', 'expense', '💸', '#9E9E9E'),
                    # Доходы
                    ('Зарплата', 'income', '💼', '#009688'),
                    ('Инвестиции', 'income', '📈', '#FFC107'),
                    ('Подработка', 'income', '💰', '#00E676'),
                    ('Подарки', 'income', '🎁', '#EA80FC')
                ]
                cursor.executemany("INSERT INTO categories (name, type, icon, color) VALUES (?, ?, ?, ?)", default_categories)

            # Заполнение счетов по умолчанию
            cursor.execute("SELECT COUNT(*) FROM accounts")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO accounts (name, balance, currency, color) VALUES ('Наличные', 200.0, 'USD', '#8BC34A')")
                cursor.execute("INSERT INTO accounts (name, balance, currency, color) VALUES ('Основная карта', 1500.0, 'USD', '#0288D1')")

            conn.commit()

    # --- РАБОТА С НАСТРОЙКАМИ ---
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row['value'] if row else default

    def set_setting(self, key: str, value: str):
        with self._get_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
            conn.commit()

    # --- РАБОТА С КУРСАМИ ВАЛЮТ ---
    def get_rates(self) -> Dict[str, float]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT code, rate_to_usd FROM currency_rates")
            return {row['code']: row['rate_to_usd'] for row in cursor.fetchall()}

    def update_rate(self, code: str, rate_to_usd: float):
        with self._get_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO currency_rates (code, rate_to_usd, last_updated) VALUES (?, ?, ?)",
                         (code.upper(), rate_to_usd, datetime.now().isoformat()))
            conn.commit()

    def convert_amount(self, amount: float, from_curr: str, to_curr: str) -> float:
        if from_curr == to_curr:
            return amount
        rates = self.get_rates()
        if from_curr not in rates or to_curr not in rates:
            return amount  # Если валюты нет, возвращаем без изменений
        
        # Переводим в USD, затем в целевую валюту
        amount_usd = amount * rates[from_curr]
        amount_target = amount_usd / rates[to_curr]
        return round(amount_target, 2)

    # --- РАБОТА СО СЧЕТАМИ (ACCOUNTS) ---
    def add_account(self, name: str, balance: float, currency: str, color: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO accounts (name, balance, currency, color) VALUES (?, ?, ?, ?)",
                           (name, balance, currency, color))
            conn.commit()
            return cursor.lastrowid

    def get_accounts(self) -> List[Account]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, balance, currency, color FROM accounts")
            return [Account(r['id'], r['name'], r['balance'], r['currency'], r['color']) for r in cursor.fetchall()]

    def get_account(self, account_id: int) -> Optional[Account]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, balance, currency, color FROM accounts WHERE id = ?", (account_id,))
            r = cursor.fetchone()
            return Account(r['id'], r['name'], r['balance'], r['currency'], r['color']) if r else None

    def update_account(self, account: Account) -> bool:
        with self._get_connection() as conn:
            conn.execute("UPDATE accounts SET name = ?, balance = ?, currency = ?, color = ? WHERE id = ?",
                         (account.name, account.balance, account.currency, account.color, account.id))
            conn.commit()
            return True

    def delete_account(self, account_id: int) -> bool:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
            conn.commit()
            return True

    # --- РАБОТА С КАТЕГОРИЯМИ (CATEGORIES) ---
    def add_category(self, name: str, type_: str, icon: str, color: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO categories (name, type, icon, color) VALUES (?, ?, ?, ?)",
                           (name, type_, icon, color))
            conn.commit()
            return cursor.lastrowid

    def get_categories(self) -> List[Category]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, type, icon, color FROM categories")
            return [Category(r['id'], r['name'], r['type'], r['icon'], r['color']) for r in cursor.fetchall()]

    def get_category(self, category_id: int) -> Optional[Category]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, type, icon, color FROM categories WHERE id = ?", (category_id,))
            r = cursor.fetchone()
            return Category(r['id'], r['name'], r['type'], r['icon'], r['color']) if r else None

    def update_category(self, category: Category) -> bool:
        with self._get_connection() as conn:
            conn.execute("UPDATE categories SET name = ?, type = ?, icon = ?, color = ? WHERE id = ?",
                         (category.name, category.type, category.icon, category.color, category.id))
            conn.commit()
            return True

    def delete_category(self, category_id: int) -> bool:
        with self._get_connection() as conn:
            # Находим ID дефолтной категории "Другое"
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM categories WHERE name = 'Другое' AND type = 'expense' LIMIT 1")
            row = cursor.fetchone()
            other_id = row['id'] if row else None

            # Если удаляем расходную категорию, переносим транзакции в "Другое"
            if other_id and other_id != category_id:
                conn.execute("UPDATE transactions SET category_id = ? WHERE category_id = ?", (other_id, category_id))
                conn.execute("UPDATE subscriptions SET category_id = ? WHERE category_id = ?", (other_id, category_id))
            
            conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
            conn.commit()
            return True

    # --- РАБОТА С ТРАНЗАКЦИЯМИ (TRANSACTIONS) ---
    def add_transaction(self, t: Transaction) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Вставляем транзакцию
            cursor.execute("""
            INSERT INTO transactions (amount, currency, category_id, account_id, transfer_to_account_id, date, description, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (t.amount, t.currency, t.category_id, t.account_id, t.transfer_to_account_id, t.date, t.description, t.tags))
            t_id = cursor.lastrowid

            # Обновляем балансы счетов
            if t.transfer_to_account_id:
                # Внутренний перевод
                # Списываем со счета-отправителя (сконвертировав в его валюту)
                acc_from = self.get_account(t.account_id)
                amount_from = self.convert_amount(t.amount, t.currency, acc_from.currency)
                cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount_from, t.account_id))

                # Зачисляем на счет-получатель (сконвертировав в его валюту)
                acc_to = self.get_account(t.transfer_to_account_id)
                amount_to = self.convert_amount(t.amount, t.currency, acc_to.currency)
                cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount_to, t.transfer_to_account_id))
            else:
                # Обычный доход / расход
                # Находим тип категории
                category = self.get_category(t.category_id)
                is_income = category and category.type == 'income'
                
                acc = self.get_account(t.account_id)
                amount_acc = self.convert_amount(t.amount, t.currency, acc.currency)
                
                if is_income:
                    cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount_acc, t.account_id))
                else:
                    cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount_acc, t.account_id))

            conn.commit()
            return t_id

    def get_transactions(self, start_date: Optional[str] = None, end_date: Optional[str] = None,
                         category_id: Optional[int] = None, account_id: Optional[int] = None,
                         tag: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = """
            SELECT t.id, t.amount, t.currency, t.category_id, t.account_id, t.transfer_to_account_id, 
                   t.date, t.description, t.tags, 
                   c.name as category_name, c.icon as category_icon, c.color as category_color, c.type as category_type,
                   a.name as account_name, a.color as account_color,
                   a2.name as transfer_account_name, a2.color as transfer_account_color
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN accounts a ON t.account_id = a.id
            LEFT JOIN accounts a2 ON t.transfer_to_account_id = a2.id
            WHERE 1=1
            """
            params = []

            if start_date:
                query += " AND t.date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND t.date <= ?"
                params.append(end_date)
            if category_id:
                query += " AND t.category_id = ?"
                params.append(category_id)
            if account_id:
                query += " AND (t.account_id = ? OR t.transfer_to_account_id = ?)"
                params.extend([account_id, account_id])
            if tag:
                query += " AND t.tags LIKE ?"
                params.append(f"%{tag}%")

            query += " ORDER BY t.date DESC, t.id DESC"
            cursor.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]

    def delete_transaction(self, t_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем детали транзакции
            cursor.execute("SELECT amount, currency, category_id, account_id, transfer_to_account_id FROM transactions WHERE id = ?", (t_id,))
            row = cursor.fetchone()
            if not row:
                return False

            amount = row['amount']
            currency = row['currency']
            category_id = row['category_id']
            account_id = row['account_id']
            transfer_to_account_id = row['transfer_to_account_id']

            # Откатываем балансы
            if transfer_to_account_id:
                acc_from = self.get_account(account_id)
                amount_from = self.convert_amount(amount, currency, acc_from.currency)
                cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount_from, account_id))

                acc_to = self.get_account(transfer_to_account_id)
                amount_to = self.convert_amount(amount, currency, acc_to.currency)
                cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount_to, transfer_to_account_id))
            else:
                category = self.get_category(category_id)
                is_income = category and category.type == 'income'
                
                acc = self.get_account(account_id)
                amount_acc = self.convert_amount(amount, currency, acc.currency)
                
                if is_income:
                    cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount_acc, account_id))
                else:
                    cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount_acc, account_id))

            cursor.execute("DELETE FROM transactions WHERE id = ?", (t_id,))
            conn.commit()
            return True

    # --- РАБОТА С БЮДЖЕТАМИ (BUDGETS) ---
    def add_or_update_budget(self, category_id: int, amount_limit: float, currency: str, month: str) -> bool:
        with self._get_connection() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO budgets (category_id, amount_limit, currency, month)
            VALUES (?, ?, ?, ?)
            """, (category_id, amount_limit, currency, month))
            conn.commit()
            return True

    def get_budgets(self, month: str) -> List[Dict[str, Any]]:
        """Возвращает бюджеты на указанный месяц с реальными тратами по ним."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT b.id, b.category_id, b.amount_limit, b.currency, b.month,
                   c.name as category_name, c.icon as category_icon, c.color as category_color
            FROM budgets b
            JOIN categories c ON b.category_id = c.id
            WHERE b.month = ?
            """, (month,))
            budgets = [dict(r) for r in cursor.fetchall()]

            # Считаем реальные траты по каждой категории за этот месяц
            for b in budgets:
                cursor.execute("""
                SELECT amount, currency FROM transactions 
                WHERE category_id = ? AND date LIKE ? AND transfer_to_account_id IS NULL
                """, (b['category_id'], f"{month}%"))
                
                total_spent = 0.0
                for row in cursor.fetchall():
                    # Конвертируем в валюту лимита бюджета
                    total_spent += self.convert_amount(row['amount'], row['currency'], b['currency'])
                
                b['spent'] = round(total_spent, 2)
            
            return budgets

    def delete_budget(self, budget_id: int) -> bool:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM budgets WHERE id = ?", (budget_id,))
            conn.commit()
            return True

    # --- РАБОТА С ЦЕЛЯМИ (GOALS) ---
    def add_goal(self, name: str, target_amount: float, currency: str, deadline: Optional[str] = None) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO goals (name, target_amount, current_amount, currency, deadline) VALUES (?, ?, 0, ?, ?)",
                           (name, target_amount, currency, deadline))
            conn.commit()
            return cursor.lastrowid

    def get_goals(self) -> List[Goal]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, target_amount, current_amount, currency, deadline, status FROM goals")
            return [Goal(r['id'], r['name'], r['target_amount'], r['current_amount'], r['currency'], r['deadline'], r['status']) 
                    for r in cursor.fetchall()]

    def update_goal(self, goal: Goal) -> bool:
        with self._get_connection() as conn:
            conn.execute("UPDATE goals SET name = ?, target_amount = ?, current_amount = ?, currency = ?, deadline = ?, status = ? WHERE id = ?",
                         (goal.name, goal.target_amount, goal.current_amount, goal.currency, goal.deadline, goal.status, goal.id))
            conn.commit()
            return True

    def delete_goal(self, goal_id: int) -> bool:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
            conn.commit()
            return True

    # --- РАБОТА С ПОДПИСКАМИ (SUBSCRIPTIONS) ---
    def add_subscription(self, name: str, amount: float, currency: str, category_id: Optional[int], period: str, next_payment_date: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO subscriptions (name, amount, currency, category_id, period, next_payment_date, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (name, amount, currency, category_id, period, next_payment_date))
            conn.commit()
            return cursor.lastrowid

    def get_subscriptions(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT s.id, s.name, s.amount, s.currency, s.category_id, s.period, s.next_payment_date, s.is_active,
                   c.name as category_name, c.icon as category_icon, c.color as category_color
            FROM subscriptions s
            LEFT JOIN categories c ON s.category_id = c.id
            """)
            return [dict(r) for r in cursor.fetchall()]

    def update_subscription(self, s: Subscription) -> bool:
        with self._get_connection() as conn:
            conn.execute("""
            UPDATE subscriptions SET name = ?, amount = ?, currency = ?, category_id = ?, period = ?, next_payment_date = ?, is_active = ?
            WHERE id = ?
            """, (s.name, s.amount, s.currency, s.category_id, s.period, s.next_payment_date, s.is_active, s.id))
            conn.commit()
            return True

    def delete_subscription(self, sub_id: int) -> bool:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM subscriptions WHERE id = ?", (sub_id,))
            conn.commit()
            return True
