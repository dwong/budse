############################
# BUDget for Spam and Eggs (Budse)
#
# Version:
#     0.3
#
# Description:
#     Budget finances on the console
#
# Requirements:
#     1) Python 2.6.* - might be (but not guaranteed to be) Py3k compatible
#     2) SQL Alchemy
#
# License:
#     Released under the GPL, a copy of which can be found at 
#     http://www.gnu.org/copyleft/gpl.html
#
# Author:
#     Derek Wong
#     http://www.goingthewongway.com
#
############################

from __future__ import with_statement
import datetime
import os
#import pdb
from optparse import OptionParser


from sqlalchemy import Table, Column, Integer, String, ForeignKey, desc
from sqlalchemy import create_engine, DateTime, Date, MetaData, Boolean, or_
from sqlalchemy.ext.declarative import declarative_base, synonym_for
from sqlalchemy.orm import sessionmaker, scoped_session, relation, backref
from sqlalchemy.orm import synonym
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.orm.properties import ColumnProperty
from sqlalchemy.sql.expression import func

default_database = 'data.db'
parser = OptionParser()
parser.set_defaults(debug=False, database=default_database)
parser.add_option('-f', '--file',
                  dest='database', help='Database file to utilize')
parser.add_option('-d', '--debug',
                  action='store_true', dest='debug',
                  help='Display debugging information')
opts, args = parser.parse_args()

debug = opts.debug
database_file = opts.database

# Homegrown XML/S-expressions
str_delimiter = ',|,'  # A string that is unlikely to be used by the user
tag_delimiter = ',:,'

engine = create_engine('sqlite:///%s' % database_file)
Base = declarative_base()
Session = sessionmaker(bind=engine)

class UpperComparator(ColumnProperty.Comparator):
    def __eq__(self, other):
        return func.upper(self.__clause_element__()) == func.upper(other)

########
#CLASSES
########
class Account(Base):
    PERCENTAGE = 'percentage'
    FIXED = 'fixed'

    __tablename__ = 'accounts'

    id = Column('account_id', Integer, primary_key=True)
    _user = Column('user_id', Integer, ForeignKey('users.user_id'))
    _name = Column('account_name', String, nullable=False)
    status = Column(Boolean, default=True)
    _total = Column('account_total', Integer)
    percentage_or_fixed = Column(String)
    _transaction_amount = Column('transaction_amount', Integer)
    affect_gross = Column(Boolean)
    description = Column('account_description', String)

    user = relation('User', backref=backref('accounts', order_by=id))
    
    def __init__(self, user, name=None, description=None,
                 percentage_or_fixed=None, amount=0.00, gross=None):
        self.user = user
        self.description = description
        self.amount = amount
        self.account_name = name
        self.percentage_or_fixed = percentage_or_fixed
        self.affect_gross = gross
        self.total = 0.00
        
    def _get_amount(self):
        if self.percentage_or_fixed == Account.PERCENTAGE:
            return float(self._transaction_amount) / 10000
        else:
            return float(self._transaction_amount) / 100
    def _set_amount(self, amount):
        self._transaction_amount = int(round(float(amount) * 100))
    amount = synonym('_transaction_amount',
                     descriptor=property(_get_amount, _set_amount))

    def _get_name(self):
        return self._name
    def _set_name(self, name):
        if name.lstrip() == '':
            raise TypeError('Cannot use a null name')
        self._name = name.lstrip().rstrip()
    name = synonym('_name', descriptor=property(_get_name, _set_name))

    def _get_total(self):
        return float(self._total) / 100
    def _set_total(self, total):
        self._total = int(round(total * 100))
    total = synonym('_total', descriptor=property(_get_total, _set_total))
    
    def __repr__(self):
        return ('%s %s %s %s %s %s' %
                (self.__class__.__name__, self.name, self.description,
                 self.percentage_or_fixed, self._transaction_amount,
                 self.affect_gross))

    def __str__(self):
        """Comma-delimited string representation of this object."""
        string_repr = 'Account Name%s %s%s' % (tag_delimiter, self.name,
                                               str_delimiter)
        string_repr += 'Description%s %s%s' % (tag_delimiter, self.description,
                                               str_delimiter)
        string_repr += 'Balance%s $%0.2f%s' % (tag_delimiter, self.total,
                                               str_delimiter)
        if self.percentage_or_fixed == Account.PERCENTAGE:
            string_repr += 'Type%s Percentage%s' % (tag_delimiter,
                                                    str_delimiter)
        else:
            string_repr += 'Type%s Fixed%s' % (tag_delimiter, str_delimiter)
        if self.percentage_or_fixed == Account.PERCENTAGE:
            string_repr += 'Amount%s %0.2f%%%s' % (tag_delimiter,
                                                   self.amount * 100,
                                                   str_delimiter)
        else:
            string_repr += 'Amount%s $%0.2f%s' % (tag_delimiter, self.amount,
                                                  str_delimiter)
        if self.affect_gross:
            string_repr += 'Affects%s Gross%s' % (tag_delimiter, str_delimiter)
        else:
            string_repr += 'Affects%s Net%s' % (tag_delimiter, str_delimiter)
        if self.status is None:
            string_repr += 'Active%s Not yet' % tag_delimiter
        else:
            string_repr += 'Active%s %s' % (tag_delimiter, self.status)
        return string_repr


class User(Base):
    __tablename__ = 'users'

    id = Column('user_id', Integer, primary_key=True)
    _name = Column('user_name', String, nullable=False)
    status = Column(Boolean, default=True)
    _last_login = Column('last_login', DateTime)
    _deductions = Column('automatic_deductions', String)
    whole_account_actions = Column(Boolean)

    def _get_name(self):
        return self._name
    def _set_name(self, name):
        if name.lstrip() == '':
            raise TypeError('Cannot use a null name')
        self._name = name.lstrip().rstrip()
    name = synonym('_name', descriptor=property(_get_name, _set_name),
                   comparator_factory=UpperComparator)

    def __init__(self, name, whole=False, deductions=None, accounts=None):
        """Initialize a new user.

        Keyword arguments:
        name -- Login name
        whole -- Prompt for whole account actions (default False)
        deductions -- List of deductions to use (default None)
        accounts -- List of Account objects (default None)

        """
        self.name = name
        self.whole_account_actions = whole
        self.deductions = deductions
        self.accounts = []
        if accounts is not None:
            for account in accounts:
                self.accounts.append(account)
    
    def login(self):
        """Record the valid login of the user."""
        self._last_login = datetime.datetime.now()

    @synonym_for('_last_login')
    @property
    def last_login(self):
        last = self._last_login
        try:
            return ('%s-%02d-%02d %d:%02d:%02d' %
                    (last.year, last.month, last.day, last.hour, last.minute,
                     last.second))
        except AttributeError:
            return 'Never'
        
    _deduction_delimiter = ';'
    _deduction_separater = ':'
    def _get_deductions(self):
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
        all_deductions = self._deductions
        deductions = []
        while all_deductions.find(self._deduction_delimiter) > 0:
            separater_index = all_deductions.find(self._deduction_separater)    
            delimiter_index = all_deductions.find(self._deduction_delimiter)
            amount = float(all_deductions[:separater_index])
            description = all_deductions[separater_index+1:delimiter_index]
            deductions.append((amount, description))
            all_deductions = all_deductions[delimiter_index+1:]
        return deductions
    def _set_deductions(self, deductions):
        """Convert list of deductions into the proper format.

        Keyword arguments:
        deductions -- List of (amount, description) tuples

        """
        deduction_repr = ''
        if deductions is not None:
            for amount, description in deductions:
                deduction_repr += '%0.2f%s%s%s' % (amount,
                                                   self._deduction_separater,
                                                   description,
                                                   self._deduction_delimiter)
        self._deductions = deduction_repr
    deductions = synonym('_deductions', descriptor=property(_get_deductions,
                                                            _set_deductions))

    def __repr__(self):
        return ('%s %s %s %s' % (self.__class__.__name__, self.name,
                                 self.whole_account_actions, self.deductions,
                                 self.accounts))

    def __str__(self):
        """Comma-delimited string representation of this object."""
        account_repr = ''
        for account in self.accounts:
            account_repr += '(%s),' % account
        else:
            account_repr = 'Accounts%s [%s]%s' % (tag_delimiter,
                                                  account_repr[:-1],#comma chop
                                                  str_delimiter)
        return('User%s %s%sWhole Account Actions%s %s%sLast Login%s %s%s'
               '%sActive%s %s' %
               (tag_delimiter, self.name, str_delimiter, tag_delimiter,
                self.whole_account_actions, str_delimiter, tag_delimiter,
                self.last_login, str_delimiter, account_repr, tag_delimiter,
                self.status))


