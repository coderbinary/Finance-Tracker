from flask import Flask, render_template, request, redirect, url_for
from flask_mysqldb import MySQL
from datetime import datetime
from collections import defaultdict
app = Flask(__name__)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''  # No password by default in XAMPP
app.config['MYSQL_DB'] = 'finance_tracker'

mysql = MySQL(app)

@app.route('/')
def home():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM expenses ORDER BY date DESC")
    expenses = cur.fetchall()

    # Summary stats
    income = 0
    expense = 0
    category_totals = defaultdict(float)
    monthly_data = defaultdict(lambda: {'income': 0, 'expense': 0})

    for row in expenses:
        amount = float(row[2])
        category = row[3]
        date_str = row[4]  # Assuming the 5th column is the date
        date_obj = date_str  # it's already a datetime.date object
        month_label = date_obj.strftime("%Y-%m")  # eg. "2025-06"

        if category.lower() == 'income':
            income += amount
            monthly_data[month_label]['income'] += amount
        else:
            expense += amount
            category_totals[category] += amount
            monthly_data[month_label]['expense'] += amount

    balance = income - expense

    if income == 0:
        insight = "Add your income to see smart tips!"
    elif expense > income:
        insight = "⚠️ You're spending more than your income."
    elif balance >= income * 0.3:
        insight = "🎉 Great job! You're saving well this month."
    else:
        insight = "🙂 You're doing fine, but keep an eye on your spending."

    cur.close()

    # Prepare data for chart
    sorted_months = sorted(monthly_data.keys())
    income_values = [monthly_data[m]['income'] for m in sorted_months]
    expense_values = [monthly_data[m]['expense'] for m in sorted_months]

    return render_template(
        'home.html',
        expenses=expenses,
        insight=insight,
        income=income,
        expense=expense,
        balance=balance,
        category_totals=dict(category_totals),
        months=sorted_months,
        income_values=income_values,
        expense_values=expense_values
    )

@app.route('/savings-goal', methods=['GET', 'POST'])
def savings_goal():
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        goal_amount = request.form['goal_amount']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        cur.execute("INSERT INTO savings_goal (goal_amount, start_date, end_date) VALUES (%s, %s, %s)",
                    (goal_amount, start_date, end_date))
        mysql.connection.commit()

    cur.execute("SELECT * FROM savings_goal ORDER BY id DESC LIMIT 1")
    goal = cur.fetchone()

    goal_amount = goal[1] if goal else 0
    start_date = goal[2] if goal else None
    end_date = goal[3] if goal else None

    # Calculate current savings
    cur.execute("SELECT amount, category FROM expenses WHERE date BETWEEN %s AND %s", (start_date, end_date))
    rows = cur.fetchall()
    current_savings = sum(float(row[0]) for row in rows if row[1].lower() == 'income') - \
                      sum(float(row[0]) for row in rows if row[1].lower() != 'income')

    progress = (current_savings / goal_amount) * 100 if goal_amount > 0 else 0
    cur.close()

    return render_template('savings.html',
                           goal_amount=goal_amount,
                           current_savings=current_savings,
                           progress=int(progress))
if __name__ == '__main__':
    app.run(debug=True)
