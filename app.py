import streamlit as st
import pandas as pd
import numpy as np
import os
import tempfile
from datetime import date, datetime, timedelta
import base64
from io import BytesIO

from database import DairyDatabase
from models import Customer, Transaction, Payment, BillSummary
from report_generator import DairyReportGenerator

# Set page title and favicon
st.set_page_config(
    page_title="Dairy Management System",
    page_icon="🐄",
    layout="wide"
)

# Initialize database
@st.cache_resource
def get_database():
    return DairyDatabase()

db = get_database()

# Initialize report generator
@st.cache_resource
def get_report_generator():
    return DairyReportGenerator()

report_gen = get_report_generator()

# Utility functions
def convert_kg_to_mound(kg_value):
    """Convert kilograms to mound. 1 mound = 40 kg."""
    return kg_value / 40

def convert_mound_to_kg(mound_value):
    """Convert mound to kilograms. 1 mound = 40 kg."""
    return mound_value * 40

def get_download_link(file_path, link_text):
    """Generate a download link for a file."""
    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{os.path.basename(file_path)}">{link_text}</a>'
    return href

# Main app structure
def main():
    st.title("🐄 Dairy Management System")
    
    # Just show the daily entry page directly (simpler interface)
    show_daily_entry_page()

# Dashboard page
def show_dashboard():
    st.header("Dashboard")
    
    # Get some basic stats
    customers = db.get_all_customers()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Customers", len(customers))
    
    # Get today's transactions
    today = date.today()
    today_transactions = []
    if customers:
        for customer in customers:
            customer_transactions = db.get_customer_transactions(customer.id, today, today)
            today_transactions.extend(customer_transactions)
    
    with col2:
        st.metric("Today's Transactions", len(today_transactions))
    
    with col3:
        total_milk_today = sum(t.milk_kg for t in today_transactions)
        st.metric("Today's Milk (kg)", f"{total_milk_today:.2f}")
    
    # Show recent transactions
    st.subheader("Recent Transactions")
    if today_transactions:
        recent_data = []
        for t in today_transactions:
            customer = db.get_customer(t.customer_id)
            recent_data.append({
                "Customer": customer.name if customer else "Unknown",
                "Date": t.date,
                "Time": t.time_of_day,
                "Milk (kg)": t.milk_kg,
                "Milk (mound)": t.milk_mound,
                "Rate": t.rate,
                "Amount": t.amount
            })
        
        recent_df = pd.DataFrame(recent_data)
        st.dataframe(recent_df)
    else:
        st.info("No transactions recorded today.")
    
    # Show customers with pending balances
    st.subheader("Pending Balances")
    
    if customers:
        pending_data = []
        for customer in customers:
            # Get all-time summary
            summary = db.get_customer_summary(
                customer.id, 
                date(2000, 1, 1),  # Start from a long time ago
                date.today()
            )
            
            if summary['remaining_amount'] > 0:
                pending_data.append({
                    "Customer": customer.name,
                    "Phone": customer.phone,
                    "Pending Amount": summary['remaining_amount']
                })
        
        if pending_data:
            pending_df = pd.DataFrame(pending_data)
            st.dataframe(pending_df)
        else:
            st.info("No pending balances.")
    else:
        st.info("No customers in the system.")

# Customers page
def show_customers_page():
    st.header("Customer Management")
    
    tab1, tab2 = st.tabs(["View Customers", "Add Customer"])
    
    with tab1:
        show_customers_list()
    
    with tab2:
        show_add_customer_form()

def show_customers_list():
    st.subheader("Customers List")
    
    customers = db.get_all_customers()
    
    if customers:
        customer_data = []
        for customer in customers:
            # Get all-time summary
            summary = db.get_customer_summary(
                customer.id, 
                date(2000, 1, 1),  # Start from a long time ago
                date.today()
            )
            
            customer_data.append({
                "ID": customer.id,
                "Name": customer.name,
                "Phone": customer.phone,
                "Address": customer.address,
                "Total Milk (kg)": summary['total_milk_kg'],
                "Pending Amount": summary['remaining_amount']
            })
        
        customer_df = pd.DataFrame(customer_data)
        st.dataframe(customer_df)
        
        # Customer actions
        st.subheader("Customer Actions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            customer_id = st.selectbox(
                "Select Customer", 
                options=[c.id for c in customers],
                format_func=lambda x: next((c.name for c in customers if c.id == x), "")
            )
        
        with col2:
            action = st.selectbox(
                "Action",
                options=["Edit", "Delete", "View Details"]
            )
        
        if st.button("Proceed"):
            if action == "Edit":
                st.session_state.edit_customer_id = customer_id
                show_edit_customer_form(customer_id)
            elif action == "Delete":
                success = db.delete_customer(customer_id)
                if success:
                    st.success("Customer deleted successfully!")
                    st.rerun()
                else:
                    st.error("Cannot delete customer with existing transactions or payments.")
            elif action == "View Details":
                show_customer_details(customer_id)
    else:
        st.info("No customers found. Add a customer to get started.")

def show_add_customer_form():
    st.subheader("Add New Customer")
    
    with st.form("add_customer_form"):
        name = st.text_input("Customer Name", key="new_customer_name")
        phone = st.text_input("Phone Number", key="new_customer_phone")
        address = st.text_area("Address", key="new_customer_address")
        
        submit = st.form_submit_button("Add Customer")
        
        if submit:
            if name:
                customer = Customer(name=name, phone=phone, address=address)
                customer_id = db.add_customer(customer)
                st.success(f"Customer '{name}' added successfully!")
                # Note: We don't need to clear the form manually
                # Streamlit will handle it on rerun
            else:
                st.error("Customer name is required.")

def show_edit_customer_form(customer_id):
    customer = db.get_customer(customer_id)
    
    if customer:
        st.subheader(f"Edit Customer: {customer.name}")
        
        with st.form("edit_customer_form"):
            name = st.text_input("Customer Name", value=customer.name)
            phone = st.text_input("Phone Number", value=customer.phone)
            address = st.text_area("Address", value=customer.address)
            
            submit = st.form_submit_button("Update Customer")
            
            if submit:
                if name:
                    updated_customer = Customer(id=customer_id, name=name, phone=phone, address=address)
                    success = db.update_customer(updated_customer)
                    if success:
                        st.success(f"Customer '{name}' updated successfully!")
                        # Return to list view
                        if 'edit_customer_id' in st.session_state:
                            del st.session_state.edit_customer_id
                        st.rerun()
                    else:
                        st.error("Failed to update customer.")
                else:
                    st.error("Customer name is required.")

