'''
this script takes as input the LSTM or RNN weights found by train.py
change the path in line 176 of this script to point to the h5 file
with LSTM or RNN weights generated by train.py

Author: Niek Tax
'''

from __future__ import division
from keras.models import load_model
import csv
import copy
import numpy as np
import distance
import sys
from itertools import izip
from jellyfish._jellyfish import damerau_levenshtein_distance
import unicodecsv
from sklearn import metrics
from math import sqrt
import time
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from collections import Counter

eventlog = "c2k_data_comma_lstmready.csv"
modelfile = ""
csvfile = open('../data/%s' % eventlog, 'r')
spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
next(spamreader, None)  # skip the headers
ascii_offset = 161

if __name__ == "__main__":
    modelfile = sys.argv[1]

print('target eventlog: ' + eventlog)
print('target model: ' + modelfile)

lastcase = ''
line = ''
firstLine = True
lines = []
timeseqs = []
timeseqs2 = []
times = []
times2 = []
numlines = 0
casestarttime = None
lasteventtime = None
for row in spamreader:
    t = int(row[2])
    if row[0]!=lastcase:
        casestarttime = t
        lasteventtime = t
        lastcase = row[0]
        if not firstLine:        
            lines.append(line)
            timeseqs.append(times)
            timeseqs2.append(times2)
        line = ''
        times = []
        times2 = []
        numlines+=1
    line+=unichr(int(row[1])+ascii_offset)
    timesincelastevent = int(row[3]) #3 is calculated time since last event
    timesincecasestart = int(row[4]) #4 is timestamp aka time since case start
    timediff = timesincelastevent
    timediff2 = timesincecasestart
    times.append(timediff)
    times2.append(timediff2)
    lasteventtime = t
    firstLine = False

# add last case
lines.append(line)
timeseqs.append(times)
timeseqs2.append(times2)
numlines+=1

elems_per_fold = int(round(numlines/3))
fold1 = lines[:elems_per_fold]
fold1_t = timeseqs[:elems_per_fold]
fold1_t2 = timeseqs2[:elems_per_fold]

fold2 = lines[elems_per_fold:2*elems_per_fold]
fold2_t = timeseqs[elems_per_fold:2*elems_per_fold]
fold2_t2 = timeseqs2[elems_per_fold:2*elems_per_fold]

lines = fold1 + fold2
lines_t = fold1_t + fold2_t
lines_t2 = fold1_t2 + fold2_t2

step = 1
sentences = []
softness = 0
next_chars = []
lines = map(lambda x: x+'!',lines)
maxlen = max(map(lambda x: len(x),lines))

chars = map(lambda x : set(x),lines)
chars = list(set().union(*chars))
chars.sort()
target_chars = copy.copy(chars)
chars.remove('!')
print('total chars: {}, target chars: {}'.format(len(chars), len(target_chars)))
char_indices = dict((c, i) for i, c in enumerate(chars))
indices_char = dict((i, c) for i, c in enumerate(chars))
target_char_indices = dict((c, i) for i, c in enumerate(target_chars))
target_indices_char = dict((i, c) for i, c in enumerate(target_chars))
print(indices_char)

lastcase = ''
line = ''
firstLine = True
lines = []
timeseqs = []  # relative time since previous event
timeseqs2 = [] # relative time since case start
timeseqs3 = [] # absolute time of previous event
times = []
times2 = []
times3 = []
numlines = 0
casestarttime = None
lasteventtime = None
csvfile = open('../data/%s' % eventlog, 'r')
spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
next(spamreader, None)  # skip the headers
for row in spamreader:
    t = int(row[2])
    if row[0]!=lastcase:
        casestarttime = t
        lasteventtime = t
        lastcase = row[0]
        if not firstLine:        
            lines.append(line)
            timeseqs.append(times)
            timeseqs2.append(times2)
            timeseqs3.append(times3)
        line = ''
        times = []
        times2 = []
        times3 = []
        numlines+=1
    line+=unichr(int(row[1])+ascii_offset)
    timesincelastevent = int(row[3]) #3 is calculated time since last event
    timesincecasestart = int(row[4]) #4 is timestamp aka time since case start
    timediff = timesincelastevent
    timediff2 = timesincecasestart
    timediff3 = int(row[2]) 
    times.append(timediff)
    times2.append(timediff2)
    times3.append(timediff3)
    lasteventtime = t
    firstLine = False

# add last case
lines.append(line)
timeseqs.append(times)
timeseqs2.append(times2)
timeseqs3.append(times3)
numlines+=1

divisor = np.mean([item for sublist in timeseqs for item in sublist]) #variable for lstm model
print('divisor: {}'.format(divisor))
divisor2 = np.mean([item for sublist in timeseqs2 for item in sublist]) #variable for lstm model
print('divisor2: {}'.format(divisor2))
divisor3 = np.mean([item for sublist in timeseqs3 for item in sublist]) #variable for lstm model
print('divisor3: {}'.format(divisor3))