class Transaction(Base):
    DEPOSIT = '+'
    WITHDRAWAL = '-'
    DEDUCTION = '|'
    INFORMATIONAL = '?'
    TRANSFER = '='

    __tablename__ = 'transactions'

    id = Column('transaction_id', Integer, primary_key=True)
    _timestamp = Column('timestamp', DateTime, default=datetime.datetime.now())
    date = Column(Date)
    _user = Column('user_id', Integer, ForeignKey('users.user_id'))
    _account = Column('account_id', Integer, ForeignKey('accounts.account_id'))
    _amount = Column('amount', Integer)
    description = Column(String)
    action = Column(String)
    _parent = Column('root_transaction_id', Integer,
                     ForeignKey('transactions.transaction_id'))
    _status = Column('status', Boolean, default=True)
    __mapper_args__ = {'polymorphic_on':action,
                       'polymorphic_identity':INFORMATIONAL}

    user = relation('User', backref=backref('transactions', order_by=id))
    account = relation('Account', backref=backref('transactions', order_by=id))
    children = relation('Transaction', primaryjoin=_parent == id, cascade='all',
                        backref=backref('parent', remote_side=id))

    def __init__(self, date, user, description=None, amount=0.00, account=None,
                 parent=None):
        self.date = date
        self.user = user
        self.account = account
        self.amount = amount
        self.description = description
        self.parent = parent

    def _set_amount(self, amount):
        self._amount = int(round(float(amount) * 100))
    def _get_amount(self):
        return float(self._amount) / 100
    amount = synonym('_amount', descriptor=property(_get_amount, _set_amount))

    @synonym_for('_timestamp')
    @property
    def timestamp(self):
        ts = self._timestamp
        return('%s-%02d-%02d %02d:%02d:%02d' % (ts.year, ts.month, ts.day,
                                                ts.hour, ts.minute, ts.second))

    def _get_status(self):
        # TODO: don't display True for an unsaved transaction
        if self._status is None:
            return 'Unsaved'
        else:
            return self._status
    def _set_status(self, status):
        if status != self._status:
            if self.account is not None:
                reversible_transactions = [self]
                single_transaction = True
                account = self.account
                amount = self.amount
            else:
                reversible_transactions = self.children
                single_transaction = False
            for transaction in reversible_transactions:
                if not single_transaction:
                    account = transaction.account
                    amount = transaction.amount
                if account is not None:
                    if (self.action == Transaction.DEPOSIT and status) or \
                      (self.action == Transaction.WITHDRAWAL and not status):
                        account.total += amount
                    elif(self.action == Transaction.WITHDRAWAL and status) or \
                      (self.action == Transaction.DEPOSIT and not status):
                        account.total -= amount
                self._status = status
    status = synonym('_status', descriptor=property(_get_status, _set_status))

    def __str__(self):
        """General human-readable transaction string."""
        if self.action == Transaction.DEPOSIT:
            action_type = 'Deposit'
        elif self.action == Transaction.WITHDRAWAL:
            action_type = 'Withdrawal'
        elif self.action == Transaction.DEDUCTION:
            action_type = 'Deduction'
        elif self.action == Transaction.TRANSFER:
            action_type = 'Transfer'
        else:
            action_type = 'Informational'

        if self.account is not None:
            account = self.account.name
        else:
            account = 'Whole account'

        deduction_repr = subdeposit_repr = ''
        if self.parent is None:
            deduction_repr = subdeposit_repr = subwithdrawal_repr = ''
            for deduction in session.query(Deduction).\
                    filter(Deduction.parent == self).all():
                deduction_repr += ('(Amount%s %s, Description%s %s)' %
                                   (tag_delimiter, deduction.amount,
                                    tag_delimiter, deduction.description))
            else:
                deduction_repr = 'Deductions%s [%s]%s' % (tag_delimiter,
                                                          deduction_repr,
                                                          str_delimiter)
            for deposit in session.query(Deposit).\
                    filter(Transaction.parent == self).all():
                subdeposit_repr += ('(Account%s %s, Amount%s %s,'
                                    'Description%s %s)' %
                                    (tag_delimiter, deposit.account.name,
                                     tag_delimiter, deposit.amount,
                                     tag_delimiter, deposit.description))
            else:
                subdeposit_repr = 'Deposits%s [%s]%s' % (tag_delimiter,
                                                         subdeposit_repr,
                                                         str_delimiter)
        return('Type%s %s%sAmount%s $%0.2f%sTransaction Date%s %s%sAccount%s '
               '%s%sDescription%s %s%s%s%sActive%s %s' %
               (tag_delimiter, action_type, str_delimiter, self.amount,
                str_delimiter, tag_delimiter,
                self.date.strftime(output_date, str_delimiter), tag_delimiter,
                account, str_delimiter, tag_delimiter, self.description,
                str_delimiter, deduction_repr, subdeposit_repr, tag_delimiter,
                self.status))




class Transfer(Transaction):
    __mapper_args__ = {'polymorphic_identity':Transaction.TRANSFER}

    def __init__(self, user, amount, date, to_account, from_account,
                 description):
        Transaction.__init__(self, user=user, date=date, 
                             description=description, amount=amount)
        self.description = '[%s -> %s] %s' % (from_account.name,
                                              to_account.name,
                                              self.description)
        self.to_account = to_account
        self.from_account = from_account
        session.add(Withdrawal(user=user, amount=amount, date=date,
                               parent=self, description=description,
                               account=from_account))
        session.add(Deposit(user=user, amount=amount, date=date, parent=self,
                            description=description, account=to_account))

    def __str__(self):
        from_account = session.query(Withdrawal).\
                            filter(Withdrawal.parent == self).one().account
        to_account = session.query(Deposit).\
                          filter(Deposit.parent == self).one().account
        return('Type%s Transfer%sAmount%s $%0.2f%sTransaction Date%s %s%sAccou'
               'nt From%s %s%sAccount To%s %s%sDescription%s %s%sActive%s %s' %
               (tag_delimiter, str_delimiter, tag_delimiter, self.amount,
                str_delimiter, tag_delimiter,  self.date.strftime(output_date),
                str_delimiter,tag_delimiter, from_account.name, str_delimiter,
                tag_delimiter, to_account.name, str_delimiter, tag_delimiter,
                self.description, str_delimiter, tag_delimiter, self.status))
        
class Deduction(Transaction):
    __mapper_args__ = {'polymorphic_identity':Transaction.DEDUCTION}

    def __init__(self, user, amount, date, parent=None, description=None):
        Transaction.__init__(self, user=user, amount=amount, date=date,
                             parent=parent, description=description)

    def __str__(self):
        return('Type%s Deduction%sAmount%s $%0.2f%sTransaction Date%s %s%s'
               'Description%s %s%sActive%s %s' %
               (tag_delimiter, str_delimiter, tag_delimiter, self.amount,
                str_delimiter, tag_delimiter, self.date.strftime(output_date),
                str_delimiter, tag_delimiter, self.description, str_delimiter,
                tag_delimiter, self.status))
        
class Deposit(Transaction):
    __mapper_args__ = {'polymorphic_identity':Transaction.DEPOSIT}

    def __init__(self, user, amount, date, description=None,
                 account=None, deductions=None, parent=None):
        """An object representation of a deposit transaction.

        Keyword arguments:
        user -- User
        amount -- Amount of transaction
        date -- Transaction date
        description -- User description of transaction (default None)
        account -- Account (default None is a whole account deposit)
        deductions -- List of Deduction objects (default None)
        parent -- Transaction object that this Deposit is a child of
            (default None)

        For a 'whole account' deposit, will perform calculation and
        instantiation of subdeposits that each represent the parts of
        the whole deposit.

        When broken down, this results in a loop each for:
        1) Percentage amounts on the gross
        2) Fixed amounts
        3) Percentage amounts on the net

        """
        Transaction.__init__(self, user=user, amount=amount, account=account,
                             description=description, date=date, parent=parent)
        deduction_total = 0.00
        self.deductions = deductions
        if self.deductions is not None:
            for deduction in self.deductions:
                deduction_total += deduction.amount
                deduction.parent = self
        self.deposits = []
        if self.account is None:
            gross = running_total = self.amount
            # Process gross percentage accounts
            for account in filter_accounts(self.user.accounts, fixed=False,
                                           gross=True):
                amount = gross * account.amount
                running_total -= amount
                deposit = Deposit(user=self.user, amount=amount, parent=self,
                                  date=self.date, account=account, 
                                  description=self.description)
                session.add(deposit)
                self.deposits.append(deposit)
            # Execute deductions
            running_total -= deduction_total
            # Process all fixed for
            for account in filter_accounts(self.user.accounts,
                                           percentage=False):
                if running_total > 0:
                    running_total -= account.amount
                    deposit = Deposit(user=self.user, amount=account.amount,
                                      date=self.date, account=account, 
                                      description=self.description,
                                      parent=self)
                    session.add(deposit)
                    self.deposits.append(deposit)
                else:
                    raise FundsException('Insufficient funds for whole account'
                                         ' deposit')
            # Process remaining with the net percentage accounts
            if running_total > 0:
                net = running_total
                for account in filter_accounts(self.user.accounts, fixed=False,
                                               gross=False):
                    amount = net * account.amount
                    running_total -= amount
                    deposit = Deposit(user=self.user, amount=amount,
                                      date=self.date, account=account,
                                      description=self.description,
                                      parent=self)
                    session.add(deposit)
                    self.deposits.append(deposit)
            else:
                raise FundsException('Insufficient funds for deposit')
            final = int(float(running_total) * 100)
            assert final == 0, 'Balance of %0.2f remains' % (final / 100)
        else:
            self.account.total += self.amount

    def __str__(self):
        if self.account is not None:
            account = self.account.name
        else:
            account = 'Whole Account'
        return('Type%s Deposit%sAmount%s $%0.2f%sTransaction Date%s %s%s'
               'Account%s %s%sDescription%s %s%sActive%s %s' %
               (tag_delimiter, str_delimiter, tag_delimiter, self.amount,
                str_delimiter, tag_delimiter, self.date.strftime(output_date),
                str_delimiter, tag_delimiter, account, str_delimiter,
                tag_delimiter, self.description, str_delimiter, tag_delimiter,
                self.status))
            