def show_customer_details(customer_id):
    customer = db.get_customer(customer_id)
    
    if customer:
        st.subheader(f"Customer Details: {customer.name}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Phone:** {customer.phone}")
        with col2:
            st.write(f"**Address:** {customer.address}")
        
        # Get date range for filter
        today = date.today()
        default_start_date = today.replace(day=1)  # First day of current month
        
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            start_date = st.date_input("From Date", value=default_start_date)
        with filter_col2:
            end_date = st.date_input("To Date", value=today)
        
        # Get summary for the selected period
        summary = db.get_customer_summary(customer_id, start_date, end_date)
        
        st.subheader("Summary")
        
        summary_col1, summary_col2, summary_col3 = st.columns(3)
        with summary_col1:
            st.metric("Total Milk (kg)", f"{summary['total_milk_kg']:.2f}")
            st.metric("Total Milk (mound)", f"{summary['total_milk_mound']:.2f}")
        with summary_col2:
            st.metric("Total Amount (Rs)", f"{summary['total_amount']:.2f}")
            st.metric("Paid Amount (Rs)", f"{summary['total_paid']:.2f}")
        with summary_col3:
            st.metric("Rent (Rs)", f"{summary['rent']:.2f}")
            st.metric("Mandi Average (Rs)", f"{summary['mandi_average']:.2f}")
            st.metric("Commission (Rs)", f"{summary['commission']:.2f}")
            st.metric("Remaining Amount (Rs)", f"{summary['remaining_amount']:.2f}")
        
        # Get transactions for the selected period
        transactions = db.get_customer_transactions(customer_id, start_date, end_date)
        
        # Display transactions
        st.subheader("Transactions")
        if transactions:
            transactions_data = []
            for t in transactions:
                transactions_data.append({
                    "Date": t.date,
                    "Time": t.time_of_day,
                    "Milk (kg)": t.milk_kg,
                    "Milk (mound)": t.milk_mound,
                    "Rate": t.rate,
                    "Amount": t.amount
                })
            
            transactions_df = pd.DataFrame(transactions_data)
            st.dataframe(transactions_df)
        else:
            st.info("No transactions found for the selected period.")
        
        # Get payments for the selected period
        payments = db.get_customer_payments(customer_id, start_date, end_date)
        
        # Display payments
        st.subheader("Payments")
        if payments:
            payments_data = []
            for p in payments:
                payments_data.append({
                    "Date": p.date,
                    "Amount": p.amount
                })
            
            payments_df = pd.DataFrame(payments_data)
            st.dataframe(payments_df)
        else:
            st.info("No payments found for the selected period.")
        
        # Generate PDF report
        st.subheader("Generate Report")
        if st.button("Generate PDF Report"):
            # Create bill summary
            bill_summary = BillSummary(
                customer=customer,
                total_milk_kg=summary['total_milk_kg'],
                total_milk_mound=summary['total_milk_mound'],
                rent=summary['rent'],
                mandi_average=summary['mandi_average'],
                commission=summary['commission'],
                total_amount=summary['total_amount'],
                paid_amount=summary['total_paid'],
                remaining_amount=summary['remaining_amount'],
                transactions=transactions,
                payments=payments,
                start_date=start_date,
                end_date=end_date
            )
            
            # Generate PDF
            pdf_path = report_gen.create_bill_pdf(bill_summary)
            
            # Provide download link
            st.markdown(
                get_download_link(pdf_path, "Download PDF Report"),
                unsafe_allow_html=True
            )

# Transactions page
def show_transactions_page():
    st.header("Milk Transactions")
    
    tab1, tab2 = st.tabs(["Add Transaction", "View Transactions"])
    
    with tab1:
        show_add_transaction_form()
    
    with tab2:
        show_transactions_list()

