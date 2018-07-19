import csv
import os
import struct

from binascii import hexlify

import pycoin.key.Key as Key
from pycoin.encoding import a2b_hashed_base58

from utxo.chainstate import ldb_iter
from utxo.script import unwitness
from utxo.util import new_utxo_file, utxo_file_name
from blockdb import read_blockfile


def snap_utxos(bitcoind, bitcoind_datadir, stop_block):

    cmd = "{} -reindex-chainstate -datadir={} -stopatheight={}".format(
        bitcoind, bitcoind_datadir, stop_block)
    print("running " + cmd)
    os.system(cmd)


def dump_joinsplits(datadir, output_dir, n, maxT=0):
    joinsplits = read_blockfile("z-blocks/blocks/blk00000.dat", bytearray.fromhex('fa 1a f9 bf'))
    i = 0
    k = 1
    print('new file')
    f = new_utxo_file(output_dir, k)

    print('new_joinsplit path: ', f)
    print("Size of joinsplits: %d" % len(joinsplits))

    for value in joinsplits:
        print("WRITINGGGGGGG")
        print("VALUE:")
        print(int(value.encode('hex'), 16))
        # amt, script = value
        print("LENGTH:")
        print(len(value))
        f.write(str(len(value)))
        f.write(value)
        f.write('\n')
        i += 1
        if i ==3:
            f.close()
            break
        if i % n == 0:
            k += 1
            print('new file: {}'.format(k))
            f.close()

    print("\nREADINGGGGGGG")
    t = open("z-dump/utxo-00001.bin", "r+b")
    stringRes=str(t.read(4))
    # print(int(stringRes.encode('hex'), 16))
    print(stringRes)

    print 'End of dump_joinsplits function'



def dump_utxos(datadir, output_dir, n, convert_segwit,
               maxT=0, debug=True, vmcp_file=None):
    # read_blockfile("/Users/nlevo/Desktop/Crypto/utxo-dump/z-blocks/blocks/blk00000.dat", bytearray.fromhex('24 e9 27 64'))
    read_blockfile("/Users/nlevo/Desktop/Crypto/utxo-dump/z-blocks/blocks/blk00000.dat", bytearray.fromhex('fa 1a f9 bf'))

    i = 0
    k = 1

    print('new file')
    f = new_utxo_file(output_dir, k)
    print('new_utxo_file path: ', f)
    for value in ldb_iter(datadir):

        tx_hash, height, index, amt, script = value
        # print("Amt: \n")
        # print(amt)
        # print("Script: \n")
        # print(script)
        if convert_segwit:
            script = unwitness(script, debug)

        if debug:
            print(k, i, hexlify(tx_hash[::-1]), height, index,
                  amt, hexlify(script))
            print(value)

        f.write(struct.pack('<QQ', amt, len(script)))
        f.write(script)
        f.write('\n')

        i += 1
        if i % n == 0:
            f.close()

            k += 1
            print('new file: {}'.format(k))
            f = new_utxo_file(output_dir, k)

        if maxT != 0 and i >= maxT:
            break

    f.close()
    print 'BEFORE WRITING TO vmcp_file'
    print(output_dir)
    write_vmcp_data(output_dir, k + 1, vmcp_file)


def write_vmcp_data(output_dir, k, vmcp_file):

    def addr_to_script(addr):
        if addr[:2] == 't3':
            scr = 'a914' + a2b_hashed_base58(addr)[2:].encode('hex') + '87'
            return scr.decode('hex')

        assert addr[:2] == 't1'
        k = Key.from_text(addr)
        enc = '76a914'+k.hash160()[1:].encode('hex')+'88ac'
        return enc.decode('hex')

    reader = csv.reader(open(vmcp_file, 'rb'), delimiter=",", quotechar='"')
    print 'writing vmcp data from {} to utxo-{}'.format(vmcp_file, utxo_file_name(output_dir, k))

    balances = {}
    for i, line in enumerate(reader):
        if i == 0:
            continue

        line[0] = addr_to_script(line[0])
        assert line[0] not in balances
        assert len(line) == 5
        balances[line[0]] = int(float(line[-1]) * 100E6)

    f = new_utxo_file(output_dir, k)
    for script, amt in balances.iteritems():
        f.write(struct.pack('<QQ', amt, len(script)))
        f.write(script)
        f.write('\n')

    f.close()
    print 'wrote {} records'.format(i)
