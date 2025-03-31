from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///financial_planner.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Add template filter for currency formatting
@app.template_filter('format_currency')
def format_currency(amount):
    if amount is None:
        return "€0,00"
    return f"€{amount:,.2f}".replace(',', ' ').replace('.', ',')

# Database Models
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # income or expense
    income_source = db.Column(db.String(50))  # Added for income sources

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    spent = db.Column(db.Float, nullable=False, default=0.0)
    period = db.Column(db.String(20), nullable=False)  # monthly or yearly
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=True)  # null for yearly budgets
    priority = db.Column(db.Integer, nullable=False)  # 1, 2, or 3

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    billing_cycle = db.Column(db.String(20), nullable=False)  # monthly, yearly
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))
    priority = db.Column(db.Integer, nullable=False)  # 1, 2, or 3
    status = db.Column(db.String(20), nullable=False, default='active')  # active, cancelled

class SavingsAllocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0.0)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class InvestmentAllocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)  # This will store the type (e.g., Stocks, Bonds)
    name = db.Column(db.String(100), nullable=False, default='')  # e.g., Apple Inc., S&P 500 ETF
    amount = db.Column(db.Float, nullable=False, default=0.0)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

# Routes
@app.route('/')
def index():
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    # Get recent transactions
    recent_transactions = Transaction.query.order_by(Transaction.date.desc()).limit(5).all()
    
    # Calculate totals
    total_income = Transaction.query.filter_by(type='income').with_entities(db.func.sum(Transaction.amount)).scalar() or 0
    total_expenses = Transaction.query.filter_by(type='expense').with_entities(db.func.sum(Transaction.amount)).scalar() or 0
    total_balance = total_income - total_expenses
    
    # Get monthly data for charts
    monthly_income = Transaction.query.filter(
        Transaction.type == 'income',
        db.extract('month', Transaction.date) == current_month,
        db.extract('year', Transaction.date) == current_year
    ).with_entities(db.func.sum(Transaction.amount)).scalar() or 0
    
    monthly_expenses = Transaction.query.filter(
        Transaction.type == 'expense',
        db.extract('month', Transaction.date) == current_month,
        db.extract('year', Transaction.date) == current_year
    ).with_entities(db.func.sum(Transaction.amount)).scalar() or 0
    
    # Get budget information
    monthly_budgets = Budget.query.filter_by(
        period='monthly',
        year=current_year,
        month=current_month
    ).all()
    
    yearly_budgets = Budget.query.filter_by(
        period='yearly',
        year=current_year
    ).all()
    
    # Calculate total budget and spent
    total_monthly_budget = sum(budget.amount for budget in monthly_budgets)
    total_monthly_spent = sum(budget.spent for budget in monthly_budgets)
    
    # Calculate budget progress
    budget_progress = 0
    if total_monthly_budget > 0:
        budget_progress = (total_monthly_spent / total_monthly_budget) * 100
    
    return render_template('dashboard.html',
                         recent_transactions=recent_transactions,
                         total_balance=total_balance,
                         monthly_income=monthly_income,
                         monthly_expenses=monthly_expenses,
                         budget_progress=budget_progress,
                         monthly_budgets=monthly_budgets,
                         yearly_budgets=yearly_budgets)

def calculate_subscription_totals():
    # Get all active subscriptions
    subscriptions = Subscription.query.filter_by(status='active').all()
    
    # Calculate monthly and yearly totals
    monthly_total = sum(s.amount for s in subscriptions if s.billing_cycle == 'monthly')
    yearly_total = sum(s.amount for s in subscriptions if s.billing_cycle == 'yearly')
    
    return monthly_total, yearly_total

