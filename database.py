import sqlite3
from datetime import date, datetime
from typing import List, Optional, Tuple, Dict, Any
import os
from models import Customer, Transaction, Payment


class DairyDatabase:
    def __init__(self, db_path="dairy_management.db"):
        """Initialize the database connection and create tables if they don't exist."""
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.initialize_database()
        
    def connect(self):
        """Establish connection to the database."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
    
    def initialize_database(self):
        """Create necessary tables if they don't exist."""
        self.connect()
        
        # Create customers table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            address TEXT
        )
        ''')
        
        # Create transactions table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            milk_kg REAL NOT NULL,
            milk_mound REAL NOT NULL,
            rate REAL NOT NULL,
            time_of_day TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
        ''')
        
        # Create payments table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
        ''')
        
        self.conn.commit()
        self.close()
    
    # Customer methods
    def add_customer(self, customer: Customer) -> int:
        """Add a new customer to the database."""
        self.connect()
        self.cursor.execute(
            "INSERT INTO customers (name, phone, address) VALUES (?, ?, ?)",
            (customer.name, customer.phone, customer.address)
        )
        customer_id = self.cursor.lastrowid
        self.conn.commit()
        self.close()
        return customer_id
    
    def get_customer(self, customer_id: int) -> Optional[Customer]:
        """Get a customer by ID."""
        self.connect()
        self.cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
        row = self.cursor.fetchone()
        self.close()
        
        if row:
            return Customer(
                id=row['id'],
                name=row['name'],
                phone=row['phone'],
                address=row['address']
            )
        return None
    
    def get_all_customers(self) -> List[Customer]:
        """Get all customers."""
        self.connect()
        self.cursor.execute("SELECT * FROM customers ORDER BY name")
        rows = self.cursor.fetchall()
        self.close()
        
        return [
            Customer(
                id=row['id'],
                name=row['name'],
                phone=row['phone'],
                address=row['address']
            )
            for row in rows
        ]
    
    def update_customer(self, customer: Customer) -> bool:
        """Update a customer's information."""
        if not customer.id:
            return False
            
        self.connect()
        self.cursor.execute(
            "UPDATE customers SET name = ?, phone = ?, address = ? WHERE id = ?",
            (customer.name, customer.phone, customer.address, customer.id)
        )
        self.conn.commit()
        success = self.cursor.rowcount > 0
        self.close()
        return success
    
    def delete_customer(self, customer_id: int) -> bool:
        """Delete a customer by ID."""
        self.connect()
        # First check if there are related transactions or payments
        self.cursor.execute("SELECT COUNT(*) FROM transactions WHERE customer_id = ?", (customer_id,))
        transaction_count = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM payments WHERE customer_id = ?", (customer_id,))
        payment_count = self.cursor.fetchone()[0]
        
        if transaction_count > 0 or payment_count > 0:
            self.close()
            return False
        
        self.cursor.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
        self.conn.commit()
        success = self.cursor.rowcount > 0
        self.close()
        return success
    
    # Transaction methods
    def add_transaction(self, transaction: Transaction) -> int:
        """Add a new transaction."""
        self.connect()
        self.cursor.execute(
            """INSERT INTO transactions 
            (customer_id, date, milk_kg, milk_mound, rate, time_of_day) 
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                transaction.customer_id,
                transaction.date.isoformat(),
                transaction.milk_kg,
                transaction.milk_mound,
                transaction.rate,
                transaction.time_of_day
            )
        )
        transaction_id = self.cursor.lastrowid
        self.conn.commit()
        self.close()
        return transaction_id
    
    def get_transaction(self, transaction_id: int) -> Optional[Transaction]:
        """Get a transaction by ID."""
        self.connect()
        self.cursor.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,))
        row = self.cursor.fetchone()
        self.close()
        
        if row:
            return Transaction(
                id=row['id'],
                customer_id=row['customer_id'],
                date=datetime.fromisoformat(row['date']).date(),
                milk_kg=row['milk_kg'],
                milk_mound=row['milk_mound'],
                rate=row['rate'],
                time_of_day=row['time_of_day']
            )
        return None
    
    def get_customer_transactions(self, customer_id: int, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Transaction]:
        """Get all transactions for a customer, optionally filtered by date range."""
        self.connect()
        
        query = "SELECT * FROM transactions WHERE customer_id = ?"
        params = [customer_id]
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date.isoformat())
        
        query += " ORDER BY date, time_of_day"
        
        self.cursor.execute(query, tuple(params))
        rows = self.cursor.fetchall()
        self.close()
        
        return [
            Transaction(
                id=row['id'],
                customer_id=row['customer_id'],
                date=datetime.fromisoformat(row['date']).date(),
                milk_kg=row['milk_kg'],
                milk_mound=row['milk_mound'],
                rate=row['rate'],
                time_of_day=row['time_of_day']
            )
            for row in rows
        ]
    
    def update_transaction(self, transaction: Transaction) -> bool:
        """Update a transaction."""
        if not transaction.id:
            return False
            
        self.connect()
        self.cursor.execute(
            """UPDATE transactions 
            SET customer_id = ?, date = ?, milk_kg = ?, milk_mound = ?, rate = ?, time_of_day = ? 
            WHERE id = ?""",
            (
                transaction.customer_id,
                transaction.date.isoformat(),
                transaction.milk_kg,
                transaction.milk_mound,
                transaction.rate,
                transaction.time_of_day,
                transaction.id
            )
        )
        self.conn.commit()
        success = self.cursor.rowcount > 0
        self.close()
        return success
    
    def delete_transaction(self, transaction_id: int) -> bool:
        """Delete a transaction."""
        self.connect()
        self.cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        self.conn.commit()
        success = self.cursor.rowcount > 0
        self.close()
        return success
    
    # Payment methods
    def add_payment(self, payment: Payment) -> int:
        """Add a new payment."""
        self.connect()
        self.cursor.execute(
            "INSERT INTO payments (customer_id, date, amount) VALUES (?, ?, ?)",
            (
                payment.customer_id,
                payment.date.isoformat(),
                payment.amount
            )
        )
        payment_id = self.cursor.lastrowid
        self.conn.commit()
        self.close()
        return payment_id
    
    def get_payment(self, payment_id: int) -> Optional[Payment]:
        """Get a payment by ID."""
        self.connect()
        self.cursor.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
        row = self.cursor.fetchone()
        self.close()
        
        if row:
            return Payment(
                id=row['id'],
                customer_id=row['customer_id'],
                date=datetime.fromisoformat(row['date']).date(),
                amount=row['amount']
            )
        return None
    
    def get_customer_payments(self, customer_id: int, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Payment]:
        """Get all payments for a customer, optionally filtered by date range."""
        self.connect()
        
        query = "SELECT * FROM payments WHERE customer_id = ?"
        params = [customer_id]
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date.isoformat())
        
        query += " ORDER BY date"
        
        self.cursor.execute(query, tuple(params))
        rows = self.cursor.fetchall()
        self.close()
        
        return [
            Payment(
                id=row['id'],
                customer_id=row['customer_id'],
                date=datetime.fromisoformat(row['date']).date(),
                amount=row['amount']
            )
            for row in rows
        ]
    
    def update_payment(self, payment: Payment) -> bool:
        """Update a payment."""
        if not payment.id:
            return False
            
        self.connect()
        self.cursor.execute(
            "UPDATE payments SET customer_id = ?, date = ?, amount = ? WHERE id = ?",
            (
                payment.customer_id,
                payment.date.isoformat(),
                payment.amount,
                payment.id
            )
        )
        self.conn.commit()
        success = self.cursor.rowcount > 0
        self.close()
        return success
    
    def delete_payment(self, payment_id: int) -> bool:
        """Delete a payment."""
        self.connect()
        self.cursor.execute("DELETE FROM payments WHERE id = ?", (payment_id,))
        self.conn.commit()
        success = self.cursor.rowcount > 0
        self.close()
        return success
    
    # Summary methods
    def get_customer_summary(self, customer_id: int, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get a summary of a customer's transactions and payments within a date range."""
        self.connect()
        
        # Get total milk and amount
        self.cursor.execute(
            """SELECT 
                SUM(milk_kg) as total_milk_kg,
                SUM(milk_mound) as total_milk_mound,
                SUM(milk_kg * rate) as total_amount
            FROM transactions 
            WHERE customer_id = ? AND date >= ? AND date <= ?""",
            (customer_id, start_date.isoformat(), end_date.isoformat())
        )
        milk_row = self.cursor.fetchone()
        
        # Get total payments
        self.cursor.execute(
            "SELECT SUM(amount) as total_paid FROM payments WHERE customer_id = ? AND date >= ? AND date <= ?",
            (customer_id, start_date.isoformat(), end_date.isoformat())
        )
        payment_row = self.cursor.fetchone()
        
        self.close()
        
        # Calculate summary
        total_milk_kg = milk_row['total_milk_kg'] or 0
        total_milk_mound = milk_row['total_milk_mound'] or 0
        total_amount = milk_row['total_amount'] or 0
        total_paid = payment_row['total_paid'] or 0
        
        # Additional calculations (based on requirements)
        rent = total_milk_kg * 0.05  # Assuming 5% rent
        mandi_average = total_milk_kg * 0.02  # Assuming 2% mandi average
        commission = total_milk_kg * 0.03  # Assuming 3% commission
        
        # Final calculations
        net_amount = total_amount - (rent + mandi_average + commission)
        remaining_amount = net_amount - total_paid
        
        return {
            'total_milk_kg': total_milk_kg,
            'total_milk_mound': total_milk_mound,
            'total_amount': total_amount,
            'rent': rent,
            'mandi_average': mandi_average,
            'commission': commission,
            'net_amount': net_amount,
            'total_paid': total_paid,
            'remaining_amount': remaining_amount
        }
