# BalanceSnapshotter
Module for eth-brownie used to take snapshots of token balances of accounts


## Requierments
```
python >= 3.9
```


## Install
### From pypi
```shell
pip3 install balance_snapshotter
```
### By cloning
```shell
git clone https://github.com/Hattyot/BalanceSnapshotter.git
pip3 install -e BalanceSnapshotter
```


## Example
```py
from balance_snapshotter import BalanceSnapshotter

...

snap = BalanceSnapshotter([wbtc], [account])
# tokens and accounts can also be given via addresses
# snap = BalanceSnapshotter(["0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599"], ["0x5b5cF8620292249669e1DCC73B753d01543D6Ac7"])
snap.snap(print_snap=True)

wbtc.transfer(account, 0.2, {"from": deployer})

snap.snap()
snap.diff_last_two()
```
```

```