class Withdrawal(Transaction):
    __mapper_args__ = {'polymorphic_identity':Transaction.WITHDRAWAL}

    def __init__(self, user, amount, date, description=None,
                 account=None, parent=None):
        """An object representation of a withdrawal transaction.

        Keyword arguments:
        user -- User
        amount -- Amount of transaction
        date -- Transaction date
        description -- User description of transaction (default None)
        account -- Account (default None is a whole account deposit)
        deductions -- List of Deduction objects (default None)
        parent -- Transaction object that this Deposit is a child of
            (default None)

        """
        Transaction.__init__(self, user=user, amount=amount, account=account,
                             description=description, parent=parent, date=date)
        self.account.total -= self.amount

    def __str__(self):
        return('Type%s Withdrawal%sAmount%s $%0.2f%sTransaction Date%s %s%s'
               'Account%s %s%sDescription%s %s%sActive%s %s' %
               (tag_delimiter, str_delimiter, tag_delimiter, self.amount,
                str_delimiter, tag_delimiter, self.date.strftime(output_date),
                str_delimiter, tag_delimiter, self.account.name, str_delimiter,
                tag_delimiter, self.description, str_delimiter, tag_delimiter,
                self.status))
        
######
#UTILITY FUNCTIONS
######
def filter_accounts(accounts, fixed=True, percentage=True, gross=None, 
                    active_only=True, id_values=[]):
    """Filter Account objects based on properties.

    Keyword Arguments:
    accounts -- List of Account objects
    fixed - Retrieve the accounts with a fixed transaction amount (default True)
    percentage -- Retrieve the accounts with a percentage transaction amount
        (default True)
    gross -- Modifies the gross amount (rather than the net amount), only
        applicable if this is a percentage amount type (default None
        will ignore gross setting)
    active_only -- Only return the active accounts (default True)
    id_values -- List of ID values to match
    
    Returns:
        List of Account objects for parameters

    """
    if not id_values:
        matching = [account for account in accounts
                    if (fixed and
                        account.percentage_or_fixed == Account.FIXED) or \
                       (percentage and \
                        account.percentage_or_fixed == Account.PERCENTAGE)
                    if gross == account.affect_gross or gross is None
                    if not active_only or account.status]
    else:
        matching = [account for account in accounts \
                        for id in id_values if account.id == id]
    return matching

def _require_reconfiguration(accounts, check_gross=True, check_net=True,
                             active_only=True):
    """Determine whether accounts need to be reconfigured.

    Keyword arguments:
    accounts -- List of Account objects to verify
    check_gross -- Verify the gross accounts in the list (Default True)
    check_net -- Verify the net accounts in the list (Default True)
    active_only -- Only check the active accounts (Default True)

    Returns:
    Two Boolean values:
        gross_reconfiguration - True if required, else False
        net_reconfiguration - True if required, else False
    
    """
    gross_reconfiguration = net_reconfiguration = False
    if check_gross:
        total = 0
        for account in filter_accounts(accounts, gross=True, fixed=False,
                                       active_only=active_only):
            total += account._transaction_amount
        if total > 10000:
            gross_reconfiguration = True
    if check_net:
        total = 0
        for account in filter_accounts(accounts, gross=False, fixed=False,
                                       active_only=active_only):
            total += account._transaction_amount
        if total != 10000:
            net_reconfiguration = True
    return gross_reconfiguration, net_reconfiguration
        
#TODO 10 turn off prompting for deducting from gross?

class BudseException(Exception):
    """Base class for exceptions in this module."""
    pass

class FundsException(BudseException):
    """Incorrect funds for a specified action."""
    def __init__(self, expression):
        self.expression = expression

    def __str__(self):
        return str(self.expression)

class MetaException(BudseException):
    """Exception raised for meta actions in the input.
    """
    def __init__(self, expression):
        """Initialization method.

        Keyword arguments:
        expression -- Input that caused the exception to be raised
         
        """
        self.expression = expression

    def __str__(self):
        return str(self.expression)

class CancelException(MetaException):
    """Exception raised to cancel out of a menu."""
    def __init__(self, expression):
        self.expression = expression

    def __str__(self):
        return str(self.expression)

class DoneException(MetaException):
    """Exception raised when completed with input."""
    def __init__(self, expression):
        self.expression = expression

    def __str__(self):
        return str(self.expression)

class ConversionException(MetaException):
    """Exception raised converting to the type specified."""
    def __init__(self, expression):
        self.expression = expression

    def __str__(self):
        return str(self.expression)

      
# Actions that have meaning for all menus
meta_actions = 'c - Cancel\nd - Done\nq - Quit Program'
output_date = '%m/%d/%Y'
# TODO move the input handling functions to BudseCLI
        
            


