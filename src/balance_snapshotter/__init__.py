import asyncio
from tabulate import tabulate
from typing import Union
from rich.console import Console
from brownie import *

console = Console()


def val(amount=0, decimals=18):
    return "{:,.18f}".format(amount / 10 ** decimals)


class Token:
    """
    Class used for making certain values of a token more easily accessible.

    Attributes
    -----------
    _token: :class:`brownie.network.contract.Contract`
        The actual token.
    address: :class:`str`
        Address of the token.
    name: :class:`str`
        Name of the token.
    symbol: :class:`str`
        Symbol of the token.
    decimals: :class:`int`
        Decimals of the token.
    """
    def __init__(self, token):
        """Constructor for the Token class."""
        self._token = token

        self.address = self._token.address
        self.name = self._token.name()
        self.symbol = self._token.symbol()
        self.decimals = self._token.decimals()

    def balanceOf(self, *args, **kwargs):
        """Redirects the balanceOf function call to the actual token."""
        return self._token.balanceOf(*args, **kwargs)

    def __hash__(self):
        """Magic method for hashing the token class."""
        return hash(self.address)

    def __eq__(self, other):
        """Checks if token is equal to other value."""
        if type(other) == str:
            return self.address == str
        elif type(other) == Token:
            return other == self
        else:
            return other == self._token


class BalanceSnapshotter:
    """
    BalanceSnapshotter class, main class of the module used to take and manage snapshots.

    Attributes
    -----------
    tokens: List[:class:`Token`]
        List of tokens converted to :class:`Token`.
    accounts: List[:class:`brownie.network.account.Account`]
        List of accounts.
    snaps: List[:class:`dict`]
        List of snapshots which are in dict form {"name": :class:`str`, balances: :class:`Balances`}
    loop: :class:`asyncio.Loop`
        Asyncio loop used to run snapshot coroutine.
    balance_event: :class:`asyncio.Event`
        Event used to regulate when snapshot code needs to move forward.
    """
    def __init__(self, _tokens: list, _accounts: list, *, loop=None):
        # convert any raw addresses to proper token objects
        for i, token in enumerate(_tokens):
            if type(token) == str:
                _tokens[i] = interface.IERC20(token)

        # convert any raw addresses to proper account objects
        for i, account in enumerate(_accounts):
            if type(account) == str:
                _accounts[i] = accounts.at(account, force=True)

        self.tokens: list[Token] = [Token(token) for token in _tokens]
        self.accounts = _accounts
        self.snaps = []

        self.loop = loop if loop else asyncio.get_event_loop()
        self.balance_event = asyncio.Event()

    def add_token(self, token):
        """
        Adds a token to the list of tokens. If a token is provided as a string, it will be converted to :class:`Token`.

        Parameters
        -----------
        token: Union[:class:`brownie.network.contract.Contract`, :class:`str`]
            The token that will be added
        """
        if type(token) == str:
            token = interface.IERC20(token)
            token = Token(token)
        self.tokens.append(token)

    def add_account(self, account):
        """
        Adds an account to the list of accounts. If account is provided as a string, it will be converted to an account.

        Parameters
        -----------
        account: Union[:class:`brownie.network.account.Account`, :class:`str`]
            The account that will be added.
        """
        # Convert raw addresses into account objects
        if type(account) == str:
            account = accounts.at(account, force=True)
        self.accounts.append(account)

    def snap(self, name="", print_snap=False):
        """
        Main snap function that will create snap task or will run the loop if needed.

        Parameters
        -----------
        name: :class:`str`
            The name that will be assigned to the snap
        print_snap: :class:`bool`
            If True, snap will be printed out
        """
        if self.loop.is_running():
            self.loop.create_task(self._async_take_snapshot(name))
        else:
            self.loop.run_until_complete(self._async_take_snapshot(name))

        while not self.balance_event.is_set():
            pass

        self.balance_event.clear()
        snap = self.snaps[-1]
        balances = snap['balances']

        if print_snap:
            if name != "":
                console.print(
                    "[green]== Balances: {} ==[/green]".format(
                        name,
                    )
                )
            balances.print()

    async def _async_take_snapshot(self, name):
        """
        Function that gathers token balances for accounts in an asynchronous manner.
        The code will gather all the needed balanceOf calls into a list and through asyncio they will all be called
        at the same time, improving efficiency.

        Parameters
        -----------
        name: :class:`str`
            The name that will be assigned to the snap
        """
        balances = Balances()

        async def set_balance(_token, _account):
            value = _token.balanceOf(_account)
            balances.set(_token, _account, value)

        futures = []
        for token in self.tokens:
            for account in self.accounts:
                future = set_balance(token, account)
                futures.append(future)

        await asyncio.gather(*futures)

        self.snaps.append({"name": name, "balances": balances})
        self.balance_event.set()

    def diff_last_two(self):
        """Prints out the difference between the last 2 snapshots."""
        if len(self.snaps) < 2:
            raise Exception("Insufficient snaps have been taken to compare last two")

        before_snap = self.snaps[-2]
        after_snap = self.snaps[-1]

        if before_snap["name"] != "" and after_snap["name"] != "":
            console.print(f'[green]== Comparing Balances: {before_snap["name"]} and {after_snap["name"]} ==[/green]')
        else:
            console.print("[green]== Comparing Balances: Latest two snapshots ==[/green]")

        before = before_snap['balances'].balances
        after = after_snap['balances'].balances

        table = []
        for token, accounts in before.items():
            for account, value in accounts.items():
                amount = (
                    val(
                        after[token][account] - value,
                        decimals=token.decimals,
                    ),
                )

                # ignore 0 balance
                if amount == 0:
                    continue

                table.append([token.symbol, account, amount])

        print(tabulate(table, headers=["asset", "account", "balance"]))


class Balances:
    """
    Class used to store balances for snapshots.

    Attributes
    -----------
    balances: Dict[:class:`Token`, Dict[:class:`brownie.network.account.Account`, :class:`float`]]
        Dictionary that contains the token balances of all the accounts.
    """
    def __init__(self):
        self.balances = {}

    def set(self, token, account, value):
        """
        Set the token balance value for an account.

        Parameters
        -----------
        token: :class:`Token`
            The token.
        account: :class:`brownie.network.account.Account`
            The account.
        value: :class:`float`
            The amount of tokens.
        """
        if token not in self.balances:
            self.balances[token] = {}
        self.balances[token][account] = value

    def print(self):
        """Prints out the all the token balances of all the accounts."""
        table = []
        for token, accounts in self.balances.items():
            for account, value in accounts.items():
                amount = val(value, decimals=token.decimals)

                # ignore 0 balance
                if amount == 0:
                    continue

                table.append(
                    [
                        account.address,
                        val(value, decimals=token.decimals),
                        token.symbol,
                    ]
                )

        print(tabulate(table, headers=["asset", "account", "balance"]))
