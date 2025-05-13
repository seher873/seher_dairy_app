from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, List


@dataclass
class Customer:
    id: Optional[int] = None
    name: str = ""
    phone: str = ""
    address: str = ""


@dataclass
class Transaction:
    id: Optional[int] = None
    customer_id: int = 0
    date: date = None
    milk_kg: float = 0.0
    milk_mound: float = 0.0
    rate: float = 0.0
    time_of_day: str = ""  # "Morning" or "Evening"
    
    @property
    def amount(self) -> float:
        """Calculate the amount based on milk quantity and rate"""
        return self.milk_kg * self.rate
    
    def __post_init__(self):
        # Convert string date to date object if needed
        if isinstance(self.date, str):
            self.date = datetime.strptime(self.date, '%Y-%m-%d').date()
        elif self.date is None:
            self.date = date.today()


@dataclass
class Payment:
    id: Optional[int] = None
    customer_id: int = 0
    date: date = None
    amount: float = 0.0
    
    def __post_init__(self):
        # Convert string date to date object if needed
        if isinstance(self.date, str):
            self.date = datetime.strptime(self.date, '%Y-%m-%d').date()
        elif self.date is None:
            self.date = date.today()


@dataclass
class BillSummary:
    customer: Customer
    total_milk_kg: float
    total_milk_mound: float
    rent: float
    mandi_average: float
    commission: float
    total_amount: float
    paid_amount: float
    remaining_amount: float
    transactions: List[Transaction]
    payments: List[Payment]
    start_date: date
    end_date: date