class BudseCLI(object):
    """Command Line Interface for Budse."""

    def __init__(self, session, user=None):
        object.__init__(self)
        self.session = session
        self.user = user
        self._status = []
        
    def _handle_input(self, prompt, base_type=str):
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
            raise SystemExit('Quitting Budse')
        if str(base_input).upper() == 'C':
            raise CancelException('Cancel current menu')
        elif str(base_input).upper() == 'D':
            raise DoneException('User is done with input')
        elif str(base_input).upper() == 'Q':
            raise SystemExit('Quitting Budse')
        try:
            expression = base_type(base_input)
        except Exception, e:
            raise ConversionException("Couldn't convert %s to %s" %
                                      (base_input, base_type))
        return expression

    def _confirm(self, prompt, default=False):
        """Prompt user for a confirmation of something.

        Keyword parameters:
        prompt -- What question to ask the user
        default -- Value that <RETURN> will be for (default False/no)

        Returns:
        Boolean for whether user confirms prompt
        
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
        prompt = '%s [%s] ' % (prompt, values)
        while confirm is None:
            answer = self._handle_input(prompt).lstrip().lower()
            if answer in no_list:
                confirm = False
            elif answer in yes_list:
                confirm = True
            else:
                print('Not an acceptable value')
        return confirm    

    def _ask_date(self, default_date=datetime.date.today(),
                  prompt='Date of transaction'):
        """Query user for a date.
    
        Keyword parameters:
        default_date -- Date to use (default today)
        prompt_for -- What date describes (default transaction)

        Returns:
        datetime.date object of desired date

        """
        date = None
        output_format = '%Y-%m-%d'
        prompt = ('%s? (YYYY-MM-DD, default %s) ' % 
                  (prompt, default_date.strftime(output_format)))
        while date is None:
            temp_input = self._handle_input(prompt)
            if temp_input == '':
                date = default_date
            else:
                try:
                    date = datetime.date(int(temp_input[0:4]), 
                                         int(temp_input[5:7]), 
                                         int(temp_input[8:10]))
                except ValueError:
                    print('Invalid date')
                # TODO: Try parsing differently on raised exceptions:
                #     1) MM/DD/YYYY
                #     2) MM/DD (default year to this year)
                #     3) MM/DD/YY (default to this century)
                # Also parse string rather than using hardcoded slices
        return date

    # Use this instead of _handle_input when possible
    def _ask_string(self, prompt='Description? '):
        """Query user for a string, usually a description.

        Keyword arguments:
        prompt -- How to query the user

        Returns:
        Input received for the description

        """
        return self._handle_input(prompt)

    def _ask_amount(self, prompt='Amount? ', type=float, require_input=True):
        """Query user for a float amount
        
        Keyword arguments:
        prompt -- Output to the user to indicate input that's expected
        type -- The type of amount that is expected
        require_input -- Require the user to input a value

        Returns:
        Numeric value

        """
        amount = None
        while amount is None:
            try:
                amount = self._handle_input(prompt, type)
            except ConversionException:
                print 'Invalid value'
        # Only keep 2 decimal places of precision for these floats
        return round(amount, 2)
            
    def _get_status(self):
        """Reset the status after retrieving it."""
        status_string = ''
        for status in self._status:
            status_string += '%s.  ' % status
        else:
            status_string = status_string[:-2]  # Chop those trailing spaces!
        self._clear_status()
        return status_string
    def _set_status(self, status):
        """Assign class-wide status"""
        self._status.append(status)
    status = property(_get_status, _set_status, doc='Global app status')

    def _clear_status(self):
        self._status = []
        
    def search(self):
        """Search the database for matching transactions.

        Returns:
        A list Transaction objects

        """
        choice = self._handle_input('Search\n\n1 - Date Range\n2 - Date\n3 - '
                                    'ID\n4 - Keywords\n%s\n\nChoice: ' %
                                    meta_actions)
        limit = 10
        if choice == '1':
            begin_date = self._ask_date(prompt='Start of transactions')
            end_date = self._ask_date(prompt='End of transactions')
            return self.session.query(Transaction).\
                filter(Transaction.date >= begin_date).\
                filter(Transaction.date <= end_date).\
                filter(Transaction.parent == None).\
                order_by(desc(Transaction.date))[:limit]
        elif choice == '2':
            date = self._ask_date(prompt='Transaction date')
            return self.session.query(Transaction).\
                filter(Transaction.date == date).\
                filter(Transaction.parent == None).\
                order_by(desc(Transaction.date))[:limit]
        elif choice == '3':
            id = self._handle_input('Unique ID of transaction: ', int)
            return [self.session.query(Transaction).\
                filter(Transaction.id == id).\
                filter(Transaction.parent == None).one()]
        elif choice == '4':
            done = False
            print 'Transaction description matching any of the keywords:\n'
            keywords = []
            while not done:
                keywords.append('%%%s%%' % self._ask_string('Keyword: '))
                done = self._confirm('Done entering keywords?', True)
            if self._confirm('Limit transactions to search for?'):
                limit = self._ask_amount(type=int, prompt='Limit: ')
            return self.session.query(Transaction).\
                filter(Transaction.parent == None).\
                filter(or_(*[Transaction.description.contains(keyword) \
                                 for keyword in keywords])).\
                order_by(desc(Transaction.date))[:limit]
        
    def output_transactions(self, transactions):
        """Output a list of transactions.

        Keyword arguments:
        transactions -- List of Transaction objects to output
        
        """
        # Tags to not print in children transactions
        restricted = ['ACTIVE', 'TRANSACTION DATE'] 
        for parent_transaction in transactions:
            if parent_transaction.id is not None:
                print('------Transaction ID: %d------' % parent_transaction.id)
            print((str(parent_transaction).replace(str_delimiter, '\n')).\
                      replace(tag_delimiter, ':'))
            if parent_transaction.children:
                print('Sub-transactions:')
            for transaction in parent_transaction.children:
                action = amount = account = description = ''
                for field in str(transaction).split(str_delimiter):
                    field_information = field.split(tag_delimiter)
                    tag = str(field_information[0]).upper()
                    info = str(field_information[1]).strip()
                    if tag.strip() in restricted:
                        continue
                    elif tag == 'TYPE':
                        action = '%s of ' % info
                    elif tag == 'AMOUNT':
                        amount = info
                    elif tag == 'DESCRIPTION':
                        description = ' (%s)' % info
                    elif tag == 'ACCOUNT':
                        account = ' into %s' % info
                print('    %s%s%s%s' % (action, amount, account, description))
            print('')

    def ask_deduction_list(self, prompt='Provide a list of deductions to make'):
        """Prompt the user for their list of deductions
        
        Keyword arguments:
        prompt -- Prompt to present to the user
        
        Returns:
        List of deductions

        """
        satisfied = False
        status = prompt
        while not satisfied:
            deductions = []
            while 1:
                clear_screen()
                prompt = ('Deduction Menu:\n1 - Add Deduction\n2 - Print '
                          'Deductions\n3 - Delete Deductions And Start Over'
                          '\n%s\n%s\n\nInput: ' % (meta_actions, status))
                status = ''
                try:
                    choice = self._handle_input(prompt)
                except DoneException:
                    break
                if choice == '1':
                    amount = self._ask_amount()
                    description = self._ask_string()
                    prompt = 'Deduct %0.2f (%s)?' % (amount, description)
                    if self._confirm(prompt, True):
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
                else:
                    status = 'Invalid choice'
            full_list = 'Deductions:\n'
            if deductions:
                for amount, description in deductions:
                    full_list += '%0.2f - %s\n' % (amount, description)
                full_list += 'Use these deductions?'
            else:
                full_list = "Are you sure that you don't want any deductions?"
            if self._confirm(full_list, True):
                satisfied = True
            else:
                deductions = []
                if not self._confirm('Start over?', True):
                    satisfied = True
        return deductions

    def make_deposit(self):
        """Initiate a new deposit.
        
        Prompt the user for the necessary parameters for a deposit into
        either the entire account according to the user specifications 
        (i.e., the account types and amounts) or into a particular
        account.

        """
        print('Make A Deposit\n')
        try:
            date = self._ask_date()
            amount = self._ask_amount()
            description = self._ask_string()
            account = None
            if not self._transact_for_whole_account():
                account = self._ask_account('Deposit into which account: ')
            deduction_tuples = None
            deductions = []
            if self._confirm('Deduct from gross?'):
                if self._confirm('Use stored deductions?'):
                    deduction_tuples = self.user.deductions
                    #TODO load from self.user.deductions instead of assigning
                    #     them?  maybe change ask_deduction_list to 
                    #     (optionally) take an initialized deduction list
                else:
                    deduction_tuples = self.ask_deduction_list()
                if deduction_tuples is not None:
                    for (amt, desc) in deduction_tuples:
                        deductions.append(
                            Deduction(user=self.user, date=date, amount=amt,
                                      description=desc))
            try:
                deposit = Deposit(date=date, user=self.user, amount=amount,
                                  description=description, account=account,
                                  deductions=deductions)
            except FundsException, e:
                self.status = str(e)
                return
            else:
                self.session.add(deposit)
                indent = '  '
                # TODO get XML back from __str__ function, which can be parsed
                #    more easily?  Might not be that necessary, though since it
                #    is just a string for output
                print('\n==  Deposit Details  ==\n')
                self.output_transactions([deposit])
                if self._confirm('Execute deposit?', True):
                    self.session.commit()
                    if deposit.account is None:
                        target = 'Whole Account'
                    else:
                        target = deposit.account.name
                    self.status = ('Deposited $%0.2f into %s' %
                                   (deposit.amount, target))
                else:
                    self.session.rollback()
                    self._clear_status()
                    self.status = 'Deposit canceled'
        except (CancelException, DoneException):
            self._clear_status()
            self.status = 'Deposit canceled'

    def make_withdrawal(self):
        """Initiate a new withdrawal.

        Prompt the user for the necessary parameters for a withdrawal 
        either from the entire account or from an individual account.

        """
        print('Make A Withdrawal\n')
        try:
            date = self._ask_date()
            amount = self._ask_amount()
            description = self._ask_string()
            account = self._ask_account()
            withdrawal = Withdrawal(user=self.user, amount=amount,
                                    date=date, description=description,
                                    account=account)
            self.session.add(withdrawal)
            print('\n== Withdrawal Details ==')
            self.output_transactions([withdrawal])
            if self._confirm('Execute withdrawal?', True):
                self.session.commit()
                self.status = ('Withdrew $%0.2f from %s' %
                               (withdrawal.amount, withdrawal.account.name))
            else:
                self.session.rollback()
                self._clear_status()
                self.status = 'Withdrawal canceled'
        except (CancelException, DoneException):
            self._clear_status()
            self.status = 'Withdrawal canceled'

    def make_transfer(self):
        """Execute a transfer between accounts.
        
        Essentially this will just be a deposit and a withdrawal of the
        same amount, but the idea of a transfer is useful to the user
        because the action seems more atomic to them.

        Also the two actions can be grouped together with the same root_transaction_id
        so that an undo would yield the proper result.

        """
        print('Transfer Between Accounts\n')
        date = datetime.date.today()
        try:
            self.print_balance(include_all=True, include_user_total=False)
            withdrawal_account = self._ask_account(prompt='Transfer from: ')
            deposit_account = self._ask_account(prompt='Transfer to: ')
            print('Transfer from: %s (%0.2f)\nTransfer to: %s (%0.2f)\n' % 
                  (withdrawal_account.name, withdrawal_account.total,
                   deposit_account.name, deposit_account.total))
            amount = self._ask_amount()
            description = self._ask_string()
            transfer = Transfer(user=self.user, amount=amount, date=date,
                                description=description,
                                to_account=deposit_account,
                                from_account=withdrawal_account)
            print('\n== Transfer Details ==')
            self.output_transactions([transfer])
            if self._confirm('Execute transfer?', default=True):
                self.session.add(transfer)
                self.session.commit()
                self.status = ('Transferred %0.2f from %s to %s' %
                               (transfer.amount, transfer.from_account.name,
                                transfer.to_account.name))
            else:
                self.session.rollback()
                self._clear_status()
                self.status = 'Transfer canceled'
        except (CancelException, DoneException):
            self._clear_status()
            self.status = 'Transfer canceled'
    
    def reverse_transaction(self):
        """Undo whatever effect a transaction group had."""
        id = self._handle_input('Transaction ID: ', int)
        try:
            transaction = self.session.query(Transaction).\
                          filter(Transaction.id == id).\
                          filter(Transaction.parent == None).one()
        except NoResultFound:
            print('ID is not a valid root transaction ID')
        self.output_transactions([transaction])
        if self._confirm('Reverse Transaction? ', default=True):
            transaction.status = not transaction.status
            app.status = 'Transaction %d reversed' % id
        else:
            app.status = 'Transaction %d not reversed' % id

    def print_balance(self, account=None, include_user_total=True, 
                      include_all=False):
        """The balance of a specific account.

        Keyword parameters:
        account -- Account object to get balance for (default None)
        include_user_total -- Whether or not to include the entire user total
            (default True)
        include_all -- Supercedes account parameter and will print out all
            account totals (default False)

        """
        if account is None:
            totals = []
            longest_name = 0
            longest_total = 4  # length of '0.00'
            user_total = 0.00
            for account in self.user.accounts:
                totals.append((account.name, '%0.2f' % account.total))
                name_length = len(str(account.name))
                if name_length > longest_name:
                    longest_name = name_length
                total_length = len(str('%0.2f' % account.total))
                if total_length > longest_total:
                    longest_total = total_length
                if include_user_total:
                    user_total += account.total
            if include_user_total:
                user_total_length = len(str('%0.2f' % user_total))
                if user_total_length > longest_total:
                    longest_total = user_total_length
            #TODO this can be done with new str.format function
            if include_all:
                print('Account balances: ')
                for (name, total) in totals:
                    print('%s = %s' % (name.ljust(longest_name),
                                       total.rjust(longest_total)))
            if include_user_total:
                if include_all:
                    print((' ' * longest_name) + '   ' + ('-' * longest_total))
                user_total_string = '%0.2f' % user_total
                print('%s = %s\n' % ('Total'.ljust(longest_name),
                                     user_total_string.rjust(longest_total)))
        else:
            print('%s = $%0.2f' % (account.name, account.total))

    def create_report(self):
        """Report menu."""
        while 1:
            prompt = ('Create Report\n\n1 - Date Range\n%s\n%s\nChoice: ' % 
                      (meta_actions, self.status))
            clear_screen()
            try:
                choice = self._handle_input(prompt)
                if choice == '1':
                    self._create_report_by_date()
                    break
                # TODO add Excel report using pyExcelerator
                # TODO account report for dates
                else:
                    self.status = 'Invalid choice'
            except (CancelException, DoneException):
                self.status = 'Report canceled'
                return

    def _create_report_by_date(self, format='tsv'):
        """Create a report for a specified date range.

        Keyword arguments:
        format -- How the report will be output (default tsv)

        """
        # Output as Delimiter-Separated Values, xls extension better supported
        extension = 'xls'
        today = datetime.datetime.today()
        if today.day == 1:
            default = today + datetime.timedelta(month=-1)
        else:
            default = datetime.date(today.year, today.month, 1)
        begin_date = self._ask_date(prompt='Date of start of report',
                                    default_date=default)
        end_date = self._ask_date(prompt='Date of end of report')
        filename = 'Budse_Report_%s%s%s-%s%s%s.%s' % (begin_date.year, 
                            begin_date.month, begin_date.day, end_date.year,
                                    end_date.month, end_date.day, extension)
        default_filepath = os.getcwd()
        prompt = 'Output report to %s/%s?' % (default_filepath, filename)
        output_file = self._ask_filepath(filename=filename, prompt=prompt,
                                         default_path=default_filepath)
        if format == 'tsv':
            delimiter = '\t'
        with open(output_file, 'w') as report_file:
            report_file.write('Account Name%sDeposits%sWithdrawals%sNet%s%s'
                              'Report for %s - %s\n' %
                              (delimiter, delimiter, delimiter, delimiter,
                               delimiter, (begin_date.strftime(output_date)),
                               (end_date.strftime(output_date))))
            parent_transactions = self.session.query(Transaction).\
                filter(Transaction.date >= begin_date).\
                filter(Transaction.date <= end_date).\
                order_by(Transaction.date).all()
            # dict of (account name, deposits, withdrawals, net change) tuples
            account_summary = {} 
            for account in self.user.accounts:
                account_summary[account.id] = (account.name, 0.00, 0.00, 0.00)
            deductions = 0.00
            transaction_log = ('Transaction Log\n\nDate%sAction%sAmount%s'
                               'Account%sDescription\n' %
                               (delimiter, delimiter, delimiter, delimiter))
            for parent_transaction in parent_transactions:
                transactions = parent_transaction.children
                transactions.insert(0, parent_transaction)
                for transaction in transactions:
                    action = transaction.action
                    if transaction.account is not None:
                        account_name, deposits, withdrawals, net = \
                                 account_summary[transaction.account.id]
                        if transaction.action == Transaction.DEPOSIT:
                            deposits += transaction.amount
                            net += transaction.amount
                            action = 'Deposit'
                        elif transaction.action == Transaction.WITHDRAWAL:
                            withdrawals += transaction.amount
                            net -= transaction.amount
                            action = 'Withdrawal'
                        account_summary[transaction.account.id] = \
                                     (account_name, deposits, withdrawals, net)
                    elif transaction.action == Transaction.DEDUCTION:
                        deductions += transaction.amount
                        action = 'Deduction'
                        account_name = 'N/A'
                    elif transaction.action == Transaction.TRANSFER:
                        account_name = 'N/A'
                        action = 'Transfer'
                    else:
                        action = 'Informational'
                        account_name = 'Whole Account'
                    transaction_log += ('%s%s%s%s%0.2f%s%s%s%s\n' % 
                                        (transaction.date.strftime(output_date),
                                         delimiter, action, delimiter,
                                         transaction.amount, delimiter,
                                         account_name, delimiter,
                                         transaction.description))
            total_deposits = total_withdrawals = total_net = 0.00
            for k, v in account_summary.iteritems():
                account, deposits, withdrawals, net = v
                report_file.write('%s%s%0.2f%s%0.2f%s%0.2f\n' %
                                  (account, delimiter, deposits, delimiter,
                                   withdrawals, delimiter, net))
                total_deposits += deposits
                total_withdrawals += withdrawals
                total_net += net
            report_file.write('\n\nTotal Deposits:%s%0.2f\nTotal Withdrawals:%s'
                              '%0.2f\nTotal Deductions:%s%0.2f\n\nNet for '
                              'period:%s%0.2f\n' %
                              (delimiter, total_deposits, delimiter,
                               total_withdrawals, delimiter, deductions,
                               delimiter, total_net))
            report_file.write('\n\n%s' % transaction_log)
        self.status = '%s successfully created' % output_file

    def _ask_filepath(self, filename, prompt, default_path=os.getcwd()):
        """Prompt user for a filename.

        Keyword arguments:
        filename -- Name of the file to default to
        prompt -- How to confirm the choices to the user
        default_path -- Default directory to use to output the file to
        
        """
        filepath = None
        if self._confirm(prompt, True):
            filepath = '%s/%s' % (default_path, filename)
        else:
            while filepath is None:
                path, name = os.path.split(self._ask_string('Full filename? '))
                if os.path.exists(path):
                    if os.path.exists(os.path.join(path, name)):
                        if self._confirm(('Overwrite existing file %s' %
                                          os.path.join(path, name)), False):
                            filepath = os.path.join(path, name)
                    else:
                        filepath = os.path.join(path, name)
                else:
                    print('Invalid path')
        return filepath

    def modify_user_settings(self):
        """Modify any of the user's settings.

        Menu to access any of the saved settings for each user.

        """
        while 1:
            if self.user.status:
                status_modification = 'Deactivate User'
            else:
                status_modification = 'Activate User'
            prompt = (('User Preferences Menu\n\n'
                      '1 - Modify Existing Accounts\n'
                      '2 - Add New Account\n3 - Login Name\n4 - %s\n'
                      '5 - Deductions\n6 - Whole Account Actions\n'
                      '%s\n%s\n\nAction: ') %
                      (status_modification, meta_actions, self.status))
            clear_screen()
            try:
                action = self._handle_input(prompt)
                if action == '1':
                    self.modify_account()
                elif action == '2':
                    self.create_account(self.user)
                elif action == '3':
                    self.modify_user_name(self.user)
                elif action == '4':
                    self.modify_user_status(self.user)
                elif action == '5':
                    self.modify_user_deductions(self.user)
                elif action == '6':
                    self.modify_user_whole(self.user)
                else:
                    self.status = 'Invalid action'
                self.session.commit()
            except CancelException:
                self._clear_status()
                self.status = 'Canceled modifying preferences'
                break
            except DoneException:
                self._clear_status()
                self.status = 'Done modifying preferences'
                break
        
    def modify_user_name(self, user):
        """Change the name that is used to login to the account."""
        current_name = user.name
        if current_name is not None:
            print('Current login name: %s' % current_name)
            name_modified = False
            try:
                while 1:   # Loop for a non-null name
                    try:
                        user.name = self._handle_input('New login name: ')
                    except TypeError as e:
                        print(e)
                    else:
                        break
                if self._confirm('Change login name to %s?' % user.name, True):
                    self.session.commit()
                    self.status = ('Changed login name from %s to %s' %
                                   (current_name, user.name))
                else:
                    self.session.rollback()
            except (CancelException, DoneException):
                pass
            if not name_modified:
                self.status = 'Kept existing login name'
        else:
            while user.name is None:
                try:
                    while 1:    # Loop for a non-null name
                        try:
                            user.name = self._ask_string('Login name '
                                                         '(required): ')
                        except TypeError as e:
                            print(e)
                        else:
                            break
                    if self._confirm(prompt="Use '%s' as the login?" %
                                     user.name, default=True):
                        self.session.commit()
                    else:
                        user.name = None
                except (CancelException, DoneException):
                    pass

    def modify_user_status(self, user):
        """Prompt to flip the status of an existing account."""
        status_modified = False
        if user.status:
            if self._confirm(prompt="Deactivate your account '%s'?" %
                             user.name, default=False):
                user.status = False
                status_modified = True
                self.status = 'Deactivated account'
        else:
            if self._confirm("Activate account '%s'?" % user.name, True):
                user.status = True
                status_modified = True
                self.status = 'Activated account'
        if not status_modified:
            self.status = 'Kept existing account status'

    def modify_user_deductions(self, user):
        """Modify the user's list of saved deductions."""
        deductions_changed = False
        deductions = user.deductions
        status = ''
        while 1:
            clear_screen()
            deduction_list = ''
            for key, (amount, description) in zip(range(len(deductions)),
                                                  deductions):
                deduction_list += ('%d - $%0.2f (%s)\n' %
                                   (key+1, amount, description))
            else:
                prompt = ("Deductions (changes saved when user enters D'one):"
                          "\n\n%sn - New Deduction\n%s\n%s\n\nModify: " %
                          (deduction_list, meta_actions, status))
            status = ''
            try:
                choice = self._handle_input(prompt)
            except DoneException:
                if deductions_changed:
                    deductions_changed = True
                    user.deductions = deductions
                    self.session.commit()
                else:
                    deductions_changed = False
                break
            except CancelException:
                deductions_changed = False
                self.session.rollback()
                break
            try:
                if choice.upper() == 'N':
                    amount = self._ask_amount()
                    description = self._ask_string()
                    if self._confirm('Add deduction: $%0.2f (%s)?' %
                                (amount, description), True):
                        deductions.append((amount, description))
                        status = 'Deduction added'
                        deductions_changed = True
                elif int(choice)-1 >= 0 and int(choice)-1 <= len(deductions):
                    amount, description = deductions[int(choice)-1]
                    prompt = ('1 - Change Amount ($%0.2f)\n'
                              '2 - Change Description (%s)\n'
                              '3 - Delete\n\nChoice: ' % 
                              (amount, description))
                    try:
                        option = self._handle_input(prompt, int)
                    except DoneException:
                        continue
                    status = 'Deduction unchanged'
                    if option == 1:
                        new_amount = self._ask_amount()
                        if self._confirm('Change amount from $%0.2f to $%0.2f?'
                                         % (amount, new_amount), True):
                            deductions[int(choice)-1] = (new_amount,
                                                         description)
                            status = 'Deduction amount changed'
                            deductions_changed = True
                    elif option == 2:
                        new_description = self._ask_string()
                        if self._confirm('Change description from "%s" to '
                                         '"%s"?' %
                                         (description, new_description), True):
                            deductions[int(choice)-1] = (amount,
                                                         new_description)
                            status = 'Deduction description changed'
                            deductions_changed = True
                    elif option == '3' and self._confirm('Are you sure that '
                           'you want to delete this deduction:\n%s - %s\n' %
                           (amount, description)):
                        deductions.pop[int(choice)-1]
                        status = 'Deduction deleted'
                        deductions_changed = True
                else:
                    status = 'Invalid Choice'
            except (CancelException, DoneException):
                status = 'Canceled action'
                continue
        if deductions_changed:
            self.status = 'Deductions modified'
        else:
            self.status = 'Deductions not modified'

    def modify_user_whole(self, user):   # not hole, that would be inappropriate
        """Change whether user is prompted for whole account actions."""
        if user.whole_account_actions is not None:
            whole_modified = False
            if self.user.whole_account_actions:
                if self._confirm('Deactivate whole account actions?', False):
                    self.user.whole_account_actions = False
                    self.status = 'Deactivated whole account actions'
                    whole_modified = True
            else:
                if self._confirm('Activate whole account actions?', True):
                    self.user.whole_account_actions = True
                    self.status = 'Activated whole account actions'
                    whole_modified = True
            if not whole_modified:
                self.status = "Kept user's setting for whole account actions"
        else:
            user.whole_account_actions = self._confirm('Activate whole account '
                                                       'actions?', True)

    def modify_account(self):
        """Allow the user to modify aspects of an existing account."""
        try:
            account = self._ask_account('Modify which account: ',
                                        active_only=False)
        except (CancelException, DoneException):
            self.status = 'Halted account modifications'
            return
        changed = False
        while 1:
            clear_screen()
            if account.status:
                status_modification = 'Deactivate Account'
            else:
                status_modification = 'Activate Account'
            prompt = ('Modify account %s:\n1 - Name\n2 - Description\n' 
                      '3 - Type\n4 - Amount\n5 - %s\n6 - Gross vs Net\n'
                      '%s\n%s\n\nAction: ' % (account.name, status_modification,
                                              meta_actions, self.status))
                      
            try:
                action = self._handle_input(prompt)
            except (CancelException, DoneException):
                break
            check_reconfiguration = False
            try:
                if action == '1':
                    self.modify_account_name(account)
                elif action == '2':
                    self.modify_account_description(account)
                elif action == '3':
                    self.modify_account_type(account)
                    check_reconfiguration = True
                elif action == '4':
                    self.modify_account_amount(account)
                    check_reconfiguration = True
                elif action == '5':
                    self.modify_account_status(account)
                    check_reconfiguration = True
                elif action == '6':
                    self.modify_account_gross(account)
                    check_reconfiguration = True
                else:
                    self.status = 'Invalid action'
                self.session.commit()
                if check_reconfiguration and self.user.whole_account_actions:
                    if self.reconfigure_accounts(self.user.accounts):
                        self.status = "Reconfigured all of the user's accounts"
            except (CancelException, DoneException):
                self.status = 'Canceled action'
                continue
        
    def modify_account_name(self, account):
        """Change the name for a particular account."""
        name_modified = False
        if account.name is not None:
            current_name = account.name
            print('Existing name: %s' % current_name)
            while 1:    # Loop for a non-null name
                try:
                    account.name = self._handle_input('New name: ')
                except TypeError as e:
                    print(e)
                else:
                    break
            if account.name.lstrip() != '':
                if self._confirm("Change name from '%s' to '%s'?" %
                                 (current_name, account.name), True):
                    name_modified = True
                    self.session.commit()
                    self.status = ("Name changed from '%s' to '%s'" %
                                   (current_name, account.name))
        else:
            while 1:
                try:
                    account.name = self._ask_string('Name for the account: ')
                except TypeError as e:
                    print(e)
                else:
                    break
            self.status = "Account name is now '%s'" % account.name
            name_modified = True
        if not name_modified:
            self.status = 'Kept existing account name'

    def modify_account_description(self, account):
        """Get a new description for a particular account."""
        description_modified = False
        try:
            if account.description is not None:
                existing_description = account.description
                print('Existing description: %s' % existing_description)
                account.description = self._ask_string('New description? ')
                prompt = ("Change description from '%s' to '%s'?" % 
                          (existing_description, account.description))
                if self._confirm(prompt, True):
                    description_modified = True
                    self.status = 'Description changed'
            else:
                prompt = "Description of account '%s': " % account.name
                account.description = self._ask_string(prompt)
                description_modified = True
                self.status = "Added description for '%s'" % account.name
        except (CancelException, DoneException):
            pass
        if not description_modified:
            self.status = 'Kept existing description'

    def modify_account_type(self, account):
        """Change the type of the account, used for whole account actions."""
        type_modified = False
        if account.percentage_or_fixed is not None:
            if account.percentage_or_fixed == Account.PERCENTAGE:
                if self._confirm('Change to fixed amount?', True):
                    account.percentage_or_fixed = Account.FIXED
                    self.status = "'%s' is now a fixed account" % account.name
                    type_modified = True
            else:
                if self._confirm('Change to percentage amount?', True):
                    account.percentage_or_fixed = Account.PERCENTAGE
                    self.status = ("'%s' is now a percentage account" %
                                   account.name)
                    type_modified = True
        else:
            status = ''
            while account.percentage_or_fixed is None:
                prompt = ("Account Type:\nP'ercentage\nF'ixed\n%s\nChoice: " %
                          status)
                status = ''
                choice = self._handle_input(prompt).upper()
                if choice.startswith('P'):
                    account.percentage_or_fixed = Account.PERCENTAGE
                    type_modified = True
                    self.status = ("'%s' is now a percentage account" %
                                   account.name)
                elif choice.startswith('F'):
                    account.percentage_or_fixed = Account.FIXED
                    type_modified = True
                    self.status = "'%s' is now a fixed account" % account.name
                else:
                    status = 'Invalid choice'
        if not type_modified:
            self.status = 'Kept existing type'
        else:
            self.modify_account_amount(account, force_change=True)

    def modify_account_amount(self, account, force_change=False):
        """Change the amount for this account, whether percentage or fixed.

        Keyword arguments:
        force_change -- Whether user has to change the amount
            (e.g., because the account type changed) (default False)

        """
        amount_modified = False
        if account.percentage_or_fixed == Account.PERCENTAGE:
            display_amount = '%0.2f%%' % float(account.amount * 100)
        else:
            display_amount = '$%0.2f' % float(account.amount)
        prompt = 'Existing Amount: %s\n' % display_amount
        if account.affect_gross:
            modifies = 'Gross'
        else:
            modifies = 'Net'
        if account.affect_gross is not None:
            prompt += 'Modifies: %s\n' % modifies

        if account.percentage_or_fixed == Account.PERCENTAGE:
            prompt += 'Percentage for whole account actions: '
        else:
            prompt += 'Fixed amount (dollars) for whole account actions: '
        while 1:
            account.amount = self._ask_amount(prompt)
            if (account.percentage_or_fixed == Account.PERCENTAGE and
                (0 > (account.amount * 100) or (account.amount * 100) > 100)):
                print('Out of range! (Must be in the range 0-100)')
                continue
            if account.percentage_or_fixed == Account.PERCENTAGE:
                display_amount = '%0.2f%%' % (account.amount * 100)
            else:
                display_amount = '$%0.2f' % account.amount
            if self._confirm('Use %s for the amount?' % display_amount, True):
                amount_modified = True
                break
            if not force_change:
                break
        if not amount_modified:
            self.session.rollback()
            self.status = "Kept existing amount for '%s'" % account.name
        else:
            self.status = "Modified amount for '%s'" % account.name

    def modify_account_status(self, account):
        """Prompt to flip the status of an existing account."""
        status_modified = False
        if account.status:
            if self._confirm("Deactivate account '%s'?" % account.name, False):
                account.status = False
                status_modified = True
                self.status = 'Deactivated account'
        else:
            if self._confirm("Activate account '%s'?" % account.name, True):
                account.status = True
                status_modified = True
                self.status = 'Activated account'
        if not status_modified:
            self.status = 'Kept existing account status'

    def modify_account_gross(self, account):
        """Modify whether this account affects the gross amount."""
        gross_modified = False
        if account.affect_gross is not None:
            if not account.affect_gross:
                if self._confirm(prompt='Affect the gross on whole account '
                                 'actions?', default=True):
                    account.affect_gross = True
                    gross_modified = True
                    self.status = "'%s' now affects the gross" % account.name
            else:
                if self._confirm(prompt='Affect the net on whole account '
                                 'actions?', default=True):
                    account.affect_gross = False
                    gross_modified = True
                    self.status = "'%s' now affects the net" % account.name
        else:
            status = ''
            while account.affect_gross is None:
                prompt = ("For whole account actions, affect:\nG'ross\n"
                          "N'et\n%s\nChoice: " % status)
                status = ''
                choice = self._handle_input(prompt).upper()
                if choice.startswith('G'):
                    account.affect_gross = True
                    gross_modified = True
                    self.status = "'%s' now affects the gross" % account.name
                elif choice.startswith('N'):
                    account.affect_gross = False
                    gross_modified = True
                    self.status = "'%s' now affects the net" % account.name
                else:
                    status = 'Invalid choice'
        if not gross_modified:
            self.status = 'Kept existing setting for affecting the gross amount'

    def _ask_account(self, prompt='Perform transaction using which account: ',
                     active_only=True, exclude_accounts=[]):
        """Query user for a specific account to use for transaction

        Keyword arguments:
        prompt -- What to ask the user
        active_only -- Only show the active accounts (default True)
        exclude_accounts -- Account objects to exclude from the prompt

        Returns:
        Account object

        """
        if active_only:
            accounts = self.session.query(Account).\
                       filter(Account.user == self.user).\
                       filter(Account.status == True).all()
        else:
            accounts = self.session.query(Account).\
                       filter(Account.user == self.user).all()
        clear_screen()
        print '\nAccounts: '
        for index, account in zip(range(len(accounts)), accounts):
            print('%d - %s (%s)' %
                  (index+1, account.name, account.description))
        account = None
        while account is None:
            try:
                # Pretty indexes
                index = self._handle_input('\n%s' % prompt, int) - 1 
                if index >= 0 and index < len(accounts):
                    account = accounts[index]
                else:
                    print('Invalid choice')
            except ConversionException:
                print('Invalid choice')
        return account

    def _transact_for_whole_account(self, default=False):
        """Query user to make transaction for whole account (using settings)

        Keyword arguments:
        default -- The default answer (default False)

        Returns:
        True to transact for whole account, False otherwise

        """
        if self.user.whole_account_actions:
            return self._confirm('Deposit into the whole account?', default)
        else: # User does not want to ever be prompted for whole account actions
            return False

    def reconfigure_accounts(self, accounts, active_only=True):
        """Modify amounts for accounts to maintain requirements.

        Keyword arguments:
        accounts -- List of Account objects to reconfigure
    
        Returns:
        accounts_modified -- True if accounts modified, else False
        
        """
        gross_reconfig, net_reconfig = \
            _require_reconfiguration(accounts, active_only=active_only)
        if not gross_reconfig and not net_reconfig:
            return False
        gross_percentage = filter_accounts(accounts, gross=True, fixed=False,
                                           active_only=active_only)
        net_percentage = filter_accounts(accounts, gross=False, fixed=False,
                                         active_only=active_only)
        gross_modified = net_modified = False
        status = ''
        while gross_reconfig:
            prompt = ('Reconfigure Account Amounts\n\nModify the gross '
                      'percentage accounts to less than 100%\n')
            total = 0.00
            for index, account in zip(range(len(gross_percentage)),
                                      gross_percentage):
                amount = account.amount * 100
                prompt += ('%d - %s (%0.2f%%)\n' %
                           ((index+1), account.name, amount))
                total += amount
            prompt += 'Total: %0.2f\n%s\nModify: ' % (total, status)
            status = ''
            try:
                choice = self._handle_input(prompt, int) - 1 # Pretty index
                if choice >= 0 and choice < len(gross_percentage):
                    amount = self._ask_amount()
                    if self._confirm(("Use %0.2f for '%sn'" %
                                      (amount, gross_percentage[choice].name)),
                                     default=True):
                        gross_percentage[choice].amount = amount
                        gross_modified = True
                        status = ("'%s' modified" %
                                  (gross_percentage[choice].name))
                else:
                    status = 'Invalid choice'
            except (CancelException, DoneException):
                status = 'Canceled change, continue to reconfigure'
            gross_reconfig, trash = _require_reconfiguration(gross_percentage,
                                      check_net=False, active_only=active_only)
        while net_reconfig:
            if len(net_percentage) == 0:
                print('You need at least one net percentage account if you '
                      'want to do whole account actions')
                if self._confirm('Keep whole account actions enabled', True):
                    print('Create net accounts to take 100% of your net')
                    account_count = 1
                    done = False
                    while not done:
                        print('Account %d:\n' % account_count)
                        account = self.create_account(self.user,
                                                      affect_gross=False,
                                                      percentage_or_fixed=\
                                                          Account.PERCENTAGE)
                        if account is not None:
                            account_count += 1
                            net_percentage.append(account)
                        done = self._confirm('Done creating net accounts?')
                        clear_screen()
                else:
                    self.user.whole_account_actions = False
                    self.session.commit()
                    return True
                self.session.add_all(net_percentage)
                self.session.commit()
                self._clear_status()
            else:
                prompt = ('Reconfigure Account Amounts\n\nModify the '
                          'net percentage accounts to exactly 100%\n')
                total = 0.00
                for index, account in zip(range(len(net_percentage)),
                                          net_percentage):
                    amount = account.amount * 100
                    prompt += ('%d - %s (%0.2f%%)\n' %
                               ((index+1), account.name, amount))
                    total += amount
                prompt += 'Total: %0.2f\n%s\nModify: ' % (total, status)
                status = ''
                try:
                    choice = self._handle_input(prompt, int) - 1 # Pretty index
                    if choice >= 0 and choice < len(net_percentage):
                        amount = self._ask_amount()
                        if self._confirm(("Use %0.2f for '%s'" %
                                          (amount,
                                           net_percentage[choice].name)),
                                         default=True):
                            net_modified = True
                            net_percentage[choice].amount = amount
                            status = ("'%s' modified" %
                                      (net_percentage[choice].name))
                    else:
                        status = 'Invalid choice'
                except (CancelException, DoneException):
                    status = 'Canceled change, continue to reconfigure'
            trash, net_reconfig = _require_reconfiguration(net_percentage,
                                     check_gross=False, active_only=active_only)
        if gross_modified or net_modified:
            self.session.commit()
            return True
        else:
            return False

    def create_account(self, user, affect_gross=None, percentage_or_fixed=None):
        """Create a new account based on user's input.

        Keyword Parameter:
        user -- User object to which the account will belong to
        affect_gross -- Default for whether to modify the gross or net
            (default None will prompt user)
        percentage_or_fixed -- Default for account type (default None will
            prompt user)

        Returns:
        Account object if confirmed, otherwise None
        
        """
        account = Account(user)
        try:
            self.modify_account_name(account)
            self.modify_account_description(account)
            if affect_gross is not None:
                account.affect_gross = affect_gross
            if percentage_or_fixed is not None:
                account.percentage_or_fixed = percentage_or_fixed
                self.modify_account_amount(account)
            else:
                self.modify_account_type(account)
            if affect_gross is None:
                if account.percentage_or_fixed == Account.PERCENTAGE:
                    self.modify_account_gross(account)
                else:
                    account.affect_gross = False   # Deprecate fixed & gross
        except (CancelException, DoneException):
            self.session.rollback()
            assert account not in self.session
            return None
        account_repr = '%s' % account
        if not self._confirm('%s\nCreate account? ' %
                             (account_repr.replace(str_delimiter,'\n')).\
                             replace(tag_delimiter, ':'), True):
            self.session.rollback()
            assert account not in self.session
            return None
        return account

    def _create_user(self, newbie=False):
        """Create a new user account.

        Returns:
        User object that was created or None if not created
    
        """
        clear_screen()
        if newbie:
            clear_screen()
            print('Welcome to Budse, create your very first user login.  \n'
                  'This name is how you will login forever (so choose a good '
                  'one!)\n')
            raw_input(continue_string)
        while 1:
            name = self._ask_string('Login Name: ')
            try:
                self.session.query(User).filter(User.name == name).one()
            except NoResultFound:
                try:
                    new_user = User(name)
                except TypeError as e:
                    print(e)
                else:
                    self.session.add(new_user)
                    break
            else:
                print("Username '%s' is already used, choose again" % name)
            clear_screen()
        if newbie:
            clear_screen()
            print('Deductions are subtracted from whole account deposits \n'
                  'after the gross deposit, before the net deposit \n'
                  '(e.g., pay $50 to social security)\n')
            raw_input(continue_string)
        new_user.deductions = self.ask_deduction_list()
        clear_screen()
        if newbie:
            clear_screen()
            print('Whole account actions allow you to filter your \nentire '
                  'transaction with your account setting \n(e.g., '
                  '$10 of net for your spam, $15 of net for your eggs,\n'
                  '40% of net for savings, 10% of gross for tithe, etc)\n\n'
                  'The order of operations for a whole account action is:\n\n'
                  '1) Gross percentage accounts\n'
                  '2) Deductions\n'
                  '3) Gross and net fixed accounts\n'
                  '4) Net percentage accounts\n')
            raw_input(continue_string)
        new_user.whole_account_actions = \
            self._confirm('Activate whole account actions?', True)
        if newbie:
            clear_screen()
            print('Accounts each represent a portion of your entire worth.\n'
                  'Each of them has the following attributes:\n\n'
                  'Name - What to call the account\n'
                  'Description - How to describe the account\n'
                  'Gross - Affect the gross (pre-deduction) or net'
                  ' (post-deduction).\n    The default is net.\n'
                  'Type - A percentage or fixed amount\n'
                  'Amount - The percentage or fixed amount (used to \n    '
                  'calculate how to split whole account transactions)\n')
            raw_input(continue_string)
        accounts = []
        done = False
        clear_screen()
        print('Need to create some accounts.\n')
        while not done:
            print('Account %d:\n' % (len(accounts) + 1))
            try:
                accounts.append(self.create_account(new_user))
            except CancelException:
                pass
            finally:
                done = self._confirm("Done creating accounts for user '%s'?" %
                                     new_user.name)
            clear_screen()
        clear_screen()
        self.reconfigure_accounts(accounts, active_only=False)
        if self._confirm(('%s\nCreate user %s?' %
                          ((str(new_user)).replace(str_delimiter, '\n').\
                           replace(tag_delimiter, ':'),
                           new_user.name)), default=True):
            self.session.add_all([new_user] + accounts)
            self._clear_status()
            self.session.commit()
        else:
            self.session.rollback()
            new_user = None
        return new_user

    def opening_prompt(self):
        """Receive the username that is to be used for the application.

        Check the input of the username in a case-insensitive manner by
        converting all strings to be compared into uppercase.  Maintain a
        dictionary with this uppercase string as the key and the User
        object as the value.

        Returns:
        Valid User object

        """
        prompt = "Username, N'ew, Q'uit: "
        try:
            self.session.query(User).one()
        except NoResultFound:
            while self.user is None:
                try:
                    self.user = self._create_user(newbie=True)
                except (CancelException, DoneException):
                    print("How sad, you're done here.")
                    self.session.rollback()
        else:
            while self.user is None:
                try:
                    username = self._ask_string(prompt)
                # Ignore C'ancel and D'one at this prompt
                except CancelException:
                    username = 'C'
                except DoneException:
                    username = 'D'
                try:
                    self.user = self.session.query(User).\
                        filter(User.name == username).one()
                except NoResultFound:
                    if username == 'N':
                        try:
                            self.user = self._create_user()
                        except (CancelException, DoneException):
                            print('Try logging in again')
                    else:
                        print("User '%s' does not exist" % username)
        assert self.user is not None
        return self.user

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


