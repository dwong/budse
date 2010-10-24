############################
# BUDget for Spam and Eggs (Budse)
#
# Version:
#     0.000000001
#
# Description:
#     Budse with a Graphical User Interface (GUI)
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

from PyQt4 import QtCore, QtGui
from sqlalchemy import and_, or_, desc
from budse_main import Ui_BudseWindow
from withdrawal_dialog import Ui_Withdrawal
from transfer_dialog import Ui_Transfer
from deposit_dialog import Ui_Deposit
from preferences import Ui_Preferences
import budse
import datetime
import random


#############
# Custom Exceptions
class AmountException(budse.BudseException):
    """Invalid value input for amount."""
    def __init__(self, expression):
        self.expression = expression

    def __str__(self):
        return str(self.expression)
    






#############
# Derived TableWidgetItems
#############

class PercentageTableWidgetItem(QtGui.QTableWidgetItem):
    """Percentage item (i.e., a float) to be used in a QTableWidget.

    Override the comparators for sorting purposes.

    """
    def __init__(self, value):
        """Initialize a percentage table widget item.

        Keyword parameters:
        value - A floating point value

        """
        QtGui.QTableWidgetItem.__init__(self)
        self.value = value
        self.setText('%0.2f' % (value * 100))

    def __lt__(self, other):
        lt = False
        if float(self.value) < float(other.value):
            lt = True
        return lt

    def __ge__(self, other):
        ge = False
        if float(self.value) >= float(other.value):
            ge = True
        return ge

class MonetaryTableWidgetItem(QtGui.QTableWidgetItem):
    """Monetary item (i.e., a float) to be used in a QTableWidget.

    Override the comparators for sorting purposes.

    """
    def __init__(self, value):
        """Initialize a monetary table widget item.

        Keyword parameters:
        value - A floating point value

        """
        QtGui.QTableWidgetItem.__init__(self)
        self.value = value
        self.setText('%0.2f' % value)

    def __lt__(self, other):
        lt = False
        if float(self.value) < float(other.value):
            lt = True
        return lt

    def __ge__(self, other):
        ge = False
        if float(self.value) >= float(other.value):
            ge = True
        return ge

class DateTableWidgetItem(QtGui.QTableWidgetItem):
    """Python datetime.date item to be used in a QTableWidget.

    Override the comparators for sorting purposes.

    Keyword parameters:
    value - datetime.date
    format - How to display the QDate (default mm/dd/yy)

    """
    def __init__(self, value, date_format='%m/%d/%y'):
        QtGui.QTableWidgetItem.__init__(self)
        self.value = value
        self.setText(value.strftime(date_format))

    def __lt__(self, other):
        lt = False
        if self.value < other.value:
            lt = True
        return lt

    def __ge__(self, other):
        ge = False
        if self.value >= other.value:
            ge = True
        return ge


#############
# Transaction Dialogs
#############

# Utility Functions (for dialogs)
def process_amount(whole_amount_text, partial_amount_text):
    """Process a whole and partial amount text into a value.

    Keyword Arguments:
    whole_amount_text
    partial_amount_text

    Returns:
    float value

    """
    whole_amount_text = str(whole_amount_text)
    partial_amount_text = str(partial_amount_text)
    try:
        whole = int(whole_amount_text.replace(',','').replace(' ',''))
    except ValueError:
        if whole_amount_text != '':
            raise AmountException('%s is not a valid number' %
                                  whole_amount_text)
        whole = 0

    try:
        partial = int(partial_amount_text.ljust(2, '0'))
    except ValueError:
        if partial_amount_text != '':
            raise AmountException('%s is not a valid number' %
                                  partial_amount_text)
        partial = 0

    return (round(float(whole) + float(partial)/100, 2))