@app.route('/budget')
def budget():
    # Get current year and month
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    # Get monthly budgets
    monthly_budgets = Budget.query.filter_by(
        period='monthly',
        year=current_year,
        month=current_month
    ).all()
    
    # Get yearly budgets
    yearly_budgets = Budget.query.filter_by(
        period='yearly',
        year=current_year
    ).all()
    
    # Get subscription totals
    monthly_subscription_total, yearly_subscription_total = calculate_subscription_totals()
    
    # Create or update "Subscriptions" budget items
    monthly_subscription_budget = Budget.query.filter_by(
        category='Subscriptions',
        period='monthly',
        year=current_year,
        month=current_month
    ).first()
    
    if not monthly_subscription_budget:
        monthly_subscription_budget = Budget(
            category='Subscriptions',
            amount=monthly_subscription_total,
            spent=monthly_subscription_total,  # Set spent equal to amount since these are fixed costs
            period='monthly',
            year=current_year,
            month=current_month,
            priority=1  # Set as high priority since these are recurring commitments
        )
        db.session.add(monthly_subscription_budget)
    else:
        monthly_subscription_budget.amount = monthly_subscription_total
        monthly_subscription_budget.spent = monthly_subscription_total
    
    yearly_subscription_budget = Budget.query.filter_by(
        category='Subscriptions',
        period='yearly',
        year=current_year
    ).first()
    
    if not yearly_subscription_budget:
        yearly_subscription_budget = Budget(
            category='Subscriptions',
            amount=yearly_subscription_total,
            spent=yearly_subscription_total,  # Set spent equal to amount since these are fixed costs
            period='yearly',
            year=current_year,
            priority=1  # Set as high priority since these are recurring commitments
        )
        db.session.add(yearly_subscription_budget)
    else:
        yearly_subscription_budget.amount = yearly_subscription_total
        yearly_subscription_budget.spent = yearly_subscription_total
    
    db.session.commit()
    
    return render_template('budget.html',
                         monthly_budgets=monthly_budgets,
                         yearly_budgets=yearly_budgets)

@app.route('/add_budget', methods=['POST'])
def add_budget():
    try:
        data = request.get_json()
        print("Received budget data:", data)  # Debug log
        
        # Create new budget
        new_budget = Budget(
            category=data['category'],
            amount=float(data['amount']),
            period=data['period'],
            year=datetime.now().year,
            month=datetime.now().month if data['period'] == 'monthly' else None,
            priority=int(data['priority'])  # Ensure priority is converted to int
        )
        
        # Add to database
        db.session.add(new_budget)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Budget added successfully'
        })
    except Exception as e:
        print("Error adding budget:", str(e))  # Debug log
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@app.route('/transactions')
def transactions():
    return render_template('transactions.html')

@app.route('/reports')
def reports():
    return render_template('reports.html')

@app.route('/goals')
def goals():
    return render_template('goals.html')

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    try:
        data = request.get_json()
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # Create new transaction
        new_transaction = Transaction(
            type=data['type'],
            amount=float(data['amount']),
            description=data['description'],
            category=data['category'],
            date=datetime.now(),
            income_source=data.get('incomeSource')  # This will be None for expenses
        )
        
        # Add to database
        db.session.add(new_transaction)
        
        # Update budget spent amount if it's an expense
        if data['type'] == 'expense':
            # Update monthly budget
            monthly_budget = Budget.query.filter_by(
                category=data['category'],
                period='monthly',
                year=current_year,
                month=current_month
            ).first()
            
            if monthly_budget:
                monthly_budget.spent += float(data['amount'])
            
            # Update yearly budget
            yearly_budget = Budget.query.filter_by(
                category=data['category'],
                period='yearly',
                year=current_year
            ).first()
            
            if yearly_budget:
                yearly_budget.spent += float(data['amount'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Transaction added successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@app.route('/update_spent', methods=['POST'])
def update_spent():
    try:
        data = request.get_json()
        budget_id = int(data['budget_id'])
        new_spent = float(data['spent'])
        
        # Get the budget
        budget = Budget.query.get(budget_id)
        if not budget:
            return jsonify({
                'success': False,
                'message': 'Budget not found'
            }), 404
        
        # Update spent amount
        budget.spent = new_spent
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Spent amount updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@app.route('/update_budget', methods=['POST'])
def update_budget():
    try:
        data = request.get_json()
        print("Received update data:", data)  # Debug log
        
        budget_id = int(data['budget_id'])
        new_category = data['category']
        new_spent = float(data['spent'])
        new_priority = int(data['priority'])
        
        # Get the budget
        budget = Budget.query.get(budget_id)
        if not budget:
            return jsonify({
                'success': False,
                'message': 'Budget not found'
            }), 404
        
        # Update budget details
        budget.category = new_category
        budget.spent = new_spent
        budget.priority = new_priority
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Budget updated successfully'
        })
    except Exception as e:
        print("Error updating budget:", str(e))  # Debug log
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@app.route('/delete_budget', methods=['POST'])
def delete_budget():
    try:
        data = request.get_json()
        budget_id = int(data['budget_id'])
        
        # Get the budget
        budget = Budget.query.get(budget_id)
        if not budget:
            return jsonify({
                'success': False,
                'message': 'Budget not found'
            }), 404
        
        # Store category for the success message
        category = budget.category
        
        # Delete the budget
        db.session.delete(budget)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Budget category "{category}" deleted successfully'
        })
    except Exception as e:
        print("Error deleting budget:", str(e))  # Debug log
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@app.route('/subscriptions')
def subscriptions():
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    # Get all active subscriptions
    active_subscriptions = Subscription.query.filter_by(status='active').all()
    
    # Calculate total monthly and yearly subscription costs
    monthly_total = sum(sub.amount for sub in active_subscriptions if sub.billing_cycle == 'monthly')
    yearly_total = sum(sub.amount for sub in active_subscriptions if sub.billing_cycle == 'yearly')
    
    return render_template('subscriptions.html',
                         subscriptions=active_subscriptions,
                         monthly_total=monthly_total,
                         yearly_total=yearly_total)

