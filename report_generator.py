import os
from datetime import date
from typing import List, Dict, Any, Optional
import pandas as pd
from fpdf import FPDF
import tempfile

from models import Customer, Transaction, Payment, BillSummary

# Helper function for conversions
def convert_kg_to_mound(kg_value):
    """Convert kilograms to mound. 1 mound = 40 kg."""
    return kg_value / 40.0

def convert_mound_to_kg(mound_value):
    """Convert mound to kilograms. 1 mound = 40 kg."""
    return mound_value * 40.0


class DairyReportGenerator:
    def __init__(self):
        """Initialize the report generator."""
        self.pdf = None
        
    def create_bill_pdf(self, bill_summary: BillSummary, output_filename: Optional[str] = None) -> str:
        """Create a PDF bill with customer and transaction details."""
        # Initialize PDF (full size A4)
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.add_page()
        
        # Set up fonts
        pdf.set_font("Arial", "B", 18)
        
        # Add title
        pdf.cell(0, 15, "Milk Obaid", 0, 1, "C")
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        # Add customer details
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"Customer: {bill_summary.customer.name}", 0, 1, "C")
        
        # Add date period
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, f"Period: {bill_summary.start_date.strftime('%d-%m-%Y')} to {bill_summary.end_date.strftime('%d-%m-%Y')}", 0, 1, "C")
        pdf.ln(5)
        
        # Add all transactions in chronological order
        if bill_summary.transactions:
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "All Milk Entries", 0, 1, "C")
            
            # Group transactions by date
            transactions_by_date = {}
            for trans in bill_summary.transactions:
                date_str = trans.date.strftime('%Y-%m-%d')
                if date_str not in transactions_by_date:
                    transactions_by_date[date_str] = []
                transactions_by_date[date_str].append(trans)
            
            # Sort dates in chronological order (oldest first)
            sorted_dates = sorted(transactions_by_date.keys())
            
            # Table header - for the entire document
            pdf.set_font("Arial", "B", 12)
            table_header_height = 10
            
            # Define column widths
            date_width = 30
            time_width = 30
            kg_width = 30 
            mound_width = 30
            rate_width = 30
            amount_width = 40
            
            # Draw the main header
            pdf.cell(date_width, table_header_height, "Date", 1, 0, "C")
            pdf.cell(time_width, table_header_height, "Time", 1, 0, "C")
            pdf.cell(kg_width, table_header_height, "KG", 1, 0, "C")
            pdf.cell(mound_width, table_header_height, "Mound", 1, 0, "C")
            pdf.cell(rate_width, table_header_height, "Rate", 1, 0, "C")
            pdf.cell(amount_width, table_header_height, "Amount (Rs)", 1, 1, "C")
            
            # Process all transactions
            pdf.set_font("Arial", "", 10)
            
            total_kg = 0
            total_amount = 0
            
            # Process each day's transactions
            for date_str in sorted_dates:
                date_transactions = sorted(
                    transactions_by_date[date_str], 
                    key=lambda x: 0 if x.time_of_day == "Morning" else 1
                )
                
                display_date = date_transactions[0].date.strftime('%d-%m-%Y')
                
                # Day's transactions
                day_total_kg = 0
                day_total_amount = 0
                
                for trans in date_transactions:
                    pdf.cell(date_width, 8, display_date, 1, 0, "C")
                    pdf.cell(time_width, 8, trans.time_of_day, 1, 0, "C")
                    pdf.cell(kg_width, 8, f"{trans.milk_kg:.2f}", 1, 0, "C")
                    pdf.cell(mound_width, 8, f"{trans.milk_mound:.2f}", 1, 0, "C")
                    pdf.cell(rate_width, 8, f"{trans.rate:.2f}", 1, 0, "C")
                    pdf.cell(amount_width, 8, f"{trans.amount:.2f}", 1, 1, "C")
                    
                    day_total_kg += trans.milk_kg
                    day_total_amount += trans.amount
                    
                    total_kg += trans.milk_kg
                    total_amount += trans.amount
                
                # Add day totals in slightly bold
                pdf.set_font("Arial", "B", 10)
                pdf.cell(date_width, 8, "", 1, 0, "C")
                pdf.cell(time_width, 8, "Day Total", 1, 0, "C")
                pdf.cell(kg_width, 8, f"{day_total_kg:.2f}", 1, 0, "C")
                pdf.cell(mound_width, 8, f"{convert_kg_to_mound(day_total_kg):.2f}", 1, 0, "C")
                pdf.cell(rate_width, 8, "", 1, 0, "C")
                pdf.cell(amount_width, 8, f"{day_total_amount:.2f}", 1, 1, "C")
                
                # Return to normal font
                pdf.set_font("Arial", "", 10)
            
            # Add grand total row
            pdf.set_font("Arial", "B", 12)
            pdf.cell(date_width, 10, "", 1, 0, "C")
            pdf.cell(time_width, 10, "TOTAL", 1, 0, "C")
            pdf.cell(kg_width, 10, f"{total_kg:.2f}", 1, 0, "C")
            pdf.cell(mound_width, 10, f"{convert_kg_to_mound(total_kg):.2f}", 1, 0, "C")
            pdf.cell(rate_width, 10, "", 1, 0, "C")
            pdf.cell(amount_width, 10, f"{total_amount:.2f}", 1, 1, "C")
        
        # Add payments section
        if bill_summary.payments:
            pdf.ln(10)
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Payment History", 0, 1, "C")
            
            # Set up payment table
            pdf.set_font("Arial", "B", 12)
            date_width = 40
            amount_width = 150
            
            # Payment header
            pdf.cell(date_width, 10, "Date", 1, 0, "C")
            pdf.cell(amount_width, 10, "Amount (Rs)", 1, 1, "C")
            
            # Payment data
            pdf.set_font("Arial", "", 10)
            for payment in bill_summary.payments:
                pdf.cell(date_width, 8, payment.date.strftime('%d-%m-%Y'), 1, 0, "C")
                pdf.cell(amount_width, 8, f"{payment.amount:.2f}", 1, 1, "C")
            
            # Total payment
            pdf.set_font("Arial", "B", 12)
            pdf.cell(date_width, 10, "Total Paid", 1, 0, "C")
            pdf.cell(amount_width, 10, f"{sum(p.amount for p in bill_summary.payments):.2f}", 1, 1, "C")
        
        # Add final balance
        pdf.ln(10)
        pdf.set_font("Arial", "B", 14)
        
        # Calculate net amount
        milk_value = sum(t.amount for t in bill_summary.transactions)
        adjustments = bill_summary.mandi_average - bill_summary.rent - bill_summary.commission
        net_amount = milk_value + adjustments
        paid_amount = sum(p.amount for p in bill_summary.payments)
        balance = net_amount - paid_amount
        
        # Show balance
        if balance != 0:
            pdf.cell(0, 10, f"Remaining Balance: Rs. {balance:.2f}", 0, 1, "C")
        
        # Add signature line at the bottom
        pdf.ln(20)
        pdf.line(20, pdf.get_y(), 80, pdf.get_y())
        pdf.line(120, pdf.get_y(), 180, pdf.get_y())
        pdf.ln(5)
        
        pdf.cell(90, 10, "Customer Signature", 0, 0, "C")
        pdf.cell(90, 10, "Authorized Signature", 0, 1, "C")
        
        # Generate temporary file if no output filename is provided
        if not output_filename:
            temp_dir = tempfile.gettempdir()
            output_filename = os.path.join(temp_dir, f"bill_{bill_summary.customer.id}_{bill_summary.start_date.strftime('%Y%m%d')}.pdf")
        
        # Save the PDF
        pdf.output(output_filename)
        return output_filename
    
    def export_transactions_to_excel(self, transactions: List[Transaction], customer: Optional[Customer] = None, 
                                     start_date: Optional[date] = None, end_date: Optional[date] = None, 
                                     output_filename: Optional[str] = None) -> str:
        """Export transaction data to Excel."""
        # Prepare data for export
        data = []
        for t in transactions:
            data.append({
                'Date': t.date,
                'Time': t.time_of_day,
                'Milk (kg)': t.milk_kg,
                'Milk (mound)': t.milk_mound,
                'Rate': t.rate,
                'Amount': t.amount
            })
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Generate filename if not provided
        if not output_filename:
            customer_name = customer.name if customer else "all_customers"
            customer_name = customer_name.replace(" ", "_").lower()
            date_str = ""
            if start_date and end_date:
                date_str = f"_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}"
            temp_dir = tempfile.gettempdir()
            output_filename = os.path.join(temp_dir, f"transactions_{customer_name}{date_str}.xlsx")
        
        # Save to Excel
        df.to_excel(output_filename, index=False)
        return output_filename