class TransferDialog(QtGui.QDialog):

    def __init__(self, user, session):
        QtGui.QDialog.__init__(self)
        self.ui = Ui_Transfer()
        self.ui.setupUi(self)
        self.user = user
        self.session = session
        self.success = False

        self.ui.accountsComboTo.addItem('Choose account...', -1)
        self.ui.accountsComboFrom.addItem('Choose account...', -1)
        
        for a in self.user.accounts:
            self.ui.accountsComboTo.addItem(a.name, a.id)
            self.ui.accountsComboFrom.addItem(a.name, a.id)

        self.ui.accountsComboFrom.activated.connect(self.from_changed)
        self.ui.accountsComboTo.activated.connect(self.to_changed)

        self.ui.buttonBox.accepted.connect(self.save)

    def to_changed(self):
        to_id = self.ui.accountsComboTo.itemData(
            self.ui.accountsComboTo.currentIndex()).toInt()[0]
        from_id_to_remove = self.ui.accountsComboFrom.findData(to_id)
        current_from_account = None
        if from_id_to_remove != self.ui.accountsComboFrom.currentIndex():
            current_from_account = self.ui.accountsComboFrom.itemData(
                self.ui.accountsComboFrom.currentIndex()).toInt()[0]
        self.ui.accountsComboFrom.clear()
        self.ui.accountsComboFrom.addItem('Choose account...', -1)
        for a in self.user.accounts:
            if a.id != to_id:
                self.ui.accountsComboFrom.addItem(a.name, a.id)
        if current_from_account is not None:
            self.ui.accountsComboFrom.setCurrentIndex(
                self.ui.accountsComboFrom.findData(current_from_account))
        
    def from_changed(self):
        from_id = self.ui.accountsComboFrom.itemData(
            self.ui.accountsComboFrom.currentIndex()).toInt()[0]
        to_id_to_remove = self.ui.accountsComboTo.findData(from_id)
        current_to_account = None
        if to_id_to_remove != self.ui.accountsComboTo.currentIndex():
            current_to_account = self.ui.accountsComboTo.itemData(
                self.ui.accountsComboTo.currentIndex()).toInt()[0]
        self.ui.accountsComboTo.clear()
        self.ui.accountsComboTo.addItem('Choose account...', -1)
        for a in self.user.accounts:
            if a.id != from_id:
                self.ui.accountsComboTo.addItem(a.name, a.id)
        if current_to_account is not None:
            self.ui.accountsComboTo.setCurrentIndex(
                self.ui.accountsComboTo.findData(current_to_account))
            

    def save(self):
        errors = []

        # Accounts
        to_id, valid_to = self.ui.accountsComboTo.itemData(
            self.ui.accountsComboTo.currentIndex()).toInt()
        from_id, valid_from = self.ui.accountsComboFrom.itemData(
            self.ui.accountsComboFrom.currentIndex()).toInt()
        
        if not valid_from or not valid_to or from_id == -1 or to_id == -1:
            if from_id == -1 or not valid_from:
                errors.append('Must choose valid account to transfer from.')
            else:
                errors.append('Must choose valid account to transfer to.')
        else:
            if to_id == from_id:
                errors.append('Cannot transfer to and from the same account.')

        # Amount
        try:
            amount = process_amount(self.ui.wholeCurrency.text(),
                                    self.ui.partialCurrency.text())
        except AmountException, e:
            errors.append(str(e))

        # Description
        description = str(self.ui.description.toPlainText())
        
        if errors:
            to_account = self.session.query(budse.Account).\
                         filter(budse.Account.id == to_id).one()
            from_account = self.session.query(budse.Account).\
                           filter(budse.Account.id == from_id).one()
            transfer = budse.Transfer(self.user, amount, datetime.date.today(),
                                      to_account, from_account, description)
            self.success = True
            QtGui.QWidget.hide(self)
        else:
            print('invalid!')
            for e in errors:
                print(e)


