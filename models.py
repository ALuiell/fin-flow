from dataclasses import dataclass
from typing import Optional

@dataclass
class Account:
    id: Optional[int]
    name: str
    balance: float
    currency: str
    color: str

@dataclass
class Category:
    id: Optional[int]
    name: str
    type: str  # 'income' or 'expense'
    icon: Optional[str]  # Emoji icon e.g. '🍏'
    color: str  # HEX code

@dataclass
class Transaction:
    id: Optional[int]
    amount: float
    currency: str
    category_id: Optional[int]
    account_id: int
    transfer_to_account_id: Optional[int]  # Used for internal transfers
    date: str  # YYYY-MM-DD
    description: Optional[str]
    tags: Optional[str]  # Comma separated e.g. "holiday,food"

@dataclass
class Budget:
    id: Optional[int]
    category_id: int
    amount_limit: float
    currency: str
    month: str  # YYYY-MM

@dataclass
class Goal:
    id: Optional[int]
    name: str
    target_amount: float
    current_amount: float
    currency: str
    deadline: Optional[str]  # YYYY-MM-DD
    status: str = 'active'  # 'active', 'completed', 'failed'

@dataclass
class Subscription:
    id: Optional[int]
    name: str
    amount: float
    currency: str
    category_id: Optional[int]
    period: str  # 'monthly' or 'yearly'
    next_payment_date: str  # YYYY-MM-DD
    is_active: int = 1
