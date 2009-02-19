############################
# BUDget for Spam and Eggs (Budse)
#
# Version:
#     0.2
#
# Description:
#     Budget finances on the console
#
# Requirements:
#     1) Python 2.6 or lower (not Python 3000 compatible yet)
#     2) Sqlite3
#     3) Courage (for the bugs)
#
# License:
#     Released under the GPL, a copy of which can be found at http://www.gnu.org/copyleft/gpl.html
#
# Author:
#     Derek Wong (http://www.goingthewongway.com)
#
#
############################

#from __future__ import with_statement
import datetime
import os
import pdb
from optparse import OptionParser
from pysqlite2 import dbapi2 as sqlite

default_database = 'data.db'
parser = OptionParser()
parser.set_defaults(debug=False, database=default_database)
parser.add_option('-f', '--file',
                  dest='database', help='Database file to utilize')
parser.add_option('-d', '--debug',
                  action='store_true', dest='debug', help='Display debugging information')
opts, args = parser.parse_args()

debug = opts.debug
if debug and opts.database == default_database:
    database_file = 'test.db'
else:
    database_file = opts.database

account_table = {'table': 'accounts', 'id': 'account_id', 'user': 'user_id',
                 'name': 'account_name', 'status': 'status',
                 'total': 'account_total', 'type': 'percentage_or_fixed',
                 'amount': 'transaction_amount', 'gross': 'affect_gross',
                 'description': 'account_description',
                 'percentage_type': 'percentage', 'fixed_type': 'fixed',
                 'gross_true': 1, 'gross_false': 0,
                 'active': 1, 'inactive': 0
                 }
#TODO 10 turn off prompting for deducting from gross
#TODO 8 deduction table instead of within user table?
user_table = {'table': 'users', 'id': 'user_id', 'name': 'user_name',
              'status': 'status', 'timestamp': 'last_login',
              'deductions': 'automatic_deductions', 
              'whole_account': 'whole_account_actions',
#              'gross': 'prompt_for_gross',
              'whole_account_true': 1, 'whole_account_false': 0,
#              'gross_true': 1, 'gross_false': 0,
              'active': 1, 'inactive': 0
              }
transaction_table = {'table': 'transactions', 'id': 'transaction_id',
                     'timestamp': 'timestamp', 'date': 'date',
                     'user':'user_id', 'account': 'account_id',
                     'amount': 'amount', 'action': 'action',
                     'description': 'description', 'status': 'status',
                     'root_id': 'root_transaction_id',
                     'deposit': '+', 'withdrawal': '-','deduction': '|',
                     'information': '?', 'transfer': '=',
                     'active': 1, 'inactive': 0
                     }

class Error(Exception):
    """Base class for exceptions in this module.
    """
    pass

class MetaError(Error):
    """Exception raised for meta actions in the input.
    """
    def __init__(self, expression, message):
        """Initialization method.

        Keyword arguments:
        expression -- Input that caused the exception to be raised
        message -- Explanation of error
         
        """
        self.expression = expression
        self.message = message

    def __str__(self):
        return '[%s] - %s' % (self.expression, self.message)

class MenuError(MetaError):
    """Exception raised to cancel out of a menu.
    """
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message

    def __str__(self):
        return '[%s] - %s' % (self.expression, self.message)

class ConversionError(MetaError):
    """Exception raised converting to the type specified.
    """
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message

    def __str__(self):
        return '[%s] - %s' % (self.expression, self.message)

      
# Actions that have meaning for all menus
meta_actions = 'c - Cancel / Done\nq - Quit Program'
output_date = '%m/%d/%Y'
def _handle_input(prompt, base_type=str):
    """Take all input, passing back errors as appropriate.

    This function will be the single point of entry for user
    input into the console.  It will catch exceptions, and pass
    them back along with the user input so that callers can
    decide what to do.

    Keyword arguments:
    prompt -- Printed to user 
    base_type -- Type to expect in the input

    Returns:
    Expression coming from input

    """
    try:
        base_input = raw_input(prompt)
    except KeyboardInterrupt:
        raise SystemExit('Quitting the Budse')
    if str(base_input).upper() == 'C':
        raise MenuError(base_input, 'Cancel current menu')
    elif str(base_input).upper() == 'Q':
        raise SystemExit('Quitting the Budse')
    try:
        expression = base_type(base_input)
    except Exception, e:
        raise ConversionError(base_input, str(e))
    return expression

def _confirm(prompt, default=False):
    """Prompt user for a confirmation of something.

    Keyword parameters:
    prompt -- What question to ask the user
    default -- Value that <RETURN> will be for (default False/no)

    """
    confirm = None
    yes_list = ('y', 'yes')
    no_list = ('n', 'no')
    if not default:
        no_list += ('',)
        values = 'y/N'
    else:
        yes_list += ('',)
        values = 'Y/n'  
    prompt = prompt + ' [' + values + '] '
    while confirm is None:
        answer = _handle_input(prompt).lstrip().lower()
        if answer in no_list:
            confirm = False
        elif answer in yes_list:
            confirm = True
        else:
            print 'Not an acceptable value'
    return confirm    

def _ask_string(prompt='Description? ', default=None):
    """Query user for a string, usually a description.

    Keyword arguments:
    prompt -- How to query the user

    Returns:
    Input received for the description

    """
    return _handle_input(prompt)

def _ask_amount(prompt='Amount? '):
    """Query user for a float amount
    
    Keyword arguments:
    prompt -- Output to the user to indicate input that's expected

    Returns:
    Float amount rounded to 2 decimal places

    """
    amount = None
    while amount is None:
        try:
            amount = _handle_input(prompt, float)
        except ConversionError:
            print 'Invalid value'
    # Only keep 2 decimal places of precision for these floats
    return round(amount, 2)
            
def table(target):
    """Construct the tables to be used in a query

    Keyword arguments:
    target -- Dictionary of tables to retrieve from.  
        Of the form (['t1': 'first_table', 't2':'second_table',
                      '1_key': 'first_id', '2_key': 'second_id'],
                     ['t1': 'second_table', 't2':'third_table',
                      '1_key': 'second_key', '2_key': 'third_key'])
        A single table can be passed as a string (not a dictionary).

    Returns:
    table portion of query string, implicit joins needed in the WHERE clause

    """
    query = ''
    if isinstance(target, str):
        query += '%s ' % target
        implicit_joins = None
    else:
        tables = []
        join_count = len(target)
        table_1 = 't1'
        table_2 = 't2'
        key_1 = '1_key'
        key_2 = '2_key'
        implicit_joins = ''
        for join in target:
            try:
                tables.index(join[table_1])
            except ValueError:
                tables.append(join[table_1])
            try:
                tables.index(join[table_2])
            except ValueError:
                tables.append(join[table_2])
            implicit_joins += '%s.%s=%s.%s AND ' % (join[table_1], join[key_1],
                                                    join[table_2], join[key_2])
        else:
            implicit_joins = implicit_joins[:implicit_joins.rindex('AND')]
        for table in tables:
            query += '%s ,' % table
        else:
            query = query[:query.rindex(',')]
    return query, implicit_joins

def where(filters=None, implicit_joins=None):
    """Where clause used when dealing with a database.

    Keyword arguments:
    filters -- List of ([comparison operator, ]column, value) filters to
        use in the WHERE clause (default None)
    implicit_joins -- String of implicit joins that are needed in order
        to join multiple tables (default None)

    Returns:
    Where portion of SQL query, parameters (list of values for each filter)
    
    """
    query = ''
    parameters = []
    if (filters is not None and filters) or implicit_joins is not None:
        if implicit_joins is None:
            implicit_joins = ''
        elif filters:
            implicit_joins += 'AND '
        query += 'WHERE %s' % implicit_joins
        if filters is not None:
            for query_filter in tuple(filters):
                if len(query_filter) == 3:
                    comparison_operator, column, value = query_filter
                else:
                    column, value = query_filter
                    comparison_operator = '='
                query += '%s%s? AND ' % (column, comparison_operator)
                parameters.append(value)
   # Can't handle using OR clause (would also require using parenthesis in query)
            else:
                query = query[:query.rindex('AND')]
    return query, parameters

def select(columns, target, filters=None, group=None, order=None, limit=None):
    """Select an arbitrary amount of columns from a table

    Keyword arguments:
    columns -- List of columns to retrieve
    target -- Dictionary of tables to retrieve from. A single table can be 
        passed as a string (not a dictionary).
        See table for further details
    filters -- List of ([comparison operator, ]column, value) filters to
        use in the WHERE clause (default None)
    order -- List of how to order the results (default None)
    group -- List of how to group the results (default None)
    limit -- An integer that allows a specified number of rows in the 
        result set (default None)
    
    Returns:
    query string and optional parameter list if filters are sent
    
    """
    query = 'SELECT '
    for column in columns:
        query += '%s ,' % column
    else:
        query = query[:query.rindex(',')]
    from_clause, implicit_joins = table(target)
    where_clause, parameters = where(filters, implicit_joins)
    query += 'FROM %s' % (from_clause + where_clause)
    if group is not None:
        query += 'GROUP BY '
        for clause in group:
            query += '%s ,' % clause
        else:
            query = query[:query.rindex(',')]
    if order is not None:
        query += 'ORDER BY ' 
        for clause in order:
            query += '%s ,' % clause
        else:
            query = query[:query.rindex(',')]
    if limit is not None:
        query += 'LIMIT %d' % limit
    if parameters:
        return query, tuple(parameters)
    else:
        return query

def update(changes, target, filters, limit=None):
    """Update an existing entry in the database.

    Keyword arguments:
    changes -- List of (columns, values) to modify
    target -- Dictionary of tables to retrieve from. A single table can be 
        passed as a string (not a dictionary).
        See table for further details
    filters -- List of (column, value) filters to use in the WHERE clause
    order -- List of how to order the results (default None)
    group -- List of how to group the results (default None)
    limit -- An integer that allows a specified number of rows in the 
        result set (default None)

    Returns:
    query string, tuple of parameters
    
    """
    query = 'UPDATE '
    table_string, implicit_joins = table(target)
    query += table_string
    query += 'SET '
    parameters = []
    for column, value in changes:
        query += '%s=? ,' % column
        parameters.append(value)
    else:
        query = query[:query.rindex(',')]
    where_string, where_values = where(filters, implicit_joins)
    query += where_string
    parameters += where_values
    if limit is not None:
        query += 'LIMIT %d' % limit
    return query, tuple(parameters)

def delete(target, filters):
    """Delete rows from a database.

    Keyword arguments:
    target -- Dictionary of tables to retrieve from. A single table can be 
        passed as a string (not a dictionary).
        See table for further details
    filters -- List of (column, value) filters to use in the WHERE clause
    
    """
    #support DELETE without filters??
    query = 'DELETE FROM '
    table_string, implicit_joins = table(target)
    query += table_string
    where_string, parameters = where(filters, implicit_joins)
    query += where_string
    return query, tuple(parameters)

def insert(insert_values, target):
    """Delete rows from a database.

    Keyword arguments:
    insert_values -- List of (column, value) tuples
    target -- A single table name

    Returns:
    query string, parameter list
    
    """
    if not isinstance(target, str):
        raise ValueError('Cannot insert into multiple tables.')
    columns = values = ''
    parameters = []
    for column, value in insert_values:
        columns += '%s, ' % column
        values += '?, '
        parameters.append(value)
    else:
        columns = columns[:columns.rindex(',')]
        values = values[:values.rindex(',')]
    query = 'INSERT INTO %s ( %s ) VALUES ( %s )' % (target, columns, values)
    return query, tuple(parameters)

