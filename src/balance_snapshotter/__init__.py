"""BalanceSnappshotter - module for eth-brownie used to take snapshots of token balances of accounts."""
import asyncio
from tabulate import tabulate
from typing import Union
from rich.console import Console
from .token_data import get_token_data
from brownie.network.contract import Contract
from brownie.network.account import Account
from brownie import (
    interface,
    accounts as b_accounts
)

__version__ = "0.3.0"

console = Console()
token_data = get_token_data()


def decimal_converter(amount: int = 0, decimals: int = 18) -> str:
    """
    Moves the decimal point for token amount.

    Parameters
    ----------
    amount: int
        The amount of tokens.
    decimals: int
        The decimals of the token.

    Returns
    -------
    str
        Amount of tokens divided by 10 to the power of `decimals`.
    """
    return "{:,.18f}".format(amount / 10 ** decimals)


class BalanceSnapshotter:
    """
    Main class of the module used to take, compare and manage snapshots.

    Parameters
    ----------
    _tokens: List[Union[brownie.network.contract.Contract, str]]
        List of tokens in either string from or badger token form.
    _accounts: List[Union[brownie.network.account.Account, str]]
        List of tokens in either string form or badger account form.
    loop: Optional[asyncio.BaseEventLoop]
        Asyncio loop that will be used in the creation of the snapshot.

    Attributes
    -----------
    tokens: List[brownie.network.contract.Contract]
        List of tokens.
    accounts: List[brownie.network.account.Account]
        List of accounts.
    snaps: List[dict]
        List of snapshots which are in dict form {"name": str, balances: Balances}
    loop: asyncio.BaseEventLoop
        Asyncio loop used to run snapshot coroutine.
    balance_event: asyncio.Event
        Event used to manage the flow of the snap method.
    """

    def __init__(self, _tokens: list[Union[Contract, str]], _accounts: list[Union[Account, str]], *, loop: asyncio.BaseEventLoop = None):
        # convert any raw addresses to proper token objects
        for i, token in enumerate(_tokens):
            if type(token) == str:
                _tokens[i] = interface.IERC20(token)

        # convert any raw addresses to proper account objects
        for i, account in enumerate(_accounts):
            if type(account) == str:
                _accounts[i] = b_accounts.at(account, force=True)

        self.tokens: list[Contract] = _tokens
        self.accounts: list[Account] = _accounts
        self.snaps: list[dict] = []

        self.loop: asyncio.BaseEventLoop = loop if loop else asyncio.get_event_loop()
        self.balance_event: asyncio.Event = asyncio.Event()

    def add_token(self, token: Union[Contract, str]):
        """
        Add a token to the list of tokens.

        If a token is provided as a string, it will be converted to brownie.network.contract.Contract.

        Parameters
        -----------
        token: Union[brownie.network.contract.Contract, str]
            The token that will be added
        """
        # if provided token is in string format, change it to Token object
        if type(token) == str:
            token = interface.IERC20(token)
        self.tokens.append(token)

    def add_account(self, account: Union[Account, str]):
        """
        Add an account to the list of accounts.

        If account is provided as a string, it will be converted to an account.

        Parameters
        -----------
        account: Union[brownie.network.account.Account, str]
            The account that will be added.
        """
        # Convert raw addresses into account objects
        if type(account) == str:
            account = b_accounts.at(account, force=True)
        self.accounts.append(account)

    def snap(self, name: str = "", print_snap: bool = False) -> dict[str, Union[str, 'Balances']]:
        """
        Take a snap of the current state of all the tokens of all the accounts.

        Optionally print out the snap in a table form.

        Parameters
        -----------
        name: str
            The name that will be assigned to the snap.
        print_snap: bool
            If True, snap will be printed out.

        Returns
        -------
        Dict[str, Union[str, Balances]]
            The snap that was taken. {"name": name, "balances": Balances}
        """
        # create a task if the loop is already running, otherwise run the loop until the async function completes.
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

        return snap

    async def _async_take_snapshot(self, name: str):
        """
        Function that gathers token balances for accounts in an asynchronous manner.

        The function will gather all the needed balanceOf calls into a list and through asyncio gather they will all
        be called at the same time, improving efficiency.

        Parameters
        -----------
        name: str
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

    def diff_last_two(self, print_diff: bool = True) -> str:
        """
        Create difference table of the last 2 snaps.

        Defaults to also printing out the table.

        Parameters
        ----------
        print_diff: bool
            If True prints out difference table, otherwise just returns it

        Returns
        -------
        str
            Generated difference table where balance is last snap balance minus second to last snap balance.

            Example:
            asset    account                                     balance
            -------  ------------------------------------------  -------------------------
            WBTC     0x5b5cF8620292249669e1DCC73B753d01543D6Ac7  2.361588530000000130
        """
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
                amount = decimal_converter(
                    after[token][account] - value,
                    decimals=token_data.get_decimals(token),
                )

                # ignore 0 balance
                if amount == 0:
                    continue

                table.append([token_data.get_symbol(token), account, amount])

        table = tabulate(table, headers=["asset", "account", "balance"])
        if print_diff:
            print(table)

        return table


class Balances:
    """
    Class used to store balances for snapshots.

    Attributes
    -----------
    balances: Dict[brownie.network.contract.Contract, Dict[brownie.network.account.Account, float]]
        Dictionary that contains the token balances of all the accounts.
    """

    def __init__(self):
        self.balances: dict[Contract, dict[Account, int]] = {}

    def set(self, token: Contract, account: Account, value: int):
        """
        Set the token balance value for an account.

        Parameters
        -----------
        token: brownie.network.contract.Contract
            The token.
        account: brownie.network.account.Account
            The account.
        value: int
            The amount of tokens.
        """
        if token not in self.balances:
            self.balances[token] = {}
        self.balances[token][account] = value

    def get(self, token: Contract, account: Account) -> int:
        """
        Get the token balance value for an account.

        Parameters
        -----------
        token: brownie.network.contract.Contract
            The token.
        account: brownie.network.account.Account
            The account.

        Returns
        -------
        int
            the token balance for an account.
        """
        return self.balances[token][account]

    def print(self):
        """
        Print out all the token balances of all the accounts.

        Output Example:
            asset    account                                       balance
            -------  ------------------------------------------  ---------
            WBTC     0x5b5cF8620292249669e1DCC73B753d01543D6Ac7    4.72318
        """
        table = []
        for token, accounts in self.balances.items():
            for account, value in accounts.items():
                amount = decimal_converter(value, decimals=token_data.get_decimals(token))

                # ignore 0 balance
                if amount == 0:
                    continue

                table.append(
                    [
                        token_data.get_symbol(token),
                        account.address,
                        decimal_converter(value, decimals=token_data.get_decimals(token))
                    ]
                )

        print(tabulate(table, headers=["asset", "account", "balance"]))
