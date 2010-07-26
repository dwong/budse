############################
# BUDget for Spam and Eggs (Budse)
#
# Version:
#     1.001
#
# Description:
#     Budse with a Command Line Interface (CLI)
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
import budse
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import desc, or_
import datetime
import os
import random

class BudseCLI(object):
    """Command Line Interface for Budse."""
    output_date = '%m/%d/%Y'
    # Actions that have meaning for all menus
    meta_actions = 'c - Cancel\nd - Done\nq - Quit Program'

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
            raise budse.CancelException('Cancel current menu')
        elif str(base_input).upper() == 'D':
            raise budse.DoneException('User is done with input')
        elif str(base_input).upper() == 'Q':
            raise SystemExit('Quitting Budse')
        try:
            expression = base_type(base_input)
        except Exception, e:
            raise budse.ConversionException("Couldn't convert %s to %s" %
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
        import re

        now = datetime.date.today()
        date = None
        prompt = ('%s? (default %s) ' %
                  (prompt, default_date.strftime('%m/%d/%Y')))
        while date is None:
            spam = self._handle_input(prompt)
            if spam == '':
                date = default_date
            else:
                splits = re.split('[-/]', spam)
                if len(splits) == 1:
                    try:
                        # DD (just the day)
                        date = datetime.date(now.year, now.month, int(splits[0]))
                    except ValueError:
                        pass
                elif len(splits) == 2:
                    try:
                        # MM/DD
                        date = datetime.date(now.year,
                                             int(splits[0]),
                                             int(splits[1]))
                    except ValueError, e:
                        pass
                elif len(splits) == 3:
                    try:
                        if int(splits[2]) < 100:
                            # MM/DD/YY
                            date = datetime.date(int(splits[2]) +
                                                 now.year // 100 * 100,
                                                 int(splits[0]),
                                                 int(splits[1]))
                        else:
                            # MM/DD/YYYY
                            date = datetime.date(int(splits[2]),
                                                 int(splits[0]),
                                                 int(splits[1]))
                    except ValueError:
                        try:
                            # YYYY-MM-DD
                            date = datetime.date(int(splits[0]),
                                                 int(splits[1]),
                                                 int(splits[2]))
                        except ValueError:
                            pass
                if date is None:
                    print("'%s' is not a valid date" % spam)
        return date

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
            except budse.ConversionException:
                print 'Invalid value - %s' % random.choice(budse.fun)
        # Only keep 2 decimal places of precision for these floats
        if type==float:
            return round(amount, 2)
        else:
            return amount
            
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
        choice = self._ask_string('Search\n\n1 - Date Range\n2 - Date\n3 - '
                                  'ID\n4 - Keywords\n%s\n\nChoice: ' %
                                  BudseCLI.meta_actions)
        limit = 10
        if choice == '1':
            begin_date = self._ask_date(prompt='Start of transactions')
            end_date = self._ask_date(prompt='End of transactions')
            return self.session.query(budse.Transaction).\
                filter(budse.Transaction.date >= begin_date).\
                filter(budse.Transaction.date <= end_date).\
                filter(budse.Transaction.parent == None).\
                order_by(desc(budse.Transaction.date))
        elif choice == '2':
            date = self._ask_date(prompt='Transaction date')
            return self.session.query(budse.Transaction).\
                filter(budse.Transaction.date == date).\
                filter(budse.Transaction.parent == None).\
                order_by(desc(budse.Transaction.date))
        elif choice == '3':
            id = self._ask_amount('Unique ID of transaction: ', int)
            return [self.session.query(budse.Transaction).\
                filter(budse.Transaction.id == id).\
                filter(budse.Transaction.parent == None).one()]
        elif choice == '4':
            done = False
            print 'Transaction description matching any of the keywords:\n'
            keywords = []
            while not done:
                keywords.append('%%%s%%' % self._ask_string('Keyword: '))
                done = self._confirm('Done entering keywords?', True)
            if self._confirm('Limit transactions to search for?'):
                limit = self._ask_amount(type=int, prompt='Limit: ')
            return self.session.query(budse.Transaction).\
                filter(budse.Transaction.parent == None).\
                filter(or_(*[budse.Transaction.description.contains(keyword) \
                                 for keyword in keywords])).\
                order_by(desc(budse.Transaction.date))[:limit]
        
    def output_transactions(self, transactions):
        """Output a list of transactions.

        Keyword arguments:
        transactions -- List of Transaction objects to output
        
        """
        # Tags to not print in children transactions
        restricted = ['ACTIVE', 'TRANSACTION DATE']
        try:
            for parent_transaction in transactions:
                if parent_transaction.id is not None:
                    print('------Transaction ID: %d------' %
                          parent_transaction.id)
                print((str(parent_transaction).\
                       replace(budse.str_delimiter, '\n')).\
                      replace(budse.tag_delimiter, ':'))
                if parent_transaction.children:
                    print('Sub-transactions:')
                for transaction in parent_transaction.children:
                    action = amount = account = description = ''
                    for field in str(transaction).split(budse.str_delimiter):
                        field_information = field.split(budse.tag_delimiter)
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
        except TypeError:
            pass

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
                          '\n%s\n%s\n\nInput: ' % (BudseCLI.meta_actions,
                                                   status))
                status = ''
                try:
                    choice = self._ask_string(prompt)
                except budse.DoneException:
                    break
                except budse.CancelException:
                    continue
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
                    status = 'Invalid choice - %s' % random.choice(budse.fun)
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
                            budse.Deduction(user=self.user, date=date,
                                            amount=amt, description=desc))
            try:
                deposit = budse.Deposit(date=date, user=self.user,
                                        amount=amount, description=description,
                                        account=account, deductions=deductions)
            except budse.FundsException, e:
                self.status = str(e)
                self.session.rollback()
                return
            except budse.DuplicateException, e:
                clear_screen()
                if (len(e.duplicates)==1):
                    plural = ''
                else:
                    plural = 's'
                print('%s:\n== Duplicate%s ==\n' % (e, plural))
                self.output_transactions(e.duplicates)
                if self._confirm('Ignore duplicate%s?' % plural, False):
                    deposit = budse.Deposit(date=date, user=self.user,
                                       amount=amount, description=description,
                                       account=account, deductions=deductions,
                                       duplicate_override=True)
                else:
                    self.status = '%s.  Ignoring transaction%s.' % (e, plural)
                    self.session.rollback()
                    return

            self.session.add(deposit)
            indent = '  '
            clear_screen()
            print('\n==  Deposit Details  ==\n')
            self.output_transactions([deposit])
            if self._confirm('Execute deposit?', True):
                self.session.commit()
                if deposit.account is None:
                    target = 'Whole Account'
                else:
                    target = deposit.account.name
                self.status = ('Successfully made deposit of $%0.2f '
                               'into %s' % (deposit.amount, target))
            else:
                self.session.rollback()
                self._clear_status()
                self.status = 'Deposit canceled'
        except (budse.CancelException, budse.DoneException):
            self.session.rollback()
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
            withdrawal = budse.Withdrawal(user=self.user, amount=amount,
                                          date=date, description=description,
                                          account=account)
        except (budse.CancelException, budse.DoneException):
            self.session.rollback()
            self._clear_status()
            self.status = 'Withdrawal canceled'
            return
        except budse.DuplicateException, e:
            clear_screen()
            if (len(e.duplicates)==1):
                plural = ''
            else:
                plural = 's'
            print('%s:\n== Duplicate%s ==\n' % (e, plural))
            self.output_transactions(e.duplicates)
            if self._confirm('Ignore duplicate%s?' % plural, False):
                withdrawal = budse.Withdrawal(user=self.user, amount=amount,
                                           date=date, description=description,
                                           account=account,
                                           duplicate_override=True)
            else:
                self.status = '%s.  Ignoring transaction%s.' % (e, plural)
                self.session.rollback()
                return

        self.session.add(withdrawal)
        clear_screen()
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

    def make_transfer(self):
        """Execute a transfer between accounts.
        
        Essentially this will just be a deposit and a withdrawal of the
        same amount, but the idea of a transfer is useful to the user
        because the action seems more atomic to them.

        Also the two actions can be grouped together with the
        same root_transaction_id so that an undo would yield the proper result.

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
            transfer = budse.Transfer(user=self.user, amount=amount, date=date,
                                      description=description,
                                      to_account=deposit_account,
                                      from_account=withdrawal_account)
        except (budse.CancelException, budse.DoneException):
            self.session.rollback()
            self._clear_status()
            self.status = 'Transfer canceled'
            return
        except budse.DuplicateException, e:
            clear_screen()
            if (len(e.duplicates)==1):
                plural = ''
            else:
                plural = 's'
            print('%s:\n== Duplicate%s ==\n' % (e, plural))
            self.output_transactions(e.duplicates)
            if self._confirm('Ignore duplicate%s?' % plural, False):
                transfer = budse.Transfer(user=self.user, amount=amount,
                                          date=date, description=description,
                                          to_account=deposit_account,
                                          from_account=withdrawal_account,
                                          duplicate_override=True)
            else:
                self.status = '%s.  Ignoring transaction%s.' % (e, plural)
                self.session.rollback()
                return

        clear_screen()
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
    
    def reverse_transaction(self):
        """Undo whatever effect a transaction group had."""
        id = self._ask_amount('Transaction ID: ', int)
        try:
            transaction = self.session.query(budse.Transaction).\
                          filter(budse.Transaction.id == id).\
                          filter(budse.Transaction.parent == None).one()
        except NoResultFound:
            self.status = 'ID is not a valid root transaction ID'
            return
        clear_screen()
        self.output_transactions([transaction])
        if self._confirm('Reverse Transaction? ', default=True):
            transaction.status = not transaction.status
            app.status = 'Transaction %d reversed' % id
            self.session.commit()
        else:
            app.status = 'Transaction %d not reversed' % id

    def print_balance(self, account=None, include_user_total=True, 
                      include_all=False, include_deactive=False):
        """The balance of a specific account.

        Keyword parameters:
        account -- Account object to get balance for (default None)
        include_user_total -- Whether or not to include the entire user total
            (default True)
        include_all -- Supercedes account parameter and will print out all
            account totals (default False)
        include_deactive -- Include deactivated accounts (default False)
        """
        if account is None:
            totals = []
            longest_name = 0
            longest_total = 4  # length of '0.00'
            user_total = 0.00
            for account in self.user.accounts:
                if account.status == False and not include_deactive:
                    continue
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
                      (BudseCLI.meta_actions, self.status))
            clear_screen()
            try:
                choice = self._ask_string(prompt)
                if choice == '1':
                    self._create_report_by_date()
                    break
                # TODO add Excel report using pyExcelerator
                # TODO account report for dates
                else:
                    self.status = 'Invalid choice - %s' % random.choice(budse.fun)
            except (budse.CancelException, budse.DoneException):
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
                               delimiter,
                               (begin_date.strftime(BudseCLI.output_date)),
                               (end_date.strftime(BudseCLI.output_date))))
            parent_transactions = self.session.query(budse.Transaction).\
                filter(budse.Transaction.date >= begin_date).\
                filter(budse.Transaction.date <= end_date).\
                filter(budse.Transaction.parent == None).\
                filter(budse.Transaction.status == True).\
                order_by(budse.Transaction.date).all()
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
                        if transaction.action == budse.Transaction.DEPOSIT:
                            deposits += transaction.amount
                            net += transaction.amount
                            action = 'Deposit'
                        elif transaction.action == \
                                 budse.Transaction.WITHDRAWAL:
                            withdrawals += transaction.amount
                            net -= transaction.amount
                            action = 'Withdrawal'
                        account_summary[transaction.account.id] = \
                                     (account_name, deposits, withdrawals, net)
                    elif transaction.action == budse.Transaction.DEDUCTION:
                        deductions += transaction.amount
                        action = 'Deduction'
                        account_name = 'N/A'
                    elif transaction.action == budse.Transaction.TRANSFER:
                        account_name = 'N/A'
                        action = 'Transfer'
                    else:
                        action = 'Informational'
                        account_name = 'Whole Account'
                    transaction_log += ('%s%s%s%s%0.2f%s%s%s%s\n' % 
                                        (transaction.date.strftime(
                                            BudseCLI.output_date),
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
                    print('Invalid path - %s' % random.choice(budse.fun))
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
                      (status_modification, BudseCLI.meta_actions, self.status))
            clear_screen()
            try:
                action = self._ask_string(prompt)
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
                    self.status = 'Invalid action - %s' % random.choice(budse.fun)
                self.session.commit()
            except budse.CancelException:
                self._clear_status()
                self.status = 'Canceled modifying preferences'
                break
            except budse.DoneException:
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
                        user.name = self._ask_string('New login name: ')
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
            except (budse.CancelException, budse.DoneException):
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
                except (budse.CancelException, budse.DoneException):
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
                          (deduction_list, BudseCLI.meta_actions, status))
            status = ''
            try:
                choice = self._ask_string(prompt)
            except budse.DoneException:
                if deductions_changed:
                    deductions_changed = True
                    user.deductions = deductions
                    self.session.commit()
                else:
                    deductions_changed = False
                break
            except budse.CancelException:
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
                        option = self._ask_amount(prompt, int)
                    except budse.DoneException:
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
                    status = 'Invalid Choice - %s' % random.choice(budse.fun)
            except (budse.CancelException, budse.DoneException):
                status = 'Canceled action'
                continue
            except ValueError:
                status = 'Invalid Choice - %s' % random.choice(budse.fun)
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
        except (budse.CancelException, budse.DoneException):
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
                                              BudseCLI.meta_actions,
                                              self.status))
                      
            try:
                action = self._ask_string(prompt)
            except (budse.CancelException, budse.DoneException):
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
                    self.status = 'Invalid action - %s' % random.choice(budse.fun)
                self.session.commit()
                if check_reconfiguration and self.user.whole_account_actions:
                    if self.reconfigure_accounts(self.user.accounts):
                        self.status = "Reconfigured all of the user's accounts"
            except (budse.CancelException, budse.DoneException):
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
                    account.name = self._ask_string('New name: ')
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
        except (budse.CancelException, budse.DoneException):
            pass
        if not description_modified:
            self.status = 'Kept existing description'

    def modify_account_type(self, account):
        """Change the type of the account, used for whole account actions."""
        type_modified = False
        if account.percentage_or_fixed is not None:
            if account.percentage_or_fixed == budse.Account.PERCENTAGE:
                if self._confirm('Change to fixed amount?', True):
                    account.percentage_or_fixed = budse.Account.FIXED
                    self.status = "'%s' is now a fixed account" % account.name
                    type_modified = True
            else:
                if self._confirm('Change to percentage amount?', True):
                    account.percentage_or_fixed = budse.Account.PERCENTAGE
                    self.status = ("'%s' is now a percentage account" %
                                   account.name)
                    type_modified = True
        else:
            status = ''
            while account.percentage_or_fixed is None:
                prompt = ("Account Type:\nP'ercentage\nF'ixed\n%s\nChoice: " %
                          status)
                status = ''
                choice = self._ask_string(prompt).upper()
                if choice.startswith('P'):
                    account.percentage_or_fixed = budse.Account.PERCENTAGE
                    type_modified = True
                    self.status = ("'%s' is now a percentage account" %
                                   account.name)
                elif choice.startswith('F'):
                    account.percentage_or_fixed = budse.Account.FIXED
                    type_modified = True
                    self.status = "'%s' is now a fixed account" % account.name
                else:
                    status = 'Invalid choice - %s' % random.choice(budse.fun)
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
        if account.percentage_or_fixed == budse.Account.PERCENTAGE:
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

        if account.percentage_or_fixed == budse.Account.PERCENTAGE:
            prompt += 'Percentage for whole account actions: '
        else:
            prompt += 'Fixed amount (dollars) for whole account actions: '
        while 1:
            account.amount = self._ask_amount(prompt)
            if (account.percentage_or_fixed == budse.Account.PERCENTAGE and
                (0 > (account.amount * 100) or (account.amount * 100) > 100)):
                print('Out of range! (Must be in the range 0-100)')
                continue
            if account.percentage_or_fixed == budse.Account.PERCENTAGE:
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
                choice = self._ask_string(prompt).upper()
                if choice.startswith('G'):
                    account.affect_gross = True
                    gross_modified = True
                    self.status = "'%s' now affects the gross" % account.name
                elif choice.startswith('N'):
                    account.affect_gross = False
                    gross_modified = True
                    self.status = "'%s' now affects the net" % account.name
                else:
                    status = 'Invalid choice - %s' % random.choice(budse.fun)
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
            accounts = self.session.query(budse.Account).\
                       filter(budse.Account.user == self.user).\
                       filter(budse.Account.status == True).all()
        else:
            accounts = self.session.query(budse.Account).\
                       filter(budse.Account.user == self.user).all()
        clear_screen()
        print '\nAccounts: '
        for index, account in zip(range(len(accounts)), accounts):
            print('%d - %s (%s)' %
                  (index+1, account.name, account.description))
        account = None
        while account is None:
            try:
                # Pretty indexes
                index = self._ask_amount('\n%s' % prompt, int) - 1 
                if index >= 0 and index < len(accounts):
                    account = accounts[index]
                else:
                    print('Invalid choice - %s' % random.choice(budse.fun))
            except budse.ConversionException:
                print('Invalid choice - %s' % random.choice(budse.fun))
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
            budse._require_reconfiguration(accounts, active_only=active_only)
        if not gross_reconfig and not net_reconfig:
            return False
        gross_percentage = budse.filter_accounts(accounts, gross=True,
                                                 fixed=False,
                                                 active_only=active_only)
        net_percentage = budse.filter_accounts(accounts, gross=False,
                                               fixed=False,
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
                choice = self._ask_amount(prompt, int) - 1 # Pretty index
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
                    status = 'Invalid choice - %s' % random.choice(budse.fun)
            except (budse.CancelException, budse.DoneException):
                status = 'Canceled change, continue to reconfigure'
            gross_reconfig, trash = budse._require_reconfiguration(
                gross_percentage, check_net=False, active_only=active_only)
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
                                                      percentage_or_fixed=
                                                      budse.Account.PERCENTAGE)
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
                    choice = self._ask_amount(prompt, int) - 1 # Pretty index
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
                        status = 'Invalid choice - %s' % random.choice(budse.fun)
                except (budse.CancelException, budse.DoneException):
                    status = 'Canceled change, continue to reconfigure'
            trash, net_reconfig = budse._require_reconfiguration(
                net_percentage, check_gross=False, active_only=active_only)
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
        account = budse.Account(user)
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
                if account.percentage_or_fixed == budse.Account.PERCENTAGE:
                    self.modify_account_gross(account)
                else:
                    account.affect_gross = False   # Deprecate fixed & gross
        except (budse.CancelException, budse.DoneException):
            self.session.rollback()
            assert account not in self.session
            return None
        clear_screen()
        account_repr = '%s' % account
        if not self._confirm('%s\nCreate account? ' %
                             (account_repr.replace(budse.str_delimiter,'\n')).\
                             replace(budse.tag_delimiter, ':'), True):
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
                self.session.query(budse.User).\
                    filter(budse.User.name == name).one()
            except NoResultFound:
                try:
                    new_user = budse.User(name)
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
            except budse.CancelException:
                pass
            finally:
                done = self._confirm("Done creating accounts for user '%s'?" %
                                     new_user.name)
            clear_screen()
        clear_screen()
        completed_accounts = []
        for acct in accounts:
            if acct is not None:
                completed_accounts.add(acct)
        self.reconfigure_accounts(completed_accounts, active_only=False)
        if self._confirm(('%s\nCreate user %s?' %
                          ((str(new_user)).replace(budse.str_delimiter, '\n').\
                           replace(budse.tag_delimiter, ':'),
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
            self.session.query(budse.User).one()
        except NoResultFound:
            while self.user is None:
                try:
                    self.user = self._create_user(newbie=True)
                except (budse.CancelException, budse.DoneException):
                    print("How sad, you're done here.")
                    self.session.rollback()
        else:
            while self.user is None:
                try:
                    username = self._ask_string(prompt)
                # Ignore C'ancel and D'one at this prompt
                except budse.CancelException:
                    username = 'C'
                except budse.DoneException:
                    username = 'D'
                try:
                    self.user = self.session.query(budse.User).\
                        filter(budse.User.name == username).one()
                except NoResultFound:
                    if username == 'N':
                        try:
                            self.user = self._create_user()
                        except (budse.CancelException, budse.DoneException):
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
    if budse.debug:
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
    session = budse.initialize()
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
            except (budse.CancelException, budse.DoneException):
                continue
            else:
                done = True
    clear_screen()
    while 1:
        prompt = ('Main Menu\n\n1 - Deposit\n2 - Withdraw\n3 - Balance\n'
                  '4 - Transfer\n5 - Search\n6 - Create Report\n'
                  '7 - Undo Transaction\n8 - Preferences\nq - Quit\n%s\n\n'
                  'Action: ' % app.status)
        try:
            action = app._ask_string(prompt)
        except (budse.CancelException, budse.DoneException):
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
            try:
                while True:
                    clear_screen()
                    app.output_transactions(app.search())
                    raw_input(continue_string)
            except (budse.CancelException, budse.DoneException):
                app.status = 'Canceled search'
        elif action == '6':
            clear_screen()
            app.create_report()
        elif action == '7':
            try:
                app.reverse_transaction()
            except (budse.CancelException, budse.DoneException):
                app.status = 'Canceled reversal'
        elif action == '8':
            app.modify_user_settings()
        else:
            app.status = 'Invalid action - %s' % random.choice(budse.fun)
        clear_screen()
