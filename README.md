# BalanceSnapshotter
A helper module for the badger system and eth-brownie used to take snapshots of token balances of accounts


## Requierments
```
python >= 3.9
```


## Install
### From pypi
```shell
pip3 install balance_snapshotter
```
### From source
```shell
git clone https://github.com/Hattyot/BalanceSnapshotter.git
pip3 install -e BalanceSnapshotter
```


## Example
```py
from balance_snapshotter import BalanceSnapshotter
from brownie import interface, accounts

# constants
wbtc_address = "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599"
account_address = "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599"

# Create account and token objects
account = accounts.at(account_address, force=True)
wbtc = interface.IERC20(account_address)

# Initialize BalanceSnapshotter() object with token contract(s) and account(s)
snap = BalanceSnapshotter([wbtc], [account])
# Tokens and accounts can also be provided directly via addresses instead of as contract and account objects
# snap = BalanceSnapshotter([wbtc_address], [account_address])

# Create a transaction
wbtc.transfer(account, wbtc.balanceOf(wbtc) // 2, {"from": wbtc})

# Take a snapshot and print it out in a table form
snap.snap(print_snap=True)

# Create another transaction
wbtc.transfer(account, wbtc.balanceOf(wbtc) // 2, {"from": wbtc})

# Take another snapshot
snap.snap()
# print out the difference of the last 2 snapshots
snap.diff_last_two()
```