import os
from flask_root.budse import db

class User(db.Model):
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


