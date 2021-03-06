############################
# BUDget for Spam and Eggs (Budse)
#
# Version:
#     0.3
#
# Description:
#     Budget library
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

import datetime
#import pdb
from optparse import OptionParser

from sqlalchemy import Table, Column, Integer, String, ForeignKey, desc
from sqlalchemy import create_engine, DateTime, Date, MetaData, Boolean, or_
from sqlalchemy.ext.declarative import declarative_base, synonym_for
from sqlalchemy.orm import sessionmaker, scoped_session, relation, backref
from sqlalchemy.orm import synonym
from sqlalchemy.orm.properties import ColumnProperty
from sqlalchemy.sql.expression import func
from sqlalchemy.orm.exc import NoResultFound

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
# Strings that are unlikely to be used by the user in descriptions, etc
str_delimiter = ',|,'  
tag_delimiter = ',:,'

if debug:
    engine = create_engine('sqlite:///%s' % database_file, echo=True)
else:
    engine = create_engine('sqlite:///%s' % database_file)
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = None

class UpperComparator(ColumnProperty.Comparator):
    """Upper case strings to compare them without regard to case."""
    def __eq__(self, other):
        return func.upper(self.__clause_element__()) == func.upper(other)

########
# Amusement
########
# Just what it's named, a whole lot of fun stuff
fun = ('Non-Sequiturs Rule The Day', 'GTWW',
       "Always choose danger (unless it's actually dangerous)",
       'Monty said to Python, "G\'day, Ate"',
       'Save the money, save the world', 'Never discount',
       'Debt me my forgive', 'I do not worship the BDFL',
       "If awesome say, 'Aye'", 'Ouch, that hurt!',
       'I go that way', 'BAM POW ZAP', 'Zimminee Zammanee Zoo',
       'I choose YOU', 'Mozart was short and ugly',
       'I am your Budse',
       "I'll never let go of you.  I promise.",
       'Give me your money, and you can exit in peace',
       "Well I say, I've never thought that before!",
       'Watch out for one-eyed Willie', 'HEY YOU GUYYYS',
       'I want to eat your M-O-N-E-Y', 'FTOAYW', #Figure This Out And You Win
       "If you're not careful, you can poke an eye out.",
       'Spam for me, eggs for you', '16 TON WEIGHT',
       'Psst, Robinson Crusoe never made it out',
       'John Cleese, please', 'Terry Merry Berry Gilliam',
       'Graham Chapman graham crackers', "I'll Idle your Eric",
       'Michael Palin For Prez 2000', 'Oh Terry Jones, behave!',
       'And now for something completely different',
       'Keeping up with the 4th Ave', 'The symphonies of LA',
       'The circus already flew over the coop',
       'Spam spam spam spam spam spam spam spam spam',
       'DWYW, IDC', 'To us do your base belong', 'Fear the pear',
       "Hey buddy, won't you be my Budse?", 'FREE HUGS!',
       'I am the slap bet commissioner', 'It was a pleasure',
       'I want you to draw me like one of your French girls',
       "Southwest Women's Adventure Group",
       'Let us play the beautiful game',
       "I'm the Budse of the world!", 'Robert loved Raymond',
       'Frank smells', 'FTW',
       'Q: How far to your house?\n'
       'A: Pianos',
       'Kinder chocolate', 'Andiamo', 'Get yourselves together',
       'The smallest Can hates us',
       'This is the silliest sketch ever', 'I <3 anagrams',
       'Wakey wakey', "That's amazing.  So much love and "
       "also so much information",
       "I'm gonna go upstairs and pay a visit to the shower "
       "fairy", 'Q: You a pothead, Focker?\n'
       'A: No I pass on grass always.  Well not always.',
       'You never told me about your cat milking days in Motown',
       "OK, well don't you think that the Samsonite people, "
       "in some crazy scheme in order to make a profit,\n"
       "MADE MORE THAN ONE BLACK SUITCASE?",
       'Bingo, Bango, Bongo!', "They'll never take...OUR FREEDOM",
       'Ego nunquam pronunciari mendacium! Sed ego sum '
       'homo indomitus',
       'Q: What is your name?\n'
       'A: My name is Gladiat..., err Budse',
       'Did you really just buy that?', 'Strength and honor'
       )

