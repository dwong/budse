import sqlite3 as sqlite

database = 'data.db'
conn = sqlite.connect(database, isolation_level=None)
conn.row_factory = sqlite.Row
c = conn.cursor()

# transactions table
c.execute('SELECT transaction_id, root_transaction_id, amount FROM transactions')
transactions = []
for row in c:
    amount = int(round(row['amount'] * 100))
    print('modify %s amount from %s to %s' % (row['transaction_id'],
					      row['amount'], amount))
    if row['root_transaction_id'] == row['transaction_id']:
        parent = None
    else:
        parent = row['root_transaction_id']
    transactions.append((amount, parent, row['transaction_id']))
conn.executemany('update transactions set amount=?, root_transaction_id=? where transaction_id=?', transactions)

# alter transactions table
conn.execute('create table temp (transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp TEXT,date TEXT,user_id INTEGER,account_id INTEGER,amount INTEGER,action TEXT,description TEXT,root_transaction_id INTEGER,status INTEGER)')
conn.execute('insert into temp select * from transactions')
conn.execute('drop table transactions')
conn.execute('alter table temp rename to transactions')

# accounts table
c.execute('SELECT account_id, transaction_amount, account_total FROM accounts')
for row in c:
    print('account %s amount from %s to %s' %(row['account_id'], row['transaction_amount'], int(round(row['transaction_amount'] * 100))))
    conn.execute('UPDATE accounts SET transaction_amount=?, account_total=? WHERE account_id=?', (int(round(row['transaction_amount'] * 100)), int(round(row['account_total'] * 100)), row['account_id']))
# alter accounts table
conn.execute('create table temp (account_id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,account_name TEXT,status INTEGER,account_total INTEGER,percentage_or_fixed TEXT,transaction_amount INTEGER,affect_gross INTEGER,account_description TEXT)')
conn.execute('insert into temp select * from accounts')
conn.execute('drop table accounts')
conn.execute('alter table temp rename to accounts')
conn.execute('vacuum')
