# Python Utility for creating UTXO snapshot from Bitcoin and Zclassic mainnet's

### To run, you should run the following commands:

This is a python utility that will create a snapshot of Bitcoin and Zclassic's Unspent Transaction Outputs (UTXO). 

Below are some of the following commands/arguments you can pass to the python utility 

**Bitcoin Data Directory:** `--bitcoind_datadir=`

Here you should pass the path to your local bitcoin data directory where bitcoin blocks are stored. For example:

`--bitcoind_datadir="/root/.bitcoin"`

**Utxo Snapshot Directory:** `--utxo_dir=`

Here you must declare where the python utility where save the snapshot results. For example:

`root/snapshot_here`

**Segwit compatibility:** `--transform_segwit=`

You should always pass this to convert segwit addresses for non-segwit compatible chains. For example:

`--transform_segwit=1`

**Blockchain Reindexing:** `--reindex=`

If you want to re-index your chain, pass this argument as true. For example:

`'--reindex'=1`

**Executable Daemon:** `--bitcoind=`

Here point to your Bitcoin or Zclassic Daemon/executable/full-node. For example:

`--bitcoind="/root/bitcoin/src/bitcoind"`

`--bitcoind="/root/zclassic/src/zcashd"`

**Utxo Block Height Specification:** `--blockheight=`

Specify up to what height you want to snapshot the UTXO's. For example:

`--blockheight=53600`

**Z-Address Joinspliting:** `--z_address=`

Turn on/off snapshot of Joinsplit's. For example:

`--z_address=1`

**Snapshot Coin Specification:** `--coin=`

Here you should choose what coin you are snapshoting, choose Bitcoin or ZClassic, only these 2 are supported at the moment. For example:

`--coin="bitcoin"` or `--coin="zcl"`

**File Start Number:** `--file_num=`

Specify what file number to start on. For example:

`--file_num=25`

**Network Specification:** `--network=`

Here declare Mainnet or Testnet, only these two are supported at the moment. For example,

`--network='mainnet'` or `--network='testnet'`

Below is an example of how the python utility is ran:

```bash
./dump.py --bitcoind_datadir="/home/user/zcl-test-blocks-2/testnet3" /home/user/zcl-test-blocks-2/result --verbose=1 --reindex=1 --bitcoind /home/user/bitcoin/src/bitcoind --blockheight=10000 --maxutxos=3500 --file_num=1 --z_address=1 --network=testnet --coin=zcl
```