########
# CLASSES
########
class Account(Base):
    """A sub-account that the user can deposit and withdraw from."""

    # Pseudo class variables that have meaning in the database
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
            return _format_out_amount(self._transaction_amount, 10000)
        else:
            return _format_out_amount(self._transaction_amount)
    def _set_amount(self, amount):
        self._transaction_amount = _format_db_amount(amount)
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
        return _format_out_amount(self._total)
    def _set_total(self, total):
        self._total = _format_db_amount(total)
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
    """The user that is accessing the library."""

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
        
    # General delimiters that are used within the string that is stored
    # in the database.
    # This can be a problem if the user attempts to use them in the deduction
    # description
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
    """Base class for all transactions."""

    # Pseudo static class variables that also have meaning in the database
    DEPOSIT = '+'
    WITHDRAWAL = '-'
    DEDUCTION = '|'
    INFORMATIONAL = '?'
    TRANSFER = '='

    __tablename__ = 'transactions'

    id = Column('transaction_id', Integer, primary_key=True)
    _timestamp = Column('timestamp', DateTime)
    date = Column(Date)
    _user = Column('user_id', Integer, ForeignKey('users.user_id'))
    _account = Column('account_id', Integer, ForeignKey('accounts.account_id'))
    _amount = Column('amount', Integer)
    description = Column(String)
    action = Column(String)
    _parent = Column('root_transaction_id', Integer,
                     ForeignKey('transactions.transaction_id'))
    _status = Column('status', Boolean, default=False)
    __mapper_args__ = {'polymorphic_on':action,
                       'polymorphic_identity':INFORMATIONAL}

    user = relation('User', backref=backref('transactions', order_by=id))
    account = relation('Account', backref=backref('transactions', order_by=id))
    children = relation('Transaction', primaryjoin=_parent == id, cascade='all',
                        backref=backref('parent', remote_side=id),
                        lazy='joined', join_depth=1, post_update=True)
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
        if not self._status:
            if self.parent is None and self.initial:
                self._status = True
                self.initial = False
                for t in self.children:
                    t.commit()
            else: # This comes from the transaction's parent
                self._status = True
                for t in self.children: # Maybe support multiple nesting in the future?
                    t.commit()
                

    def _get_status(self):
        if self._status is None:
            return 'Unsaved'
        else:
            return self._status
    def _set_status(self, status):
        if status != self._status:
            self._undo_action(status)
            for t in self.children:
                t._undo_action(status)
    status = synonym('_status', descriptor=property(_get_status, _set_status))

    def _undo_action(self, status):
        if self.account is not None:
            if (self.action == Transaction.DEPOSIT and status) or \
                   (self.action == Transaction.WITHDRAWAL and not status):
                self.account.total += self.amount
            elif(self.action == Transaction.WITHDRAWAL and status) or \
                   (self.action == Transaction.DEPOSIT and not status):
                self.account.total -= self.amount
        self._status = status

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
                self.date.strftime('', str_delimiter), tag_delimiter,
                account, str_delimiter, tag_delimiter, self.description,
                str_delimiter, deduction_repr, subdeposit_repr, tag_delimiter,
                self.status))


