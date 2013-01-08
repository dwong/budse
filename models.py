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
from datetime import datetime
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
    
class SubDeposit(db.Model):
    """An sub-deposit to divide a deposit into accounts.

    Stored as a group
    """
    
    # Pseudo class variables that have meaning in the database
    PERCENTAGE = 'percentage'
    FIXED = 'fixed'

    __tablename__ = 'sub_deposits'

    id = Column(Integer, primary_key=True)
    _user = Column('user_id', Integer, ForeignKey('users.id'))
    _account = Column('account_id', Integer, ForeignKey('accounts.id'))
    _amount = Column('amount', Integer)
    description = Column('description', String)
    group = Column(String) # User-defined name for a group of sub-deposits
    active = Column(Boolean, default=True)
    percentage_or_fixed = Column(String)
    affect_gross = Column(Boolean)
    
    user = relation('User', backref=backref('sub_deposits'))
    account = relation('Account', backref=backref('sub_deposits'))
    
    def __init__(self, user, account, amount, description=None, group=None, 
                 percentage_or_fixed=None, affect_gross=False):
        self.user = user
        self.account = account
        self.amount = amount
        self.description = description
        self.group = group
        self.percentage_or_fixed = (percentage_or_fixed
                                    if percentage_or_fixed is not None
                                    else SubDeposit.PERCENTAGE)
        self.affect_gross = affect_gross
        
    def _get_amount(self):
        if self.percentage_or_fixed == SubDeposit.PERCENTAGE:
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
        self.timestamp = datetime.now()

        if not duplicate_override:
            duplicates = []
            for t in db.session.query(Transaction).\
                filter(or_(Transaction.parent != parent,
                           Transaction.parent == None)).\
                filter(Transaction.action != Transaction.TRANSFER).\
                filter(Transaction.action != Transaction.DEDUCTION).\
                filter(Transaction.action != Transaction.INFORMATIONAL).\
                filter(Transaction.date == date).\
                filter(Transaction.active).\
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
                self._active = True
                self.initial = False
                for t in self.children:
                    t.commit()
            else: # This comes from the transaction's parent
                self._active = True
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
            deductions = db.session.query(Deduction).\
                    filter(Deduction.parent == self).all()
            for deduction in deductions:
                deduction_repr += ('(Amount: %s, Description: %s)' %
                                   (deduction.amount, deduction.description))
            else:
                deduction_repr = ('' if not deductions else 'Deductions: [%s]'
                                  '%s' % (deduction_repr, delimiter))
            subdeposits = db.session.query(Deposit).\
                    filter(Transaction.parent == self).all()
            for deposit in subdeposits:
                subdeposit_repr += ('(Account: %s, Amount: %s,'
                                    'Description: %s)' %
                                    (deposit.account.name, deposit.amount,
                                     deposit.description))
            else:
                subdeposit_repr = ('' if not subdeposits else 'Deposits: [%s]'
                                   '%s' % (subdeposit_repr, delimiter))
        return ('Type: %s%sAmount: $%0.2f%sTransaction Date: %s%sAccount: '
                '%s%sDescription: %s%s%s%sActive: %s' %
                (action_type, delimiter, self.amount, delimiter,
                 self.date.strftime('', delimiter), account, delimiter,
                 self.description, delimiter, deduction_repr, subdeposit_repr, 
                 self.active))

class Transfer(Transaction):
    """A deposit and withdrawal."""
    
    __mapper_args__ = {'polymorphic_identity':Transaction.TRANSFER}

    def __init__(self, user, amount, date, to_account, from_account,
                 description=None, duplicate_override=False):
        """A deposit from one account combined with a withdrawal from another.

        Keyword arguments:
        user -- User
        amount -- Amount of transaction
        date -- Transaction date
        to_account -- Account to deposit into
        from_account -- Account to withdraw from
        description -- User description of transaction (default None)
        duplicate_override -- Do not check for duplicates (default False)

        """
        Transaction.__init__(self, user=user, date=date, 
                             description=description, amount=amount)
        self.description = '[%s -> %s] %s' % (from_account.name,
                                              to_account.name,
                                              self.description)
        self.to_account = to_account
        self.from_account = from_account
        db.session.add(Withdrawal(user=user, amount=amount, date=date,
                                  parent=self, description=description,
                                  account=from_account,
                                  duplicate_override=duplicate_override))
        db.session.add(Deposit(user=user, amount=amount, date=date, parent=self,
                               description=description, account=to_account,
                               duplicate_override=duplicate_override))

    def __str__(self):
        delimiter = '\n'
        try:
            from_account = db.session.query(Withdrawal).\
                           filter(Withdrawal.parent == self).one().account
            to_account = db.session.query(Deposit).\
                         filter(Deposit.parent == self).one().account
        except NoResultFound:
            transfer_type = 'INVALID Transfer'
            account_info = ''
        else:
            transfer_type = 'Transfer'
            account_info = ('Account From: %s%sAccount To: %s%s' %
                            (from_account.name, delimiter,
                             to_account.name, delimiter))
        return('Type: %s%sAmount: $%0.2f%sTransaction Date: %s%s'
               '%sDescription: %s%sActive: %s' %
               (transfer_type, delimiter, self.amount, delimiter,
                self.date.strftime('%m/%d/%Y'), delimiter, account_info,
                self.description, delimiter, self.active))
        
