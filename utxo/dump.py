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
        elif coin == "anon":
            return bytearray.fromhex('7a 74 8d 38') #testnetAnonMagic
    elif network == "mainnet":
        if coin == "zcl":
            return bytearray.fromhex('24 e9 27 64') #mainnetZCLMagic
        elif coin == "bitcoin":
            return bytearray.fromhex('f9 be b4 d9') #mainnetBitcoinMagic
        elif coin == "anon":
            return bytearray.fromhex('83 d8 47 a7') #mainnetAnonMagic
    assert 0, "The provided network or coin name aren't supported. Use the following network: 'mainnet' or 'testnet'; coin: 'zcl' or 'bitcoin' "


def dump_transactions(datadir, output_dir, file_size, convert_segwit, maxT, debug, file_num_start, z_address, network, coin, t_address):
    
    magic = get_magic(network, coin) #get magic for the provided network and coin

    ret = {
        "file_num_start": int(file_num_start),
        "z_files_written": 0,
        "t_files_written": 0,
        "z_transactions_total": 0,
        "t_transactions_total": 0
    }

    ret.update
    #write regular utxo (t-transactions)
    if t_address:
        ret.update(dump_utxos(datadir, output_dir, file_size, convert_segwit, maxT, debug, ret['file_num_start']))
        print "Total T-files written: \t%d " % ret['t_files_written']
        print  "utxo-{:05}.bin".format(int(file_num_start)) + " - utxo-{:05}.bin".format(ret['file_num_start'] + ret['t_files_written'] - 1)
    
    if z_address:
        ret.update(dump_jointsplits(datadir, output_dir, file_size, maxT, (int(ret['file_num_start']) + int(ret['t_files_written'])), magic))
        print "Total Z-files written: \t%d " % ret['z_files_written']
        print  "utxo-{:05}.bin".format(ret['file_num_start'] + ret['t_files_written']) + " - utxo-{:05}.bin".format(ret['file_num_start'] + ret['t_files_written'] + ret['z_files_written'] - 1)

    print "Total transactions written: \t%d " % (ret['z_transactions_total'] + ret['t_transactions_total'])
    print "Total files created: \t", ret['z_files_written'] + ret['t_files_written']
    print("##########################################")
    return


def dump_jointsplits(datadir, output_dir, n, maxT, fileNumber, magic):
    trans_counter_perfile = 0 #keep track of transcations per file
    trans_z_total = 0
    maxBlockFile = 9999
    blkFile = 0
    file_num = fileNumber
    duplicates = 0
    files_written = 0
    hashStore = {}

    print("Extracting joinsplits from " + datadir + "/blocks/blk" + '{0:0>5}'.format(blkFile) + ".dat")
    joinsplits = read_blockfile(datadir + "/blocks/blk" + '{0:0>5}'.format(blkFile) + ".dat", magic)

    while len(joinsplits) != 0:
        f = new_utxo_file(output_dir, file_num)  #open a new file
        files_written += 1
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
            # append first sha256(transaction + its length)
            sha = hashlib.sha256()
            sha.update(value + lengthStr)
            sha256_hash = sha.digest()
            print("SHA256: ", sha256_hash)
            f.write(sha256_hash)
            f.close()
            return
            trans_counter_perfile += 1
            trans_z_total += 1

            if maxT != 0 and trans_counter_perfile >= maxT:
                break
                
        #remove objects from array that were written
        joinsplits = joinsplits[trans_counter_perfile:]
        trans_counter_perfile = 0
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
        # append 1st 32 bits of sha256 hash of the whole file (checksum)
        # sha = hashlib.sha256()
        # sha.update(value)
        # sha256_hash = "{0:b}".format(len(sha256_hash))   sha.digest()
        # lengthStr = 
        f.close()
    # append 1st 32 bits of sha256 hash of the whole file (checksum)
    # sha = hashlib.sha256()
    # sha.update(value)
    # sha256_hash = sha.digest()
    f.close()
    
    print("##########################################")
    print 'Found duplicates: \t%d' % duplicates
    print 'Total Z written: \t%s' % trans_z_total
    return { 'z_transactions_total': trans_z_total, 'z_files_written': files_written }

def dump_utxos(datadir, output_dir, n, convert_segwit,
               maxT, debug, fileNum):
    # print("Starting to write Z-transactions")
    j = 0 #total utxo
    i = 0 #keep track of utxo per file
    k = fileNum #relative number of file
    n = 0 #number of files written

    print('new file')
    f = new_utxo_file(output_dir, k)
    n += 1
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
            n += 1

    f.close()
    print("##########################################")
    print("Total T written: \t%d" % j)
    print("##########################################")
    return { 't_transactions_total': j, 't_files_written': n }