class Transfer(Transaction):
    """A deposit and withdrawal."""
    
    __mapper_args__ = {'polymorphic_identity':Transaction.TRANSFER}

    def __init__(self, user, amount, date, to_account, from_account,
                 description, duplicate_override=False):
        """A deposit from one account and withdrawal from another.

        Keyword arguments:
        user -- User
        amount -- Amount of transaction
        date -- Transaction date
        description -- User description of transaction (default None)
        to_account -- Account to deposit into
        from_account -- Account to withdraw from
        duplicate_override -- Do not check for duplicates (default False)

        """
        Transaction.__init__(self, user=user, date=date, 
                             description=description, amount=amount)
        self.description = '[%s -> %s] %s' % (from_account.name,
                                              to_account.name,
                                              self.description)
        self.to_account = to_account
        self.from_account = from_account
        session.add(Withdrawal(user=user, amount=amount, date=date,
                               parent=self, description=description,
                               account=from_account,
                               duplicate_override=duplicate_override))
        session.add(Deposit(user=user, amount=amount, date=date, parent=self,
                            description=description, account=to_account,
                            duplicate_override=duplicate_override))

    def __str__(self):
        try:
            from_account = session.query(Withdrawal).\
                           filter(Withdrawal.parent == self).one().account
            to_account = session.query(Deposit).\
                         filter(Deposit.parent == self).one().account
        except NoResultFound:
            return('Type%s INVALID Transfer%sAmount%s $%0.2f%sTransaction Date'
                '%s %s%sDescription%s %s%sActive%s %s' %
                (tag_delimiter, str_delimiter, tag_delimiter,
                 self.amount, str_delimiter, tag_delimiter,
                 self.date.strftime('%m/%d/%Y'), str_delimiter,tag_delimiter,
                 self.description, str_delimiter, tag_delimiter, self.status))
        else:
            return('Type%s Transfer%sAmount%s $%0.2f%sTransaction Date%s %s%s'
                'Account From%s %s%sAccount To%s %s%sDescription%s %s%sActive'
                '%s %s' % (tag_delimiter, str_delimiter, tag_delimiter,
                self.amount, str_delimiter, tag_delimiter,
                self.date.strftime('%m/%d/%Y'), str_delimiter,tag_delimiter,
                from_account.name, str_delimiter, tag_delimiter,
                to_account.name, str_delimiter, tag_delimiter,
                self.description, str_delimiter, tag_delimiter, self.status))

        
class Deduction(Transaction):
    """A deduction is subtracted from the gross amount of a Deposit."""

    __mapper_args__ = {'polymorphic_identity':Transaction.DEDUCTION}

    def __init__(self, user, amount, date, parent=None, description=None):
        Transaction.__init__(self, user=user, amount=amount, date=date,
                             parent=parent, description=description)

    def __str__(self):
        return('Type%s Deduction%sAmount%s $%0.2f%sTransaction Date%s %s%s'
               'Description%s %s%sActive%s %s' %
               (tag_delimiter, str_delimiter, tag_delimiter, self.amount,
                str_delimiter, tag_delimiter, self.date.strftime('%m/%d/%Y'),
                str_delimiter, tag_delimiter, self.description, str_delimiter,
                tag_delimiter, self.status))

        