fold3 = lines[2*elems_per_fold:]
fold3_t = timeseqs[2*elems_per_fold:]
fold3_t2 = timeseqs2[2*elems_per_fold:]
fold3_t3 = timeseqs3[2*elems_per_fold:]

lines = fold3
lines_t = fold3_t
lines_t2 = fold3_t2
lines_t3 = fold3_t3

# set parameters
predict_size = 1

# load model, set this to the model generated by train.py
model = load_model('output_files/models/'+modelfile)

# define helper functions
def encode(sentence, times, times2, times3, maxlen=maxlen):
    num_features = len(chars)+4
    X = np.zeros((1, maxlen, num_features), dtype=np.float32)
    leftpad = maxlen-len(sentence)
    for t, char in enumerate(sentence):
        for c in chars:
            if c==char:
                X[0, t+leftpad, char_indices[c]] = 1
        X[0, t+leftpad, len(chars)] = t+1
        X[0, t+leftpad, len(chars)+1] = times[t]/divisor
        X[0, t+leftpad, len(chars)+2] = times2[t]/divisor2
        X[0, t+leftpad, len(chars)+3] = times3[t]/divisor3
    return X

def getSymbol(predictions):
    maxPrediction = 0
    symbol = ''
    i = 0;
    for prediction in predictions:
        if(prediction>=maxPrediction):
            maxPrediction = prediction
            symbol = target_indices_char[i]
        i += 1
    return symbol

# make predictions
with open('output_files/results/next_activity_and_cascade_results_%s' % eventlog, 'wb') as csvfile:
    spamwriter = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    spamwriter.writerow(["sequenceid","sequencelength", "prefix", "sumprevious", "timestamp", "completion", "gt_sumprevious", "gt_timestamp", "gt_allowed"])
    sequenceid = 0
    print('sequences: {}'.format(len(lines)))    
    for pline, ptimes, ptimes2, ptimes3 in izip(lines, lines_t, lines_t2, lines_t3):
        #line = sequence of symbols (activityid)
        #times = sequence of time since last event
        #times2 = sequence of timestamps
        #times3 = sequence of durations
        #calculate max line length
        sequencelength = len(pline)
        print('sequence length: {}'.format(sequencelength))
        #calculate ground truth
        ground_truth_sumprevious = sum(ptimes)
        ground_truth_timestamp = ptimes2[-1]
        #ptimes.append(0)
        #ptimes2.append(0)
        #ptimes3.append(0)
        for prefix_size in range(1,sequencelength):
            print('prefix size: {}'.format(prefix_size))            
            cropped_line = ''.join(line[:prefix_size])
            cropped_times = ptimes[:prefix_size]
            cropped_times2 = ptimes2[:prefix_size]
            cropped_times3 = ptimes3[:prefix_size]
            if '!' in cropped_line:
                break # make no prediction for this case, since this case has ended already
            predicted = ''
            predicted_t = []
            predicted_t2 = []
            predicted_t3 = []
            #predict until ! found
            for i in range(maxlen):
                enc = encode(cropped_line, cropped_times, cropped_times2, cropped_times3)
                y = model.predict(enc, verbose=0)
                y_char = y[0][0]
                y_t = y[1][0][0]
                y_t2 = y[1][0][1]
                y_t3 = y[1][0][2]
                prediction = getSymbol(y_char)
                if prediction == '!': # end of case was just predicted, therefore, stop predicting further into the future
                    print('! predicted, end case')
                    break                
                cropped_line += prediction
                if y_t<0:
                    y_t=0
                if y_t2<0:
                    y_t2=0
                if y_t3<0:
                    y_t3=0
                cropped_times.append(y_t)
                cropped_times2.append(y_t2)
                cropped_times3.append(y_t3)
                y_t = y_t * divisor
                y_t2 = y_t2 * divisor2
                y_t3 = y_t3 * divisor3

                predicted += prediction
                predicted_t.append(y_t)
                predicted_t2.append(y_t2)
                predicted_t3.append(y_t3)
                #end prediction loop

            #output stuff (sequence, prefix)
            if len(predicted) > 0:
                output = []
                output.append(sequenceid)
                output.append(sequencelength)
                output.append(prefix_size)
                output.append(sum(times[:prefix_size]) + sum(predicted_t))
                output.append(predicted_t2[-1])
                #output.append(sum(predicted_t3)) #remove duration because process is parallel and therefore sum is useless
                output.append(prefix_size / sequencelength)
                output.append(ground_truth_sumprevious)
                output.append(ground_truth_timestamp)
                spamwriter.writerow(output)
            #end prefix loop
        sequenceid += 1
        #end sequence loop
print('finished generating cascade results')
