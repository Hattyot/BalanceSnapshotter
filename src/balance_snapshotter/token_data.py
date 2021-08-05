"""Module for caching certain data of tokens to improve efficiency."""
from typing import Union
from brownie.network.contract import Contract
from brownie import interface

token_data = None


class TokenData:
    """Class that manages all the token data."""

    def __init__(self):
        self.data: dict[str, dict[str, Union[str, int]]] = {}

    def get_decimals(self, token: Union[Contract, str]) -> int:
        """
        Fetch token decimals from cache or from chain on first lookup.

        Parameters
        ----------
        token: Union[:class:`brownie.network.contract.Contract`, :class:`str`])
            The token as a contract object or token address.

        Returns
        -------
        :class:`int`
            Token decimals.
        """
        return self.fetch_token_data(token)['decimals']

    def get_symbol(self, token: Union[Contract, str]) -> str:
        """
        Fetch token symbol from cache or from chain on first lookup.

        Parameters
        ----------
        token: Union[:class:`brownie.network.contract.Contract`, :class:`str`])
            The token as a contract object or token address.

        Returns
        -------
        :class:`str`
            Token symbol.
        """
        return self.fetch_token_data(token)['symbol']

    def get_name(self, token: Union[Contract, str]) -> str:
        """
        Fetch token name from cache or from chain on first lookup.

        Parameters
        ----------
        token: Union[:class:`brownie.network.contract.Contract`, :class:`str`])
            The token as a contract object or token address.

        Returns
        -------
        :class:`str`
            Token name.
        """
        return self.fetch_token_data(token)['name']

    def fetch_token_data(self, token: Union[Contract, str]) -> dict[str, Union[str, int]]:
        """
        Return cached token data or data from chain on first lookup.

        Parameters
        ----------
        token: Union[:class:`brownie.network.contract.Contract`, :class:`str`])
            The token as a contract object or token address.

        Returns
        -------
        Dict[:class:`str`, Union[:class:`str`, :class:`int`]]
            All the token data in dict form {"name": name, "symbol": symbol, "decimals": decimals}
        """
        # first check if token data is already cached, if not, cache it
        address = token.address if isinstance(token, Contract) else token
        if address not in self.data:
            # only convert token to Contract object if actually needed
            if isinstance(token, str):
                token = interface.IERC20(token)

            self.data[token.address] = {
                'name': token.name(),
                'symbol': token.symbol(),
                'decimals': token.decimals()
            }

        return self.data[token.address]


def get_token_data() -> TokenData:
    """
    Get an active TokenData instance.

    Creates one if instance has not yet been established.
    """
    global token_data

    if token_data is None:
        token_data = TokenData()

    return token_data