def execute_query(query, query_arguments=None):
    """Execute an arbitrary command on the database
    
    Keyword arguments:
    query -- Arbitrary SQL query 
    query_arguments -- List of arguments to the SQL query (default None)

    Returns:
    Cursor with which to loop through the result set, if applicable

    """
    #TODO 20 check out pysqlite using connection as context manager
#    if debug: print 'Executing query: %s\nWith parameters: %s' % (query, query_arguments)
    if query_arguments is None:
        try:
#             if debug: print 'Query (no args): %s' % query
            cursor = connection.execute(query)
            connection.commit()
        except sqlite.Error, e: 
            print "Query error (parameter-less query): ", e.args[0]
            print 'Query: %s' % query
    else:
        try:
#             if debug: print 'Query: %s\nArgs: %s' % (query, query_arguments)
            cursor = connection.execute(query, query_arguments)
            connection.commit()            
        except sqlite.Error, e: 
            print "Query error (with parameters): ", e.args[0]
            print 'Query: %s\nArgs:%s' % (query, query_arguments)
    return cursor
connector = execute_query


class DatabaseObject(object):

    def __init__(self, table, id_column, id=None, indent=''):
        """Initialize an object to interact with a row of a database.

        Keyword arguments:
        table -- Database table to retrieve from
        id_column -- Name of the column storing the unique IDs
        id -- Unique ID of the entry to reference (default None)
        indent -- An empty string (e.g., '    ') that will indent the object
            when it's printed out as a string (via __str__) (default '')

        """
        object.__init__(self)
        try:
            if id is not None:
                query, parameters = select([id_column], 
                                           table,
                                           [(id_column, id)],
                                           limit=1)
                cursor = connector(query, parameters)
            else:
                query = select((id_column,), table, limit=1)
                cursor = connector(query)
        except sqlite.Error:
            raise ValueError('Invalid database reference')
        if id is not None:
            row = cursor.fetchone()
            if row is None or row[id_column] is None:
                raise ValueError('Invalid database reference')
        self.table = table
        self.id_column = id_column
        self.id = id
        self.indent = indent
        # cache and dirty dictionaries are keyed by [column name]
        self.cache = {}
        self.dirty = {}
        
    def discard(self):
        """Discard any changes that have been made.

        This is the inverse function of save.
        
        """
        if debug:
            print 'discard(): \ndirty:%s\ncache:%s' % (self.dirty, self.cache)
        self.dirty = {}
    
#Concerns - This could be bad in cases where the cache becomes stale.

#Perhaps put a lock per user within the database
#itself? This can also be a problem if somehow the user escapes (or 
#is dumped) out of the program without "properly" quitting.  This 
#reader writer problem is of minimal concern at this point
#since this is aimed at being a small application to be 
#used by a single user on a local machine at a time.  Speed is of
#much more importance for that goal.

#Another idea would be to create another access table that would
#essentially dictate the coherency protocol to keep data consistent
#across all instances.
    @staticmethod
    def _get_function(column_name):
        """Return closure for retrieving a column from a specified table.

        Keyword arguments:
        column_name -- The column in the database to retrieve

        Returns:
        Function closure that will retrieve a specific column for a row

        """
        def get_setting(self):
            if column_name in self.dirty:
                return self.dirty[column_name]
            elif (column_name not in self.cache or
                  self.cache[column_name] is None):
                if self.id is not None:
                    query, parameters = select([column_name],
                                               self.table,
                                               [(self.id_column, self.id)])
                    row = connector(query, parameters).fetchone()
                    self.cache[column_name] = row[column_name]
                else:
                    return None
            return self.cache[column_name]
        return get_setting

    @staticmethod
    def _set_function(column_name):
        """Return closure for updating specific database column.

        Keyword arguments:
        column_name -- The column in the database to retrieve

        Returns:
        Function closure that will set a specific column for a row

        """
        def set_setting(self, new_value):
            self.dirty[column_name] = new_value
        return set_setting

    @staticmethod
    def _del_function(column_name):
        """Blank the value from the database before deleting the attribute.

        Keyword arguments:
        column_name -- The column in the database to retrieve


        """
        def del_setting(self):
            if column_name in self.cache:
                del self.cache[column_name]
            if column_name in self.dirty:
                del self.dirty[column_name]
            if self.id is not None:
                query, parameters = update([(column_name, '')],
                                           self.table,
                                           [(self.id_column, self.id)])
                connector(query, parameters)
        return del_setting

    @staticmethod
    def accessors(column_name):
        """Return a tuple of get and set accessor functions.

        Keyword arguments:
        column_name -- The column in the database to retrieve

        Returns:
        Tuple of function closures of (get_setting, set_setting,
            del_setting)

        """
        return (DatabaseObject._get_function(column_name),
                DatabaseObject._set_function(column_name),
                DatabaseObject._get_function(column_name))


class Account(DatabaseObject):

    def __init__(self, account_id=None, name=None, description=None, 
                 type=None, amount=0.00, gross=None, user=None):
        """Initialize a new account object.

        Keyword arguments:
        account_id -- Unique ID of the account this object represents,
            will disregard other parameters if this is present
        name -- Name of new account
        description -- User description of new account
        type -- % or fixed, affects whole account actions
        amount -- % or fixed amount for whole account actions
        gross -- Affects gross amount
        user -- User object to which this account belongs to

        """
        DatabaseObject.__init__(self, table=account_table['table'],
                                id_column=account_table['id'], id=account_id)
        if self.id is None:
            self.name = name
            self.description = description
            self.type = type
            self.amount = amount
            self.gross = gross
            self.total = 0.00
            self.status = False
            self.user = user

    (get_total, set_total, del_total) = \
                DatabaseObject.accessors(account_table['total'])
    total = property(get_total, set_total, del_total, 'Current balance')

    (get_user, set_user, del_user) = \
               DatabaseObject.accessors(account_table['user'])
    user = property(get_user, set_user, del_user, 'Owner of account')

    (get_name, set_name, del_name) = \
               DatabaseObject.accessors(account_table['name'])
    name = property(get_name, set_name, del_name, 'Account name')

    def modify_name(self):
        """Change the name for a particular subaccount.

        Returns:
        status of login name modification

        """
        status = 'Kept existing login name'
        if self.name is not None:
            print '\nExisting name: %s' % self.name
            temporary_name = _handle_input('New name: ')
            if temporary_name.lstrip() != '':
                if _confirm(prompt='Change name from %s to %s?' % (self.name,
                                             temporary_name), default=True):
                    self.name = temporary_name
                    status = 'Name changed'
        else:
            self.name = _ask_string('Name for the account: ')
            status = 'Created new login name'
        return status

    (get_desc, set_desc, del_desc) = \
        DatabaseObject.accessors(account_table['description'])
    description = property(get_desc, set_desc, del_desc, 'Account description')

    def modify_description(self):
        """Get a new description for a particular subaccount.

        Returns:
        status of description change

        """
        status = 'Kept existing description'
        try:
            if self.description is not None:
                print 'Existing description: %s' % self.description
                temporary_description = _ask_string('New description? ')
                prompt = ('Change description from %s to %s?' % 
                          (self.description, temporary_description))
                if _confirm(prompt=prompt, default=True):
                    self.description = temporary_description
                    status = 'Description changed'
            else:
                self.description = _ask_string()
                status = 'Now have an account description'
        except MenuError:
            pass
        return status

    (_get_stat, _set_stat, del_status) = \
                DatabaseObject.accessors(account_table['status'])

    def get_status(self):
        """Convert database value for status into readable string.

        Returns:
        True if active, False otherwise

        """
        if self._get_stat() == account_table['active']:
            return True
        else:
            return False

    def set_status(self, status):
        """Convert boolean status assignment into a specified database value.

        Keyword arguments:
        status -- Boolean value for active state

        """
        if bool(status):
            new_status = account_table['active']
        else:
            new_status = account_table['inactive']
        self._set_stat(new_status)

    status = property(get_status, set_status, del_status, 'Active state')

    def modify_status(self):
        """Prompt to flip the status of an existing subaccount

        Returns:
        status string of change

        """
        status = 'Kept existing account status'
        if self.status:
            if _confirm(prompt='Deactivate account?', default=False):
                self.status = False
                status = 'Deactivated account'
        else:
            if _confirm(prompt='Activate account?', default=True):
                self.status = True
                status = 'Activated account'
        return status

    (get_type, set_type, del_type) = \
               DatabaseObject.accessors(account_table['type'])

    type = property(get_type, set_type, del_type, '% or fixed')

    def modify_type(self):
        """Change the type of the account, used for whole account actions.

        Returns:
        status of modification

        """
        if self.type is not None:
            status = 'Kept existing type'
            if self.type == account_table['percentage_type']:
                if _confirm(prompt='Change to fixed amount?', 
                                 default=True):
                    self.type = account_table['fixed_type']
                    status = 'Changed type to fixed amount'
            else:
                if _confirm(prompt='Change to percentage amount?', 
                                 default=True):
                    self.type = account_table['percentage_type']
                    status = 'Changed type to percentage amount'
        else:
            new_type_status = ''
            while self.type is None:
                prompt = ('Type:\n1 - Percentage\n'
                          '2 - Fixed\n%s\n%s\nChoice: ' %
                          (meta_actions, new_type_status))
                new_type_status = ''
                choice = _handle_input(prompt)
                if choice == '1':
                    self.type = account_table['percentage_type']
                    status = 'Type is now percentage'
                elif choice == '2':
                    self.type = account_table['fixed_type']
                    status = 'Type is now fixed'
                else:
                    new_type_status = 'Invalid choice'
        return status

    (_get_amt, _set_amt, del_amount) = \
               DatabaseObject.accessors(account_table['amount'])

    def get_amount(self):
        """Return amount specified for whole account transactions

        Returns:
        Fraction (zero to 1) for percentage types, value specified otherwise

        """
        temporary_amount = self._get_amt()
        if self.type == account_table['percentage_type']:
            temporary_amount = float(temporary_amount) / 100
        return round(temporary_amount, 4)

    def set_amount(self, amount):
        """Pretend like whole numbers can be percentages.

        Keyword arguments:
        amount -- The amount to assign to the account.
        
        """
        self._set_amt(round(amount, 2))
        
    amount = property(get_amount, set_amount, del_amount, '% or fixed value')

    def modify_amount(self, loop=False, type_change=False):
        """Change the amount for this account, whether percentage or fixed.

        Keyword arguments:
        loop -- Continue to loop until the user modifies the amount 
            (default False)
        type_change -- Whether have to change the amount because the account
            type changed (default False)

        Returns:
        status of amount modification

        """
        prompt = ''
        status = 'Kept existing amount'
        if self.amount is not None:
            if not type_change:
                # Overwrite parameter if subaccount object is passed
                if self.type == account_table['percentage_type']:
                    display_amount = '%s%%' % (self.amount * 100)
                else:
                    display_amount = '$%s' % self.amount
                prompt += 'Existing Amount: %s\n' % display_amount
                if self.gross:
                    modifies = 'Gross'
                else:
                    modifies = 'Net'
                prompt += 'Modifies: %s\n' % modifies
            else:
                prompt += 'Type changed, modify amount\n'
        else:
            prompt = 'No existing amount\n'
        if self.type == account_table['percentage_type']:
            prompt += 'Percentage for whole account actions: '
        else:
            prompt += 'Fixed amount (dollars) for whole account actions: '
        while 1:
            temporary_amount = _ask_amount(prompt)
            if (self.type == account_table['percentage_type'] and
                not 0 <= temporary_amount <= 100):
                print 'Out of range! (Must be in the range 0-100)'
                continue
            if self.type == account_table['percentage_type']:
                display_amount = '%0.2f%%' % temporary_amount
            else:
                display_amount = '$%0.2f' % temporary_amount
            confirm_prompt = 'Use %s for the amount? ' % display_amount
            if _confirm(prompt=confirm_prompt, default=True):
                self.amount = temporary_amount
                status = 'Amount changed'
                break
            elif not loop:
                break
        return status

    (_get_gross, _set_gross, del_gross) = \
                 DatabaseObject.accessors(account_table['gross'])

    def get_gross(self):
        """Convert database values for affecting the gross (vs net).

        Returns:
        True if affect gross, False if affect net

        """
        gross = self._get_gross()
        if gross is not None:
            if gross == account_table['gross_true']:
                return True
            else:
                return False
        else:
            return None

    def set_gross(self, gross):
        """Convert a boolean to one of the allowed values for the gross volume.

        Keyword arguments:
        gross -- Whether whole account actions will use this account on the
            gross amount or the net

        """
        if gross is not None:
            if bool(gross):
                affect_gross = account_table['gross_true']
            else:
                affect_gross = account_table['gross_false']
        else:
            affect_gross = None
        self._set_gross(affect_gross)

    gross = property(get_gross, set_gross, del_gross, 'Affect gross income')

    def modify_gross(self):
        """Modify whether this account affects the gross amount (vs net)

        Returns:
        status of modification to gross vs net

        """
        status = 'Kept existing setting for affecting the gross amount'
        if debug: print 'gross value: %s' % self.gross
        if self.gross is not None:
            if not self.gross:
                if _confirm(prompt='Affect the gross amount (on whole account'
                            ' actions)?', default=True):
                    self.gross = True
                    status = 'Now affecting the gross amount'
            else:
                if _confirm(prompt='Affect the net amount (on whole account '
                            'actions)?', default=True):
                    self.gross = False
                    status = 'Now affecting the net amount'
        else:
            new_gross_status = ''
            while self.gross is None:
                prompt = ('For whole account actions, affect:\n1 - Gross\n'
                          '2 - Net\n%s\n%s\n\nChoice: ' % (meta_actions, 
                                                           new_gross_status))
                new_gross_status = ''
                choice = _handle_input(prompt)
                if choice == '1':
                    self.gross = True
                    status = 'Now affecting the gross amount'
                elif choice == '2':
                    self.gross = False
                    status = 'Now affecting the net amount'
                else:
                    new_gross_status = 'Invalid choice'
        return status
        
    def save(self):
        """Store the details of the account in the database.
        """
        if self.id is None:
            self.status = True
            insertions = []
            for column_name, value in self.dirty.iteritems():
                if isinstance(value, DatabaseObject):
                    insertions.append((column_name, value.id))
                else:
                    insertions.append((column_name, value))
            query, arguments = insert(insertions, account_table['table'])
            connector(query, arguments)
            self.dirty = {}
            query = 'SELECT last_insert_rowid()'
            self.id = int(connector(query).fetchone()[0])
        else:
            updates = []
            for column_name, value in self.dirty.iteritems():
                if isinstance(value, DatabaseObject):
                    update.append((column_name, value.id))
                else:
                    updates.append((column_name, value))
                # optimization over just clearing cache
                self.cache[column_name] = value 
            if updates:
                query, arguments = update(updates,
                                          account_table['table'],
                                          [(account_table['id'], self.id)])
                connector(query, arguments)
                self.dirty = {}

    def __str__(self):
        string_repr = '%sAccount: %s\n' % (self.indent, self.name)
        string_repr += '%sDescription: %s\n' % (self.indent, self.description)
        string_repr += '%sBalance: $%0.2f\n' % (self.indent, self.total)
        string_repr += '%sType: %s\n' % (self.indent, self.type)
        if self.type == account_table['percentage_type']:
            display_amount = self.amount * 100
            string_repr += '%sAmount: %s%%\n' % (self.indent, display_amount)
        else:
            string_repr += '%sAmount: $%0.2f\n' % (self.indent, self.amount)
        string_repr += '%sAffect Gross: %s\n' % (self.indent, self.gross)
        if self.status:
            status = 'Active'
        else:
            status = 'Inactive'
        string_repr += '%sStatus: %s\n' % (self.indent, status)
        return string_repr