class DepositDialog(QtGui.QDialog):

    def __init__(self, user, session):
        QtGui.QDialog.__init__(self)
        self.ui = Ui_Deposit()
        self.ui.setupUi(self)
        self.user = user
        self.session = session
        self.success = False

        # Accounts table and drop down
        self.ui.accountsTable.horizontalHeader().setResizeMode(
            QtGui.QHeaderView.Stretch)
        self.ui.accountsTable.horizontalHeader().show()
        self.ui.accountsTable.verticalHeader().hide()
        self.ui.accountsTable.setColumnCount(3)
        self.ui.accountsTable.setHorizontalHeaderLabels(
            ('Name', 'Type', 'Value'))
        self.ui.accountsTable.setRowCount(len(self.user.accounts))

        self.ui.accountsCombo.addItem('-- Whole Account --', 0)
        row = 0
        twi_flags = (QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsDragEnabled |
                     QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDropEnabled)
        for a in self.user.accounts:
            self.ui.accountsCombo.addItem(a.name, a.id)
            # Account
            twi = QtGui.QTableWidgetItem(a.name)
            twi.setFlags(twi_flags)
            self.ui.accountsTable.setItem(row, 0, twi)
            # Type
            if a.affect_gross:
                twi = QtGui.QTableWidgetItem('Gross')
            else:
                twi = QtGui.QTableWidgetItem('Net')
            twi.setFlags(twi_flags)
            self.ui.accountsTable.setItem(row, 1, twi)
            # Amount
            if a.percentage_or_fixed == budse.Account.PERCENTAGE:
                twi = PercentageTableWidgetItem(a.amount)
            else: # Fixed
                twi = MonetaryTableWidgetItem(a.amount)
            twi.setFlags(twi_flags)
            twi.setTextAlignment(QtCore.Qt.AlignRight)
            self.ui.accountsTable.setItem(row, 2, twi)
            row += 1

        self.ui.accountsCombo.currentIndexChanged.connect(self.account_changed)
        
        # Deposits cannot be made in the future
        self.ui.date.setMaximumDate(QtCore.QDate.currentDate())

        # Deductions
        deductions = self.user.deductions

        # Fill table
        d = self.ui.deductionsTable
        d.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)
        d.setRowCount(len(deductions))
        d.setColumnCount(2)
        d.setHorizontalHeaderLabels(('Amount', 'Description'))
        d.verticalHeader().hide()
        row = 0
        for a, desc in deductions:
            # Description
            twi = QtGui.QTableWidgetItem(desc)
            twi.setTextAlignment(QtCore.Qt.AlignLeft)
            d.setItem(row, 0, twi)
            # Amount
            twi = MonetaryTableWidgetItem(a)
            twi.setTextAlignment(QtCore.Qt.AlignRight)
            d.setItem(row, 1, twi)
            row += 1
        self.ui.deductFromGross.clicked.connect(self.deductions_changed)
        self.ui.deductFromGross.click()

        # Use own slot to validate input and save
        self.ui.buttonBox.accepted.connect(self.save)

    def account_changed(self):
        enable = False
        if self.ui.accountsCombo.currentIndex() == 0:
            enable = True
        self.change_table_status(self.ui.accountsTable, enable)

    def deductions_changed(self):
        enable = False
        if self.ui.deductFromGross.isChecked():
            enable = True
        self.change_table_status(self.ui.deductionsTable, enable, True)


    def change_table_status(self, table, enable, editable_items=False):
        if enable:
            twi_flags = (QtCore.Qt.ItemIsEnabled |
                         QtCore.Qt.ItemIsDragEnabled |
                         QtCore.Qt.ItemIsSelectable |
                         QtCore.Qt.ItemIsDropEnabled)
            if editable_items:
                twi_flags = twi_flags | QtCore.Qt.ItemIsEditable
            bg = QtGui.QBrush('black')
        else:
            twi_flags = (QtCore.Qt.ItemIsSelectable)
            bg = QtGui.QBrush('gray')

        for r in range(table.rowCount()):
            for c in range(table.columnCount()):
                twi = table.item(r, c)
                twi.setFlags(twi_flags)
                twi.setBackground(bg)
        
    def save(self):
        errors = []

        # Date
        q_date = self.ui.date.selectedDate()
        if q_date > QtCore.QDate.currentDate():
            errors.append('Cannot set a deposit in the future')
        else:
            date = datetime.date(q_date.year(), q_date.month(), q_date.day())

        # Amount
        try:
            amount = process_amount(self.ui.wholeCurrency.text(),
                                    self.ui.partialCurrency.text())
        except AmountException, e:
            errors.append(str(e))

        # Description
        description = str(self.ui.description.toPlainText())
        
        # Deduction(s)
        #TODO read in deductions
        deductions = []
        if self.ui.deductFromGross.isChecked():
            table = self.ui.deductionsTable
            for r in range(table.rowCount()):
                # Description
                d = str((table.item(r, 0)).text())
                # Amount
                a = (table.item(r, 1)).value
                deductions.append(budse.Deduction(user=self.user, date=date,
                                                  amount=a, description=d))

        # Account(s)
        account_id = self.ui.accountsCombo.itemData(
            self.ui.accountsCombo.currentIndex()
            ).toInt()[0]  # toInt returns (int, bool)
        if account_id > 0:
            account = self.session.query(budse.Account).\
                filter(budse.Account.id == account_id).one()
        else:
            account = None  # i.e., a whole account deposit

        if not errors:
            print(amount)
            try:
                deposit = budse.Deposit(self.user, amount, date,
                                        description, account, deductions)
            except budse.FundsException as e:
                errors.append(str(e))
            else:
                self.success = True
                QtGui.QWidget.hide(self)

        if errors:  # errors can happen when creating the deposit as well
            print('invalid!')
            for e in errors:
                print(e)