class Deposit(Transaction):
    """Amount to be placed into one or all of the user's Accounts."""

    __mapper_args__ = {'polymorphic_identity':Transaction.DEPOSIT}

    def __init__(self, user, amount, date, description=None,
                 account=None, deductions=None, parent=None,
                 duplicate_override=False, accounts=None):
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
        duplicate_override -- Do not check for duplicates (default False)
        accounts -- List of (Account, affect_gross, percentage_or_fixed,
            amount) tuples (default None)

        (deprecated)
        For a 'whole account' deposit, will perform calculation and
        instantiation of subdeposits that each represent the parts of
        the whole deposit.

        (current)
        Whole account deposits are not always desirable so the caller
        can pass a list of tuples using the 'accounts' parameter.
        Usage of this parameter will supercede anything done with the
        'account' parameter.

        When a multiple account deposit is broken down:
        1) Percentage amounts on the gross
        2) Fixed amounts
        3) Percentage amounts on the net

        """
        # A None value for account is a flag for a multiple account deposit
        if accounts is not None:
            account = None
        elif account is None:
            accounts = []
            for a in user.accounts:
                if a.status:
                    accounts.append((a, a.affect_gross, a.percentage_or_fixed,
                                     a.amount))
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
            if self.amount < deduction_total:
                raise FundsException('Deductions are more than the deposit')
        self.deposits = []
        if self.account is None:
            # last ditch check
            if accounts is None or len(accounts) == 0:
                raise DepositException('Accounts are required.')
            
            # lists of separated accounts
            gross_accounts = []
            fixed_accounts = []
            net_accounts = []
            # lists of (Account, amount) tuples
            gross_deposits = []
            fixed_deposits = []
            net_deposits = []

            # Calculate minimum deposit for error message
            minimum_deposit = deduction_total

            for (a, affect_gross, percentage_or_fixed, amount) in accounts:
                # Fixed
                if percentage_or_fixed == Account.FIXED:
                    minimum_deposit += amount
                    fixed_accounts.append((a, amount))
                # Percentage, gross
                elif affect_gross:
                    minimum_deposit += self.amount * amount
                    gross_accounts.append((a, amount))
                else:
                    net_accounts.append((a, amount))
            
            if self.amount < minimum_deposit:
                raise FundsException('Insufficient funds for whole account'
                                     ' deposit.  (Minimum $%0.2f)' %
                                     minimum_deposit)

            total = 0.00
            gross = running_total = self.amount
            # Calculate gross deposits
            for (a, amt) in gross_accounts:
                amount = gross * amt
                if amount > 0:
                    amount = round(amount, 2)
                    total += amount
                    running_total -= amount
                    gross_deposits.append((a, amount))

            # Execute deductions
            running_total -= deduction_total
            total += deduction_total

            # Calculate fixed deposits
            for (a, amt) in fixed_accounts:
                if running_total > 0:
                    if amt > 0:
                        running_total -= amt
                        total += amt
                        fixed_deposits.append((a, amt))
                    elif amt < 0:
                        raise DepositException('Invalid negative deposit')
                else:
                    raise FundsException('Insufficient funds for whole account'
                                         ' deposit')
                
            # Calculate net deposits
            if running_total > 0:
                net = running_total
                if net_accounts:
                    for (a, amt) in net_accounts:
                        amount = net * amt
                        if amount > 0:
                            amount = round(amount, 2)
                            total += amount
                            running_total -= amount
                            net_deposits.append((a, amount))
                    else: 
                        difference = gross - total
                        if difference != 0.00:
                            a, amount = net_deposits.pop()
                            amount += difference
                            net_deposits.append((a, amount))
                
            # Process gross percentage accounts
            for account, amount in gross_deposits:
                deposit = Deposit(user=self.user, amount=amount, parent=self,
                                  date=self.date, account=account, 
                                  description=self.description,
                                  duplicate_override=duplicate_override)
                session.add(deposit)
                self.deposits.append(deposit)
            # Process all (gross and net) fixed amounts at once
            for account, amount in fixed_deposits:
                deposit = Deposit(user=self.user, amount=amount,
                                  date=self.date, account=account, 
                                  description=self.description, parent=self,
                                  duplicate_override=duplicate_override)
                session.add(deposit)
                self.deposits.append(deposit)
            # Process remaining with the net percentage accounts
            for account, amount in net_deposits:
                deposit = Deposit(user=self.user, amount=amount,
                                  date=self.date, account=account,
                                  description=self.description, parent=self,
                                  duplicate_override=duplicate_override)
                session.add(deposit)
                self.deposits.append(deposit)
            
        else:
            self.amount -= deduction_total
            self.account.total += self.amount

    def __str__(self):
        if self.account is not None:
            account = self.account.name
        else:
            account = 'Whole Account'
        return('Type%s Deposit%sAmount%s $%0.2f%sTransaction Date%s %s%s'
               'Account%s %s%sDescription%s %s%sActive%s %s' %
               (tag_delimiter, str_delimiter, tag_delimiter, self.amount,
                str_delimiter, tag_delimiter, self.date.strftime('%m/%d/%Y'),
                str_delimiter, tag_delimiter, account, str_delimiter,
                tag_delimiter, self.description, str_delimiter, tag_delimiter,
                self.status))
            

class Withdrawal(Transaction):
    """Subtract from the total of an Account."""

    __mapper_args__ = {'polymorphic_identity':Transaction.WITHDRAWAL}

    def __init__(self, user, amount, date, description,
                 account, parent=None, duplicate_override=False):
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
        duplicate_override -- Do not check for duplicates (default False)

        """
        Transaction.__init__(self, user=user, amount=amount, account=account,
                             description=description, parent=parent, date=date,
                             duplicate_override=duplicate_override)
        self.account.total -= self.amount

    def __str__(self):
        return('Type%s Withdrawal%sAmount%s $%0.2f%sTransaction Date%s %s%s'
               'Account%s %s%sDescription%s %s%sActive%s %s' %
               (tag_delimiter, str_delimiter, tag_delimiter, self.amount,
                str_delimiter, tag_delimiter, self.date.strftime('%m/%d/%Y'),
                str_delimiter, tag_delimiter, self.account.name, str_delimiter,
                tag_delimiter, self.description, str_delimiter, tag_delimiter,
                self.status))
    