class User(DatabaseObject):

    def __init__(self, user_id=None, name=None, whole=False, deductions=None,
                 accounts=None):
        """Initialize a user object from a unique ID.

        Keyword arguments:
        user_id -- Unique ID of user in database (default None if new user)
        name -- Login name (default None)
        whole -- Prompt for whole account actions (default False)
        deductions -- List of deductions to use (default None)
        accounts -- List of Account objects (default None)

        """
        DatabaseObject.__init__(self, table=user_table['table'],
                                id_column=user_table['id'], id=user_id)
        if user_id is None:
            self.name = name
            self.whole_account_actions = whole
            self.deductions = deductions
            self.accounts = accounts
            self.timestamp = None

    (get_name, set_name, del_name) = \
               DatabaseObject.accessors(user_table['name'])
    name = property(get_name, set_name, del_name, 'Name of the user')

    def modify_name(self):
        """Change the name that is used to login to the account.

        Returns:
        status message of change

        """
        print 'Current login name: %s' % self.name
        status = 'Keeping existing login name'
        try:
            new_name = _handle_input('New login name: ')
            if _confirm(prompt='Change login name to %s?' % new_name,
                        default=True):
                self.name = new_name
                status = 'Changed login name to %s' % new_name
        except MenuError:
            pass
        return status

    (_get_whole, _set_whole, del_whole) = \
                 DatabaseObject.accessors(user_table['whole_account'])

    def get_whole(self):
        """Return setting for prompting user to perform whole account actions.

        Returns:
        True if prompt for whole account actions, False otherwise

        """
        if self._get_whole() == user_table['whole_account_true']:
            return True
        else:
            return False

    def set_whole(self, status):
        """Assign database values for user setting for whole account actions.

        Keyword arguments:
        status -- Boolean value to perform whole account actions

        """
        if bool(status):
            new_status = user_table['whole_account_true']
        else:
            new_status = user_table['whole_account_false']
        self._set_whole(new_status)

    whole_account_actions = property(get_whole, set_whole, del_whole,
                                     'Perform whole account actions')

    def modify_whole(self):
        """Change whether user is prompted for whole account actions.

        Returns:
        status of modification
        
        """
        status = 'Keeping user\'s existing setting for whole account actions'
        if self.whole_account_actions:
            if _confirm(prompt='Deactivate whole account actions?',
                        default=False):
                self.whole_account_actions = False
                status = 'Deactivated whole account actions'
        elif _confirm(prompt='Activate whole account actions?', default=True):
            self.whole_account_actions = True
            status = 'Activated whole account actions'
        return status
    
#TODO figure out if disabling prompting for modifying the gross amount is desirable

#     (_get_gross, _set_gross, del_gross) = \
#                  DatabaseObject.accessors(user_table['gross'])

#     def get_gross(self):
#         """Return setting for prompting user to modify the gross amount.

#         Returns:
#         True if prompt to modify gross, False otherwise

#         """
#         if self._get_gross() == user_table['gross_true']:
#             return True
#         else:
#             return False

#     def set_gross(self, gross):
#         """Assign database values for user setting for modifying gross.

#         Keyword arguments:
#         status -- Boolean value for whether to prompt to modify gross

#         """
#         if bool(gross):
#             new_gross = user_table['gross_true']
#         else:
#             new_gross = user_table['gross_false']
#         self._set_gross(new_gross)

#     prompt_for_gross = property(get_gross, set_gross, del_gross,
#                                 'Prompt to affect gross amount')

    (_get_stat, _set_stat, del_status) = \
                DatabaseObject.accessors(user_table['status'])

    def get_status(self):
        """Convert the database status into a string.
        
        Returns:
        True if user is active, False otherwise

        """
        if self._get_stat() == user_table['active']:
            return True
        else:
            return False

    def set_status(self, status):
        """Assign new status to the user account.
        
        Keyword arguments:
        status -- Boolean for active state of user

        """
        if bool(status):
            new_status = user_table['active']
        else:
            new_status = user_table['inactive']
        self._set_stat(new_status)

    status = property(get_status, set_status, del_status, 'Active status')
    
    def modify_status(self):
        """Prompt to flip the status of the user.

        Returns:
        status message of change

        """
        changed = False
        if self.status:
            if _confirm(prompt='Deactivate user?', default=False):
                self.status = False
                status = 'Deactivated user'
                changed = True
        else:
            if _confirm(prompt='Activate user?', default=True):
                self.status = True
                status = 'Activated user'
                changed = True
        if not changed:
            status = 'Keeping user\'s existing status'
        return status

    (get_time, set_time, del_time) = \
               DatabaseObject.accessors(user_table['timestamp'])
    timestamp = property(get_time, set_time, del_time, 'Previous login time')

    # Class properties for parsing/converting deduction string in database
    deduction_delimiter = ';'
    deduction_separater = ':'
    (_get_ded, _set_ded, del_ded) = \
               DatabaseObject.accessors(user_table['deductions'])
    def get_ded(self):
        """Parse deductions in database and convert to a list of tuples.

        Deductions in database should be stored as a continuous list of:
        <amount>:<description>;

        Example:
        10:Taxes;20:More taxes;
        
        Deductions are currently only allowed to be a fixed amount.  
        Allowing percentage amounts is a possibility in the future.

        Returns:
        List of (amount, description) tuples

        """
        all_deductions = self._get_ded()
        deductions = []
        while all_deductions.find(self.deduction_delimiter) > 0:
            separater_index = all_deductions.find(self.deduction_separater)
            delimiter_index = all_deductions.find(self.deduction_delimiter)
            amount = float(all_deductions[:separater_index])
            description = all_deductions[separater_index+1:delimiter_index]
            deductions.append((amount, description))
            all_deductions = all_deductions[delimiter_index+1:]
        return deductions

    def set_ded(self, new_deductions):
        """Convert list of deductions into the proper format.

        Keyword arguments:
        new_deductions -- List of (amount, description) tuples

        """
        deductions = ''
        if new_deductions is not None:
            for amount, description in new_deductions:
                deductions += '%0.2f%s%s%s' % (amount,
                                       self.deduction_separater,
                                       description, self.deduction_delimiter)
        self._set_ded(deductions)

    deductions = property(get_ded, set_ded, del_ded, 'Saved deductions')

    def reconfigure_deductions(self, deductions):
        """Reconfigure the existing deductions.

        Keyword arguments:
        deductions -- List of (amount, description) deductions that are existing
        
        Returns:
        deductions -- List of (amount, description) tuples to be used as a
            user's deductions
        
        """
        deduction_choices = {}
        for counter, (amount, description) in zip(range(1, len(deductions)+1),
                                                  deductions):
            deduction_choices[counter] = (amount, description)
        status = ''
        while 1:
            clear_screen()
            prompt = 'Deductions:\n\n'
            for counter in range(1, len(deductions)+1):
                amount, description = deduction_choices[counter]
                prompt += '%d - $%0.2f (%s)\n' % (counter, amount, description)
            prompt += ('n - New Deduction\n%s\n%s\n\nModify: ' % (meta_actions,
                                                                  status))
            status = ''
            try:
                choice = _handle_input(prompt)
            except MenuError:
                break
            if choice.upper() == 'N':
                amount = _ask_amount()
                description = _ask_string()
                if _confirm('Add deduction: $%0.2f (%s)?' % (amount,
                                                             description)):
                    deduction_choices[len(deductions)+1] = (amount, description)
#                    status = 'Deduction added'
                    break
            elif int(choice) in deduction_choices:
                amount, description = deduction_choices[int(choice)]
                inner_prompt = ('1 - Change Amount ($%0.2f)\n'
                                '2 - Change Description (%s)\n'
                                '3 - Delete\n\nChoice: ' % 
                                (amount, description))
                try:
                    option = _handle_input(inner_prompt)
                except MenuError:
                    continue
                status = 'Deduction unchanged'
                if option == '1':
                    new_amount = _ask_amount()
                    if _confirm('Change amount from $%0.2f to $%0.2f?' %
                                (amount, new_amount)):
                        deduction_choices[int(choice)] = (new_amount, description)
