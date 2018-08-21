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

import hashlib

def snap_utxos(bitcoind, bitcoind_datadir, stop_block):
    
    cmd = "{} -reindex-chainstate -datadir=\"{}\" -stopatheight={}".format(
        bitcoind, bitcoind_datadir, stop_block)
    print("cmd")
    print (cmd)
    print("running " + cmd)
    os.system(cmd)


def get_magic(network, coin):
    if network == "testnet":
        if coin == "zcl":
            return bytearray.fromhex('fa 1a f9 bf') #testnetZCLMagic
        elif coin == "bitcoin":
            return bytearray.fromhex('0b 11 09 07') #testnetBitcoinMagic
    elif network == "mainnet":
        if coin == "zcl":
            return bytearray.fromhex('24 e9 27 64') #mainnetZCLMagic
        elif coin == "bitcoin":
            return bytearray.fromhex('f9 be b4 d9') #mainnetBitcoinMagic
    assert 0, "The provided network or coin name aren't supported. Use the following network: 'mainnet' or 'testnet'; coin: 'zcl' or 'bitcoin' "


def dump_transactions(datadir, output_dir, file_size, convert_segwit, maxT, debug, file_num_start, z_address, network, coin, t_address):
    
    magic = get_magic(network, coin) #get magic for the provided network and coin
    trans_total = 0 #keep track of total transaction 
    ret = {}
    file_num = file_num_start
    #write regular utxo (t-transactions)
    if(t_address):
        ret = dump_utxos(datadir, output_dir, file_size, convert_segwit, maxT, debug, file_num)
        print "Total T-files written: \t%d " % ret['file_num']
        print  "utxo-{:05}.bin".format(file_num) + " - utxo-{:05}.bin".format(ret['file_num'])
        ret['file_num'] = file_num + 1
    else:
        ret['file_num'] = file_num
        ret['trans_total'] = 0
    
    if z_address:
        trans_total = ret['trans_total']
        file_num = int(ret['file_num'])
        ret = {}
        ret = dump_jointsplits(datadir, output_dir, file_size, maxT, trans_total, file_num, magic)
        
        print "Total Z-files written: \t%d " % (int(ret['file_num']) - file_num)
        print  "utxo-{:05}.bin".format(file_num) + " - utxo-{:05}.bin".format(ret['file_num'])

        trans_total = ret['trans_total']
        file_num = ret['file_num']
    else:
        trans_total = ret['trans_total']
        file_num = ret['file_num']

    print "Total T+Z written: \t%d " % trans_total
    print "Total files created: \t", file_num - file_num_start
    print("##########################################")
    return


def dump_jointsplits(datadir, output_dir, n, maxT, globalTransactionCounter, fileNumber, magic):
    trans_counter = 0 #keep track of transcations per file
    trans_z_total = 0
    maxBlockFile = 9999
    blkFile = 0
    file_num = fileNumber
    duplicates = 0
    
    hashStore = {}

    print("Extracting joinsplits from " + datadir + "/blocks/blk" + '{0:0>5}'.format(blkFile) + ".dat")
    joinsplits = read_blockfile(datadir + "/blocks/blk" + '{0:0>5}'.format(blkFile) + ".dat", magic)

    while len(joinsplits) != 0:
        f = new_utxo_file(output_dir, file_num)  #open a new file
        for value in joinsplits:
            lengthStr = "{0:b}".format(len(value)) #bytes length of the transaction
            #format binary length in big-endian (32 bit) format
            if (len(lengthStr) < 32 ):
                while len(lengthStr) < 32:
                    lengthStr = "{0:b}".format(0) + lengthStr
            m = hashlib.md5()
            m.update(value)
            md5_hash = m.digest()

            if md5_hash in hashStore:
                print("Found a duplicate transaction...skipping.")
                duplicates += 1
                joinsplits = joinsplits[1:] #remove duplicate 
                continue

            hashStore[md5_hash] = 1
            f.write(lengthStr) #write length of the transaction
            f.write(value)#write actual z-utxo 
            globalTransactionCounter += 1
            trans_counter += 1
            trans_z_total += 1

            if maxT != 0 and trans_counter >= maxT:
                break
                
        #remove objects from array that were written
        joinsplits = joinsplits[trans_counter:]
        trans_counter = 0
        if(len(joinsplits) == 0 and (blkFile <= maxBlockFile)):
            try: 
                blkFile += 1
                print("Extracting joinsplits from " + datadir + "/blocks/blk" + '{0:0>5}'.format(blkFile) + ".dat")
                joinsplits = read_blockfile(datadir + "/blocks/blk" + '{0:0>5}'.format(blkFile) + ".dat", magic)
                print()
            except IOError:
                print("Oops! File %s/blocks/blk0000%i.dat doesn't exist..." % (datadir, blkFile))
                break
        file_num += 1
        f.close()
    f.close()
    print("##########################################")
    print 'Found duplicates: \t%d' % duplicates
    print 'Total Z written: \t%s' % trans_z_total
    return { 'trans_total': globalTransactionCounter, 'file_num': file_num }

def dump_utxos(datadir, output_dir, n, convert_segwit,
               maxT, debug, fileNum):
    # print("Starting to write Z-transactions")
    j = 0
    i = 0
    k = fileNum

    print('new file')
    f = new_utxo_file(output_dir, k)
    print('new_utxo_file path: ', f)

    for value in ldb_iter(datadir):
        tx_hash, height, index, amt, script = value
        
        if debug:
            print "Height: %d" % height
            print "Reversed: "
            reversedString = hexlify(tx_hash)
            print("".join(reversed([reversedString[x:x+2] for x in range(0, len(reversedString), 2)])))
            print ""

        if convert_segwit:
            script = unwitness(script, debug)

        # if debug:
        #     print(k, i, hexlify(tx_hash[::-1]), height, index,
        #           amt, hexlify(script))
        #     print(value)

        f.write(struct.pack('<QQ', amt, len(script)))
        f.write(script)
        f.write('\n')

        i += 1
        j += 1
        if i >= maxT:
            f.close()
            k += 1
            i = 0
            f = new_utxo_file(output_dir, k)

    f.close()
    print("##########################################")
    print("Total T written: \t%d" % j)
    print("##########################################")
    return { 'trans_total': j, 'file_num': k }

