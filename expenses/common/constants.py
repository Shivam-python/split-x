EXPENSE_STATUS_CHOICES = (
    ('Pending', 'Pending'),
    ('Paid', 'Paid'),
)

SPLIT_CHOICES = (
    ('Equal', 'Equal'),
    ('Exact', 'Exact'),
    ('Percentage', 'Percentage'),
)

from enum import Enum

class SplitType(Enum):
    PERCENTAGE = 'Percentage'
    EXACT = 'Exact'
    EQUAL = 'Equal'


class SplitExpenseStatus(Enum):
    PAID = "Paid"
    PENDING = "Pending"


SETTLEMENT_STATUS_CHOICES = (
    ('Pending', 'Pending'),
    ('Settled', 'Settled'),
    ('Failed', 'Failed'),
)
PAYMENT_LINK_URL = '/expense-app/payment-summary/{payment_uid}?signature={signature}'