#                        status = 'Deduction amount changed'
                        break
                elif option == '2':
                    new_description = _ask_string()
                    if _confirm('Change description from "%s" to "%s"?' %
                                (description, new_description)):
                        deduction_choices[int(choice)] = (amount, new_description)
#                        status = 'Deduction description changed'
                        break
                elif option == '3' and _confirm('Are you sure that you want '
                                          'to delete this deduction:\n%s - %s\n' %
                                          (amount, description), default=False):
                    del deduction_choices[int(choice)]
#                    status = 'Deduction deleted'
                    break
            else:
                status = 'Invalid Choice'
        deductions = []
        for k, v in deduction_choices.iteritems():
            deductions.append(v)
        return deductions
        
    def modify_deductions(self):
        """Modify the user's saved deductions by prompting for a new list.

        Returns:
        Status of deduction modification

        """
        existing_deductions = self.deductions
        prompt = ('Deductions Menu:\n\n1 - Create New List\n'
                  '2 - Modify Existing\n%s\n\nAction: ' % meta_actions)
        status = 'Kept existing deductions'
        while 1:
            clear_screen()
            try:
                action = _handle_input(prompt)
                if action == '1' or len(self.deductions) == 0:
                    self.deductions = self.ask_deduction_list(prompt=('Please '
                                     'provide a list of default deductions'))
                elif action == '2':
                    self.deductions = self.reconfigure_deductions(self.deductions)
            except MenuError:
                break
            if existing_deductions != self.deductions:
                status = 'Deductions changed'
                break
        return status
            
    def ask_deduction_list(self, prompt=('Please provide a list of deductions '
                                         'that you would like to make')):
        """Prompt the user for their list of deductions

        Keyword arguments:
        prompt -- Prompt to present to the user

        Returns:
        List of deductions if approved, empty otherwise

        """
        satisfied = False
        status = prompt
        while not satisfied:
            deductions = []
            while 1:
                clear_screen()
                prompt = ('Deduction Menu:\n1 - Add Deduction\n'
                          '2 - Print Deductions\n3 - Start Over'
                          '\n%s\n%s\n\nInput: ' % (meta_actions, status))
                status = ''
                try:
                    choice = _handle_input(prompt)
                except MenuError:
                    break
                if choice == '1':
                    amount = _ask_amount()
                    description = _ask_string()
                    prompt = 'Deduct %0.2f (%s)?' % (amount, description)
                    if _confirm(prompt=prompt, default=True):
                        deductions.append((amount, description))
                        status = 'Deduction added'
                    else:
                        status = 'No deduction added'
                elif choice == '2':
                    clear_screen()
                    for amount, description in deductions:
                        print '$%0.2f - %s' % (amount, description)
                    raw_input(continue_string)
                elif choice == '3':
                    deductions = []
                    status = 'Deductions cleared'
            full_list = 'Deductions:\n'
            if deductions:
                for amount, description in deductions:
                    full_list += '%0.2f - %s\n' % (amount, description)
                full_list += ('Are you sure that you want to '
                              'use these deductions?')
            else:
                full_list = ('Are you sure that you don\'t want any '
                             'deductions at this time?')
            if _confirm(prompt=full_list, default=True):
                satisfied = True
            else:
                deductions = []
                if not _confirm(prompt='Start over?', default=True):
                    satisfied = True
        return deductions
            
    def get_accounts(self):
        """Get all of self's active accounts.

        Returns:
        List of Account objects belonging to this user

        """
        if account_table['id'] not in self.cache:
            query, parameters = select([account_table['id']],
                                       account_table['table'],
                                       [(account_table['user'], self.id)])
            self.cache[account_table['id']] = \
                                      [account_by_id(row[account_table['id']])
                                       for row in connector(query, parameters)]
        return self.cache[account_table['id']]

    def set_accounts(self, accounts):
        """Save each of the user's accounts with the new information.

        Keyword arguments:
        accounts -- List of Account objects that are modified
        
        """
        if accounts is not None:
            for account in accounts:
                account.save()
        self.cache[account_table['id']] = accounts
      
    accounts = property(get_accounts, set_accounts, doc='User\'s accounts')

    def _reconfigure_subaccounts(self, new_subaccount=None):
        """Modify amounts for accounts to maintain requirements.

        Keyword arguments:
        new_subaccount -- New subaccount that is being added 
            (default None the reconfigure all subaccounts)

        Returns:
        Complete list of user's Account objects
        
        """
        gross_accounts = self.filter_accounts(fixed=False, gross=True)
        if debug:
            print 'Gross %%:\n%s\n' % gross_accounts
        net_accounts = self.filter_accounts(fixed=False, gross=False)
        if debug:
            print 'Net %%:\n%s\n' % net_accounts
        completed_accounts = self.filter_accounts(fixed=True, percentage=False)
        if debug:
            print 'Fixed accounts:\n%s\n' % completed_accounts
        if new_subaccount is not None:
            if new_subaccount.gross:
                gross_accounts.append(new_subaccount)
            else:
                net_accounts.append(new_subaccount)
        account_types = [(True, gross_accounts), (False, net_accounts)]

        # Looping through both gross and net is necessary for certain situations
        # (e.g., modifying an account from gross to net)
        for gross_status, accounts in account_types:
            if gross_status:
                initial_prompt = ('Reconfigure Account Amounts\n\nModify the '
                    'gross percentage accounts so that they are under 100%\n')
            else:
                initial_prompt = ('Reconfigure Account Amounts\n\nModify the '
                    'net percentage accounts so that they are exactly 100%\n')
            # Maintain temporary dictionary before save is confirmed
            temporary_accounts = {}
            for index, account in zip(range(len(accounts)), accounts):
                temporary_accounts[index+1] = account
            status = ''
            # Mimic a do-while loop since always need to total up amounts
            while 1:
                total = 0.00
                prompt = initial_prompt
                for index in temporary_accounts:
                    prompt += ('%d - %s (%0.2f%%)\n' %
                               (index, temporary_accounts[index].name,
                                temporary_accounts[index].amount*100))
                    total += temporary_accounts[index].amount
                if (len(temporary_accounts) == 0 or
                    (not gross_status and total == 1.00) or
                    (gross_status and total <= 1.00)):
                    break
                else:
                    prompt += 'Total:%0.2f\n%s\nModify: ' % (total*100, status)
                    choice = _handle_input(prompt, float)
                    if choice in temporary_accounts:
                        account_name = temporary_accounts[choice].name
                        try:
                            new_amount = _ask_amount()
                            if _confirm('Use %0.2f for \'%s\'' %
                                        (new_amount, account_name), True):
                                temporary_accounts[choice].amount = new_amount
                                status = '\'%s\' modified' % (account_name)
                        except MenuError:
                            status = 'Canceled change, continue to reconfigure'
                    else:
                        status = 'Invalid choice'
            completed_accounts += [temporary_accounts[key]
                                   for key in temporary_accounts]
        return completed_accounts, 'Subaccounts reconfigured'

    def filter_accounts(self, fixed=True, percentage=True, gross=None, 
                        active_only=True, id=None):
        """Get a filtered list of accounts for the user.
    
        Keyword arguments:
        fixed - Retrieve the accounts with a fixed transaction amount
            (default True)
        percentage -- Retrieve the accounts with a percentage
            transaction amount (default True)
        gross -- Modifies the gross amount (rather than the net amount), only
            applicable if this is a percentage amount type (default None
            will ignore gross setting)
        active_only -- Only return the active accounts (default True)
        id -- Get a specific account, uses less objects and therefore less
            database retrievals (default None)

        Returns:
        List of Account objects for parameters or a single Account object
            for a specified id
        
        """
        if id is None:
            accounts = [acct for acct in self.accounts
            if ((fixed and acct.type == account_table['fixed_type']) or
                (percentage and acct.type == account_table['percentage_type']))
            if (gross == acct.gross or gross is None)
            if (not active_only or acct.status)]
        else:
            accounts = [acct for acct in self.accounts if acct.id == id].pop()
        return accounts

    def get_transactions(self, limit=10, restrict_type=None, subaccount=None,
                         order_by_most_recent=True, keyword_list=None,
                         begin_date=None, end_date=None, root_id=None):
        """Retrieve a list of the user's transactions

        Keyword arguments:
        limit -- Limit on the number of returned values (default 10)
        restrict_type -- Restrict transactions by action (default None)
        account -- Account object to search for
        order_by_most_recent -- Order the returned values (default True)
        keyword_list -- List of terms to search for in the description
        begin_date -- A datetime.datetime object for the start of
            the date range
        end_date -- A datetime.datetime object for the end of the date
            range
        root_id -- Retrieve group of transactions with this root_id
            (default None)
            
        Returns:
        List of (root_transaction, list of Transaction objects)

        """
        date_format = '%Y-%m-%d'
        filters = [(transaction_table['user'], self.id)]
        if restrict_type is not None:
            if (restrict_type != transaction_table['deposit'] and
                restrict_type != transaction_table['withdrawal'] and
                restrict_type != transaction_table['deduction']):
                raise TypeError('Invalid transaction action')
            filters.append((transaction_table['action'], restrict_type))
        if subaccount is not None:
            if not isinstance(subaccount, Account):
                raise TypeError('Invalid account object')
            filters.append((transaction_table['account'], subaccount.id))
        if begin_date is not None:
            filters.append(('>=', transaction_table['date'],
                            begin_date.strftime(date_format)))
        if end_date is not None:
            filters.append(('<=', transaction_table['date'],
                            end_date.strftime(date_format)))
        if root_id is not None:
            filters.append((transaction_table['root_id'], root_id))
        if order_by_most_recent is not None:
            if order_by_most_recent:
                order = '%s DESC' % transaction_table['date']
            else:
                order = '%s ASC' % transaction_table['date']
        query, arguments = select([transaction_table['root_id'],
                                   transaction_table['id']],
                                  transaction_table['table'],
                                  filters=filters,
                                  order=[order],
                                  group=[transaction_table['root_id']],
                                  limit=limit)
        root_transactions = []
        for row in connector(query, arguments):
            root_id = row[transaction_table['root_id']]
            root_transaction = Transaction(\
                id=int(row[transaction_table['root_id']]))
            query, arguments = select([transaction_table['id']],
                                      transaction_table['table'],
                                      [(transaction_table['root_id'], root_id),
                                       ('<>', transaction_table['id'],
                                        root_transaction.id)])
            root_group = []
            for row in connector(query, arguments):
                transaction = Transaction(id=int(row[transaction_table['id']]))
                root_group.append(transaction)
            root_transactions.append((root_transaction, root_group))
        return root_transactions
    transactions = property(get_transactions, doc='List of transactions')

    def save(self):
        """Save the changes that were made to the User object.
        """
        insertions = []
        updates = []
        if self.id is None:
            for column_name, value in self.dirty.iteritems():
                if isinstance(value, DatabaseObject):
                    insertions.append((column_name, value.id))
                else:
                    insertions.append((column_name, value))
            query, arguments = insert(insertions, user_table['table'])
            connector(query, arguments)
            query = 'SELECT last_insert_rowid()'
            self.id = int(connector(query).fetchone()[0])
        else:
            for column_name, value in self.dirty.iteritems():
                if isinstance(value, DatabaseObject):
                    updates.append((column_name, value.id))
                else:
                    updates.append((column_name, value))
                # optimization over just clearing cache
                self.cache[column_name] = value 
            if updates:
                query, arguments = update(updates, user_table['table'],
                                          [(user_table['id'], self.id)])
                connector(query, arguments)
        self.dirty = {}
    def __str__(self):