class WithdrawalDialog(QtGui.QDialog):

    def __init__(self, user, session):
        QtGui.QDialog.__init__(self)
        self.ui = Ui_Withdrawal()
        self.ui.setupUi(self)
        self.user = user
        self.session = session
        self.success = False

        # Fill account drop down
        for a in self.user.accounts:
            self.ui.accountsCombo.addItem(a.name, a.id)

        # Withdrawals cannot be made in the future
        self.ui.date.setMaximumDate(QtCore.QDate.currentDate())

        # Use own slot to validate input and save
        self.ui.buttonBox.accepted.connect(self.save)

    def save(self):
        errors = []

        # Date
        q_date = self.ui.date.selectedDate()
        if q_date > QtCore.QDate.currentDate():
            errors.append('Cannot set a withdrawal in the future')
        else:
            date = datetime.date(q_date.year(), q_date.month(), q_date.day())

        # Amount
        try:
            amount = process_amount(self.ui.wholeCurrency.text(),
                                    self.ui.partialCurrency.text())
        except AmountException, e:
            errors.append(str(e))
        else:
            if amount <= 0:
                errors.append('Cannot withdraw %0.2f' % amount)

        # Description
        description = str(self.ui.description.toPlainText())

        account = self.session.query(budse.Account).\
            filter(budse.Account.id ==
                   self.ui.accountsCombo.itemData(
                       self.ui.accountsCombo.currentIndex()
                       ).toInt()[0]  # toInt returns (int, bool)
                   ).one()

        if not errors:
            withdrawal = budse.Withdrawal(self.user, amount, date,
                                          description, account)
            self.success = True
            QtGui.QWidget.hide(self)
        else:
            print('invalid!')
            for e in errors:
                print(e)

class PreferencesDialog(QtGui.QDialog):

    def __init__(self, user, session):
        QtGui.QDialog.__init__(self)
        self.ui = Ui_Preferences()
        self.ui.setupUi(self)
        self.user = user
        self.session = session
        
        # Slots
        self.ui.add_account.clicked.connect(self.add_account)
        self.ui.add_deduction.clicked.connect(self.add_deduction)

        # Username
        self.ui.username.setText(self.user.name)

        # TODO: if not whole_account_actions then do not display amounts
        #       or types

        # TO TEST: Whole account settings
        if self.user.whole_account_actions:
            self.ui.whole_account.setChecked(True)

        # TODO keep track of the identity of each row, either adding
        #      a hidden ID or storing the original values in an internal
        #      data structure to compare the result against

        # Accounts
        self.at = self.ui.accountsTable
        self.active_group = QtGui.QButtonGroup()
        self.active_group.setExclusive(False)
        row = 0
        for a in self.user.accounts:
            self.insert_account(row, a.id, a.name, a.affect_gross,
                                a.percentage_or_fixed, a.amount, a.status)
            row += 1
           
        # Deductions
        self.dt = self.ui.deductionsTable

        row = 0
        for a, d in self.user.deductions:
            self.insert_deduction(row, d, a)
            row += 1

        # TODO check out doc.trolltech.com/stylesheet-examples.html
        #      for help with styling (e.g., text-align, width, etc)

    def add_account(self):
        self.insert_account(self.at.rowCount(), -1, '', False,
                            budse.Account.PERCENTAGE, 0, True)

    def insert_account(self, row, id, name, gross, acct_type, amount, active):
        nc = 0 # Name column
        vc = 1 # Value column
        tc = 2 # Type column
        gc = 3 # Gross column
        ac = 4 # Active column

        self.at.setRowCount(self.at.rowCount() + 1)

        # Account
        self.at.setItem(row, nc, QtGui.QTableWidgetItem(name))
        # Affect gross
        gross_or_net = QtGui.QComboBox()
        gross_or_net.addItem('Net', 0)
        gross_or_net.addItem('Gross', 1)
        if gross:
            gross_or_net.setCurrentIndex(1)
        self.at.setCellWidget(row, gc, gross_or_net)
        # Amount and Accont type
        acct_type = QtGui.QComboBox()
        acct_type.addItem('Percentage', 0)
        acct_type.addItem('Fixed', 1)
        if acct_type == budse.Account.PERCENTAGE:
            twi = PercentageTableWidgetItem(amount)
            acct_type.setCurrentIndex(0)
        else:
            twi = MonetaryTableWidgetItem(amount)
            acct_type.setCurrentIndex(1)
        twi.setTextAlignment(QtCore.Qt.AlignHCenter)
        self.at.setCellWidget(row, tc, acct_type)
        self.at.setItem(row, vc, twi)
        # Active checkbox
        cb = QtGui.QCheckBox()
        if active:
            cb.setChecked(True)
        self.at.setCellWidget(row, ac, cb)
        self.active_group.addButton(cb)
        # TODO: need the button group or the ID?
#        self.active_group.setId(cb, id)
        self.at.resizeRowsToContents()

    def add_deduction(self):
        self.insert_deduction(self.dt.rowCount(), '', 0)

    def insert_deduction(self, row, description, amount):
        dc = 0 # Description column
        ac = 1 # Amount column
        rc = 2 # Remove column
        
        # TODO right now each row is identified by its description
        #      is it worth it to make a unique ID so that there can be
        #      multiple instances of a description and value?
        
        self.dt.setRowCount(self.dt.rowCount() + 1)
        # Description
