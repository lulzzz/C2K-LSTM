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
from collections import Counter
from scipy import spatial

eventlog = "c2k_data_comma_lstmready_multi.csv"
modelfile = ""
csvfile = open('../data/%s' % eventlog, 'r')
spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
next(spamreader, None)  # skip the headers

if __name__ == "__main__":
    modelfile = sys.argv[1]

print('target eventlog: ' + eventlog)
print('target model: ' + modelfile)

lastcase = ''
line = [] #needs to be an array now for rgb encoding
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
        line = []
        times = []
        times2 = []
        numlines+=1
    line.append(row[1])
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
lines = map(lambda x: x + ['!'],lines)
maxlen = max(map(lambda x: len(x),lines))

#chars are concurrent activities e.g. 'AEI'
#uniquechars are activities e.g. 'A'
chars = map(lambda x : set(x),lines)
chars = list(set().union(*chars))
chars.sort()
target_chars = copy.copy(chars)
chars.remove('!')
print('total chars: {}, target chars: {}'.format(len(chars), len(target_chars)))

uniquechars = [l for word in chars for l in word]
uniquechars.append('!')
uniquechars = list(set(uniquechars))
uniquechars.sort()
target_uchars = copy.copy(uniquechars)
uniquechars.remove('!')
print('unique characters: {}', uniquechars)

char_indices = dict((c, i) for i, c in enumerate(chars)) #dictionary<key,value> with <char, index> where char is unique symbol for activity
uchar_indices = dict((c, i) for i, c in enumerate(uniquechars))
indices_char = dict((i, c) for i, c in enumerate(chars)) #dictionary<key,value> with <index, char> where char is unique symbol for activity
indices_uchar = dict((i, c) for i, c in enumerate(uniquechars))

target_char_indices = dict((c, i) for i, c in enumerate(target_chars))
target_uchar_indices = dict((c, i) for i, c in enumerate(target_uchars))
target_indices_char = dict((i, c) for i, c in enumerate(target_chars))
target_indices_uchar = dict((i, c) for i, c in enumerate(target_uchars))

print(char_indices)
print(indices_char)
print(target_char_indices) #does contain '!'
print(target_indices_char) #does contain '!'

print(uchar_indices)
print(indices_uchar)
print(target_uchar_indices) #does contain '!'
print(target_indices_uchar) #does contain '!'

## end variables

lastcase = ''
line = []
firstLine = True
lines = []
timeseqs = []  # relative time since previous event
timeseqs2 = [] # relative time since case start
timeseqs3 = [] # absolute time of previous event
times = []
times2 = []
times3 = []
meta_tv1 = []
meta_tv2 = []
meta_plannedtimestamp = []
meta_processid = []
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
            meta_plannedtimestamp.append(meta_tv1)
            meta_processid.append(meta_tv2)
        line = []
        times = []
        times2 = []
        times3 = []
        meta_tv1 = []
        meta_tv2 = []
        numlines+=1
    line.append(row[1])
    timesincelastevent = int(row[3]) #3 is calculated time since last event
    timesincecasestart = int(row[4]) #4 is timestamp aka time since case start
    timediff = timesincelastevent
    timediff2 = timesincecasestart
    timediff3 = int(row[2]) 
    times.append(timediff)
    times2.append(timediff2)
    times3.append(timediff3)
    meta_tv1.append(int(row[6]))
    meta_tv2.append(int(row[7]))
    lasteventtime = t
    firstLine = False

# add last case
lines.append(line)
timeseqs.append(times)
timeseqs2.append(times2)
timeseqs3.append(times3)
meta_plannedtimestamp.append(meta_tv1)
meta_processid.append(meta_tv2)
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
fold3_m1 = meta_plannedtimestamp[2*elems_per_fold:]
fold3_m2 = meta_processid[2*elems_per_fold:]

lines = fold3
lines_t = fold3_t
lines_t2 = fold3_t2
lines_t3 = fold3_t3
lines_m1 = fold3_m1
lines_m2 = fold3_m2