#TODO print deductions?
        string_repr = '%sUser: %s\n' % (self.indent, self.name)
        string_repr += '%sUse Whole Account Actions: %s\n' % (self.indent,
                                                    self.whole_account_actions)
#         string_repr += '%sPrompt To Affect Gross Amount: %s\n' % (self.indent,
#                                                          self.prompt_for_gross)
        string_repr += '%sLast login: %s\n' % (self.indent, self.timestamp)
        string_repr += '%sAccounts:\n\n' % self.indent
        for account in self.accounts:
            string_repr += '%s%s\n' % (self.indent, account)
        if self.status:
            user_status = 'Active'
        else:
            user_status = 'Inactive'
        string_repr += '%sStatus: %s\n' % (self.indent, user_status)
        return string_repr


class Transaction(DatabaseObject):

    def __init__(self, user=None, amount=None, date=None, description=None,
                 action=None, account=None, root_id=None, id=None):
        """This is the base transaction when no side effect is required.

        Keyword arguments:
        id -- Unique ID of the transaction in the database
        user_id -- User for whom the transaction is for
        amount -- Dollar amount of transaction (default 0.00)
        account -- Account of the user
        date -- Datetime.date object representing transaction date
        description -- User description of transaction details (default None)

        """
        try:
            DatabaseObject.__init__(self, table=transaction_table['table'],
                                    id_column=transaction_table['id'], id=id)
        except ValueError:
            DatabaseObject.__init__(self, table=transaction_table['table'],
                                    id_column=transaction_table['id'])
        if self.id is not None:
            query, parameters = select([transaction_table['date'],
                                        transaction_table['user'],
                                        transaction_table['account'], 
                                        transaction_table['amount'],
                                        transaction_table['action'],
                                        transaction_table['description'],
                                        transaction_table['root_id']],
                                       transaction_table['table'],
                                       [(transaction_table['id'], id)])
            row = connector(query, parameters).fetchone()
            temporary_date = str(row[transaction_table['date']])
            self.date = datetime.date(int(temporary_date[0:4]),
                                      int(temporary_date[5:7]),
                                      int(temporary_date[8:10]))
            self.user = user_by_id(int(row[transaction_table['user']]))
            self.amount = float(row[transaction_table['amount']])
            self.action = str(row[transaction_table['action']])
            self.description = str(row[transaction_table['description']])
            self.root_id = int(row[transaction_table['root_id']])
            if row[transaction_table['account']] is not None:
                self.account = self.user.filter_accounts(
                    id=int(row[transaction_table['account']]))
            else:
                self.account = None
        else:
            self.date = date
            if not isinstance(user, User):
                raise TypeError('Bad user for Transaction class')
            self.user = user
            self.original_amount = amount
            self.amount = amount
            self.description = description
            self.account = account
            self.root_id = root_id
            self.action = action

    (get_date, set_date, del_date) = \
                (DatabaseObject.accessors(transaction_table['date']))
    date = property(get_date, set_date, del_date, doc='Transaction date')

    (get_ts, set_ts, del_ts) = \
                (DatabaseObject.accessors(transaction_table['timestamp']))
    timestamp = property(get_ts, set_ts, del_ts, doc='Timestamp of input')

    (get_user, set_user, del_user) = \
                (DatabaseObject.accessors(transaction_table['user']))
    user = property(get_user, set_user, del_user, doc='User ID')
    
    (get_acct_id, set_acct, del_acct) = \
                (DatabaseObject.accessors(transaction_table['account']))

    def get_acct(self):
        """Stored in the database as an ID but need an object.
        """
        if transaction_table['account'] in self.dirty:
            return self.dirty[transaction_table['account']]
        if transaction_table['account'] not in self.cache:
            self.cache[transaction_table['account']] = \
                                            account_by_id(self.get_acct_id())
        return self.cache[transaction_table['account']]

    account = property(get_acct, set_acct, del_acct, doc='Account object')
    
    (get_amt, set_amt, del_amt) = \
                (DatabaseObject.accessors(transaction_table['amount']))
    amount = property(get_amt, set_amt, del_amt, doc='How much transacted')

    (get_act, set_act, del_act) = \
                (DatabaseObject.accessors(transaction_table['action']))
    action = property(get_act, set_act, del_act, doc='Transaction type')

    (get_desc, set_desc, del_desc) = \
                (DatabaseObject.accessors(transaction_table['description']))
    description = property(get_desc, set_desc, del_desc, doc='User described')

    (get_root, set_root, del_root) = \
                (DatabaseObject.accessors(transaction_table['root_id']))
    root_id = property(get_root, set_root, del_root, doc='Group by this ID')

    (get_stat, set_stat, del_status) = \
                (DatabaseObject.accessors(transaction_table['status']))

    def get_status(self):
        """Convert the database status of the transaction into a word.

        Returns:
        True if active, False otherwise

        """
        if self.get_stat() == transaction_table['active']:
            return True
        else:
            return False

    def set_status(self, status):
        """Assign new status to the transaction.
        
        Keyword arguments:
        status -- Boolean

        """
        if bool(status):
            new_status = transaction_table['active']
        else:
            new_status = transaction_table['inactive']
        self.set_stat(new_status)

    status = property(get_status, set_status, del_status, 'Active status')

    def _create_deductions(self, deductions):
        """Normalize list of deductions to Transaction objects

        Use the ID of the calling object (i.e., self) as the root ID
        of each of these deductions.

        Keyword arguments:
        deductions -- List of (amount, description) tuples

        Returns:
        total_deduction -- Sum of all deductions
        deductions -- List of Transaction objects, each a deduction

        """
        total_deduction = 0.00
        deduction_transactions = []
        if deductions is not None:
            for amount, description in deductions:
                total_deduction += amount
                deduction = Transaction(user=self.user, amount=amount,
                                        date=self.date, root_id=self.id,
                                        description=description,
                                        action=transaction_table['deduction'])
                deduction_transactions.append(deduction)
        return total_deduction, deduction_transactions

    def save(self):
        """Store the class variables into the database.
        """
        now = datetime.datetime.now()
        timestamp = '%s-%02d-%02d %02d:%02d:%02d' % (now.year, now.month,
                                 now.day, now.hour, now.minute, now.second)
        self.timestamp = timestamp
        insertions = []
        updates = []
        if self.id is None:
            self.status = True
            for column_name, value in self.dirty.iteritems():
                if isinstance(value, DatabaseObject):
                    insertions.append((column_name, value.id))
                else:
                    insertions.append((column_name, value))
            query, parameters = insert(insertions, transaction_table['table'])
            connector(query, parameters)
            query = 'SELECT last_insert_rowid()'
            self.id = int(connector(query).fetchone()[0])
            if self.root_id is None:
                self.root_id = self.id
            query, parameters = update([(transaction_table['root_id'],
                                         self.root_id)],
                                       transaction_table['table'],
                                       [(transaction_table['id'], self.id)])
            connector(query, parameters)
            if self.account is not None:
                if self.action == transaction_table['deposit']:
                    self.account.total += self.amount
                    self.account.save()
                elif self.action == transaction_table['withdrawal']:
                    self.account.total -= self.amount
                    self.account.save()
        else:
            for column_name, value in self.dirty.iteritems():
                if isinstance(value, DatbaseObject):
                    updates.append((column_name, value.id))
                else:
                    updates.append((column_name, value))
                # optimization over forcing user access to cache value
                self.cache[column_name] = value
            if updates:
                query, parameters = update(updates, transaction_table['table'],
                                          [(transaction_table['id'], self.id)])
                connector(query, parameters)
        self.dirty = {}
        
    def __str__(self):
        if self.action == transaction_table['deposit']:
            action_type = 'Deposit'
        elif self.action == transaction_table['withdrawal']:
            action_type = 'Withdrawal'
        elif self.action == transaction_table['deduction']:
            action_type = 'Deduction'
        elif self.action == transaction_table['transfer']:
            action_type = 'Transfer'
        else:
            action_type = 'Informational'
        string_repr = '%sAction: %s\n' % (self.indent, action_type)
        string_repr += '%sAmount: $%0.2f\n' % (self.indent, self.amount)
        string_repr += '%sTransaction Date: %s\n' % (self.indent, 
                                             self.date.strftime(output_date))
        if self.account is not None:
            acct = self.account.name
        elif (self.action == transaction_table['deduction'] or
              self.action == transaction_table['transfer']):
            acct = 'N/A'
        else:
            acct = 'Whole account'
        string_repr += '%sAccount: %s\n' % (self.indent, acct)
        string_repr += '%sDescription: %s\n' % (self.indent, self.description)
        try:
            if self.status:
                transaction_status = 'Active'
            else:
                transaction_status = 'Inactive'
        except TypeError:
            transaction_status = 'Unsaved'
        string_repr += '%sStatus: %s\n' % (self.indent, transaction_status)
        return string_repr


class Deposit(Transaction):

    def __init__(self, user, amount, date, description=None,
                     account=None, root_id=None, deductions=None):
        """An object representation of a deposit transaction.

        Keyword arguments:
        user -- Unique user account
        amount -- Amount of transaction
        date -- Date that transaction occurred
        description -- User description of transaction (default None)
        account -- Unique user subaccount 
            (default None - will split deposit according to database)
        root_id -- Transaction ID of the meta transaction (default None - it
            will be set to its own ID once it has been determined on INSERT)
        deductions -- A list of tuples representing deductions of the form
            (amount, description) (default None)

        For a 'whole account' deposit, will perform calculation and
        instantiation of subdeposits that each represent the parts of
        the whole deposit.

        When broken down, this results in a loop each for:
        1) Percentage amounts on the gross
        2) Fixed amounts on the net
        3) Percentage amounts on the net

        """
        Transaction.__init__(self, user=user, amount=amount, account=account,
                             description=description, root_id=root_id,
                             date=date, action=transaction_table['deposit'])
        self.deductions = deductions
        if self.deductions is not None:
            self.total_deduction, self.deductions = \
                Transaction._create_deductions(self, self.deductions)
        else:
            self.total_deduction = 0.00
            self.deduction = None

        if self.account is None:
            gross = running_total = self.amount
            self.subaccount_deposits = []
            for account in self.user.filter_accounts(fixed=False, gross=True):
                amount = gross * account.amount
                running_total -= amount
                subdeposit = Deposit(user=self.user, amount=amount,
                                     date=self.date, account=account, 
                                     description=self.description)
                self.subaccount_deposits.append(subdeposit)
            running_total -= self.total_deduction
            for account in self.user.filter_accounts(percentage=False):
                if running_total > 0:
                    running_total -= account.amount
                    subdeposit = Deposit(user=self.user, amount=account.amount,
                                         date=self.date, account=account, 
                                         description=self.description)
                    self.subaccount_deposits.append(subdeposit)
            if running_total > 0:
                net = running_total
                for account in self.user.filter_accounts(fixed=False,
                                                         gross=False):
                    amount = net * account.amount
                    running_total -= amount
                    subdeposit = Deposit(user=self.user, amount=amount,
                                         date=self.date, account=account,
                                         description=self.description)
                    self.subaccount_deposits.append(subdeposit)
            if debug: 
                print ('!!!!!\nTotal should be 0, actually: %s\n!!!!!' % 
                       running_total)
        self.amount -= self.total_deduction

    def save(self):
        """Save the transaction details and update the total in the database.
        """
        Transaction.save(self)
        if self.account is None:
            for subdeposit in self.subaccount_deposits:
                subdeposit.root_id = self.id
                subdeposit.save()
        if self.deductions is not None:
            for deduction in self.deductions:
                deduction.root_id = self.id
                deduction.save()

    def __str__(self):
        """Print out details of the deposit."""
        string_repr = Transaction.__str__(self)
        if self.account is None:
            string_repr += '%s%d subdeposits:\n' % (self.indent,
                                        len(self.subaccount_deposits))
            for subdeposit in self.subaccount_deposits:
                string_repr += ('%s  Deposit: $%0.2f - %s\n' % (self.indent,
                                subdeposit.amount, subdeposit.account.name))
        if self.original_amount != self.amount:
            string_repr += '%sOriginal Amount: $%0.2f\n' % (self.indent,
                                                    self.original_amount)
        if self.deductions is not None:
            for transaction in self.deductions:
                string_repr += ('%s  Deduction: $%0.2f - %s\n' % (self.indent,
                                transaction.amount, transaction.description))
        return string_repr