#        print(self.dt.size())
        twi = QtGui.QTableWidgetItem(description)
        twi.setTextAlignment(QtCore.Qt.AlignLeft)
#        twi.setSizeHint(QtCore.QSize(50, 10))
        self.dt.setItem(row, dc, twi)
        # Amount
        twi = MonetaryTableWidgetItem(amount)
        twi.setTextAlignment(QtCore.Qt.AlignHCenter)
        self.dt.setItem(row, ac, twi)
        # Delete
        b = QtGui.QCheckBox()
        self.dt.setCellWidget(row, rc, b)
        # TODO set the size of the horizontal header based on the length of the contents
        self.dt.resizeRowsToContents()

    def save(self):
        errors = []

        # TODO

        # loop through accounts
        #   if deactivated, set status to False
        #   else if new, insert a new entry
        #   else if changed in any way, update the account
        # loop through deductions
        #   create a new set for deductions
        #   if removed, do not add
        #   else add info

        if not errors:
            QtGui.QWidget.hide(self)
        else:
            print('invalid')
            for e in errors:
                print(e)



#############
# Main Window
#############
    
class BudseGUI(QtGui.QMainWindow):
    """Graphical User Interface frontend for Budse.
    """

    # Internal PyQt signals
    account_changed = QtCore.pyqtSignal()
    keyword_added = QtCore.pyqtSignal()
    do_search = QtCore.pyqtSignal()
    transaction_made = QtCore.pyqtSignal()

    show_all = True

    def __init__(self, user, parent=None):
        """Initialize GUI and signals/slots.

        Keyword paramters:
        user - budse.User object of user to initialize
            the window for
        parent - Parent of the window (default None)

        """
        QtGui.QWidget.__init__(self, parent)
        self.ui = Ui_BudseWindow()
        self.ui.setupUi(self)

        self.session = budse.initialize()

        self.user = self.session.query(budse.User).\
                    filter(budse.User.name == user).one()

        # Snapshot
        self.ui.snapshot.horizontalHeader().setResizeMode(
            QtGui.QHeaderView.Stretch)

        # Reset
        self.ui.resetButton.clicked.connect(self.reset)

        # Keywords
        self.ui.keywordLine.returnPressed.connect(self.add_keyword)
        self.ui.addKeyword.clicked.connect(self.add_keyword)
        self.keyword_added.connect(self.ui.searchButton.click)

        # Search
        self.ui.searchButton.clicked.connect(self.search)
        self.do_search.connect(self.search)

        # Calendar
        # self.ui.endDate.setSelectedDate(QtCore.QDate.currentDate())
        # self.ui.endDate.setMaximumDate(QtCore.QDate.currentDate())
        # self.ui.endDate.selectionChanged.connect(self.search)

        # Menu Items
        self.ui.newDeposit.triggered.connect(self.make_deposit)
        self.ui.newTransfer.triggered.connect(self.make_transfer)
        self.ui.newWithdrawal.triggered.connect(self.make_withdrawal)
        self.ui.preferences.triggered.connect(self.change_preferences)
        self.transaction_made.connect(self.refresh)

        # Transaction(s)
#         self.ui.transactions.horizontalHeader().setResizeMode(
#             QtGui.QHeaderView.Stretch)

        # Account(s)
        self.accounts = QtGui.QGroupBox()
        self.accounts.setFlat(True)
        acct_vlayout = QtGui.QVBoxLayout()

        self.account_buttons = QtGui.QButtonGroup()
        self.account_buttons.setExclusive(False)
        self.account_buttons.buttonClicked.connect(self.account_changed)

        self.whole_account = QtGui.QCheckBox('Whole Account')
        self.whole_account.setToolTip("Select all of the user's accounts")
        self.whole_account.clicked.connect(self.select_whole_account)

        self.deselect_accounts = QtGui.QCheckBox('Select None')
        self.deselect_accounts.setToolTip('Deselect all accounts')
        self.deselect_accounts.clicked.connect(self.deselect_all_accounts)
        self.account_buttons.setId(self.deselect_accounts, -2) # -1 reserved

        acct_vlayout.addWidget(self.whole_account)
        acct_vlayout.addWidget(self.deselect_accounts)

        # TODO expand item to fill the space allocated for it
        for a in self.user.accounts:
            cb = QtGui.QCheckBox(a.name)
            cb.setToolTip(a.description)
            self.account_buttons.addButton(cb)
            self.account_buttons.setId(cb, a.id)
            acct_vlayout.addWidget(cb)
#        self.accounts.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.accounts.setLayout(acct_vlayout)
        self.ui.accountsArea.setWidget(self.accounts)

        # The default initial view is whole account
        self.ui.keywords.setPlainText('')
        self.whole_account.click()
        self.transaction_made.emit()