if __name__ == "__main__":
    #TODO 5: program versioning in the database?
    session = Session()
    Base.metadata.create_all(engine)
    continue_string = 'Hit return to continue'
    clear_screen = _clear_screen
    clear_screen()
    app = BudseCLI(session)
    app.opening_prompt()
    last_login = app.user.last_login
    app.user.login()
    session.commit()
    app.status =  ('Welcome to Budse, %s.  Last login: %s' %
                   (app.user.name, last_login))
    if app.user.whole_account_actions:
        # Force the user to reconfigure the accounts if they're out of wack
        done = False
        while not done:
            try:
                app.reconfigure_accounts(app.user.accounts)
            except (CancelException, DoneException):
                continue
            else:
                done = True
    clear_screen()
    while 1:
        prompt = ('Main Menu\n\n1 - Deposit\n2 - Withdraw\n3 - Balance\n'
                  '4 - Transfer\n5 - Search\n6 - Create Report\n'
                  '7 - Undo Transaction\n8 - Preferences\n'
                  '%s\n%s\n\nAction: ') % (meta_actions, app.status)
        try:
            action = app._handle_input(prompt)
        except (CancelException, DoneException):
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
            try:
                app.output_transactions(app.search())
                raw_input(continue_string)
            except (CancelException, DoneException):
                app.status = 'Canceled search'
        elif action == '6':
            clear_screen()
            app.create_report()
        elif action == '7':
            try:
                app.reverse_transaction()
            except (CancelException, DoneException):
                app.status = 'Canceled reversal'
        elif action == '8':
            app.modify_user_settings()
        else:
            app.status = 'Invalid action'
        clear_screen()
