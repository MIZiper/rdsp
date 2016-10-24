import numpy as np

def findContinuous(boolArray, minCount):
    w = boolArray.size
    se_pairs = np.zeros([1,2])

    i = 0
    while True:
        while i<w and (not boolArray[i]):
            i += 1
        s = i
        while i<w and boolArray[i]:
            i += 1
        e = i
        if s<e:
            if e-s>=minCount:
                se_pairs = np.append(se_pairs,[[s,e]],axis=0)
        else:
            break
        
    se_pairs = np.delete(se_pairs,0,axis=0)
    return se_pairs

def getAprxValue(dataArray, se_pair, tolerance):
    subArray = dataArray[se_pair[0]:se_pair[1]]
    baseIndex = subArray.argmin()
    baseVal = subArray[baseIndex]
    l = se_pair[1]-se_pair[0]
    n = 1
    s = baseVal
    i = baseIndex-1
    while i>=0 and abs(subArray[i]-baseVal)<=tolerance:
        n += 1
        s += subArray[i]
        i -= 1
    i = baseIndex+1
    while i<l and abs(subArray[i]-baseVal)<=tolerance:
        n += 1
        s += subArray[i]
        i += 1
    return (s/n,n)

def findSEIndex(kp_se_pairs, track_se_pairs):
    '''
    Index of start/end pair for kp pulse
    '''
    se_index = np.array([])
    (l,w) = track_se_pairs.shape
    (ll,ww) = kp_se_pairs.shape
    k = 0
    for i in range(ll):
        j = int((kp_se_pairs[i,0]+kp_se_pairs[i,1])/2)
        while (k+1)<l:
            if j<=track_se_pairs[k+1,0]:
                if j>track_se_pairs[k,0]:
                    se_index = np.append(se_index,k+1)
                break
            else:
                k += 1
    return se_index