@app.route('/add_subscription', methods=['POST'])
def add_subscription():
    try:
        data = request.get_json()
        
        # Create new subscription
        new_subscription = Subscription(
            name=data['name'],
            amount=float(data['amount']),
            billing_cycle=data['billing_cycle'],
            category=data['category'],
            description=data.get('description', ''),
            priority=int(data['priority']),
            status='active'
        )
        
        # Add to database
        db.session.add(new_subscription)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Subscription added successfully'
        })
    except Exception as e:
        print("Error adding subscription:", str(e))
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@app.route('/update_subscription', methods=['POST'])
def update_subscription():
    try:
        data = request.get_json()
        subscription_id = int(data['subscription_id'])
        
        # Get the subscription
        subscription = Subscription.query.get(subscription_id)
        if not subscription:
            return jsonify({
                'success': False,
                'message': 'Subscription not found'
            }), 404
        
        # Update subscription details
        subscription.name = data['name']
        subscription.amount = float(data['amount'])
        subscription.billing_cycle = data['billing_cycle']
        subscription.category = data['category']
        subscription.description = data.get('description', '')
        subscription.priority = int(data['priority'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Subscription updated successfully'
        })
    except Exception as e:
        print("Error updating subscription:", str(e))
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@app.route('/cancel_subscription', methods=['POST'])
def cancel_subscription():
    try:
        data = request.get_json()
        subscription_id = int(data['subscription_id'])
        
        # Get the subscription
        subscription = Subscription.query.get(subscription_id)
        if not subscription:
            return jsonify({
                'success': False,
                'message': 'Subscription not found'
            }), 404
        
        # Cancel the subscription
        subscription.status = 'cancelled'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Subscription "{subscription.name}" cancelled successfully'
        })
    except Exception as e:
        print("Error cancelling subscription:", str(e))
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@app.route('/savings')
def savings():
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    # Get savings allocations
    savings_allocations = SavingsAllocation.query.filter_by(
        year=current_year,
        month=current_month
    ).all()
    
    # Get the savings amount from budget overview
    savings_budget = Budget.query.filter_by(
        category='Savings',
        period='monthly',
        year=current_year,
        month=current_month
    ).first()
    
    # Set total_available to the amount from Savings budget if it exists, otherwise 0
    total_available = savings_budget.amount if savings_budget else 0.0
    
    # Calculate total allocated
    total_allocated = sum(allocation.amount for allocation in savings_allocations)
    
    # Get historical savings data (last 6 months)
    historical_data = []
    for i in range(5, -1, -1):
        target_month = current_month - i
        target_year = current_year
        if target_month <= 0:
            target_month += 12
            target_year -= 1
            
        month_savings = Budget.query.filter_by(
            category='Savings',
            period='monthly',
            year=target_year,
            month=target_month
        ).first()
        
        month_amount = month_savings.amount if month_savings else 0
        month_rate = 0  # We'll skip the rate calculation since we're not using income/expenses
        
        historical_data.append({
            'month': datetime(target_year, target_month, 1).strftime('%B %Y'),
            'savings': month_amount,
            'rate': month_rate
        })
    
    # Serialize savings allocations for JavaScript
    serialized_allocations = [{
        'id': allocation.id,
        'category': allocation.category,
        'amount': allocation.amount
    } for allocation in savings_allocations]
    
    return render_template('savings.html',
                         savings_allocations=savings_allocations,
                         serialized_allocations=serialized_allocations,
                         total_available=total_available,
                         total_allocated=total_allocated,
                         historical_data=historical_data)