#        self.refresh()

    def select_whole_account(self):
        """Select the whole account (i.e., all of the accounts).

        Selecting the whole account is similar to selecting all
        of the individual accounts.  However, it provides quicker
        selection of all of the accounts.

        """
        if self.whole_account.isChecked():
            self.deselect_accounts.setChecked(False)
            for cb in self.account_buttons.buttons():
                cb.setChecked(True)
            self.whole_account_snapshot()
        else:
            self.accounts_snapshot()
        self.do_search.emit()

    def deselect_all_accounts(self):
        """Deselect all of the accounts.

        This will provide the user with no accounts to search
        and no snapshot to have.  Instead a fun message will
        be put into the snapshot GUI element to keep things
        lively.

        """
        if self.deselect_accounts.isChecked():
            for cb in self.account_buttons.buttons():
                if self.account_buttons.id(cb) > 0:
                    cb.setChecked(False)
            self.whole_account.setChecked(False)
            # No transactions will match if it's empty
            self.no_transactions()
            # Clear out the snapshot
	    self.ui.snapshot.clear()
            self.ui.snapshot.horizontalHeader().hide()
            self.ui.snapshot.setRowCount(1)
            self.ui.snapshot.setColumnCount(1)
            # Show a fun message since there's nothing to display
            twi = QtGui.QTableWidgetItem(random.choice(budse.fun))
            self.ui.snapshot.setItem(0, 0, twi)
            self.ui.snapshot.setWordWrap(True)
            self.ui.snapshot.resizeRowsToContents()
        else:
            self.whole_account.click()


    def add_keyword(self):
        """Move the keyword from the QLineEdit to the QTextEdit.
        """
        existing_words = self.ui.keywords.toPlainText()
        new_keyword = self.ui.keywordLine.text()
        # Place each keyword on a new line
        self.ui.keywords.setPlainText('%s%s\n' % (existing_words, new_keyword))
        self.ui.keywordLine.clear()
        self.keyword_added.emit()

    def reset(self):
        """Reset all of the inputs."""
        # self.ui.endDate.setSelectedDate(QtCore.QDate.currentDate())
        self.ui.keywords.clear()
        if not self.whole_account.isChecked():
            self.whole_account.click()
        else:
            self.do_search.emit()

    def search(self):
        """Search based on the existing criteria.

        Examine all of the search criteria:
        1) Account(s) - which are checked
        2) Keyword(s) - parse as groups of names using OR clauses for
	       those that are separated by newline and AND clauses for
	       those that are separated by whitespace
        3) Date - search for a specific date if it has been changed.
	       In the future the dates should be expanded from just
	       a single day to be any number of days (which will
	       require subclassing QCalendar).

        Search the database according to the processed parameters,
        and display the matching transactions to the user.

        """
        self.ui.transactions.clear()
        # Base query no matter what the other criteria are
        query = self.session.query(budse.Transaction).\
                filter(budse.Transaction.user == self.user).\
                filter(budse.Transaction.status == True)

        # Keywords
        # List of lists (e.g., [[key1, key2], [key3]])
        kws = [[k for k in keyword.split('\s', QtCore.QString.SkipEmptyParts)]
                   for keyword in self.ui.keywords.toPlainText().\
                                  split('\n', QtCore.QString.SkipEmptyParts)]
        if kws:
            query = query.filter(or_(*map(self.parse_keyword, kws)))

        # Accounts
        if self.whole_account.isChecked():
            # Do not include subtransactions (e.g., a deposit from a whole
            #     account deposit) when a high level view is desired
            query = query.filter(budse.Transaction.parent == None)
        else:
            # Hide high level transactions (i.e., those w/o an account)
            query = query.filter(budse.Transaction.account != None)

            accts = []
            s = budse.Session()
            for b in self.account_buttons.buttons():
                if b.isChecked():
                    id = self.account_buttons.id(b)
                    accts.append(s.query(budse.Account).\
                            filter(budse.Account.id == id).one())
            if accts:
		# Cannot just do budse.Transaction.account.id w/ SQLAlchemy
		# in the query construction
		# Need to retrieve the object in order to compare it since
		# it does not recognize the property correctly
                query = query.filter(or_(*map(lambda n:
                                              budse.Transaction.account == n,
                                              accts)))
            else:
                self.no_transactions()
        
        # Date
        # q_date = self.ui.endDate.selectedDate()
        # date = datetime.date(q_date.year(), q_date.month(), q_date.day())
        # if self.ui.endDate.selectedDate() != QtCore.QDate.currentDate():
        #     query = query.filter(budse.Transaction.date == date)

        # Columns positions, this makes it easier to re-arrange them if desired
