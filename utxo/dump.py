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

    # mainnetZCLMagic = bytearray.fromhex('24 e9 27 64') 
    # testnetZCLMagic = bytearray.fromhex('fa 1a f9 bf')
    # mainnetBitcoinMagic = bytearray.fromhex('f9 be b4 d9')
    # testnetBitcoinMagic = bytearray.fromhex('0b 11 09 07')

def dump_transactions(datadir, output_dir, file_size, convert_segwit, maxT, debug, file_num, z_address, network, coin):
    #get magic for the provided network and coin
    magic = get_magic(network, coin)
    fileNumber = file_num 
    returnObject = {}
    globalTransactionCounter = 0 #keep track of total transaction 
    fileNumber = 1 #keep track of created files
    # counterPerFile = 0 #keep track of transcations per file
    # maxT = maxT #4000 

    #write regular utxo (t-transactions)
    returnObject = dump_utxos(datadir, output_dir, file_size, convert_segwit, maxT, debug, file_num)
    if z_address:
        # print("z_address: %d" % z_address)
        globalTransactionCounter = returnObject['globalTransactionCounter']
        fileNumber = returnObject['fileNumber'] + 1
        returnObject = {}
        returnObject = dump_jointsplits(datadir, output_dir, file_size, maxT, globalTransactionCounter, fileNumber, magic)
        
        globalTransactionCounter = returnObject['globalTransactionCounter']
        fileNumber = returnObject['fileNumber']
    else:
        globalTransactionCounter = returnObject['globalTransactionCounter']
        fileNumber = returnObject['fileNumber']

    print "Total T+Z written: \t%d " % globalTransactionCounter
    print "Total files created: \t", fileNumber - 1
    print("##########################################")
    return


def dump_jointsplits(datadir, output_dir, n, maxT, globalTransactionCounter, fileNumber, magic):
    counterPerFile = 0 #keep track of transcations per file
    #1. WRITE ZCL T-transactions
    # print("Starting to write Z-transactions")
    # fileNumber = dump_utxos(datadir, output_dir, n, False, False, 3500, fileNumber) + 1
    # print("Starting to write Z-transactions")

    #2. WRITE ZCL Z-transactions
    # print(datadir)
    numberOfFilesToRead = 0
    localTotalCounter = 0
    numberFile = 0
    # print("magic")
    # print(hexlify(magic))
    joinsplits = read_blockfile(datadir + "/blocks/blk0000%i.dat" % numberFile, magic)
    numberFile += 1
    while len(joinsplits) != 0:
        # print('NEW FILE')
        # print(fileNumber))
        f = new_utxo_file(output_dir, fileNumber)  #create and open a new file
        for value in joinsplits:
            lengthStr = "{0:b}".format(len(value)) #bytes length of the transaction
            #format binary length in big-endian (32 bit) format
            if (len(lengthStr) < 32 ):
                while len(lengthStr) < 32:
                    lengthStr = "{0:b}".format(0) + lengthStr
            f.write(lengthStr) #write length of the transaction
            f.write(value)     #write actual transaction
            globalTransactionCounter += 1
            counterPerFile += 1
            localTotalCounter += 1
            # print(fileNumber)
            # print(hexlify(value))
            # limit transaction per file (<= max transactions)
            if maxT != 0 and counterPerFile >= maxT:
                # print(hexlify(value))
                break
        #remove objects from array that were written
        joinsplits = joinsplits[counterPerFile:]
        if(len(joinsplits) == 0 and (numberFile <= numberOfFilesToRead)):
            joinsplits = read_blockfile(datadir + "/blocks/blk0000%i.dat" % numberFile, magic)
            numberFile += 1
        counterPerFile = 0
        fileNumber += 1
        f.close()
    print("##########################################")
    print 'Total Z written: \t%s' % localTotalCounter
    return { 'globalTransactionCounter': globalTransactionCounter, 'fileNumber': fileNumber }

def dump_utxos(datadir, output_dir, n, convert_segwit,
               maxT, debug, fileNum):
    # print("Starting to write Z-transactions")
    
    j = 0
    i = 0
    k = fileNum

    print('new file')
    f = new_utxo_file(output_dir, k)
    print('new_utxo_file path: ', f)
    # print('value length: %d' % len(ldb_iter(datadir)))
    for value in ldb_iter(datadir):
        tx_hash, height, index, amt, script = value
        print "Height: %d" % height
        # print "Original: "
        # print(hexlify(tx_hash))
        print "Reversed: "
        reversedString = hexlify(tx_hash)
        print("".join(reversed([reversedString[i:i+2] for i in range(0, len(reversedString), 2)])))
        print()
        # print("Amt: \n")
        # print(amt)
        # print("Script: \n")
        # print(script)
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
            # print("Saved T-transactions: %d in file# %d" % (i,k))
            k += 1
            # print('new file: {}'.format(k))
            i = 0
            f = new_utxo_file(output_dir, k)

        # if maxT != 0 and i >= maxT:
        #     break
    # print("Saved T-transactions: %d in file# %d" % (j, k-1 if k==0 else k))
    f.close()
    print("##########################################")
    print("Total T written: \t%d" % j)
    print("##########################################")
    return { 'globalTransactionCounter': j, 'fileNumber': k }





    
    # print 'BEFORE WRITING TO vmcp_file'
    # print(output_dir)
    # write_vmcp_data(output_dir, k + 1, vmcp_file)

# print(int(stringRes.encode('hex'), 16))
# if i ==3:
    #     f.close()
    #     break
# if i % n == 0:
#     k += 1
#     print('new file: {}'.format(k))

#   t = open("z-dump/anon/testnet/utxo-00002.bin", "rb")

#     while True:
#         # print(numberWrites)
#         stringRes=t.read(32)
#         # print(stringRes)
#         # print(int(stringRes,2))
#         if len(stringRes) <= 1:
#             break
#         print(int(stringRes,2))

        
#         thing = t.read(int(stringRes,2))
#         print(hexlify(thing))