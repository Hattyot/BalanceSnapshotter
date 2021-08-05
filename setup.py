import setuptools

setuptools.setup(
    name="balance_snapshotter",
    version="0.3",
    author="Hattyot",
    description="Module for eth-brownie used to take snapshots of token balances of accounts",
    url="https://github.com/Hattyot/BalanceSnapshotter",
    project_urls={
        "Bug Tracker": "https://github.com/Hattyot/BalanceSnapshotter/issues"
    },
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.9",
)