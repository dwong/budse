import os
from flask.ext.sqlalchemy import SQLAlchemy

class User(db.Model):
    """The user that is accessing the library."""

    __tablename__ = 'users'

    id = Column('user_id', Integer, primary_key=True)
    _name = Column('user_name', String, nullable=False)
    status = Column(Boolean, default=True)
    _last_login = Column('last_login', DateTime)
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
