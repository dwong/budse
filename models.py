import os
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import Table, Column, Integer, String, ForeignKey, desc
from sqlalchemy import create_engine, DateTime, Date, MetaData, Boolean, or_
from sqlalchemy.ext.declarative import declarative_base, synonym_for
from sqlalchemy.orm import sessionmaker, scoped_session, relation, backref
from sqlalchemy.orm import synonym
from sqlalchemy.sql.expression import func
from sqlalchemy.orm.exc import NoResultFound
from comparator import UpperComparator
from app import db

class User(db.Model):
    """The user that is accessing the library."""

    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    _name = Column('name', String, nullable=False)
    status = Column(Boolean, default=True)
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
        self.accounts = []
        if accounts is not None:
            for account in accounts:
                self.accounts.append(account)
    
    def login(self):
        """Record the valid login of the user."""
        pass

    def __repr__(self):
        return ('%s %s %s %s' % (self.__class__.__name__, self.name,
                                 self.whole_account_actions,# self.deductions,
                                 self.accounts))

    def __str__(self):
        """Comma-delimited string representation of this object."""
        account_repr = ''
        # for account in self.accounts:
        #     account_repr += '(%s),' % account
        # else:
        #     account_repr = 'Accounts%s [%s]%s' % (tag_delimiter,
        #                                           account_repr[:-1],#comma chop
        #                                           str_delimiter)
        delimiter = '\n'
        return('User: %s%s%sActive %s' %
               (self.name, delimiter, account_repr, self.status))

class Account(db.Model):
    """A sub-account that the user can deposit and withdraw from."""

    __tablename__ = 'accounts'

    id = Column(Integer, primary_key=True)
    _user = Column('user_id', Integer, ForeignKey('users.id'))
    active = Column(Boolean, default=True)
    _total = Column('total', Integer, default=0)
    _name = Column('name', String, nullable=False)
    description = Column('description', String)

    user = relation('User', backref=backref('accounts', order_by=id))

    def __init__(self, user, name=None, description=None, total=0):
        self.user = user
        self.description = description
        self.name = name
        self.total = 0

    def _get_total(self):
        return _format_out_amount(self._total)
    def _set_total(self, total):
        self._total = _format_db_amount(total)
    total = synonym('_total', descriptor=property(_get_total, _set_total))
    
    def _get_name(self):
        return self._name
    def _set_name(self, name):
        if name.lstrip() == '':
            raise TypeError('Cannot use a null name')
        self._name = name.lstrip().rstrip()
    name = synonym('_name', descriptor=property(_get_name, _set_name))
    
    def __repr__(self):
        return ('%s %s %s %s' %
                (self.__class__.__name__, self.name, self.description, self.total))

    def __str__(self):
        delimiter = '\n'
        return ('Name: %s%sDescription: %s%sTotal: %s%sActive: %s' %
                (self.name, delimiter, self.description, delimiter,
                 self.total, delimiter, self.active))
    
class AutoDeposit(db.Model):
    """An automatic deposit to divide a deposit into accounts."""
    
    # Pseudo class variables that have meaning in the database
    PERCENTAGE = 'percentage'
    FIXED = 'fixed'

    __tablename__ = 'auto_deposits'

    id = Column(Integer, primary_key=True)
    _user = Column('user_id', Integer, ForeignKey('users.id'))
    _account = Column('account_id', Integer, ForeignKey('accounts.id'))
    _amount = Column('amount', Integer)
    description = Column('description', String)
    group = Column(String) # User-defined name for a group of auto deposits
    active = Column(Boolean, default=True)
    percentage_or_fixed = Column(String)
    affect_gross = Column(Boolean)
    
    user = relation('User', backref=backref('auto_deposits'))
    account = relation('Account', backref=backref('auto_deposits'))
    
    def __init__(self, user, account, amount, description=None, group=None, 
                 percentage_or_fixed=None, affect_gross=False):
        self.user = user
        self.account = account
        self.amount = amount
        self.description = description
        self.group = group
        self.percentage_or_fixed = (percentage_or_fixed
                                    if percentage_or_fixed is not None
                                    else AutoDeposit.PERCENTAGE)
        self.affect_gross = affect_gross
        
    def _get_amount(self):
        if self.percentage_or_fixed == AutoDeposit.PERCENTAGE:
            return _format_out_amount(self._amount, 10000)
        else:
            return _format_out_amount(self._amount)
    def _set_amount(self, amount):
        self._transaction_amount = _format_db_amount(amount)
    amount = synonym('_amount', descriptor=property(_get_amount, _set_amount))
    
    def __repr__(self):
        return ('%s %s %s %s %s %s %s %s' %
                (self.__class__.__name__, self.user, self.account, self.amount,
                 self.description, self.group, self.percentage_or_fixed,
                 self.affect_gross))

    def __str__(self):
        delimiter = '\n'
        return ('Group: %s%sDescription: %s%sAmount: %s%s'
                'Percentage/Fixed: %s%sGross/Net: %s%sActive: %s' %
                (self.group, delimiter, self.description, delimiter,
                 self.amount, delimiter, self.percentage_or_fixed, delimiter,
                 'Gross' if self.affect_gross else 'Net', delimiter, self.active))