#        undo_c = 0
        date_c = 0
        amt_c = 1
        act_c = 2
        action_c = 3
        desc_c = 4

        size = query.count()
        if size == 0:
            self.no_transactions()
        else:
            self.ui.transactions.horizontalHeader().show()
            self.ui.transactions.setRowCount(size)
            # TODO add Undo column
            self.ui.transactions.setColumnCount(5)
            self.ui.transactions.setHorizontalHeaderLabels(
                ('Date', 'Amount', 'Account', 'Type', 'Description'))

            row = 0
	        #self.undo_buttons = QtGui.QButtonGroup()
            for t in query.order_by(desc(budse.Transaction.date)).all():
                # TODO Undo Button
                # twi = QtGui.QTableWidgetItem('u')
                # q = QtGui.QPushButton('undo', parent=twi)
                # self.undo_buttons.addButton(q)
                # self.undo_buttons.setId(q, t.id)
                #self.ui.transactions.setItem(row, undo_c, twi)

                # Date
                twi = DateTableWidgetItem(
                    datetime.date(t.date.year, t.date.month, t.date.day))
                self.ui.transactions.setItem(row, date_c, twi)
                # Amount
                twi = MonetaryTableWidgetItem(t.amount)
                twi.setTextAlignment(QtCore.Qt.AlignRight)
                self.ui.transactions.setItem(row, amt_c, twi)
                # Action and Account
                if t.account is not None:
                    twi = QtGui.QTableWidgetItem(t.account.name)
                    self.ui.transactions.setItem(row, act_c, twi)
                    if t.action == budse.Transaction.DEPOSIT:
                        twi = QtGui.QTableWidgetItem('Deposit')
                    if t.action == budse.Transaction.WITHDRAWAL:
                        twi = QtGui.QTableWidgetItem('Withdrawal')
                    self.ui.transactions.setItem(row, action_c, twi)
                # Special logic for non-account transactions (aka meta
                # transactions)
                else:
                    if t.action == budse.Transaction.DEDUCTION:
                        twi = QtGui.QTableWidgetItem('')
                        self.ui.transactions.setItem(row, act_c, twi)
                        twi = QtGui.QTableWidgetItem('Deduction')
                        self.ui.transactions.setItem(row, action_c, twi)
                    elif t.action == budse.Transaction.TRANSFER:
                        twi = QtGui.QTableWidgetItem('')
                        self.ui.transactions.setItem(row, act_c, twi)
                        twi = QtGui.QTableWidgetItem('Transfer')
                        self.ui.transactions.setItem(row, action_c, twi)
                    else:
                        twi = QtGui.QTableWidgetItem('Whole Account')
                        self.ui.transactions.setItem(row, act_c, twi)
                        twi = QtGui.QTableWidgetItem('Deposit')
                        self.ui.transactions.setItem(row, action_c, twi)
                # Description
                twi = QtGui.QTableWidgetItem(t.description)
                self.ui.transactions.setItem(row, desc_c, twi)

                row += 1
            self.ui.transactions.setSortingEnabled(True)
            self.ui.transactions.resizeColumnsToContents()
            self.ui.transactions.resizeRowsToContents()

    def parse_keyword(self, keys):
        """Parse a list of keywords for searching Transaction objects.

        Each list of keywords will either be parsed as a single keyword
        or as a combination of keywords.

        Keyword parameters:
        keys - List of keywords

        Returns:
        where clause for an SQLAlchemy query

        """
        if len(keys) == 1:
            return budse.Transaction.description.like('%%%s%%' % keys[0])
        else:
            return and_(*map(lambda n:
                             budse.Transaction.description.like('%%%s%%' % n),
                             keys))
        
    def no_transactions(self):
        """Show a special message when no matching transactions are found."""
        self.ui.transactions.horizontalHeader().hide()
        self.ui.transactions.setRowCount(1)
        self.ui.transactions.setColumnCount(1)
        twi = QtGui.QTableWidgetItem('No matching transactions')
        self.ui.transactions.setItem(0, 0, twi)
        self.ui.transactions.resizeColumnsToContents()
        self.ui.transactions.resizeRowsToContents()

    def whole_account_snapshot(self):
        """Displays a snapshot of the whole account.

        The snapshot will be the names and totals of all
        of the accounts.  There will also be a total included
        that will be the summation of the account totals.

        """
        self.ui.snapshot.clear()
        self.ui.snapshot.setWordWrap(False)
        self.ui.snapshot.setColumnCount(2)
        self.ui.snapshot.horizontalHeader().show()
        self.ui.snapshot.setHorizontalHeaderLabels(('Account Name',
                                                    'Account Total'))
        self.ui.snapshot.setRowCount(len(self.user.accounts) + 2)
        user_total = 0.00
        row = 0
        # Calculate the snapshot for all of the user's accounts
        for a in self.user.accounts:
            user_total += a.total
            # Account name
            twi = QtGui.QTableWidgetItem(a.name)
            twi.setTextAlignment(QtCore.Qt.AlignLeft)
            self.ui.snapshot.setItem(row, 0, twi)
            # Account total
            twi = QtGui.QTableWidgetItem('%0.2f' % a.total)
            twi.setTextAlignment(QtCore.Qt.AlignRight)
            if a.total < 0:
                twi.setTextColor(QtGui.QColor('red'))
            self.ui.snapshot.setItem(row, 1, twi)
            row += 1
        # Print out the summation of the account totals
        twi = QtGui.QTableWidgetItem('-------')
        twi.setTextAlignment(QtCore.Qt.AlignRight)
        self.ui.snapshot.setItem(row, 1, twi)
        row += 1
        twi = QtGui.QTableWidgetItem('%0.2f' % user_total)
        twi.setTextAlignment(QtCore.Qt.AlignRight)
        if user_total < 0:
            twi.setTextColor(QtGui.QColor('red'))
        self.ui.snapshot.setItem(row, 1, twi)
        self.ui.snapshot.resizeRowsToContents()

    def accounts_snapshot(self):
        """Display a snapshot of one, some, or all of the accounts.

        Display all of the properties of the selected accounts.  If
        no accounts are selected then call deselect_accounts (since
        that is essentially what is happening).  Otherwise display
        the pertinent details for the accounts selected, up to (and
        including) all of the accounts.

        """
        checked_buttons = []
        no_accounts = True
        
        for b in self.account_buttons.buttons():
            if b.isChecked():
                no_accounts = False
                checked_buttons.append(b)
        if no_accounts:
            self.deselect_accounts.click()
            return
        else:
            self.ui.snapshot.clear()
            self.ui.snapshot.setColumnCount(2)
            self.ui.snapshot.horizontalHeader().hide()
            # 7 properties: name, description, balance, type, amount,
            #               affects gross/net, active
            # plus whitespace line between them
            self.ui.snapshot.setRowCount(len(checked_buttons) * 8)
            row = 0
            for b in checked_buttons:
                b_id = self.account_buttons.id(b)
                a = self.session.query(budse.Account).\
                    filter(budse.Account.id == b_id).one()
                # Loop through account's properties
                for s in str(a).split(budse.str_delimiter):
                    fields = s.split(budse.tag_delimiter)
                    k = str(fields[0]).strip()
                    v = str(fields[1]).strip()

                    # Key/Tag
                    twi = QtGui.QTableWidgetItem('%s' % k)
                    twi.setTextAlignment(QtCore.Qt.AlignRight)
                    twi.setTextColor(QtGui.QColor('gray'))
                    self.ui.snapshot.setItem(row, 0, twi)
                    k = k.upper()   # For comparisons

                    # Value
                    twi = QtGui.QTableWidgetItem('%s' % v)
                    twi.setTextAlignment(QtCore.Qt.AlignLeft)
                    # Chop off the currency symbol for comparisons
                    if k == 'BALANCE' and float(v[1:]) < 0.00:  
                        twi.setTextColor(QtGui.QColor('red'))
                    self.ui.snapshot.setItem(row, 1, twi)
                    row += 1
                # Account delimiter (i.e., a blank line)
                self.ui.snapshot.setItem(row, 0, QtGui.QTableWidgetItem(''))
                row += 1
            self.ui.snapshot.setWordWrap(True)
            self.ui.snapshot.resizeRowsToContents()

    def account_changed(self, button):
        if not button.isChecked():
            self.whole_account.setChecked(False)
        else:
            self.deselect_accounts.setChecked(False)
        self.accounts_snapshot()
        self.do_search.emit()

    def make_deposit(self):
        deposit = DepositDialog(self.user, self.session)
        deposit.exec_()
        if deposit.success:
            self.transaction_made.emit()

    def make_withdrawal(self):
        withdrawal = WithdrawalDialog(self.user, self.session)
        withdrawal.exec_()
        if withdrawal.success:
            self.transaction_made.emit()

    def make_transfer(self):
        transfer = TransferDialog(self.user, self.session)
        transfer.exec_()
        if transfer.success:
            pass
        self.transaction_made.emit()

    def change_preferences(self):
        preferences = PreferencesDialog(self.user, self.session)
        preferences.exec_()

    def undo(self):
        print('undo')

    def refresh(self):
        if self.whole_account.isChecked():
            self.whole_account_snapshot()
        else:
            self.accounts_snapshot()
        self.do_search.emit()
