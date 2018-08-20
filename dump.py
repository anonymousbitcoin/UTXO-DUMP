#!/usr/bin/env python

from argparse import ArgumentParser
from os.path import isdir

from utxo.dump import dump_utxos, snap_utxos, dump_transactions

parser = ArgumentParser()
parser.add_argument('--bitcoind_datadir', type=str, required=True)
parser.add_argument('utxo_dir')

parser.add_argument('--nperfile', type=int, default=10E3)
parser.add_argument('--transform_segwit', type=int, default=0)

# to run bitcoind with -reindex-chainstate and -stopatheight provide all three
parser.add_argument('--reindex', type=int, default=0)
parser.add_argument('--bitcoind')
parser.add_argument('--blockheight', type=int)
parser.add_argument('--chainstate_version', type=int, default=15)

# anon
parser.add_argument('--z_address', type=int, default=0)
parser.add_argument('--t_address', type=int, default=0)
parser.add_argument('--coin', type=str, default="zcl")
parser.add_argument('--file_num', type=int, default=1)
parser.add_argument('--network', type=str, default="mainnet")

# debugging options
parser.add_argument('--verbose', type=int, default=0)
parser.add_argument('--maxutxos', type=int, default=0)

args = parser.parse_args()


if not isdir(args.utxo_dir):
    raise Exception("invalid utxo_dir")

if not isdir(args.bitcoind_datadir):
    raise Exception("invalid bitcoind_datadir")

if(args.reindex or args.bitcoind or args.blockheight):
    assert args.reindex and args.bitcoind is not None and args.blockheight >= 0
    snap_utxos(args.bitcoind, args.bitcoind_datadir, args.blockheight)


dump_transactions(datadir=args.bitcoind_datadir, output_dir=args.utxo_dir, file_size=args.nperfile, convert_segwit=args.transform_segwit, maxT=args.maxutxos, debug=args.verbose, file_num=args.file_num, z_address=args.z_address, network=args.network, coin=args.coin, t_address=args.t_address)