class Transaction(db.Model):
    """Base class for all transactions."""

    # Pseudo static class variables that also have meaning in the database
    DEPOSIT = '+'
    WITHDRAWAL = '-'
    DEDUCTION = '|'
    INFORMATIONAL = '?'
    TRANSFER = '='

    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True)
    _timestamp = Column('timestamp', DateTime)
    date = Column(Date)
    _user = Column('user_id', Integer, ForeignKey('users.id'))
    _account = Column('account_id', Integer, ForeignKey('accounts.id'))
    account_name = Column(String)
    _amount = Column('amount', Integer)
    description = Column(String)
    action = Column(String)
    tags = Column(String)
    _parent = Column('parent_id', Integer, ForeignKey('transactions.id'))
    _active = Column('active', Boolean, default=False)
    __mapper_args__ = {'polymorphic_on':action,
                       'polymorphic_identity':INFORMATIONAL}

    user = relation('User', backref=backref('transactions', order_by=id))
    account = relation('Account', backref=backref('transactions', order_by=id))
    children = relation('Transaction', primaryjoin=_parent == id, cascade='all',
                        backref=backref('parent', remote_side=id),
                        lazy='joined', join_depth=1)
    initial = False

    def __init__(self, date, user, description=None, amount=0.00, account=None,
                 parent=None, duplicate_override=False):
        self.date = date
        self.user = user
        self.account = account
        self.amount = amount
        self.description = description
        self.parent = parent
        self.initial = True
        self.timestamp = datetime.datetime.now()

        if not duplicate_override:
            duplicates = []
            for t in session.query(Transaction).\
                filter(or_(Transaction.parent != parent,
                           Transaction.parent == None)).\
                filter(Transaction.action != Transaction.TRANSFER).\
                filter(Transaction.action != Transaction.DEDUCTION).\
                filter(Transaction.action != Transaction.INFORMATIONAL).\
                filter(Transaction.date == date).\
                filter(Transaction.status == True).\
                filter(Transaction.account == account).\
                filter(Transaction.amount ==
                       _format_db_amount(amount)).all():
                duplicates.append(t)
            if len(duplicates) > 0:
                if len(duplicates) == 1:
                    error = 'Possible duplicate found'
                else:
                    error = 'Possible duplicates found'
                raise DuplicateException(error, duplicates)

    def _set_amount(self, amount):
        self._amount = _format_db_amount(amount)
    def _get_amount(self):
        return _format_out_amount(self._amount)
    amount = synonym('_amount', descriptor=property(_get_amount, _set_amount))

    def _set_timestamp(self, ts):
        self._timestamp = ts
    def _get_timestamp(self):
        ts = self._timestamp
        return('%s-%02d-%02d %02d:%02d:%02d' % (ts.year, ts.month, ts.day,
                                                ts.hour, ts.minute, ts.second))
    timestamp = synonym('_timestamp', descriptor=property(_get_timestamp,
                                                          _set_timestamp))

    def commit(self):
        """Only used for the first save to the database."""
        if not self.active:
            ## TODO: self.initial seems unnecessary
            if self.parent is None and self.initial:
                self._status = True
                self.initial = False
                for t in self.children:
                    t.commit()
            else: # This comes from the transaction's parent
                self._status = True
                for t in self.children: # Maybe support multiple nesting in the future?
                    t.commit()

    def _get_active(self):
        return self._active
    def _set_active(self, active):
        if active != self._active:
            self._undo_action(active)
            for t in self.children:
                t._undo_action(active)
    active = synonym('_active', descriptor=property(_get_active, _set_active))

    def _undo_action(self, active):
        if self.account is not None:
            if (self.action == Transaction.DEPOSIT and active) or \
                   (self.action == Transaction.WITHDRAWAL and not active):
                self.account.total += self.amount
            elif(self.action == Transaction.WITHDRAWAL and active) or \
                   (self.action == Transaction.DEPOSIT and not active):
                self.account.total -= self.amount
        self._active = active

    def __str__(self):
        delimiter = '\n'
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
                deduction_repr += ('(Amount: %s, Description: %s)' %
                                   (deduction.amount, deduction.description))
            else:
                deduction_repr = 'Deductions: [%s]%s' % (deduction_repr,
                                                         delimiter)
            for deposit in session.query(Deposit).\
                    filter(Transaction.parent == self).all():
                subdeposit_repr += ('(Account: %s, Amount: %s,'
                                    'Description: %s)' %
                                    (deposit.account.name, deposit.amount,
                                     deposit.description))
            else:
                subdeposit_repr = 'Deposits: [%s]%s' % (subdeposit_repr,
                                                         delimiter)
        return('Type: %s%sAmount: $%0.2f%sTransaction Date: %s%sAccount: '
               '%s%sDescription: %s%s%s%sActive: %s' %
               (action_type, delimiter, self.amount, delimiter,
                self.date.strftime('', delimiter), account, delimiter,
                self.description, delimiter, deduction_repr, subdeposit_repr, 
                self.active))

def _format_db_amount(amount):
    return int(round(float(amount) * 100))

def _format_out_amount(amount, divisor=100):
    return float(amount) / divisor