class Withdrawal(Transaction):

    def __init__(self, user, amount, date, description=None,
                     account=None, root_id=None, deductions=None):
        """An object representation of a withdrawal transaction.

        Keyword arguments:
        user -- A unique user account
        amount -- Amount of transaction
        date -- Date that transaction occurred
        description -- User description of transaction (default None)
        account -- Unique user sub-account 
            (default None - will split withdrawal according to database)
        root_id -- Transaction ID of the meta transaction (default None - it
            will be set to its own ID once it has been determined on INSERT)
        deductions -- A list of tuples representing deductions of the form
            (amount, description) (default None)

        """
        Transaction.__init__(self, user=user, amount=amount, account=account,
                             description=description, root_id=root_id,
                             date=date, action=transaction_table['withdrawal'])
        if deductions is not None:
            self.total_deduction, self.deductions = \
                Transaction._create_deductions(self, deductions)
        else:
            self.total_deduction = 0.00
            self.deductions = None

        if self.account is None:
            gross = running_total = self.amount
            self.subaccount_withdrawals = []
            for account in self.user.filter_accounts(fixed=False, gross=True):
                amount = gross * account.amount
                running_total -= amount
                subwithdrawal = Withdrawal(self.user, amount, self.date,
                                           self.description, account, self.id)
                self.subaccount_withdrawals.append(subwithdrawal)
            running_total -= self.total_deduction
            for account in self.user.filter_accounts(percentage=False):
                if running_total > 0:
                    running_total -= account.amount
                    subwithdrawal = Withdrawal(self.user, account.amount,
                                 self.date, self.description, account, self.id)
                    self.subaccount_withdrawals.append(subwithdrawal)
            if running_total > 0:
                net = running_total
                for account in self.user.filter_accounts(fixed=False,
                                                         gross=False):
                    amount = net * account.amount
                    running_total -= amount
                    subwithdrawal = Withdrawal(self.user, amount, self.date,
                                            self.description, account, self.id)
                    self.subaccount_withdrawals.append(subwithdrawal)
            if debug: 
                print ('!!!!!\nTotal should be 0, actually: %s\n!!!!!' % 
                       running_total)
        self.amount -= self.total_deduction

    def save(self):
        """Save the transaction details and update the total in the database.
        """
        Transaction.save(self)
        if self.account is None:
            for subwithdrawal in self.subaccount_withdrawals:
                subwithdrawal.root_id = self.id
                subwithdrawal.save()

    def __str__(self):
        """Print out details of the withdrawal."""
        string_repr = Transaction.__str__(self)
        if self.account is None:
            string_repr += ('%s%d subwithdrawals:\n' % (self.indent, 
                            len(self.subaccount_withdrawals)))
            for subwithdrawal in self.subaccount_withdrawals:
                string_repr += ('%s  Withdrew $%0.2f - %s\n' % (self.indent,
                            subwithdrawal.amount, subwithdrawal.account.name))
        if self.original_amount != self.amount:
            string_repr += '%sOriginal Amount: $%0.2f\n' % (self.indent,
                                                    self.original_amount)
        if self.deductions is not None:
            string_repr += '%sTotal Deduction: $%0.2f\n' % (self.indent,
                                                    self.total_deduction)
            for transaction in self.deductions:
                string_repr += ('%s  Applied $%0.2f - %s\n' % (self.indent,
                                transaction.amount, transaction.description))
        return string_repr


class Budse(object):

    def __init__(self, user):
        object.__init__(self)
        self.user = user
        self._status = ''
        
    def _get_status(self):
        """Reset the status after retrieving it."""
        status_string = self._status
        self._status = ''
        return status_string

    def _set_status(self, status):
        """Assign class-wide status"""
        self._status = status

    status = property(_get_status, _set_status, doc='Global application status')

    def search(self, keywords=None, limit=10, subaccount=None,
               most_recent=False, begin_date=None,
               end_date=None):
        """Search the database for matching transactions.

        Keyword arguments:
        keywords -- List of keyword(s) to search for (default None)
        limit -- Maximum size of return list (default 10)
        begin_date -- Datetime.date object inclusive
        end_date -- Datetime.date object inclusive
        subaccount -- Search particular subaccount (default None - search all)
        most_recent -- Order the most recent searches first (default True)

        Returns:
        A list of (root_transaction, [transaction_group]) tuples

        """
        #TODO 4 prompt user for parameters
        # specific transaction id
        # keywords
        # date

        # put prompting here and break out the parameterized function call
        # to another function
        return self.user.get_transactions(subaccount=subaccount, 
                                          order_by_most_recent=True,
                                          limit=limit, 
                                          keyword_list=keywords,
                                          begin_date=begin_date,
                                          end_date=end_date)
        
    def output_transactions(self, transactions):
        """Output a list of transactions.

        Keyword arguments:
        transactions -- List of Transaction objects to output
        
        """
        for root_transaction, group in transactions:
            print '-------Transaction ID: #%d-------' % root_transaction.id
            print root_transaction
            for item in group:
                item.indent = '   '
                print item

    def make_deposit(self):
        """Initiate a new deposit.
        
        Prompt the user for the necessary parameters for a deposit into
        either the entire account according to the user specifications 
        (i.e., the account types and amounts) or into a particular
        subaccount.

        """
        print 'Make A Deposit\n'
        try:
            date = self._ask_date()
            amount = _ask_amount()
            description = _ask_string()
            account = None
            if not self._transact_for_whole_account(is_deposit=True):
                account = self._ask_subaccount()
            deductions = None
            if (_confirm(prompt='Deduct from gross?')):
                if _confirm(prompt='Use stored deductions?'):
                    deductions = self.user.deductions
                else:
                    deductions = self.user.ask_deduction_list()
            new_deposit = Deposit(user=self.user, amount=amount, date=date,
                                  description=description, account=account,
                                  deductions=deductions)
            print '\n==  Deposit Details  ==\n%s' % new_deposit
            if _confirm(prompt='Execute deposit?', default=True):
                new_deposit.save()
                print 'new_deposit account: %s' % new_deposit.account
                if new_deposit.account is None:
                    target = 'Whole Account'
                else:
                    target = new_deposit.account.name
                self.status = ('Deposited $%0.2f into %s' %
                               (new_deposit.amount, target))
            else:
                new_deposit.discard()
                self.status = 'Deposit canceled'
        except MenuError:
            self.status = 'Deposit canceled'

    def make_withdrawal(self):
        """Initiate a new withdrawal.

        Prompt the user for the necessary parameters for a withdrawal 
        either from the entire account or from an individual subaccount.

        """
        print 'Make A Withdrawal\n'
        try:
            date = self._ask_date()
            amount = _ask_amount()
            description = _ask_string()
            account = None
            if not self._transact_for_whole_account(is_deposit=False):
                account = self._ask_subaccount()
            new_withdrawal = Withdrawal(user=self.user, amount=amount,
                                        date=date, description=description,
                                        account=account)
            print '\n== Withdrawal Details ==\n%s' % new_withdrawal
            if _confirm(prompt='Execute withdrawal?', default=True):
                new_withdrawal.save()
                if new_withdrawal.account is None:
                    target = 'Whole Account'
                else:
                    target = new_withdrawal.account.name
                self.status = ('Withdrew $%0.2f from %s' %
                               (new_withdrawal.amount, target))
            else:
                new_withdrawal.discard()
                self.status = 'Withdrawal canceled'
        except MenuError:
            self.status = 'Withdrawal canceled'

    def make_transfer(self):
        """Execute a transfer between subaccounts.
        
        Essentially this will just be a deposit and a withdrawal of the
        same amount, but the idea of a transfer is useful to the user
        because the action seems more atomic to them.

        Also the two actions can be grouped together with the same root_id
        so that an undo would yield the proper result.

        """
        print 'Transfer Between Subaccounts\n'
        date = datetime.date.today()
        try:
            self.print_balance(include_all=True, include_total=False)
            withdrawal_account = self._ask_subaccount(prompt='From: ')
            deposit_account = self._ask_subaccount(prompt='To: ')
            print ('From: %s (%0.2f)\nTo: %s (%0.2f)\n' % 
                   (withdrawal_account.name, withdrawal_account.total,
                    deposit_account.name, deposit_account.total))
            amount = _ask_amount()
            description = _ask_string()
            transfer = Transaction(user=self.user, amount=amount, date=date,
                                   action=transaction_table['transfer'],
                                   description=description)
            print '\n== Transfer Details ==\n%sFrom: %s\nInto: %s' % (transfer,
                                 withdrawal_account.name, deposit_account.name)
            if _confirm(prompt='Execute transfer?', default=True):
                transfer.save()
                transfer_id = transfer.id
                new_withdrawal = Withdrawal(user=self.user, amount=amount, 
                                            date=date, description=description,
                                            root_id=transfer_id,
                                            account=withdrawal_account)
                new_withdrawal.save()
                new_deposit = Deposit(user=self.user, amount=amount, date=date,
                                      description=description, 
                                      account=deposit_account,
                                      root_id=transfer_id)
                new_deposit.save()
                self.status = ('Completed transfer of $%0.2f from %s to %s\n'
                               % (transfer.amount, withdrawal_account.name,
                                  deposit_account.name))
            else:
                transfer.discard()
                self.status = 'Transfer canceled'
        except MenuError:
            self.status = 'Transfer canceled'
    
    def reverse_transaction(self, root_id):
        """Undo whatever effect a transaction group had.

        Keyword arguments:
        root_id -- The root ID that groups the entire transaction.
        
        """
        root_transaction, transactions = \
                          self.user.get_transactions(root_id=root_id)
        transactions.append(root_transaction)
        for transaction in transactions:
            if transaction.action == transaction_table['deposit']:
                transaction.account.total -= transaction.amount
            elif transaction.action == transaction_table['withdrawal']:
                transaction.account.total += transaction.amount
            transaction.status = False
            transaction.save()

    def print_balance(self, subaccount=None, include_total=True, 
                      include_all=False):
        """The balance of a specific subaccount

        Keyword parameters:
        subaccount -- Account object to get balance for (default None)
        include_total -- Whether or not to include the entire user total
            (default True)
        include_all -- Supercedes subaccount parameter and will print
            out all subaccount totals (default False)
        spacing -- Amount of spaces to pad with whitespace (default 16)

        """
        if subaccount is not None:
            if _confirm(prompt='Retrieve a subaccount balance'):
                try:
                    subaccount = self._ask_subaccount(
                        prompt='Get balance for which subaccount: ')
                except MenuError:
                    print 'Interrupted balance check'
                    return
            subaccount_total = '$%0.2f' % subaccount.total
            print '%s = %s' % (subaccount.name.ljust(longest_name), 
                               subaccount_total.rjust(longest_total))
        else:
            accounts = self.user.accounts
            account_totals = []
            longest_name = 0
            longest_total = 3
            user_total = 0.00
            for account in accounts:
                name_length = len(str(account.name))
                account_total = '%0.2f' % account.total
                account_totals.append((account.name, account_total))
                if name_length > longest_name:
                    longest_name = name_length
                if include_total:
                    user_total += account.total
                account_total_length = len(str(account_total))
                if account_total_length > longest_total:
                    longest_total = account_total_length
            if include_total:
                user_total_string = '%0.2f' % user_total
                user_total_length = len(str(user_total_string))
                if user_total_length > longest_total:
                    longest_total = user_total_length
            if include_all:
                print 'Account balances:'
                for account_name, account_total in account_totals:
                    print '%s = %s' % (account_name.ljust(longest_name),
                                       account_total.rjust(longest_total))
            if include_total:
                if include_all:
                    print (' ' * longest_name) + '   ' + ('-' * longest_total)
                print '%s = %s\n' % ('Total'.ljust(longest_name),
                                     user_total_string.rjust(longest_total))

    def create_report(self):
        """Prompt user for dates and output format to create a report from.

        """
        prompt = ('Create Report\n\n1 - Date Range\n%s\n%s\n\nChoice:' % 
                  (meta_actions, self.status))
        while 1:
            try:
                choice = _handle_input(prompt)
                if choice == '1':
                    self._create_report_by_date()
                    break
            except MenuError:
                return

    def _create_report_by_date(self, format='csv'):
        """Create a report for a specified date range.

        Keyword arguments:
        format -- How the report will be output (default csv)

        """
        timestamp_string = '%Y%m%d.%H%M%S'
        today = datetime.datetime.today()
        report_timestamp = datetime.datetime.now().strftime(timestamp_string)
        if today.day == 1:
            default = today + datetime.timedelta(month=-1)
        else:
            default = datetime.date(today.year, today.month, 1)
        begin_date = self._ask_date(prompt_for='start of report',
                                    default_date=default)
        end_date = self._ask_date(prompt_for='end of report')
        filename = 'Report_%s.csv' % report_timestamp
        prompt = 'Output report to %s/%s' % (os.getcwd(), filename)
        output_file = self._ask_filepath(filename=filename, prompt=prompt)
        delimiter = ','
        with open(output_file, 'w') as report_file:
            if format == 'csv':
                report_file.write('Account Name%sDeposits%s'
                                  'Withdrawals%sNet%s%s'
                                  'Report for %s - %s\n' %
                                   (delimiter, delimiter, delimiter,
                                    delimiter, delimiter,
                                   (begin_date.strftime(output_date)),
                                    (end_date.strftime(output_date))))
                root_transaction_groups = self.search(limit=None,
                                                      begin_date=begin_date,
                                                      end_date=end_date,
                                                      most_recent=False)
                account_summary = {}
                for account in self.user.accounts:
                    account_summary[account.id] = (account, 0.00, 0.00, 0.00)
                deductions = 0.00
                transaction_log = ('Transaction Log\n\n'
                                   'Date%sAction%sAmount%sAccount'
                                   '%sDescription\n' % (delimiter, 
                                   delimiter, delimiter, delimiter))
                for root_transaction, transactions in root_transaction_groups:
                    transactions.insert(0, root_transaction)
                    for transaction in transactions:
                        action = transaction.action
                        if transaction.account is not None:
                            account, deposits, withdrawals, net = \
                                     account_summary[transaction.account.id]
                            if action == transaction_table['deposit']:
                                deposits += transaction.amount
                                net += transaction.amount
                                output_action = 'Deposit'
                            elif action == transaction_table['withdrawal']:
                                withdrawals += transaction.amount
                                net -= transaction.amount
                                output_action = 'Withdrawal'
                            account_summary[transaction.account.id] = \
                                        (account, deposits, withdrawals, net)
                            account_name = transaction.account.name
                        elif action == transaction_table['deduction']:
                            deductions += transaction.amount
                            output_action = 'Deduction'
                            account_name = 'N/A'
                        elif action == transaction_table['transfer']:
                            account_name = 'N/A'
                            output_action = 'Transfer'
                        else:
                            output_action = 'Informational'
                            account_name = 'Whole Account'
                        transaction_log += ('%s%s%s%s%0.2f%s%s%s%s\n' % 
                                       (transaction.date.strftime(output_date),
                                        delimiter,
                                        output_action,
                                        delimiter,
                                        transaction.amount,
                                        delimiter,
                                        account_name,
                                        delimiter,
                                        transaction.description))
                total_deposits = total_withdrawals = total_net = 0.00
                for k, v in account_summary.iteritems():
                    account, deposits, withdrawals, net = v
                    report_file.write('%s%s%0.2f%s%0.2f%s%0.2f\n' %
                                      (account.name, delimiter,
                                       deposits, delimiter,
                                       withdrawals, delimiter,
                                       net))
                    total_deposits += deposits
                    total_withdrawals += withdrawals
                    total_net += net
                report_file.write('\n\nTotal Deposits:%s%0.2f\n'
                                  'Total Withdrawals:%s%0.2f\n'
                                  'Total Deductions:%s%0.2f\n\n'
                                  'Net for period:%s%0.2f\n'% 
                                  (delimiter, total_deposits,
                                   delimiter, total_withdrawals,
                                   delimiter, deductions,
                                   delimiter, total_net))
                report_file.write('\n\n%s' % transaction_log)

    def _ask_filepath(self, filename, prompt, default_path=os.getcwd()):
        """Prompt user for a location to output a file.

        Keyword arguments:
        filename -- Name of the file to output to
        prompt -- How to confirm the choices to the user
        default_path -- Default directory to use to output the file to
        
        """
        if _confirm(prompt=prompt, default=True):
            filepath = '%s/%s' % (default_path, filename)
        else:
            #TODO 3 prompt for filepath
            pass
        return filepath

    def modify_user_settings(self, clear):
        """Modify any of the user's settings.

        Keyword parameters:
        clear -- Function object to clear the screen

        Menu to access any of the saved settings for each user.

        """
        while 1:
            if self.user.status:
                status_modification = 'Deactivate User'
            else:
                status_modification = 'Activate User'
            prompt = ('User Preferences Menu\n\n'
                      '1 - Modify Existing Subaccounts\n'
                      '2 - Add New Subaccount\n3 - Login Name\n4 - %s\n'
                      '5 - Deductions\n6 - Whole Account Actions\n'
#                      '7 - Gross\n'
                      '%s\n%s\n\nAction: ') % (status_modification,
                                               meta_actions, self.status)
            clear_screen()
            try:
                action = _handle_input(prompt)
                if action == '1':
                    self.modify_subaccount()
                elif action == '2':
                    self.add_subaccount()
                elif action == '3':
                    self.status = self.user.modify_name()
                elif action == '4':
                    self.status = self.user.modify_status()
                elif action == '5':
                    self.status = self.user.modify_deductions()
                elif action == '6':
                    self.status = self.user.modify_whole()