@app.route('/add_savings_allocation', methods=['POST'])
def add_savings_allocation():
    try:
        data = request.get_json()
        
        # Create new savings allocation
        new_allocation = SavingsAllocation(
            category=data['category'],
            amount=float(data['amount']),
            year=datetime.now().year,
            month=datetime.now().month
        )
        
        # Add to database
        db.session.add(new_allocation)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Savings allocation added successfully'
        })
    except Exception as e:
        print("Error adding savings allocation:", str(e))
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@app.route('/update_savings_allocation', methods=['POST'])
def update_savings_allocation():
    try:
        data = request.get_json()
        allocation_id = int(data['allocation_id'])
        
        # Get the allocation
        allocation = SavingsAllocation.query.get(allocation_id)
        if not allocation:
            return jsonify({
                'success': False,
                'message': 'Savings allocation not found'
            }), 404
        
        # Update allocation
        allocation.category = data['category']
        allocation.amount = float(data['amount'])
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Savings allocation updated successfully'
        })
    except Exception as e:
        print("Error updating savings allocation:", str(e))
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@app.route('/delete_savings_allocation', methods=['POST'])
def delete_savings_allocation():
    try:
        data = request.get_json()
        allocation_id = int(data['allocation_id'])
        
        # Get the allocation
        allocation = SavingsAllocation.query.get(allocation_id)
        if not allocation:
            return jsonify({
                'success': False,
                'message': 'Savings allocation not found'
            }), 404
        
        # Delete the allocation
        db.session.delete(allocation)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Savings allocation deleted successfully'
        })
    except Exception as e:
        print("Error deleting savings allocation:", str(e))
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@app.route('/investments')
def investments():
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    # Get investment allocations
    investment_allocations = InvestmentAllocation.query.filter_by(
        year=current_year,
        month=current_month
    ).all()
    
    # Get the investments amount from savings allocations
    savings_investment = SavingsAllocation.query.filter_by(
        category='Investment',
        year=current_year,
        month=current_month
    ).first()
    
    # Set total_available to the amount from savings investment allocation if it exists, otherwise 0
    total_available = savings_investment.amount if savings_investment else 0.0
    
    # Calculate total allocated
    total_allocated = sum(allocation.amount for allocation in investment_allocations)
    
    # Serialize investment allocations for JavaScript
    serialized_allocations = [{
        'id': allocation.id,
        'category': allocation.category,
        'amount': allocation.amount
    } for allocation in investment_allocations]
    
    return render_template('investments.html',
                         investment_allocations=investment_allocations,
                         serialized_allocations=serialized_allocations,
                         total_available=total_available,
                         total_allocated=total_allocated)

@app.route('/add_investment_allocation', methods=['POST'])
def add_investment_allocation():
    try:
        data = request.get_json()
        
        # Create new investment allocation
        new_allocation = InvestmentAllocation(
            category=data['type'],  # Use type as category
            name=data.get('name', ''),  # Make name optional with default empty string
            amount=float(data['amount']),
            year=datetime.now().year,
            month=datetime.now().month
        )
        
        # Add to database
        db.session.add(new_allocation)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Investment allocation added successfully'
        })
    except Exception as e:
        print("Error adding investment allocation:", str(e))
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@app.route('/update_investment_allocation', methods=['POST'])
def update_investment_allocation():
    try:
        data = request.get_json()
        allocation_id = int(data['allocation_id'])
        
        # Get the allocation
        allocation = InvestmentAllocation.query.get(allocation_id)
        if not allocation:
            return jsonify({
                'success': False,
                'message': 'Investment allocation not found'
            }), 404
        
        # Update allocation
        allocation.category = data['type']  # Use type as category
        allocation.name = data.get('name', '')  # Make name optional
        allocation.amount = float(data['amount'])
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Investment allocation updated successfully'
        })
    except Exception as e:
        print("Error updating investment allocation:", str(e))
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@app.route('/delete_investment_allocation', methods=['POST'])
def delete_investment_allocation():
    try:
        data = request.get_json()
        allocation_id = int(data['allocation_id'])
        
        # Get the allocation
        allocation = InvestmentAllocation.query.get(allocation_id)
        if not allocation:
            return jsonify({
                'success': False,
                'message': 'Investment allocation not found'
            }), 404
        
        # Delete the allocation
        db.session.delete(allocation)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Investment allocation deleted successfully'
        })
    except Exception as e:
        print("Error deleting investment allocation:", str(e))
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 