######
# UTILITY FUNCTIONS
######
def initialize():
    """Initialize the library.

    This must be called by any user program before utilizing to ensure
    that the database is established and a session is created.

    Returns:
        Session object to access the database

    """

    Base.metadata.create_all(engine)
    global session    # Each instance can only have a single session
    session = Session()
    return session

def filter_accounts(accounts, fixed=True, percentage=True, gross=None, 
                    active_only=True, id_values=[]):
    """Filter Account objects based on properties.

    Keyword Arguments:
    accounts -- List of Account objects
    fixed - Retrieve the accounts with a fixed transaction amount
            (default True)
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

def recalculate_account_totals(accounts):
    """Recalculate the account totals based on the transaction log.
    """
    amounts = [] # Set of tuples (Account, old total, new total)
    for account in accounts:
        deposit_sum = session.query(func.sum(Transaction.amount).\
                                    label('deposit_sum')).\
                            filter(Transaction.account == account).\
                            filter(Transaction.status == True).\
                            filter(Transaction.action == Transaction.DEPOSIT).\
                            one().deposit_sum
        withdraw_sum = session.query(func.sum(Transaction.amount).\
                                     label('withdrawal_sum')).\
                         filter(Transaction.account == account).\
                         filter(Transaction.status == True).\
                         filter(Transaction.action == Transaction.WITHDRAWAL).\
                         one().withdrawal_sum
        if debug:
            print('Deposits: %s; Withdrawals: %s' % (deposit_sum, withdraw_sum))
        new_total = ((deposit_sum if deposit_sum is not None else 0) -
                     (withdraw_sum if withdraw_sum is not None else 0))
        amounts.append((account, account.total, _format_out_amount(new_total)))
    return amounts

def harmless_filter_accounts(accounts, fixed=True, percentage=True,
                             gross=None, active_only=True, id_values=[]):
    """Filter Account objects based on properties.

    Keyword Arguments:
    accounts -- List of (Account, affect_gross, percentage_or_fixed, amount)
                tuples to filter    
    fixed -- Retrieve the accounts with a fixed transaction amount
            (default True)
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
        matching = [(a, ag, pf, amt) for (a, ag, pf, amt) in accounts
                    if (fixed and pf == Account.FIXED) or \
                       (percentage and pf == Account.PERCENTAGE)
                    if gross == ag or gross is None
                    if not active_only or a.status]
    else:
        matching = [(a, ag, pf, amt) for (a, ag, pf, amt) in accounts \
                        for id in id_values if a.id == id]
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

def _harmless_require_reconfiguration(accounts, check_gross=True,
                                      check_net=True, active_only=True):
    """Determine whether accounts need to be reconfigured.

    Keyword arguments:
    accounts -- List of (Account, affect_gross,
                         percentage_or_fixed, amount) to verify
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
        for (a, ag, pf, amt) in harmless_filter_accounts(accounts, gross=True,
                                   fixed=False, active_only=active_only):
            total += _format_db_amount(amt)
        if total > 10000:
            gross_reconfiguration = True
    if check_net:
        total = 0
        for (a, ag, pf, amt) in harmless_filter_accounts(accounts, gross=False,
                                    fixed=False, active_only=active_only):
            total += _format_db_amount(amt)
        if total != 10000:
            net_reconfiguration = True
    return gross_reconfiguration, net_reconfiguration


def _format_db_amount(amount):
    return int(round(float(amount) * 100))

def _format_out_amount(amount, divisor=100):
    return float(amount) / divisor


class BudseException(Exception):
    """Base class for exceptions in this module."""
    pass

class DepositException(BudseException):
    """General invalid deposit."""
    def __init__(self, expression):
        self.expression = expression

    def __str__(self):
        return str(self.expression)

class FundsException(BudseException):
    """Incorrect funds for a specified action."""
    def __init__(self, expression):
        self.expression = expression

    def __str__(self):
        return str(self.expression)

class ParameterException(BudseException):
    """Parameters are not as expected."""
    def __init__(self, expression):
        self.expression = expression

    def __str__(self):
        return str(self.expression)

class DuplicateException(BudseException):
    """Possible duplicate transaction."""
    def __init__(self, expression, duplicates):
        self.expression = expression
        self.duplicates = duplicates

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
