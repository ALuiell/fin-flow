import unittest
import os
import tempfile
from database.db_manager import DBManager
from models import Transaction, Account, Category
from utils.analytics_helper import (
    eval_expression,
    calculate_safe_to_spend,
    get_period_bounds,
    build_cumulative_spend_series,
    sort_transactions_by_selected_subcategories,
)
from datetime import date

class TestFinFlowLogic(unittest.TestCase):
    def setUp(self):
        # Используем временную БД на диске для тестов
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.db = DBManager(self.db_path)

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_eval_expression(self):
        # Простые тесты
        self.assertEqual(eval_expression("100+200"), 300.0)
        self.assertEqual(eval_expression("150 * 2 - 50"), 250.0)
        self.assertEqual(eval_expression(" (10 + 20) / 2 "), 15.0)
        self.assertEqual(eval_expression("12.5 + 7.5"), 20.0)
        self.assertEqual(eval_expression(""), 0.0)
        
        # Ошибки
        with self.assertRaises(ValueError):
            eval_expression("100 + abc")
        with self.assertRaises(ValueError):
            eval_expression("100 / 0")

    def test_currency_conversion(self):
        # Базовые курсы по умолчанию:
        # USD: 1.0
        # EUR: 1.08
        # RUB: 0.011 (т.е. 1 RUB = 0.011 USD)
        
        # 100 USD в RUB: 100 * 1.0 / 0.011 = 9090.91 RUB
        # Давайте проверим
        rub_amount = self.db.convert_amount(100.0, "USD", "RUB")
        self.assertAlmostEqual(rub_amount, 9090.91, places=2)

        # 90.91 RUB в USD (должно быть около 1 USD)
        usd_amount = self.db.convert_amount(90.91, "RUB", "USD")
        self.assertAlmostEqual(usd_amount, 1.0, places=2)

    def test_default_subcategories_are_created_once(self):
        categories = self.db.get_categories()
        products = next(c for c in categories if c.name == "Продукты" and c.parent_id is None)
        product_children = [c for c in categories if c.parent_id == products.id]

        self.assertTrue(any(c.name == "Бакалея и крупы" for c in product_children))

        DBManager(self.db_path)
        categories_after_reinit = self.db.get_categories()
        product_children_after_reinit = [
            c for c in categories_after_reinit
            if c.parent_id == products.id and c.name == "Бакалея и крупы"
        ]
        self.assertEqual(len(product_children_after_reinit), 1)

    def test_transaction_balances(self):
        # Создаем категорию расходов
        cat_id = self.db.add_category("Тест Еда", "expense", "🍎", "#FF0000")
        
        # Получаем исходные балансы
        accs = self.db.get_accounts()
        acc = accs[0] # По умолчанию 'Наличные' с 200.0 USD
        initial_balance = acc.balance
        
        # Делаем расход на 50.0 USD
        t = Transaction(
            id=None,
            amount=50.0,
            currency="USD",
            category_id=cat_id,
            account_id=acc.id,
            transfer_to_account_id=None,
            date="2026-06-04",
            description="Тестовый расход",
            tags=""
        )
        t_id = self.db.add_transaction(t)
        self.assertIsNotNone(t_id)

        # Проверяем, что баланс счета уменьшился на 50
        updated_acc = self.db.get_account(acc.id)
        self.assertEqual(updated_acc.balance, initial_balance - 50.0)

        # Удаляем транзакцию
        self.db.delete_transaction(t_id)

        # Проверяем, что баланс вернулся
        restored_acc = self.db.get_account(acc.id)
        self.assertEqual(restored_acc.balance, initial_balance)

    def test_internal_transfer(self):
        accs = self.db.get_accounts()
        acc1 = accs[0] # Наличные (200.0 USD)
        acc2 = accs[1] # Основная карта (1500.0 USD)
        
        # Переводим 300.0 USD с Основная карта (acc2) на Наличные (acc1)
        t = Transaction(
            id=None,
            amount=300.0,
            currency="USD",
            category_id=None,
            account_id=acc2.id,
            transfer_to_account_id=acc1.id,
            date="2026-06-04",
            description="Перевод на наличные",
            tags=""
        )
        self.db.add_transaction(t)

        updated_acc1 = self.db.get_account(acc1.id)
        updated_acc2 = self.db.get_account(acc2.id)

        self.assertEqual(updated_acc1.balance, acc1.balance + 300.0)
        self.assertEqual(updated_acc2.balance, acc2.balance - 300.0)

    def test_analytics_period_bounds(self):
        selected = date(2026, 6, 18)

        self.assertEqual(get_period_bounds(selected, "day"), ("2026-06-18", "2026-06-18"))
        self.assertEqual(get_period_bounds(selected, "month"), ("2026-06-01", "2026-06-30"))

    def test_cumulative_spend_series_includes_full_month_and_subscriptions(self):
        transactions = [
            {
                "amount": 10.0,
                "currency": "USD",
                "date": "2026-06-01",
                "category_type": "expense",
                "transfer_to_account_id": None,
            },
            {
                "amount": 5.0,
                "currency": "USD",
                "date": "2026-06-03",
                "category_type": "expense",
                "transfer_to_account_id": None,
            },
            {
                "amount": 99.0,
                "currency": "USD",
                "date": "2026-06-04",
                "category_type": "income",
                "transfer_to_account_id": None,
            },
        ]
        subscriptions = [
            {
                "amount": 20.0,
                "currency": "USD",
                "next_payment_date": "2026-06-05",
                "is_active": 1,
            },
            {
                "amount": 50.0,
                "currency": "USD",
                "next_payment_date": "2026-06-10",
                "is_active": 0,
            },
        ]

        series = build_cumulative_spend_series(
            transactions,
            subscriptions,
            2026,
            6,
            300.0,
            lambda amount, _from, _to: amount,
            "USD",
            today=date(2026, 6, 18),
        )

        self.assertEqual(len(series["days"]), 30)
        self.assertEqual(series["actual_spend"][0], 10.0)
        self.assertEqual(series["actual_spend"][2], 15.0)
        self.assertEqual(series["actual_spend"][17], 15.0)
        self.assertIsNone(series["actual_spend"][18])
        self.assertEqual(series["ideal_spend"][-1], 300.0)
        self.assertEqual(series["planned_spend"][3], 0.0)
        self.assertEqual(series["planned_spend"][4], 20.0)
        self.assertEqual(series["planned_spend"][-1], 20.0)

    def test_selected_subcategory_transactions_are_sorted_first(self):
        transactions = [
            {"id": 1, "category_id": 10},
            {"id": 2, "category_id": 20},
            {"id": 3, "category_id": 10},
        ]

        sorted_txs = sort_transactions_by_selected_subcategories(transactions, [20])
        self.assertEqual([t["id"] for t in sorted_txs], [2, 1, 3])

    def test_tags_migrate_from_existing_transactions(self):
        cat_id = self.db.add_category("Тест теги", "expense", "🏷️", "#9E9E9E")
        acc = self.db.get_accounts()[0]
        self.db.add_transaction(Transaction(
            id=None,
            amount=10.0,
            currency="USD",
            category_id=cat_id,
            account_id=acc.id,
            transfer_to_account_id=None,
            date="2026-06-18",
            description="Тест",
            tags="alpha, beta"
        ))

        with self.db._get_connection() as conn:
            conn.execute("DELETE FROM tags")
            conn.commit()

        DBManager(self.db_path)
        self.assertEqual(self.db.get_all_tags(), ["alpha", "beta"])
        filtered = self.db.get_transactions(tags=["alpha"])
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["tags"], "alpha, beta")

    def test_standalone_tag_can_be_created(self):
        before = self.db.revision
        self.db.add_tag("future")
        self.assertIn("future", self.db.get_all_tags())
        self.assertGreater(self.db.revision, before)

    def test_transaction_tags_are_stored_in_link_table(self):
        cat_id = self.db.add_category("Тест связь тегов", "expense", "🏷️", "#9E9E9E")
        acc = self.db.get_accounts()[0]
        tx_id = self.db.add_transaction(Transaction(
            id=None,
            amount=15.0,
            currency="USD",
            category_id=cat_id,
            account_id=acc.id,
            transfer_to_account_id=None,
            date="2026-06-18",
            description="Связь",
            tags="alpha, beta"
        ))

        with self.db._get_connection() as conn:
            rows = conn.execute("""
                SELECT tg.name
                FROM transaction_tags tt
                JOIN tags tg ON tg.id = tt.tag_id
                WHERE tt.transaction_id = ?
                ORDER BY tg.name
            """, (tx_id,)).fetchall()

        self.assertEqual([row["name"] for row in rows], ["alpha", "beta"])
        filtered = self.db.get_transactions(tags=["alpha"])
        self.assertEqual([t["id"] for t in filtered], [tx_id])
        self.assertEqual(filtered[0]["tags"], "alpha, beta")

if __name__ == '__main__':
    unittest.main()