#                elif action == '7':
#                    self._modify_user_gross()
                else:
                    self.status = 'Invalid action'
                self.user.save()
            except MenuError:
                break

#     def _modify_user_gross(self):
#         """Allow the user to turn off prompts dealing with gross/net.
#         """
#         existing_gross = self.user.gross
#         gross = None
#         if self.user.gross:
#             if _confirm(prompt='Deactivate prompts to affect gross?', 
#                              default=True):
#                 gross = False
#                 modify_status = 'Deactivated prompts for affecting gross'
#         else:
#             if _confirm(prompt='Activate prompts to affect gross?', 
#                              default=True):
#                 gross = True
#                 modify_status = 'Activated prompts for affecting gross'
#         if status is None:
#             modify_status = ('Keeping user\'s existing setting for affecting '
#                              'the gross amount')
#             status = active
#         return gross, modify_status

    
#     def _reconfigure_subaccount_amounts(self, subaccount, new=False):
#         """Modify amounts for accounts to maintain requirements.

#         Keyword arguments:
#         subaccount -- Reconfigure amounts based on this changed account
#         new -- Whether the account added was a new account (default False
#             account already existed)

#         Returns:
#         List of changed Account objects
        
#         """
#         if subaccount.type != account_table['percentage_type']:
#             accounts = self.user.accounts
#             accounts.append(subaccount)
#             return accounts
#         initial_prompt = 'Reconfigure Account Amounts\n\n'
#         if not subaccount.gross:
#             # Need to always keep net percentage accounts' total at 100%
#             accounts = self.user.filter_accounts(fixed=False)
#             initial_prompt += ('Modify the net percentage accounts so '
#                               'that they are exactly 100%\n')
#         else:
#             # Total them up, they cannot be 100% or greater
#             accounts = self.user.filter_accounts(fixed=False, gross=True)
#             initial_prompt += ('Modify the gross percentage accounts so '
#                               'that they are under 100%\n')
#         if new:
#             accounts.append(subaccount)