# set parameters
predict_size = 1

# load model, set this to the model generated by train.py
model = load_model('output_files/models/'+modelfile)

# define helper functions
def encode(sentence, times, times2, times3, maxlen=maxlen):
    num_features = len(uniquechars)+4
    X = np.zeros((1, maxlen, num_features), dtype=np.float32)
    leftpad = maxlen-len(sentence)
    for t, char in enumerate(sentence):
        for c in uniquechars:
            if c in char:
                X[0, t+leftpad, uchar_indices[c]] = 1
        X[0, t+leftpad, len(uniquechars)] = t+1
        X[0, t+leftpad, len(uniquechars)+1] = times[t]/divisor
        X[0, t+leftpad, len(uniquechars)+2] = times2[t]/divisor2
        X[0, t+leftpad, len(uniquechars)+3] = times3[t]/divisor3
    return X

# create kd tree
A = []
for line in lines:
    for activity in line:
        B = np.zeros(len(uniquechars) + 1)
        for c in uniquechars:
            if c in activity:
                B[target_uchar_indices[c]] = 1
        A.append(B)
# '!' case
B = np.zeros(len(uniquechars) + 1)
B[target_uchar_indices['!']] = 1
A.append(B)

A = list(set(tuple(element) for element in A))
tree = spatial.KDTree(A)
print('tree size: {}'.format(len(A)))
print(A)

def getSymbol(predictions):
    closest = A[tree.query(predictions)[1]]
    prediction = ''
    for i in range(0,len(closest)):
        if closest[i] == 1:
            prediction += target_indices_uchar[i]
#    print(prediction)
#    print(closest)
    return prediction

# make predictions
with open('output_files/results/next_activity_and_cascade_results_%s' % eventlog, 'wb') as csvfile:
    spamwriter = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    spamwriter.writerow(["sequenceid","sequencelength", "prefix", "sumprevious", "timestamp", "completion", "gt_sumprevious", "gt_timestamp", "gt_planned", "gt_instance", "prefix_activities", "predicted_activities"])
    sequenceid = 0
    print('sequences: {}'.format(len(lines)))    
    for line, times, times2, times3, meta1, meta2 in izip(lines, lines_t, lines_t2, lines_t3, lines_m1, lines_m2):
        #line = sequence of symbols (activityid)
        #times = sequence of time since last event
        #times2 = sequence of timestamps
        #times3 = sequence of durations
        #calculate max line length
        sequencelength = len(line)
        print('sequence length: {}'.format(sequencelength))
        #calculate ground truth
        ground_truth_sumprevious = sum(times)
        ground_truth_timestamp = times2[-1]
        ground_truth_plannedtimestamp = meta1[-1]
        ground_truth_processid = meta2[-1]

        for prefix_size in range(1,sequencelength):
            print('prefix size: {}'.format(prefix_size))            
            cropped_line = line[:prefix_size]
            cropped_times = times[:prefix_size]
            cropped_times2 = times2[:prefix_size]
            cropped_times3 = times3[:prefix_size]
            if '!' in cropped_line:
                break # make no prediction for this case, since this case has ended already
            predicted = []
            predicted_t = []
            predicted_t2 = []
            predicted_t3 = []            
            prefix_activities = line[:prefix_size]
            #predict until ! found
            for i in range(100):
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
                cropped_line.append(prediction)
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

                predicted.append(prediction)
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
                output.append(ground_truth_plannedtimestamp)
                output.append(ground_truth_processid)
                prefix_activities = ' '.join(prefix_activities)
                predicted_activities = ' '.join(predicted)
                output.append(prefix_activities)   #prefix_activities.encode('utf-8'))
                output.append(predicted_activities)   #predicted.encode('utf-8'))
                spamwriter.writerow(output)
            #end prefix loop
        sequenceid += 1
        #end sequence loop
print('finished generating cascade results')