class Deduction(Transaction):
    """A deduction is subtracted from the gross amount of a Deposit."""

    __mapper_args__ = {'polymorphic_identity':Transaction.DEDUCTION}

    def __init__(self, user, amount, date, parent=None, description=None):
        Transaction.__init__(self, user=user, amount=amount, date=date,
                             parent=parent, description=description)

class Deposit(Transaction):
    """Amount to be placed into one or all of the user's Accounts."""

    __mapper_args__ = {'polymorphic_identity':Transaction.DEPOSIT}

    def __init__(self, user, amount, date, sub_deposits, description=None,
                 deductions=None, parent=None, duplicate_override=False):
        """An object representation of a deposit transaction.

        Keyword arguments:
        user -- User
        amount -- Initial amount of transaction
        date -- Transaction date
        description -- User description of transaction (default None)
        deductions -- List of Deduction objects (default None)
        parent -- Transaction object that this Deposit is a child of
            (default None)
        duplicate_override -- Do not check for duplicates (default False)
        sub_deposits -- List of SubDeposit objects (cannot be an empty list)

        When a multiple account deposit is broken down:
        1) Percentage amounts on the gross
        2) Fixed amounts
        3) Percentage amounts on the net

        """
        account = sub_deposits.pop() if len(sub_deposits) == 1 else None
        
        Transaction.__init__(self, user=user, amount=amount, account=account,
                             description=description, date=date, parent=parent,
                             duplicate_override=duplicate_override)
        
        # Calculate deductions
        deduction_total = 0.00
        self.deductions = deductions
        if self.deductions is not None:
            for deduction in self.deductions:
                deduction_total += deduction.amount
                deduction.parent = self
            if amount < deduction_total:
                raise FundsException('Deductions are more than the deposit')
            
        if account is not None:
            self.amount -= deduction_total
            self.account.total += self.amount
        else:
            # last ditch check
            if accounts is None or len(accounts) == 0:
                raise DepositException('Accounts are required.')
            
            self.deposits = []
            
            # lists of separated accounts
            gross_accounts = []
            fixed_accounts = []
            net_accounts = []
            # lists of (Account, amount) tuples
            deposits = []

            # Calculate minimum deposit before embarking
            minimum_deposit = deduction_total
            for sd in sub_deposits:
                # Fixed
                if s.percentage_or_fixed == SubDeposit.FIXED:
                    minimum_deposit += s.amount
                # Percentage, gross
                elif s.affect_gross:
                    minimum_deposit += self.amount * amount
            
            if self.amount < minimum_deposit:
                raise FundsException('Insufficient funds for whole account'
                                     ' deposit.  (Minimum $%0.2f)' %
                                     minimum_deposit)

            total = 0.00 # Verify that every cent is getting deposited!
            gross = running_total = self.amount
            
            # Calculate gross deposits
            for gsd in [sd for sd in sub_deposits
                        if sd.percentage_or_fixed == SubDeposit.PERCENTAGE and
                        sd.affect_gross]:
                amount = gross * gsd.amount
                if amount > 0:
                    amount = round(amount, 2)
                    total += amount
                    running_total -= amount
                    deposits.append((gsd.account, amount))

            # Execute deductions
            running_total -= deduction_total
            total += deduction_total

            # Calculate fixed deposits
            for fsd in [sd for sd in sub_deposits
                        if sd.percentage_or_fixed == SubDeposit.FIXED]:
                if running_total > 0:
                    if fsd.amount >= 0:
                        running_total -= fsd.amount
                        total += fsd.amount
                        deposits.append((fsd.account, fsd.amount))
                    else:
                        raise DepositException('Invalid negative deposit')
                else:
                    raise FundsException('Insufficient funds available for '
                                         'specified deposits')
                
            # Calculate net deposits
            if running_total > 0:
                net = running_total
                for nsd in [sd for sd in sub_deposits
                            if sd.PERCENTAGE_OR_FIXED == SubDeposit.PERCENTAGE
                            and not sd.affect_gross]:
                    amount = net * nsd.amount
                    if amount > 0:
                        amount = round(amount, 2)
                        total += amount
                        running_total -= amount
                        deposits.append((nsd.account, amount))

            # Sanity check on the deposit to ensure that everything is
            # accounted for.  The difference SHOULD always be zero, but
            # rounding is a beast (especially with percentages).
            difference = gross - total
            if difference != 0.00:
                account, amount = deposits.pop()
                amount += difference
                deposits.append((account, amount))
                
            # Execute the deposits
            for account, amount in deposits:
                deposit = Deposit(user=self.user, amount=amount, parent=self,
                                  date=self.date, account=account, 
                                  description=self.description,
                                  duplicate_override=duplicate_override)
                db.session.add(deposit)
                self.deposits.append(deposit)

def _format_db_amount(amount):
    return int(round(float(amount) * 100))

def _format_out_amount(amount, divisor=100):
    return float(amount) / divisor