def show_add_transaction_form():
    st.subheader("Record Milk Transaction")
    
    customers = db.get_all_customers()
    
    if not customers:
        st.warning("No customers found. Please add a customer first.")
        return
    
    with st.form("add_transaction_form"):
        customer_id = st.selectbox(
            "Select Customer", 
            options=[c.id for c in customers],
            format_func=lambda x: next((c.name for c in customers if c.id == x), "")
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            transaction_date = st.date_input("Date", value=date.today())
            
            # Allow user to input either kg or mound
            unit_selection = st.radio("Input Unit", ["Kilograms (kg)", "Mound"])
            
            if unit_selection == "Kilograms (kg)":
                milk_kg = st.number_input("Milk Quantity (kg)", min_value=0.0, step=0.1)
                milk_mound = convert_kg_to_mound(milk_kg)
            else:
                milk_mound = st.number_input("Milk Quantity (mound)", min_value=0.0, step=0.01)
                milk_kg = convert_mound_to_kg(milk_mound)
        
        with col2:
            time_of_day = st.radio("Time of Day", ["Morning", "Evening"])
            rate = st.number_input("Rate per kg (Rs)", min_value=0.0, step=0.1, value=80.0)
            amount = milk_kg * rate
            st.metric("Amount (Rs)", f"{amount:.2f}")
        
        submit = st.form_submit_button("Save Transaction")
        
        if submit:
            if milk_kg <= 0:
                st.error("Milk quantity must be greater than zero.")
            else:
                transaction = Transaction(
                    customer_id=customer_id,
                    date=transaction_date,
                    milk_kg=milk_kg,
                    milk_mound=milk_mound,
                    rate=rate,
                    time_of_day=time_of_day
                )
                
                transaction_id = db.add_transaction(transaction)
                
                if transaction_id:
                    customer = db.get_customer(customer_id)
                    st.success(f"Transaction recorded for {customer.name}: {milk_kg:.2f} kg ({milk_mound:.2f} mound) at Rs {rate:.2f}/kg = Rs {amount:.2f}")
                else:
                    st.error("Failed to record transaction.")

def show_transactions_list():
    st.subheader("Transactions List")
    
    # Filters
    customers = db.get_all_customers()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Allow "All Customers" option
        all_customer_option = Customer(id=0, name="All Customers", phone="", address="")
        customer_options = [all_customer_option] + customers
        selected_customer_id = st.selectbox(
            "Filter by Customer", 
            options=[c.id for c in customer_options],
            format_func=lambda x: next((c.name for c in customer_options if c.id == x), "")
        )
    
    with col2:
        start_date = st.date_input("From Date", value=date.today() - timedelta(days=30))
    
    with col3:
        end_date = st.date_input("To Date", value=date.today())
    
    # Get transactions based on filters
    all_transactions = []
    transaction_data = []
    
    if selected_customer_id == 0:  # All customers
        for customer in customers:
            customer_transactions = db.get_customer_transactions(customer.id, start_date, end_date)
            for t in customer_transactions:
                transaction_data.append({
                    "ID": t.id,
                    "Customer": customer.name,
                    "Date": t.date,
                    "Time": t.time_of_day,
                    "Milk (kg)": t.milk_kg,
                    "Milk (mound)": t.milk_mound,
                    "Rate": t.rate,
                    "Amount": t.amount
                })
                all_transactions.append(t)
    else:
        customer = next((c for c in customers if c.id == selected_customer_id), None)
        if customer:
            customer_transactions = db.get_customer_transactions(customer.id, start_date, end_date)
            for t in customer_transactions:
                transaction_data.append({
                    "ID": t.id,
                    "Customer": customer.name,
                    "Date": t.date,
                    "Time": t.time_of_day,
                    "Milk (kg)": t.milk_kg,
                    "Milk (mound)": t.milk_mound,
                    "Rate": t.rate,
                    "Amount": t.amount
                })
                all_transactions.append(t)
    
    # Display transactions
    if transaction_data:
        df = pd.DataFrame(transaction_data)
        st.dataframe(df)
        
        # Show summary
        total_milk_kg = sum(t.milk_kg for t in all_transactions)
        total_milk_mound = sum(t.milk_mound for t in all_transactions)
        total_amount = sum(t.amount for t in all_transactions)
        
        summary_col1, summary_col2, summary_col3 = st.columns(3)
        
        with summary_col1:
            st.metric("Total Transactions", len(all_transactions))
        
        with summary_col2:
            st.metric("Total Milk", f"{total_milk_kg:.2f} kg ({total_milk_mound:.2f} mound)")
        
        with summary_col3:
            st.metric("Total Amount", f"Rs {total_amount:.2f}")
        
        # Export option
        if st.button("Export to Excel"):
            customer_obj = None
            if selected_customer_id != 0:
                customer_obj = next((c for c in customers if c.id == selected_customer_id), None)
            
            excel_path = report_gen.export_transactions_to_excel(
                all_transactions, 
                customer=customer_obj,
                start_date=start_date,
                end_date=end_date
            )
            
            st.markdown(
                get_download_link(excel_path, "Download Excel Report"),
                unsafe_allow_html=True
            )
        
        # Transaction actions
        st.subheader("Transaction Actions")
        
        action_col1, action_col2 = st.columns(2)
        
        with action_col1:
            transaction_id = st.selectbox(
                "Select Transaction", 
                options=[t["ID"] for t in transaction_data]
            )
        
        with action_col2:
            action = st.selectbox(
                "Action",
                options=["Edit", "Delete"]
            )
        
        if st.button("Proceed"):
            if action == "Edit":
                st.session_state.edit_transaction_id = transaction_id
                show_edit_transaction_form(transaction_id)
            elif action == "Delete":
                success = db.delete_transaction(transaction_id)
                if success:
                    st.success("Transaction deleted successfully!")
                    st.rerun()
                else:
                    st.error("Failed to delete transaction.")
    else:
        st.info("No transactions found for the selected criteria.")

def show_edit_transaction_form(transaction_id):
    transaction = db.get_transaction(transaction_id)
    
    if transaction:
        customer = db.get_customer(transaction.customer_id)
        customers = db.get_all_customers()
        
        st.subheader(f"Edit Transaction for {customer.name if customer else 'Unknown'}")
        
        with st.form("edit_transaction_form"):
            customer_id = st.selectbox(
                "Customer", 
                options=[c.id for c in customers],
                index=[i for i, c in enumerate(customers) if c.id == transaction.customer_id][0],
                format_func=lambda x: next((c.name for c in customers if c.id == x), "")
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                transaction_date = st.date_input("Date", value=transaction.date)
                
                # Allow user to input either kg or mound
                unit_selection = st.radio("Input Unit", ["Kilograms (kg)", "Mound"])
                
                if unit_selection == "Kilograms (kg)":
                    milk_kg = st.number_input("Milk Quantity (kg)", min_value=0.0, step=0.1, value=float(transaction.milk_kg))
                    milk_mound = convert_kg_to_mound(milk_kg)
                else:
                    milk_mound = st.number_input("Milk Quantity (mound)", min_value=0.0, step=0.01, value=float(transaction.milk_mound))
                    milk_kg = convert_mound_to_kg(milk_mound)
            
            with col2:
                time_of_day = st.radio(
                    "Time of Day", 
                    ["Morning", "Evening"],
                    index=0 if transaction.time_of_day == "Morning" else 1
                )
                rate = st.number_input("Rate per kg (Rs)", min_value=0.0, step=0.1, value=float(transaction.rate))
                amount = milk_kg * rate
                st.metric("Amount (Rs)", f"{amount:.2f}")
            
            submit = st.form_submit_button("Update Transaction")
            
            if submit:
                if milk_kg <= 0:
                    st.error("Milk quantity must be greater than zero.")
                else:
                    updated_transaction = Transaction(
                        id=transaction_id,
                        customer_id=customer_id,
                        date=transaction_date,
                        milk_kg=milk_kg,
                        milk_mound=milk_mound,
                        rate=rate,
                        time_of_day=time_of_day
                    )
                    
                    success = db.update_transaction(updated_transaction)
                    
                    if success:
                        st.success("Transaction updated successfully!")
                        # Return to list view
                        if 'edit_transaction_id' in st.session_state:
                            del st.session_state.edit_transaction_id
                        st.rerun()
                    else:
                        st.error("Failed to update transaction.")

# Payments page
def show_payments_page():
    st.header("Payments")
    
    tab1, tab2 = st.tabs(["Record Payment", "View Payments"])
    
    with tab1:
        show_add_payment_form()
    
    with tab2:
        show_payments_list()

def show_add_payment_form():
    st.subheader("Record Payment")
    
    customers = db.get_all_customers()
    
    if not customers:
        st.warning("No customers found. Please add a customer first.")
        return
    
    with st.form("add_payment_form"):
        customer_id = st.selectbox(
            "Select Customer", 
            options=[c.id for c in customers],
            format_func=lambda x: next((c.name for c in customers if c.id == x), "")
        )
        
        # Show current balance
        if customer_id:
            summary = db.get_customer_summary(
                customer_id, 
                date(2000, 1, 1),  # Start from a long time ago
                date.today()
            )
            st.info(f"Current Balance: Rs {summary['remaining_amount']:.2f}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            payment_date = st.date_input("Payment Date", value=date.today())
        
        with col2:
            amount = st.number_input("Amount (Rs)", min_value=0.0, step=100.0)
        
        submit = st.form_submit_button("Record Payment")
        
        if submit:
            if amount <= 0:
                st.error("Payment amount must be greater than zero.")
            else:
                payment = Payment(
                    customer_id=customer_id,
                    date=payment_date,
                    amount=amount
                )
                
                payment_id = db.add_payment(payment)
                
                if payment_id:
                    customer = db.get_customer(customer_id)
                    st.success(f"Payment of Rs {amount:.2f} recorded for {customer.name}")
                else:
                    st.error("Failed to record payment.")

def show_payments_list():
    st.subheader("Payments List")
    
    # Filters
    customers = db.get_all_customers()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Allow "All Customers" option
        all_customer_option = Customer(id=0, name="All Customers", phone="", address="")
        customer_options = [all_customer_option] + customers
        selected_customer_id = st.selectbox(
            "Filter by Customer", 
            options=[c.id for c in customer_options],
            format_func=lambda x: next((c.name for c in customer_options if c.id == x), ""),
            key="payments_customer_filter"
        )
    
    with col2:
        start_date = st.date_input("From Date", value=date.today() - timedelta(days=30), key="payments_start_date")
    
    with col3:
        end_date = st.date_input("To Date", value=date.today(), key="payments_end_date")
    
    # Get payments based on filters
    all_payments = []
    payment_data = []
    
    if selected_customer_id == 0:  # All customers
        for customer in customers:
            customer_payments = db.get_customer_payments(customer.id, start_date, end_date)
            for p in customer_payments:
                payment_data.append({
                    "ID": p.id,
                    "Customer": customer.name,
                    "Date": p.date,
                    "Amount": p.amount
                })
                all_payments.append(p)
    else:
        customer = next((c for c in customers if c.id == selected_customer_id), None)
        if customer:
            customer_payments = db.get_customer_payments(customer.id, start_date, end_date)
            for p in customer_payments:
                payment_data.append({
                    "ID": p.id,
                    "Customer": customer.name,
                    "Date": p.date,
                    "Amount": p.amount
                })
                all_payments.append(p)
    
    # Display payments
    if payment_data:
        df = pd.DataFrame(payment_data)
        st.dataframe(df)
        
        # Show summary
        total_amount = sum(p.amount for p in all_payments)
        
        summary_col1, summary_col2 = st.columns(2)
        
        with summary_col1:
            st.metric("Total Payments", len(all_payments))
        
        with summary_col2:
            st.metric("Total Amount", f"Rs {total_amount:.2f}")
        
        # Payment actions
        st.subheader("Payment Actions")
        
        action_col1, action_col2 = st.columns(2)
        
        with action_col1:
            payment_id = st.selectbox(
                "Select Payment", 
                options=[p["ID"] for p in payment_data]
            )
        
        with action_col2:
            action = st.selectbox(
                "Action",
                options=["Edit", "Delete"]
            )
        
        if st.button("Proceed", key="payment_action_button"):
            if action == "Edit":
                st.session_state.edit_payment_id = payment_id
                show_edit_payment_form(payment_id)
            elif action == "Delete":
                success = db.delete_payment(payment_id)
                if success:
                    st.success("Payment deleted successfully!")
                    st.rerun()
                else:
                    st.error("Failed to delete payment.")
    else:
        st.info("No payments found for the selected criteria.")

def show_edit_payment_form(payment_id):
    payment = db.get_payment(payment_id)
    
    if payment:
        customer = db.get_customer(payment.customer_id)
        customers = db.get_all_customers()
        
        st.subheader(f"Edit Payment for {customer.name if customer else 'Unknown'}")
        
        with st.form("edit_payment_form"):
            customer_id = st.selectbox(
                "Customer", 
                options=[c.id for c in customers],
                index=[i for i, c in enumerate(customers) if c.id == payment.customer_id][0],
                format_func=lambda x: next((c.name for c in customers if c.id == x), "")
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                payment_date = st.date_input("Payment Date", value=payment.date)
            
            with col2:
                amount = st.number_input("Amount (Rs)", min_value=0.0, step=100.0, value=float(payment.amount))
            
            submit = st.form_submit_button("Update Payment")
            
            if submit:
                if amount <= 0:
                    st.error("Payment amount must be greater than zero.")
                else:
                    updated_payment = Payment(
                        id=payment_id,
                        customer_id=customer_id,
                        date=payment_date,
                        amount=amount
                    )
                    
                    success = db.update_payment(updated_payment)
                    
                    if success:
                        st.success("Payment updated successfully!")
                        # Return to list view
                        if 'edit_payment_id' in st.session_state:
                            del st.session_state.edit_payment_id
                        st.rerun()
                    else:
                        st.error("Failed to update payment.")

# Reports page
def show_reports_page():
    st.header("Reports")
    
    report_type = st.selectbox(
        "Select Report Type",
        options=["Customer Bill", "Transaction Summary", "Payment Summary"]
    )
    
    if report_type == "Customer Bill":
        show_customer_bill_report()
    elif report_type == "Transaction Summary":
        show_transaction_summary_report()
    elif report_type == "Payment Summary":
        show_payment_summary_report()
        
# Daily entry and bill page
def show_daily_entry_page():
    st.header("Dairy Management System")
    
    # Top row for customer selection and basic info
    customers = db.get_all_customers()
    
    if not customers:
        st.warning("No customers found. Please add a customer first.")
        customer_col1, customer_col2 = st.columns(2)
        with customer_col1:
            with st.form("add_customer_inline"):
                new_name = st.text_input("Customer Name")
                new_phone = st.text_input("Phone Number")
                new_address = st.text_input("Address")
                if st.form_submit_button("Add Customer"):
                    if new_name:
                        customer = Customer(name=new_name, phone=new_phone, address=new_address)
                        db.add_customer(customer)
                        st.success("Customer added! Please refresh the page.")
                        st.rerun()
        return
    
    # Top row with customer and date selection
    col1, col2 = st.columns([3, 1])
    
    with col1:
        customer_id = st.selectbox(
            "Select Customer", 
            options=[c.id for c in customers],
            format_func=lambda x: next((c.name for c in customers if c.id == x), ""),
            key="main_customer_select"
        )
    
    with col2:
        entry_date = st.date_input("Date", value=date.today())
    
    # Add new customer button
    if st.button("Add New Customer", key="add_customer_btn"):
        with st.form("add_new_customer"):
            new_name = st.text_input("Customer Name")
            new_phone = st.text_input("Phone Number")
            new_address = st.text_input("Address")
            if st.form_submit_button("Save Customer"):
                if new_name:
                    customer = Customer(name=new_name, phone=new_phone, address=new_address)
                    db.add_customer(customer)
                    st.success("Customer added!")
                    st.rerun()
        return
    
    if not customer_id:
        st.warning("Please select a customer.")
        return
    
    customer = db.get_customer(customer_id)
    
    # Customer details and balance
    st.info(f"**Name:** {customer.name} | **Phone:** {customer.phone} | **Address:** {customer.address}")
    
    # Get current balance
    summary = db.get_customer_summary(
        customer_id, 
        date(2000, 1, 1),  # Start from a long time ago
        date.today()
    )
    
    st.metric("Current Balance (Rs)", f"{summary['remaining_amount']:.2f}")
    
    # Create a container for milk entry form in two columns
    entry_container = st.container()
    
    with entry_container:
        st.subheader("Add Milk Entry")
        
        with st.form("milk_entry_form", clear_on_submit=True):
            # Create two columns for morning and evening entries side by side
            morning_col, evening_col = st.columns(2)
            
            # Morning entry column
            with morning_col:
                st.markdown("### Morning Entry")
                
                # Customer and date info is already at the top
                morning_kg = st.number_input("Milk (kg)", min_value=0.0, step=0.1, key="morning_kg")
                morning_mound = convert_kg_to_mound(morning_kg)
                st.write(f"= {morning_mound:.2f} mound")
                
                morning_rate = st.number_input("Rate (Rs/kg)", min_value=0.0, step=1.0, value=80.0, key="morning_rate")
                
                # Calculate morning amount
                morning_amount = morning_kg * morning_rate
                st.metric("Morning Total", f"Rs. {morning_amount:.2f}")
            
            # Evening entry column
            with evening_col:
                st.markdown("### Evening Entry")
                
                # Same format as morning
                evening_kg = st.number_input("Milk (kg)", min_value=0.0, step=0.1, key="evening_kg")
                evening_mound = convert_kg_to_mound(evening_kg)
                st.write(f"= {evening_mound:.2f} mound")
                
                evening_rate = st.number_input("Rate (Rs/kg)", min_value=0.0, step=1.0, value=80.0, key="evening_rate")
                
                # Calculate evening amount
                evening_amount = evening_kg * evening_rate
                st.metric("Evening Total", f"Rs. {evening_amount:.2f}")
            
            # Total for the day
            st.markdown("---")
            
            # Create three columns for the totals
            total_col1, total_col2, total_col3 = st.columns(3)
            
            with total_col1:
                total_day_kg = morning_kg + evening_kg
                st.metric("Total Milk (kg)", f"{total_day_kg:.2f}")
            
            with total_col2:
                total_day_mound = morning_mound + evening_mound
                st.metric("Total Milk (mound)", f"{total_day_mound:.2f}")
            
            with total_col3:
                total_day_amount = morning_amount + evening_amount
                st.metric("Total Amount", f"Rs. {total_day_amount:.2f}")
            
            # Submit button
            entry_submit = st.form_submit_button("Add Entries", use_container_width=True)
            
            if entry_submit:
                entries_added = False
                
                # Add morning entry if quantity > 0
                if morning_kg > 0:
                    morning_transaction = Transaction(
                        customer_id=customer_id,
                        date=entry_date,
                        milk_kg=morning_kg,
                        milk_mound=morning_mound,
                        rate=morning_rate,
                        time_of_day="Morning"
                    )
                    
                    morning_id = db.add_transaction(morning_transaction)
                    if morning_id:
                        entries_added = True
                
                # Add evening entry if quantity > 0
                if evening_kg > 0:
                    evening_transaction = Transaction(
                        customer_id=customer_id,
                        date=entry_date,
                        milk_kg=evening_kg,
                        milk_mound=evening_mound,
                        rate=evening_rate,
                        time_of_day="Evening"
                    )
                    
                    evening_id = db.add_transaction(evening_transaction)
                    if evening_id:
                        entries_added = True
                
                if entries_added:
                    st.success(f"Entries added successfully!\nMorning: {morning_kg:.2f} kg ({morning_mound:.2f} mound) = Rs. {morning_amount:.2f}\nEvening: {evening_kg:.2f} kg ({evening_mound:.2f} mound) = Rs. {evening_amount:.2f}\nTotal: {total_day_kg:.2f} kg = Rs. {total_day_amount:.2f}")
                else:
                    st.error("No entries added. Please enter milk quantity greater than zero.")
    
    # Payment form in a small container
    payment_container = st.container()
    
    with payment_container:
        payment_col1, payment_col2 = st.columns([1, 3])
        
        with payment_col1:
            with st.form("payment_form", clear_on_submit=True):
                st.subheader("Record Payment")
                payment_amount = st.number_input("Amount (Rs)", min_value=0.0, step=100.0, key="payment_amount")
                payment_submit = st.form_submit_button("Record Payment", use_container_width=True)
                
                if payment_submit and payment_amount > 0:
                    payment = Payment(
                        customer_id=customer_id,
                        date=entry_date,
                        amount=payment_amount
                    )
                    
                    payment_id = db.add_payment(payment)
                    
                    if payment_id:
                        st.success(f"Payment of Rs {payment_amount:.2f} recorded")
    
    # Display today's entries
    entries_container = st.container()
    
    with entries_container:
        st.subheader(f"Today's Entries ({entry_date.strftime('%d-%m-%Y')})")
        
        # Get transactions for this customer on this date
        daily_transactions = db.get_customer_transactions(customer_id, entry_date, entry_date)
        
        if daily_transactions:
            transaction_data = []
            for t in daily_transactions:
                transaction_data.append({
                    "Time": t.time_of_day,
                    "Milk (kg)": f"{t.milk_kg:.2f}",
                    "Milk (mound)": f"{t.milk_mound:.2f}",
                    "Rate": f"{t.rate:.2f}",
                    "Amount": f"{t.amount:.2f}"
                })
            
            transactions_df = pd.DataFrame(transaction_data)
            st.dataframe(transactions_df, use_container_width=True)
            
            # Calculate daily totals
            total_kg = sum(t.milk_kg for t in daily_transactions)
            total_mound = sum(t.milk_mound for t in daily_transactions)
            total_amount = sum(t.amount for t in daily_transactions)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Milk (kg)", f"{total_kg:.2f}")
            col2.metric("Total Milk (mound)", f"{total_mound:.2f}")
            col3.metric("Total Amount (Rs)", f"{total_amount:.2f}")
        else:
            st.info(f"No entries for today. Add entries using the form above.")
    
    # Add a section to view all customer entries with expandable date groups
    if st.button("Show All Entries for this Customer", use_container_width=True):
        st.subheader(f"All Entries for {customer.name}")
        
        # Option to filter by date range
        all_col1, all_col2 = st.columns(2)
        with all_col1:
            all_start_date = st.date_input("From", value=date.today().replace(day=1), key="all_start_date")
        with all_col2:
            all_end_date = st.date_input("To", value=date.today(), key="all_end_date")
        
        # Get all transactions for this customer in the date range
        all_transactions = db.get_customer_transactions(customer_id, all_start_date, all_end_date)
        
        if all_transactions:
            # Group transactions by date
            transactions_by_date = {}
            
            for t in all_transactions:
                date_str = t.date.strftime('%Y-%m-%d')
                if date_str not in transactions_by_date:
                    transactions_by_date[date_str] = []
                
                transactions_by_date[date_str].append(t)
            
            # Display transactions grouped by date
            for date_str, date_transactions in sorted(transactions_by_date.items(), reverse=True):
                with st.expander(f"Date: {date_str} ({len(date_transactions)} entries)", expanded=(date_str == entry_date.strftime('%Y-%m-%d'))):
                    # Create DataFrame for this day's transactions
                    day_data = []
                    day_total_kg = 0
                    day_total_amount = 0
                    
                    for t in date_transactions:
                        day_data.append({
                            "Time": t.time_of_day,
                            "Milk (kg)": f"{t.milk_kg:.2f}",
                            "Milk (mound)": f"{t.milk_mound:.2f}",
                            "Rate": f"{t.rate:.2f}",
                            "Amount": f"{t.amount:.2f}"
                        })
                        
                        day_total_kg += t.milk_kg
                        day_total_amount += t.amount
                    
                    # Display this day's transactions
                    day_df = pd.DataFrame(day_data)
                    st.dataframe(day_df, use_container_width=True)
                    
                    # Display day totals
                    st.write(f"**Day Total:** {day_total_kg:.2f} kg | Rs. {day_total_amount:.2f}")
            
            # Show period totals
            period_total_kg = sum(t.milk_kg for t in all_transactions)
            period_total_mound = sum(t.milk_mound for t in all_transactions)
            period_total_amount = sum(t.amount for t in all_transactions)
            
            st.markdown("---")
            st.markdown(f"**Period Summary:** {len(all_transactions)} entries")
            summary_col1, summary_col2, summary_col3 = st.columns(3)
            summary_col1.metric("Total Milk (kg)", f"{period_total_kg:.2f}")
            summary_col2.metric("Total Milk (mound)", f"{period_total_mound:.2f}")
            summary_col3.metric("Total Amount (Rs)", f"{period_total_amount:.2f}")
            
            # Export to Excel button
            if st.button("Export to Excel", key="export_all_button"):
                excel_file = report_gen.export_transactions_to_excel(
                    all_transactions, 
                    customer, 
                    all_start_date, 
                    all_end_date
                )
                
                st.success("Transactions exported to Excel successfully!")
                
                st.markdown(
                    get_download_link(excel_file, "Download Excel File"),
                    unsafe_allow_html=True
                )
        else:
            st.info(f"No transactions found for the selected period.")
    
    # All entries for this customer and bill generation
    st.markdown("---")
    st.subheader(f"All Entries for {customer.name}")
    
    # Date range for filtering entries
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input("From Date", value=date.today().replace(day=1), key="entries_start_date")
    
    with col2:
        end_date = st.date_input("To Date", value=date.today(), key="entries_end_date")
    
    # Get all transactions for the selected period
    all_transactions = db.get_customer_transactions(customer_id, start_date, end_date)
    
    if all_transactions:
        # Group transactions by date
        transactions_by_date = {}
        
        for t in all_transactions:
            date_str = t.date.strftime('%Y-%m-%d')
            if date_str not in transactions_by_date:
                transactions_by_date[date_str] = []
            transactions_by_date[date_str].append(t)
        
        # Sort dates from newest to oldest
        sorted_dates = sorted(transactions_by_date.keys(), reverse=True)
        
        # Display each day's transactions in a separate expander
        for date_str in sorted_dates:
            day_transactions = transactions_by_date[date_str]
            display_date = day_transactions[0].date.strftime('%d-%m-%Y')
            
            with st.expander(f"Date: {display_date} ({len(day_transactions)} entries)", expanded=(date_str == entry_date.strftime('%Y-%m-%d'))):
                # Create morning and evening data
                morning_data = []
                evening_data = []
                
                morning_total_kg = 0
                morning_total_amount = 0
                evening_total_kg = 0
                evening_total_amount = 0
                
                for t in day_transactions:
                    entry_data = {
                        "Time": t.time_of_day,
                        "Milk (kg)": f"{t.milk_kg:.2f}",
                        "Milk (mound)": f"{t.milk_mound:.2f}",
                        "Rate (Rs/kg)": f"{t.rate:.2f}",
                        "Amount (Rs)": f"{t.amount:.2f}"
                    }
                    
                    if t.time_of_day == "Morning":
                        morning_data.append(entry_data)
                        morning_total_kg += t.milk_kg
                        morning_total_amount += t.amount
                    else:
                        evening_data.append(entry_data)
                        evening_total_kg += t.milk_kg
                        evening_total_amount += t.amount
                
                # Display morning entries
                if morning_data:
                    st.markdown("#### Morning Entries")
                    morning_df = pd.DataFrame(morning_data)
                    st.dataframe(morning_df, use_container_width=True)
                    st.write(f"**Morning Total:** {morning_total_kg:.2f} kg = Rs. {morning_total_amount:.2f}")
                
                # Display evening entries
                if evening_data:
                    st.markdown("#### Evening Entries")
                    evening_df = pd.DataFrame(evening_data)
                    st.dataframe(evening_df, use_container_width=True)
                    st.write(f"**Evening Total:** {evening_total_kg:.2f} kg = Rs. {evening_total_amount:.2f}")
                
                # Display day total
                day_total_kg = morning_total_kg + evening_total_kg
                day_total_mound = convert_kg_to_mound(day_total_kg)
                day_total_amount = morning_total_amount + evening_total_amount
                
                st.markdown("---")
                total_col1, total_col2, total_col3 = st.columns(3)
                total_col1.metric("Day Total (kg)", f"{day_total_kg:.2f}")
                total_col2.metric("Day Total (mound)", f"{day_total_mound:.2f}")
                total_col3.metric("Day Amount (Rs)", f"{day_total_amount:.2f}")
        
        # Calculate totals
        total_milk_kg = sum(t.milk_kg for t in all_transactions)
        total_milk_mound = sum(t.milk_mound for t in all_transactions)
        total_amount = sum(t.amount for t in all_transactions)
        
        # Display totals
        totals_col1, totals_col2, totals_col3 = st.columns(3)
        totals_col1.metric("Total Milk (kg)", f"{total_milk_kg:.2f}")
        totals_col2.metric("Total Milk (mound)", f"{total_milk_mound:.2f}")
        totals_col3.metric("Total Amount (Rs)", f"{total_amount:.2f}")
    else:
        st.info(f"No entries found for {customer.name} in the selected period.")
    
    # Bill section
    st.markdown("---")
    st.header("Bill Details")
    
    # Parameters in two columns
    bill_params_col1, bill_params_col2 = st.columns(2)
    
    with bill_params_col1:
        st.subheader("Milk Summary")
        
        # Show milk metrics
        milk_summary_df = pd.DataFrame({
            "Detail": ["Total Milk (kg)", "Total Milk (mound)"],
            "Amount": [f"{total_milk_kg:.2f}", f"{total_milk_mound:.2f}"]
        })
        st.dataframe(milk_summary_df, use_container_width=True, hide_index=True)
        
        # Total transactions amount
        st.metric("Total Milk Value", f"Rs. {total_amount:.2f}")
    
    with bill_params_col2:
        st.subheader("Bill Adjustments")
        
        # Bill parameter inputs
        rent_percentage = st.number_input("Rent %", min_value=0.0, max_value=100.0, value=5.0, step=0.1)
        mandi_percentage = st.number_input("Mandi %", min_value=0.0, max_value=100.0, value=2.0, step=0.1)
        commission_percentage = st.number_input("Commission %", min_value=0.0, max_value=100.0, value=3.0, step=0.1)
    
    # Generate bill button
    if st.button("Generate Complete Bill", use_container_width=True, type="primary"):
        if not all_transactions:
            st.warning("No transactions found for the selected period.")
        else:
            # Get payments for the period
            payments = db.get_customer_payments(customer_id, start_date, end_date)
            
            # Calculate deductions
            rent = total_milk_kg * (rent_percentage / 100.0) * 80.0  # Assuming avg rate of Rs 80 for rent
            mandi_average = total_milk_kg * (mandi_percentage / 100.0) * 80.0
            commission = total_milk_kg * (commission_percentage / 100.0) * 80.0
            
            # Calculate net amount after deductions
            net_amount = total_amount - rent - commission + mandi_average
            
            # Calculate paid amount
            paid_amount = sum(p.amount for p in payments)
            
            # Calculate remaining amount
            remaining_amount = net_amount - paid_amount
            
            # Create bill summary
            bill_summary = BillSummary(
                customer=customer,
                total_milk_kg=total_milk_kg,
                total_milk_mound=total_milk_mound,
                rent=rent,
                mandi_average=mandi_average,
                commission=commission,
                total_amount=net_amount,  # Net amount after deductions
                paid_amount=paid_amount,
                remaining_amount=remaining_amount,
                transactions=all_transactions,
                payments=payments,
                start_date=start_date,
                end_date=end_date
            )
            
            # Display bill summary
            st.success("Bill generated successfully!")
            
            # Show summary details
            st.markdown(f"""
            ### Bill for {customer.name}
            **Period:** {start_date.strftime('%d-%m-%Y')} to {end_date.strftime('%d-%m-%Y')}
            """)
            
            # Show summary in a table with two columns side by side
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Milk Details")
                milk_df = pd.DataFrame({
                    "Detail": ["Total Milk (kg)", "Total Milk (mound)", "Total Value"],
                    "Amount": [
                        f"{total_milk_kg:.2f}",
                        f"{total_milk_mound:.2f}",
                        f"Rs. {total_amount:.2f}"
                    ]
                })
                st.dataframe(milk_df, use_container_width=True, hide_index=True)
            
            with col2:
                st.subheader("Amount Details")
                amount_df = pd.DataFrame({
                    "Item": ["Rent", "Mandi Average", "Commission", "Net Amount", "Paid Amount", "Remaining"],
                    "Amount (Rs)": [
                        f"{rent:.2f}",
                        f"{mandi_average:.2f}",
                        f"{commission:.2f}",
                        f"{net_amount:.2f}",
                        f"{paid_amount:.2f}",
                        f"{remaining_amount:.2f}"
                    ]
                })
                st.dataframe(amount_df, use_container_width=True, hide_index=True)
            
            # Payment summary in metrics
            st.markdown("---")
            payment_col1, payment_col2, payment_col3 = st.columns(3)
            payment_col1.metric("Final Amount", f"Rs. {net_amount:.2f}")
            payment_col2.metric("Paid Amount", f"Rs. {paid_amount:.2f}")
            payment_col3.metric("Remaining Balance", f"Rs. {remaining_amount:.2f}")
            
            # Generate PDF with all details
            pdf_path = report_gen.create_bill_pdf(bill_summary)
            
            # Provide download link
            st.markdown("### Print Bill")
            st.markdown(
                get_download_link(pdf_path, "Download Complete Bill PDF"),
                unsafe_allow_html=True
            )
            
            st.info("👆 Click the download link above to get the complete bill PDF with all transaction details. You can print this PDF and give it to the customer.")

def show_customer_bill_report():
    st.subheader("Generate Customer Bill")
    
    customers = db.get_all_customers()
    
    if not customers:
        st.warning("No customers found. Please add a customer first.")
        return
    
    customer_id = st.selectbox(
        "Select Customer", 
        options=[c.id for c in customers],
        format_func=lambda x: next((c.name for c in customers if c.id == x), ""),
        key="report_customer_select"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input("From Date", value=date.today().replace(day=1))
    
    with col2:
        end_date = st.date_input("To Date", value=date.today())
    
    if st.button("Generate Bill"):
        customer = db.get_customer(customer_id)
        
        if customer:
            # Get customer summary
            summary = db.get_customer_summary(customer_id, start_date, end_date)
            
            # Get transactions and payments
            transactions = db.get_customer_transactions(customer_id, start_date, end_date)
            payments = db.get_customer_payments(customer_id, start_date, end_date)
            
            # Create bill summary
            bill_summary = BillSummary(
                customer=customer,
                total_milk_kg=summary['total_milk_kg'],
                total_milk_mound=summary['total_milk_mound'],
                rent=summary['rent'],
                mandi_average=summary['mandi_average'],
                commission=summary['commission'],
                total_amount=summary['total_amount'],
                paid_amount=summary['total_paid'],
                remaining_amount=summary['remaining_amount'],
                transactions=transactions,
                payments=payments,
                start_date=start_date,
                end_date=end_date
            )
            
            # Display bill preview
            st.subheader("Bill Preview")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Customer:** {customer.name}")
                st.write(f"**Period:** {start_date.strftime('%d-%m-%Y')} to {end_date.strftime('%d-%m-%Y')}")
            
            with col2:
                st.write(f"**Phone:** {customer.phone}")
                st.write(f"**Address:** {customer.address}")
            
            # Summary
            st.subheader("Summary")
            
            summary_data = [
                ["Total Milk (kg)", f"{summary['total_milk_kg']:.2f} kg"],
                ["Total Milk (mound)", f"{summary['total_milk_mound']:.2f} mound"],
                ["Total Amount", f"Rs. {summary['total_amount']:.2f}"],
                ["Rent", f"Rs. {summary['rent']:.2f}"],
                ["Mandi Average", f"Rs. {summary['mandi_average']:.2f}"],
                ["Commission", f"Rs. {summary['commission']:.2f}"],
                ["Net Amount", f"Rs. {summary['net_amount']:.2f}"],
                ["Paid Amount", f"Rs. {summary['total_paid']:.2f}"],
                ["Remaining Amount", f"Rs. {summary['remaining_amount']:.2f}"]
            ]
            
            summary_df = pd.DataFrame(summary_data, columns=["Item", "Value"])
            st.table(summary_df)
            
            # Generate PDF
            pdf_path = report_gen.create_bill_pdf(bill_summary)
            
            # Provide download link
            st.markdown(
                get_download_link(pdf_path, "Download PDF Bill"),
                unsafe_allow_html=True
            )

def show_transaction_summary_report():
    st.subheader("Transaction Summary Report")
    
    # Filters
    customers = db.get_all_customers()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Allow "All Customers" option
        customer_options = [{"id": 0, "name": "All Customers"}] + customers
        selected_customer_id = st.selectbox(
            "Customer", 
            options=[c.id for c in customer_options],
            format_func=lambda x: next((c.name for c in customer_options if c.id == x), ""),
            key="trans_report_customer"
        )
    
    with col2:
        start_date = st.date_input("From Date", value=date.today().replace(day=1), key="trans_report_start")
    
    with col3:
        end_date = st.date_input("To Date", value=date.today(), key="trans_report_end")
    
    if st.button("Generate Report", key="gen_trans_report"):
        # Get transactions based on filters
        all_transactions = []
        transaction_data = []
        
        if selected_customer_id == 0:  # All customers
            for customer in customers:
                customer_transactions = db.get_customer_transactions(customer.id, start_date, end_date)
                for t in customer_transactions:
                    transaction_data.append({
                        "Customer": customer.name,
                        "Date": t.date.strftime('%d-%m-%Y'),
                        "Time": t.time_of_day,
                        "Milk (kg)": t.milk_kg,
                        "Milk (mound)": t.milk_mound,
                        "Rate": t.rate,
                        "Amount": t.amount
                    })
                    all_transactions.append(t)
        else:
            customer = next((c for c in customers if c.id == selected_customer_id), None)
            if customer:
                customer_transactions = db.get_customer_transactions(customer.id, start_date, end_date)
                for t in customer_transactions:
                    transaction_data.append({
                        "Customer": customer.name,
                        "Date": t.date.strftime('%d-%m-%Y'),
                        "Time": t.time_of_day,
                        "Milk (kg)": t.milk_kg,
                        "Milk (mound)": t.milk_mound,
                        "Rate": t.rate,
                        "Amount": t.amount
                    })
                    all_transactions.append(t)
        
        # Display transactions
        if transaction_data:
            # Display summary
            total_milk_kg = sum(t.milk_kg for t in all_transactions)
            total_milk_mound = sum(t.milk_mound for t in all_transactions)
            total_amount = sum(t.amount for t in all_transactions)
            
            summary_col1, summary_col2, summary_col3 = st.columns(3)
            
            with summary_col1:
                st.metric("Total Transactions", len(all_transactions))
            
            with summary_col2:
                st.metric("Total Milk", f"{total_milk_kg:.2f} kg ({total_milk_mound:.2f} mound)")
            
            with summary_col3:
                st.metric("Total Amount", f"Rs {total_amount:.2f}")
            
            # Display table
            df = pd.DataFrame(transaction_data)
            st.dataframe(df)
            
            # Export option
            customer_obj = None
            if selected_customer_id != 0:
                customer_obj = next((c for c in customers if c.id == selected_customer_id), None)
            
            excel_path = report_gen.export_transactions_to_excel(
                all_transactions, 
                customer=customer_obj,
                start_date=start_date,
                end_date=end_date
            )
            
            st.markdown(
                get_download_link(excel_path, "Download Excel Report"),
                unsafe_allow_html=True
            )
        else:
            st.info("No transactions found for the selected criteria.")

def show_payment_summary_report():
    st.subheader("Payment Summary Report")
    
    # Filters
    customers = db.get_all_customers()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Allow "All Customers" option
        customer_options = [{"id": 0, "name": "All Customers"}] + customers
        selected_customer_id = st.selectbox(
            "Customer", 
            options=[c.id for c in customer_options],
            format_func=lambda x: next((c.name for c in customer_options if c.id == x), ""),
            key="payment_report_customer"
        )
    
    with col2:
        start_date = st.date_input("From Date", value=date.today().replace(day=1), key="payment_report_start")
    
    with col3:
        end_date = st.date_input("To Date", value=date.today(), key="payment_report_end")
    
    if st.button("Generate Report", key="gen_payment_report"):
        # Get payments based on filters
        all_payments = []
        payment_data = []
        
        if selected_customer_id == 0:  # All customers
            for customer in customers:
                customer_payments = db.get_customer_payments(customer.id, start_date, end_date)
                for p in customer_payments:
                    payment_data.append({
                        "Customer": customer.name,
                        "Date": p.date.strftime('%d-%m-%Y'),
                        "Amount": p.amount
                    })
                    all_payments.append(p)
        else:
            customer = next((c for c in customers if c.id == selected_customer_id), None)
            if customer:
                customer_payments = db.get_customer_payments(customer.id, start_date, end_date)
                for p in customer_payments:
                    payment_data.append({
                        "Customer": customer.name,
                        "Date": p.date.strftime('%d-%m-%Y'),
                        "Amount": p.amount
                    })
                    all_payments.append(p)
        
        # Display payments
        if payment_data:
            # Display summary
            total_amount = sum(p.amount for p in all_payments)
            
            summary_col1, summary_col2 = st.columns(2)
            
            with summary_col1:
                st.metric("Total Payments", len(all_payments))
            
            with summary_col2:
                st.metric("Total Amount", f"Rs {total_amount:.2f}")
            
            # Display table
            df = pd.DataFrame(payment_data)
            st.dataframe(df)
            
            # Export option
            if st.button("Export to Excel", key="export_payments_excel"):
                # Create a pandas Excel writer
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                    df.to_excel(writer, sheet_name="Payments", index=False)
                    writer.close()
                
                # Generate temp file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                temp_file.write(buffer.getvalue())
                temp_file.close()
                
                # Provide download link
                st.markdown(
                    get_download_link(temp_file.name, "Download Excel Report"),
                    unsafe_allow_html=True
                )
        else:
            st.info("No payments found for the selected criteria.")

if __name__ == "__main__":
    main()