#         # Maintain temporary dictionary before save is confirmed
#         temporary_accounts = {}
#         for counter, account in zip(range(len(accounts)), accounts):
#             temporary_accounts[counter+1] = account
#         while 1:
#             total = 0.00
#             prompt = '%s\n' % initial_prompt
#             for counter in range(1, len(temporary_accounts)+1):
#                 prompt += ('%s - %s (%0.2f%%)\n' % (counter,
#                            temporary_accounts[counter].name,
#                            temporary_accounts[counter].amount * 100))
#                 total += temporary_accounts[counter].amount
#             prompt += 'Total:%0.2f\n%s\n\nModify: ' % (total*100, self.status)
#             if ((not subaccount.gross and total == 1.00) or
#                 (subaccount.gross and total <= 1.00)):
#                 break
#             choice = _handle_input(prompt, float)
#             if choice in temporary_accounts:
#                 try:
#                     new_amount = _ask_amount()
#                     prompt = 'Use %0.2f for account \'%s\'' % (new_amount,
#                                              temporary_accounts[choice].name)
#                     if _confirm(prompt, default=True):
#                         temporary_accounts[choice].amount = new_amount
#                         self.status = 'Account modified'
#                 except MenuError:
#                     self.status = ('Cancel account change, '
#                                    'still need to reconfigure')
#             else:
#                 self.status = 'Invalid choice'
#         temporary_accounts += other_accounts
#         accounts = [v for k, v in temporary_accounts.iteritems()]
#         return accounts
        
    def modify_subaccount(self):
        """Allow the user to modify aspects of an existing subaccount.
        """
        prompt = 'Modify which subaccount: '
        try:
            subaccount = (self._ask_subaccount(prompt=prompt,
                                               active_only=False))
        except MenuError:
            print 'Halted modification'
            return
        changed = False
        while 1:
            clear_screen()
            if subaccount.status:
                status_modification = 'Deactivate Account'
            else:
                status_modification = 'Activate Account'
            prompt = ('Modify subaccount %s:\n1 - Name\n2 - Description\n' 
                      '3 - Type\n4 - Amount\n5 - %s\n6 - Gross vs Net\n'
                      '%s\n%s\n\nAction: ') % (subaccount.name,
                             status_modification, meta_actions, self.status)
            try:
                action = _handle_input(prompt)
            except MenuError:
                break
            try:
                if action == '1':
                    self.status = subaccount.modify_name()
                elif action == '2':
                    self.status = subaccount.modify_description()
                elif action == '3':
                    existing_type = subaccount.type
                    self.status = subaccount.modify_type()
                    if subaccount.type != existing_type:
                        existing_amount = subaccount.amount
                        try:
                            self.status += ', ' + (subaccount.modify_amount(
                                loop=True, type_change=True))
                        except MenuError:
                            pass
                        finally:
                            self.user.accounts, status = \
                                 self.user._reconfigure_subaccounts()
                elif action == '4':
                    existing_amount = subaccount.amount
                    self.status = subaccount.modify_amount()
                    if existing_amount != subaccount.amount:
                        self.user.accounts, status = \
                                 self.user._reconfigure_subaccounts()
                elif action == '5':
                    existing_status = subaccount.status
                    self.status = subaccount.modify_status()
                    if existing_status != subaccount.status:
                        self.user.accounts, status = \
                                 self.user._reconfigure_subaccounts()
                elif action == '6':
                    self.status = subaccount.modify_gross()
                    self.user.accounts, status = \
                                 self.user._reconfigure_subaccounts()
                else:
                    self.status = 'Invalid action'
                subaccount.save()
            except MenuError:
                self.status = 'Canceled action'
                continue
        
    def add_subaccount(self):
        """Add a new subaccount to the user's accounts.

        Need to reconfigure the amounts of the other accounts if this is
        an account that affects the net and is a percentage amount.
        
        """
        try:
            subaccount = _create_account(self.user)
            subaccounts, self.status = \
                  self.user._reconfigure_subaccounts(new_subaccount=subaccount)
            prompt = 'New Account:\n\n%s\nAdd this account?' % subaccount
            if _confirm(prompt=prompt, default=True):
                subaccount.save()
                self.user.accounts = subaccounts
                self.status = ('New account %s added successfully' %
                               subaccount.name)
                all_accounts.append(subaccount)
            else:
                subaccount.discard()
                self.status = 'Did not add account %s' % subaccount.name
        except MenuError:
            self.status = 'Canceled subaccount addition'

    def _ask_subaccount(self, prompt='Perform transaction using ' +
                        'which subaccount: ', active_only=True):
        """Query user for a specific subaccount to use for transaction

        Keyword arguments:
        prompt -- What to ask the user
        active_only -- Only show the active accounts (default True)

        Returns:
        Account object

        """
        if active_only:
            all_accounts = self.user.filter_accounts(gross=None)
        else:
            all_accounts = self.user.accounts
        accounts = {}
        clear_screen()
        print '\nSubaccounts:'
        counter = 0
        for account in all_accounts:
            counter += 1
            print '%d - %s (%s)' % (counter, account.name, 
                                      account.description)
            accounts[counter] = account
        subaccount = None
        while subaccount is None:
            try:
                id = _handle_input('\n%s' % prompt, int)
                if accounts.has_key(id):
                    subaccount = accounts[id]
                else:
                    print 'Invalid choice'
            except ConversionError:
                print 'Invalid input'
        return subaccount

    def _transact_for_whole_account(self, is_deposit=True, default=False):
        """Query user to make transaction for whole account (using settings)

        Keyword arguments:
        is_deposit -- This is for a deposit (default True)
        default -- The default answer (default False)

        Returns:
        True to transact for whole account, False otherwise

        """
        if is_deposit:
            action = 'Deposit into'
        else:
            action = 'Withdraw from'
        prompt = '%s the whole account?' % action
        if self.user.whole_account_actions:
            return _confirm(prompt=prompt, default=default)
        # User does not want to be prompted for whole account actions
        else:
            return False

    def _ask_date(self, default_date=datetime.date.today(), 
                  prompt_for='transaction'):
        """Query user for a date.
        
        Keyword parameters:
        default_date -- Date to use (default today)
        prompt_for -- What date describes (default transaction)

        Returns:
        datetime.date object of desired date

        """
        #TODO 5 print out using datetime.TextCalendar
        date = None
        output_format = '%Y-%m-%d'
        prompt = ('Date of %s? (YYYY-MM-DD, default %s) ' % 
                  (prompt_for, default_date.strftime(output_format)))
        while 1:
            temp_input = _handle_input(prompt)
            if temp_input == '':
                date = default_date
            else:
                try:
                    date = datetime.date(int(temp_input[0:4]), 
                                         int(temp_input[5:7]), 
                                         int(temp_input[8:10]))
                except ValueError:
                    print 'Invalid date'
            if date is not None:
                break
        return date

def _create_account(user):
    """Create a new account with all of its properties.
    """
    # if possible, move this to Account.__init__
    subaccount = Account(user=user)
    subaccount.modify_name()
    subaccount.modify_description()
    subaccount.modify_gross()
    subaccount.modify_type()
    subaccount.modify_amount(loop=True)
    return subaccount

def _create_user(newbie=False):
    """Create a new user account.

    Returns:
    User object that was created or None if not created
    
    """
    new_user = User()
    clear_screen()
    if newbie:
        clear_screen()
        print ('Welcome to Budse, create your very first user login.  This '
               'name is how you will login forever (so choose a good one!)\n')
        raw_input(continue_string)
    need_name_input = True
    while need_name_input:
        name = _ask_string(prompt='Login Name: ')
        need_name_input = False
        for user in all_users:
            if user.name == name:
                need_name_input = True
        clear_screen()
        if need_name_input:
           print 'Login already used, try again' 
    new_user.name = name
    if newbie:
        clear_screen()
        print ('Deductions are subtracted from whole account deposits after '
               'the gross deposit and before the net deposit (e.g., pay $50 '
               'per deposit to social security)\n')
        raw_input(continue_string)
    new_user.deductions = new_user.ask_deduction_list()
    clear_screen()
    if newbie:
        clear_screen()
        print ('Whole account actions allow you to filter your entire '
               'transaction through the settings for your accounts (e.g., '
               'set aside $10 per whole account deposit for your spam '
               'and egg account)\n')
        raw_input(continue_string)
    new_user.modify_whole()
    if newbie:
        clear_screen()
        print ('Accounts each represent a portion of your entire worth.  Each '
               'has the following attributes:\n\n'
               'Name - What to call the account\n'
               'Description - How to describe the account\n'
               'Gross - Affect the gross (pre-deduction) or net'
               ' (post-deduction) amount (e.g., title 10% of gross instead of'
               ' 10% of net).  If in doubt just choose net.\n'
               'Type - Whether this account has a percentage or fixed amount\n'
               'Amount - the percentage or fixed amount (used to calculate how'
               ' to split whole account transactions)\n'
               'Total - running amount that is set aside for this account\n')
        raw_input(continue_string)
    accounts = []
    done = False
    clear_screen()
    print ('Need to create some accounts.\n')
    count = 1
    while not done:
        print 'Account %d:\n' % count
        account = None
        try:
            account = _create_account(new_user)
        except MenuError:
            pass
        else:
            clear_screen()
            if _confirm(prompt='%s\nUse account?' % account, default=True):
                accounts.append(account)
                count += 1
        finally:
            if debug and account is not None: print '==\n%s\n==' % account
            done = _confirm('Done creating accounts?')
            clear_screen()
    new_user.accounts = accounts
    new_user.accounts, status = new_user._reconfigure_subaccounts()
    clear_screen()
    if _confirm(('%s\nCreate user?' % new_user), default=True):
        new_user.save()
        all_users.append(new_user)
        for account in new_user.accounts:
            account.user = new_user.id
            account.save()
            all_accounts.append(account)
    else:
        for account in new_user.accounts:
            account.discard()
        new_user.discard()
        new_user = None
    return new_user

def opening_prompt(prompt='Username, N\'ew, Q\'uit: '):
    """Receive the username that is to be used for the application.

    Keyword arguments:
    prompt -- Printed to the user

    Check the input of the username in a case-insensitive manner by
    converting all strings to be compared into uppercase.  Maintain a
    dictionary with this uppercase string as the key and the User
    object as the value.

    Returns:
    Valid User object

    """
    users = dict([(user.name.upper(), user) for user in all_users])
    user = None
    if not users:
        try:
            user = _create_user(newbie=True)
        except MenuError:
            print 'How sad, you\'re done here.'
    else:
        while user is None:
            try:
                input_user = str(_handle_input(prompt)).upper()
            except MenuError:
                # Ignore C'ancel at this prompt
                input_user = 'C'
            if input_user == 'N':
                try:
                    user = _create_user()
                except MenuError:
                    'Try again'
            elif input_user in users:
                user = users[input_user]
            else:
                print 'Invalid user'
    return user

def _clear_screen():
    """Execute a command to clear the screen for the console application.
    
    Registered names (as of 9/2008): 
    'posix', 'nt', 'mac', 'os2', 'ce', 'java', 'riscos'

    """
    os_name = os.name
    if debug:
        os_clear = ''
    elif os_name in ('nt', 'os2', 'ce'):
        os_clear = 'cls'
    elif os_name in ('mac', 'posix'):
        os_clear = 'clear'
    # not sure what the command is for java or riscos
    else:
        os_clear = ''
    os.system(os_clear)
    
def initialize_database():
    """Initalize the database tables if they do not exist.
    """
    #Errors with CREATE TABLE IF NOT EXISTS
    connector('CREATE TABLE accounts (account_id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,account_name TEXT,status INTEGER,account_total REAL,percentage_or_fixed TEXT,transaction_amount REAL,affect_gross INTEGER,account_description TEXT)')
    connector('CREATE TABLE users (user_id INTEGER PRIMARY KEY AUTOINCREMENT,user_name TEXT,status INTEGER,last_login TEXT,automatic_deductions TEXT,whole_account_actions INTEGER)')
    connector('CREATE TABLE transactions (transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp TEXT,date TEXT,user_id INTEGER,account_id INTEGER,amount REAL,action TEXT,description TEXT,root_transaction_id INTEGER,status INTEGER)')

def user_by_id(id):
    """Retrieve a User object.

    Keyword arguments:
    id -- Unique ID of a User object

    Returns:
    User object
    
    """
    for user in all_users:
        if user.id == id:
            return user
    else:
        return None

def account_by_id(id):
    """Retrieve an Account object.

    Keyword arguments:
    id -- Unique ID of an Account object

    Returns:
    Account object
    
    """
    for account in all_accounts:
        if account.id == id:
            return account
    else:
        return None

initialize = False
if not os.path.exists(database_file):
    initialize = True
#TODO 5: program versioning in the database?
connection = sqlite.connect(database_file)
connection.row_factory = sqlite.Row
if initialize:
    initialize_database()
all_users = [User(row[user_table['id']]) for
             row in connector(select([user_table['id']], user_table['table']))]
all_accounts = [Account(row[account_table['id']]) for
                row in connector(select([account_table['id']],
                                        account_table['table']))]
continue_string = 'Strike any key to continue'
clear_screen = _clear_screen
clear_screen()
main_user = opening_prompt()
last_login = main_user.timestamp
now = datetime.datetime.now()
main_user.timestamp = '%s-%02d-%02d %d:%02d:%02d' % (now.year, now.month, 
                                   now.day, now.hour, now.minute, now.second)

main_user.save()
app = Budse(main_user)
app.status =  ('Welcome to Budse, %s.  Last login: %s' %
               (main_user.name, last_login))
#TODO 4 what to do if interrupted modifying user settings, especially things
#  that need to be configured (e.g., net percentage amounts)
#  force user to correct these and any other exceptions from User class
clear_screen()
while 1:
    prompt = ('Main Menu\n\n1 - Deposit\n2 - Withdraw\n3 - Balance\n'
              '4 - Transfer\n5 - Search\n6 - Create Report\n'
              '7 - Undo Transaction\n8 - Preferences\n'
              '%s\n%s\n\nAction: ') % (meta_actions, app.status)
    app.status = ''
    try:
        action = _handle_input(prompt)
    except MenuError:
        app.status = 'Main menu, cannot backup any further'
        clear_screen()
        continue
    if action == '1':
        clear_screen()
        app.make_deposit()
    elif action == '2':
        clear_screen()
        app.make_withdrawal()
    elif action == '3':
        clear_screen()
        app.print_balance(include_all=True)
        raw_input(continue_string)
    elif action == '4':
        clear_screen()
        app.make_transfer()
    elif action == '5':
        clear_screen()
        app.output_transactions(app.search())
        raw_input(continue_string)
    elif action == '6':
        clear_screen()
        app.create_report()
    elif action == '7':
        clear_screen()
        print 'hold up'
    elif action == '8':
        app.modify_user_settings(clear_screen)
    else:
        app.status = 'Invalid action'
    clear_screen()
