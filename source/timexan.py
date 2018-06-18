#!/usr/bin python
# -*- coding: utf-8 -*-

"""Time Expression Extraction 

This module extracts time expressions from text. The implementation borrows some code from usfd2. 
[http://code.google.com/p/usfd2] and Tarsqi toolkit [http://www.timeml.org/site/tarsqi/]

The core functions it provides include:

annotateTimexes() -- Take the text as input, and return a list of Timex3 objects. 
It determines the type of timex and evaluate absolute date.

getRelativeDatetime() -- Evaluate a relative time based on time expression, relationship 
and time reference. 

class Timex3 -- Define a timex with information such as time string, type, datetime, location, etc 

"""
#
# Wei Wang, Engility, wei.wang@engility.com
#

from nltk import word_tokenize, sent_tokenize
from datetime import date, datetime, timedelta
import re, util
from dateutil.parser import parser
from StringIO import StringIO

numbersRx = re.compile(r'^[0-9]+ ')
months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']

#relTimeSignals = ['in','during','on','at','before','after','when','since','from','until','prior','later','earlier','post','ago','next', 'following']    
relTimeSignals = ['before','after','prior','later','earlier','post','ago','next', 'following']    
            
class Timex3:
    """ Implements a timex with information such as time string, type, datetime, location, etc. 
        Note that this is not the same as the TLink is defined in TimeML. It was initially design 
        to follow TimeML, but turned out to take a different approach. """ 
        
    def __init__(self,inStart,inEnd,inType, inDatetime, inStr, conf = 0):
        self.start = inStart
        self.end = inEnd
        self.type = inType
        self.string = inStr
        self.sentNum = -1
        self.confidence = conf
        self.id = -1
        
        if inType not in ['AGE', 'FRQ']:
            self.role = 'NORMAL'
        else:
            self.role = 'IGNORE'
        
        if isinstance(inDatetime, dict):
            self.YMD = inDatetime
            if self.YMD['year'] and self.YMD['month'] and self.YMD['day']:
                try:
                    self.datetime = datetime(self.YMD['year'], self.YMD['month'], self.YMD['day'])
                except:
                    self.datetime = None
            else:
                self.datetime = None
        elif isinstance(inDatetime, datetime):
            self.datetime = inDatetime
            self.YMD = None
        else:
            self.datetime = None
            self.YMD = None
    
    def copy(self):
        timex = Timex3(self.start, self.end, self.type, self.datetime, self.string, self.confidence)
        return timex

    def isPartial(self):
        if self.datetime:
            return False
        else:
            return True
        
    def setRole(self, r):
        self.role = r
        
    def getRole(self):
        return self.role
    
    def getDateCompleteness(self):
        if not self.YMD:
            return 3
        
        val = 0
        if self.YMD['year']:
            val += 1
        if self.YMD['month']:
            val += 1
        if self.YMD['day']:
            val +=1
        return val
    
    def setConfidence(self, conf):
        self.confidence = conf
        
    def getStartPos(self):
        return self.start
    
    def getEndPos(self):
        return self.end
        
    def getConfidence(self):
        return self.confidence
    
    def setSentenceNum(self, num):
        self.sentNum = num
        
    def getSentNum(self):
        return self.sentNum
        
    def getDateTime(self):
        return self.datetime
    
    def setDateTime(self, dt):
        self.datetime = dt
    
    def getType(self):
        return self.type
    
    def setType(self, tp):
        self.type = tp
    
    def getString(self):
        return self.string
            
    def getTimexString(self):
        if self.datetime:
            return (self.string, self.start, self.end, self.datetime.isoformat().split('T')[0])
        else:
            return (self.string, self.start, self.end, '')
    
    def setID(self, id):
        self.id = id
    
    def getID(self):
        return self.id
        
def addBoundary(string):
    return '^' + string + '$'

def buildSentenceList(sentenceDict): 
    """convert a sentence dictionary including character offsets to an ordered and tokenized sentence list."""
    #: sort by key, then return items in order.
    items = sentenceDict.items()
    items.sort()
    sentenceList = []
    for position,  word in items:
        sentenceList.insert(position, word)
    return sentenceList

def buildTimeString(wordList):
    """Build string from a word list. Note, when ',' is in a time expression, there shouldn't be a space before it. 
        For example, Feb. 12, 2011"""
    if ',' in wordList:
        loc = wordList.index(',')
        if loc>0:
            wordList[loc] = wordList[loc-1] + wordList[loc]
            del wordList[loc-1]
    #: eg. sept. 12
    if '.' in wordList:
        loc = wordList.index('.')
        if loc>0:
            wordList[loc] = wordList[loc-1] + wordList[loc]
            del wordList[loc-1]

    return ' '.join(wordList)

def findTimexes(words):  
    """Extract time expressions using Regular Expression rules. 
    input -- words to be in the format of ngram: words[filename][sentence index][word index] = "token" .
    return -- a list of timex object indicating its starting and ending location in words 
    """

    #calendar_interval = "(minute|hour|day|weekend|week|month|quarter|year)"
    calendar_interval = "(minute|hour|day|weekend|week|month|quarter|year|hr|min|wk|mo|yr|time)"
    longdays = "((mon|tues|wednes|thurs|fri|satur|sun|to|yester)day|tomorrow|morning|afternoon|evening|night)"
    dayspec = "("+longdays+"|(mon|tue|wed|thu|fri|sat|sun))"
    fullmonth = "(january|february|march|april|may|june|july|august|september|october|november|december)"
    shortmonth = "(jan|feb|mar|apr|may|jun|jul|aug|sept|sep|oct|nov|dec)"
    monthspec = "(jan|feb|mar|apr|may|jun|jul|aug|sept|sep|oct|nov|dec|"+fullmonth+")"
    fullyear = "1[0-9]{3}|20[0-3][0-9]"
    #shortyear = "'?[0-9]{2}"
    shortyear = "['|\-|/][0-9]{2}"
    simple_ordinals = "(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)"
    numeric_days = "([0-9]{1,2}(st|nd|rd|th)?)"
    teen = "(ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen)"
    #digits = "(one|two|three|four|five|six|seven|eight|nine)"
    digits = "(one|two|three|four|five|six|seven|eight|nine|half|a half)"
    fractions = '(([0-9]+ )?[1-9]+/[1-9]+)'
    #textual_number = "(((twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)[\ \-])?"+digits+"|"+digits+"|a|an|"+teen+")"
    tens = '(twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)'
    #textual_number = "(((twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)[\ \-])?"+digits+"|"+digits+"|"+fractions+"|a|an|"+teen+")"
    textual_number = "(("+tens+"[\ \-])?"+digits+"|"+digits+"|"+tens+"|"+fractions+"|a|an|"+teen+")"
    vague = "(around|about|roughly|nearly|over|approx|approximately|approximate)"
    #times = "([012][0-9][\:\.][0-5][0-9](pm|am)?|noon|breakfast|sunrise|sundown|sunset|nightfall|dawn|dusk)"
    times = "([012][0-9][\:][0-5][0-9](pm|am)?|noon|breakfast|sunrise|sundown|sunset|nightfall|dawn|dusk)"
    year = '('+fullyear+'|'+shortyear+')'

    timex_re = []
    timex_re.append(fullmonth)
    timex_re.append(longdays)
    #timex_re.append("(((early|late|earlier|later) )?((this|next|following|last|same) )?("+calendar_interval+"|"+longdays+"))")
    timex_re.append("(((this|next|following|last|same) )?("+calendar_interval+"s?|"+longdays+"))")
    timex_re.append("(now|currently|current)")
    timex_re.append("((first|second|third|fourth|final) quarter)")
#    timex_re.append("(("+dayspec+" )?[0-9]{1,2}([\.\/\-\ ])([0-9]{1,2}|" + monthspec + ")\\7(19|20)?[0-9]{2})") # backreference id may change, be sure it's correct after altering this regex
    timex_re.append("(("+dayspec+" )?[0-9]{1,2}([\.\/\-\ ])(" + monthspec + ")\\7(19|20)?[0-9]{2})") # backreference id may change, be sure it's correct after altering this regex
    timex_re.append("(("+dayspec+" )?[0-9]{1,2}([\.\/\-])([0-9]{1,2})\\7(19|20)?[0-9]{2})") # backreference id may change, be sure it's correct after altering this regex
    timex_re.append("("+textual_number + "[\-\ ]" + calendar_interval + "([\-\ ](long|old))?)")
    #timex_re.append("(((recent|previous|past|first|last) )?(([0-9]+|"+textual_number+"|couple of|few) )?"+calendar_interval+"s?( (ago|later|earlier))?)")
    timex_re.append("(((recent|previous|past|first|last) )?(([0-9]+|"+textual_number+"|couple of|several|few) )?"+calendar_interval+"s?)")
    timex_re.append("(the "+calendar_interval+"s?)")
    #timex_re.append("((early|mid|end)[\-\ ]("+fullmonth+"|"+calendar_interval+"))")
    timex_re.append("(("+fullmonth+"|"+calendar_interval+"))")
    timex_re.append("((the )?"+simple_ordinals+" "+calendar_interval+")")
    timex_re.append("((a|"+textual_number+") "+calendar_interval+"s? (or so )(earlier|later|previous|ago|since))")
    #timex_re.append("("+monthspec+"\.? "+year+")")
    timex_re.append("("+monthspec+"\.? (of )?"+year+")")
    timex_re.append("((the )(end|start|beginning|middle) of the "+calendar_interval+")")
    timex_re.append("(("+longdays+"|this) (morning|afternoon|evening|night)|tonight)")
    timex_re.append("((within|in ((more|less) than )("+vague+" )?)"+textual_number+" "+calendar_interval+")")
    timex_re.append("((next|previous|last|following) (few|many|"+textual_number+") "+calendar_interval+"s?)")
    #timex_re.append("("+vague+" "+textual_number+" "+calendar_interval+")")
    timex_re.append("("+vague+" ([0-9]+|" +textual_number+") "+calendar_interval+"s?)")
    timex_re.append("(("+times+"( "+longdays+")?)|("+longdays+" "+times+"))")
    timex_re.append("("+monthspec+"\.? ?[0-3]?[0-9](st|nd|rd|th)?)")
    #timex_re.append("("+numeric_days+"? (of )?"+monthspec+" "+year+"?)")
    timex_re.append("("+numeric_days+"? ?(of )?"+monthspec+",? ?"+year+"?)")
    timex_re.append(year)

    #print "("+monthspec+"\.? "+numeric_days+",? "+year+"?)"        
    timex_re.append("((19|20)[0-9]{2}([\.\/\-])[0-1]?[0-9]([\.\/\-])([0-3]?[0-9]))") # 2012/03/12, 2012-03-12, 2012.03.12  
    timex_re.append("([\.\/\-\ ]?" + monthspec + "[\.\/\-\ ](19|20)?[0-9]{2})") # ??-Aug-2013    
    #timex_re.append("(("+dayspec+" )?[0-9]{1,2}([\.\/\-\ ])(" + monthspec + "))") # 3-Sep 13-Aug
    timex_re.append("("+monthspec+"\.? "+numeric_days+",? "+year+"?)")
    timex_re.append("(([0-3]?[0-9])" + shortmonth + "(" + fullyear + "|[0-9]{2}))") # 13APR2011 or 13APR11
    timex_re.append("(([0-3]?[0-9])" + shortmonth + ")") # 13Nov or 3NOV
    timex_re.append("(" + shortmonth + "(" + fullyear + "|[0-9]{2}))") # APR2011 or APR11
    timex_re.append("([0-1]?[0-9]/[0-3]?[0-9])") # mon/day, e.g., 10/2, 3/9
    timex_re.append("([0-1]?[0-9]/(19|20)?([0-9][0-9]))") # mon/year, e.g., 10/02, 3/99
    timex_re.append("(" + shortmonth + "|[0-1]?[0-9])/([0-3]?[0-9])-([0-3]?[0-9])/(" + fullyear + "|[0-9]{2})") # mon/day-day/year, e.g., 10/02-13/99
    timex_re.append("(" + shortmonth + "|[0-1]?[0-9])/([0-3]?[0-9])-([0-1]?[0-9])/([0-3]?[0-9])/(" + fullyear + "|[0-9]{2})") # mon/day-day/year, e.g., 10/22-11/13/99
    timex_re.append("(" + shortmonth + "|[0-1]?[0-9])/?([0-3]?[0-9])?/(" + fullyear + "|[0-9]{2})-([0-1]?[0-9])/?([0-3]?[0-9])?/(" + fullyear + "|[0-9]{2})") # mon/day-day/year, e.g., 10/02/98-1/13/99
    timex_re.append("(([0-3]?[0-9])" + shortmonth + "(" + fullyear + "|[0-9]{2}))-(([0-3]?[0-9])" + shortmonth + "(" + fullyear + "|[0-9]{2}))")
    
    ##: Added for i2b2 time expressions
    timex_re.append("((19|20)[0-9]{2}[0-1]?[0-9]([0-3]?[0-9]))")    
    timex_re.append("([0-1]?[0-9]-[0-3]?[0-9])") # mon/day, e.g., 10/2, 3/9
    timex_re.append("((hd|pod) ?#? ?[1-9][0-9]?)") # HD: Hospital day; POD: Post-op day     
    timex_re.append("((hospital|his|her|the) stay)") #: during his hospital stay    
    timex_re.append("([1-9][0-9]? ?y/o)")    
    
    ###: add '^' + string + '$'
    timex_re = map(addBoundary, timex_re)

    # ngrams[0] is empty; ngrams[1] contains unigrams; ngrams [2] bigrams, and so on.
    ngrams = []
    ngrams.insert(0,  [])

    # build ngrams of input string
    for n in range(1, 6):
        ngrams.insert(n,  {})

        for docName in words.keys():
            for sentenceIndex,  wordList in enumerate(words[docName]):
                sentenceList = buildSentenceList(words[docName][sentenceIndex])

                if n == 1:
                    maxBound = len(sentenceList)
                else:
                    maxBound = -(n - 1)

                for wordIndex,  word in enumerate(sentenceList[0:maxBound]):
                    ngrams[n][':'.join([docName,  str(sentenceIndex),  str(wordIndex)])] = sentenceList[wordIndex:wordIndex + n]

    timexes = []

    # feed this regex list a set of ngrams; look for complete matches.
    tid = 0
    for n in range(1, 6):
        for key,  wordList in ngrams[n].items():
            
            #window_string = ' '.join(wordList)
            window_string = buildTimeString(wordList)
            for test in timex_re:
                matches = re.compile(test,  re.I).finditer(window_string)

                for match in matches:
                    matchDoc,  matchSentence,  matchStart = key.split(':')
                    matchSentence,  matchStart = map(int,  [matchSentence,  matchStart])
                    matchEnd = matchStart + n - 1

                    c = {'doc':matchDoc,  'sentence':matchSentence,  'start':matchStart,  'end':matchEnd}

                    # list item l
                    added = False
#                    print c['start'],  c['end'],  buildSentenceList(words[c['doc']][c['sentence']])[c['start']:c['end']+1]
                    for k, l in enumerate(timexes):

                        # skip timexes not in the same sentence
                        if c['sentence'] != l['sentence'] or c['doc'] != l['doc']:
                            continue

                        # already found this one - don't bother doing anything with it
                        if c['start'] == l['start'] and c['end'] == l['end']:
                            added = True
                            break

                        # have we got an overlap?
                        elif (c['start'] >= l['start'] and c['start'] <= l['end']) or (c['end'] >= l['start'] and c['end'] <= l['end']):
                            expanded_start = min(c['start'],  l['start'])
                            expanded_end = max(c['end'],  l['end'])
                            expanded_string = buildSentenceList(words[c['doc']][c['sentence']])[expanded_start:expanded_end+1]
                            expanded_entry = {'doc':c['doc'], 'sentence':c['sentence'],  'start':expanded_start,  'end':expanded_end,  'tid':tid}
#                            print 'Merged with', l['start'], '-', l['end'], 'to',  expanded_entry,  expanded_string,  '(from)',  buildSentenceList(words[c['doc']][c['sentence']])[c['start']:c['end']+1],  'and',  buildSentenceList(words[c['doc']][c['sentence']])[l['start']:l['end']+1]
                            tid += 1
                            timexes[k] = expanded_entry
                            added = True
                            continue

#                        k += 1 # This does nothing in Python for loop. k is reassigned each loop

                    if not added:
                        c['tid'] = tid
                        timexes.append(c)
                        tid += 1

    # remove duplicate timexes - these can be annotated when we have something like 10th January 1920, and annotate "January" and "1920" separately, then merge to form "10th January" and "1920", and try to merge "10th January 1920", which will match both fragments.
    # de-dupe timexes by doc / sentence / start / end
    for t in timexes:
        # count how many matches for this timex there are; if a copy is found when matches already = 1, nuke it
        matches = 0
        for reference,  y in enumerate(timexes):
            if t['doc'] == y['doc'] and t['sentence'] == y['sentence'] and t['start'] == y['start'] and t['end'] == y['end']:
                if matches == 0:
                    matches += 1
                else:
                    # remove this element
                    del timexes[reference]
        
        ##: remove elements if it is included within this timex
        nr = range(len(timexes))
        nr.reverse()
        for reference in nr:
            y = timexes[reference]
            if t['doc'] == y['doc'] and t['sentence'] == y['sentence'] and ((t['start'] <= y['start'] and t['end'] > y['end'])
                                                                             or (t['start'] < y['start'] and t['end'] >= y['end'])):
                # remove this element
                del timexes[reference]
                
    timexes.sort(key=lambda t: t['start'])
     
    ##: handle "two and half weeks" or "1 1/2 wks"     
    ww=words['stdin'][0]
    nr = range(len(timexes))
    nr.reverse()
    for i in nr:
        t = timexes[i]
        if t['start'] > 0:
            timeString = ' '.join([ww[k] for k in range(t['start'], t['end']+1)])
            
            if ww[t['start']-1].lower()=='and':
                if re.match('^([0-9]+|'+textual_number+')$', ww[t['start']-2]) \
                    and re.match('^([0-9]+|'+textual_number+')$', ww[t['start']]) \
                    and re.match(calendar_interval, ww[t['start']+1]):
                    t2 = t['start'] - 2
                    if not [tt  for tt in timexes if tt['start']<=t2 and t2<=tt['end']]:
                        t['start'] -= 2
                    continue 
                
                if re.match('^([0-9]+|'+textual_number+')$', ww[t['start']-2]) \
                    and re.match('^([0-9]+|'+textual_number+')$', ww[t['start']]) \
                    and re.match(monthspec, ww[t['start']+1], re.I):
                    t2 = t['start'] - 2
                    if not [tt  for tt in timexes if tt['start']<=t2 and t2<=tt['end']]:
                        t['start'] -= 2
                    continue 
                
            if re.match('[0-9]+', ww[t['start']-1]) and re.match('^'+fractions+'$', ww[t['start']]): ###: "3 3/4 weeks"
                if t['start']==t['end']: ##: just a fraction number like "3 3/4"
                    timexes.remove(t)
                else:
                    t['start'] -= 1
                continue
            ##: 3-4 days
            if re.match('^([0-9]+|'+textual_number+')-('+ '[0-9]+|'+textual_number+')$', ww[t['start']-1]):
                t['start'] -= 1
                continue
            
            ##: e.g., three to four days
            if (ww[t['start']-1].lower()=='to' or ww[t['start']-1].lower()=='-') and t['start']>1 and re.match('^([0-9]+|'+textual_number+')$', ww[t['start']-2]):
                t2 = t['start'] - 2
                if not [tt  for tt in timexes if tt['start']<=t2 and t2<=tt['end']]:
                    t['start'] -= 2
            
            ##: day 1, day 2, day two,...
            if ww[t['start']].lower()=='day' and t['start']==t['end'] and t['end']+1<len(ww) \
                and (ww[t['end']+1].lower() in digits or ww[t['end']+1].isdigit()):
                t['end'] += 1
                continue
            
#             ##: only keep "... the time/day of..."
#             if ww[t['end']].lower() in ['time', 'day'] and ww[t['start']].lower()!='same' and not re.match('^([0-9]+|'+textual_number+')$', ww[t['start']]) \
#                     and t['end']+1<len(ww) and not ww[t['end']+1].lower() in ['of', 'that', 'when']:
#                 timexes.remove(t)
    
    # remove timexes contained in others, AGAIN, after above merge operations
    for t in timexes:
        ##: remove elements if it is included within this timex
        nr = range(len(timexes))
        nr.reverse()
        for reference in nr:
            y = timexes[reference]
            if t['doc'] == y['doc'] and t['sentence'] == y['sentence'] and ((t['start'] <= y['start'] and t['end'] > y['end'])
                                                                             or (t['start'] < y['start'] and t['end'] >= y['end'])):
                # remove this element
                del timexes[reference]
                 
    timexes.sort(key=lambda t: t['start'])
    
    return timexes

def getTimexType(timexString,  previous3Words, next2Words):
    """Determine the type of time expression based on its neighbouring information"""

    #durationRx = re.compile(r'\b(for|during)\b',  re.I)
    longdays = "((mon|tues|wednes|thurs|fri|satur|sun|to|yester)day|tomorrow)"
    dayspec = "("+longdays+"|(mon|tue|wed|thu|fri|sat|sun)\.? )"
    weekdayRx = re.compile(dayspec, re.I)
    
    calendar_interval = "(minute|hour|day|weekend|week|month|quarter|year|morning|afternoon|evening|night|hr|wk|mo|yr|time)"
    intervalRx = re.compile(calendar_interval, re.I)
    
    digits = "(one|two|three|four|five|six|seven|eight|nine)"
    ordinals = "(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)"
    ordinalRx =  re.compile(ordinals, re.I)
    
    abbrRx = re.compile("((HD|POD) ?#? ?[1-9][0-9]?)") # HD: Hospital day; POD: Post op day 
    stayRx = re.compile("((hospital|his|her|the|unit) stay)") #: during his hospital stay    
    
    # DURATION: "for 6 months"
    # a year ago - relative date
    # a year - duration
    
    #if durationRx.search(previous3Words) or timexString[-1:] == 's' or (timexString[0:2].lower() == 'a ' and timexString.count(' ') < 2):
    #    timexType = 'DURATION'
    #if next2Words[0:3].lower() == 'old' or next2Words[0:6].lower() == "of age" or previous3Words[-7:].lower()=='born in':
    if (len(next2Words)>0 and next2Words[0].lower() == 'old') \
        or (len(next2Words)==2 and next2Words[0].lower() == 'of' and next2Words[1].lower()=="age") \
        or (len(previous3Words)>=2 and previous3Words[-2].lower()=='born' and previous3Words[-1].lower()=='in') \
        or (len(previous3Words)>=2 and previous3Words[-2].lower()=='age' and previous3Words[-1].lower()=='of'):
        timexType = 'AGE'    
    elif weekdayRx.search(timexString): # weekday
        #timexType = 'WEEKDAY'
        timexType = 'REL'
    elif abbrRx.search(timexString) or stayRx.search(timexString): # HD#1 or POD#2
        timexType = 'REL'
    elif intervalRx.search(timexString): # time interval
        if (len(previous3Words)>0 and previous3Words[-1].lower() in ['for', 'x', 'over', 'last', 'lasting', 'lasted', 'persisted', 'persisting', 'within']) \
            or (len(previous3Words)>1 and previous3Words[-2].lower()=='the' \
                and previous3Words[-2].lower() in ['for', 'over', 'last', 'lasting', 'lasted', 'within']):
            timexType = 'DUR'          
        elif len(previous3Words)>0 and previous3Words[-1].lower() in ['every', 'per']:      
            timexType = 'FRQ'          
        elif (timexString.lower().split()[0] in relTimeSignals) \
            or (len(previous3Words)>0 and previous3Words[-1].lower() in relTimeSignals) \
            or (len(next2Words)>0 and next2Words[0].lower() in relTimeSignals) \
            or ordinalRx.search(timexString) \
            or set(timexString.lower().split()).intersection(set(['same', 'time','day','morning','afternoon','evening', 'night'])) \
            or timexString.lower().split()[-1].lower() in digits \
            or timexString.lower().split()[-1].isdigit():
            timexType = 'REL'
        else: # a 3 day span, a five week treatment
            timexType = 'OTHER'
    elif timexString.lower()=='now':
        timexType = 'REL'
    else:
        timexType = 'DATE'
    
    return timexType


def getTimexType4Annotation(timexString,  previous3Words, next2Words):
    """Determine the type of time expression for time annotation purpose"""

    longdays = "((mon|tues|wednes|thurs|fri|satur|sun)day)"
    dayspec = "("+longdays+"|(mon|tue|wed|thu|fri|sat|sun)\.? )"
    weekdayRx = re.compile(dayspec, re.I)
    
    reldays = "((to|yester)day|tomorrow)"
    reldayRx = re.compile(reldays, re.I)
    
    calendar_interval = "(minute|hour|day|weekend|week|month|quarter|year|morning|afternoon|evening|night|hr|wk|mo|yr|time)"
    intervalRx = re.compile(calendar_interval, re.I)
    
    digits = "(one|two|three|four|five|six|seven|eight|nine)"
    ordinals = "(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)"
    ordinalRx =  re.compile(ordinals, re.I)
    
    abbrRx = re.compile("((HD|POD) ?#? ?[1-9][0-9]?)") # HD: Hospital day; POD: Post op day 
    stayRx = re.compile("((hospital|his|her|the|unit) stay)") #: during his hospital stay    
    
    # DURATION: "for 6 months"
    # a year ago - relative date
    # a year - duration
    
    #if durationRx.search(previous3Words) or timexString[-1:] == 's' or (timexString[0:2].lower() == 'a ' and timexString.count(' ') < 2):
    #    timexType = 'DURATION'
    #if next2Words[0:3].lower() == 'old' or next2Words[0:6].lower() == "of age" or previous3Words[-7:].lower()=='born in':
    if (len(next2Words)>0 and next2Words[0].lower() == 'old') \
        or (len(next2Words)==2 and next2Words[0].lower() == 'of' and next2Words[1].lower()=="age") \
        or (len(previous3Words)>=2 and previous3Words[-2].lower()=='born' and previous3Words[-1].lower()=='in') \
        or (len(previous3Words)>=2 and previous3Words[-2].lower()=='age' and previous3Words[-1].lower()=='of'):
        timexType = 'Age'    
    elif weekdayRx.search(timexString): # weekday
        timexType = 'Weekday'
#         timexType = 'REL'
    elif abbrRx.search(timexString) or stayRx.search(timexString) or reldayRx.search(timexString): # HD#1 or POD#2
        timexType = 'Relative'
    elif intervalRx.search(timexString): # time interval
        if (len(previous3Words)>0 and previous3Words[-1].lower() in ['for', 'x', 'over', 'last', 'lasting', 'lasted', 'persisted', 'persisting', 'within']) \
            or (len(previous3Words)>1 and previous3Words[-2].lower()=='the' \
                and previous3Words[-2].lower() in ['for', 'over', 'last', 'lasting', 'lasted', 'within']):
            timexType = 'Duration'          
        elif len(previous3Words)>0 and previous3Words[-1].lower() in ['every', 'per']:      
            timexType = 'Frequency'          
        elif (timexString.lower().split()[0] in relTimeSignals) \
            or (len(previous3Words)>0 and previous3Words[-1].lower() in relTimeSignals) \
            or (len(next2Words)>0 and next2Words[0].lower() in relTimeSignals) \
            or ordinalRx.search(timexString) \
            or set(timexString.lower().split()).intersection(set(['same', 'time','day','morning','afternoon','evening', 'night'])) \
            or timexString.lower().split()[-1].lower() in digits \
            or timexString.lower().split()[-1].isdigit():
            timexType = 'Relative'
        else: # a 3 day span, a five week treatment
            timexType = ''
    elif timexString.lower()=='now':
        timexType = 'Relative'
    else:
        timexType = 'Date'
    
    return timexType

def getDayDifference(s):
    timeDiff = {'today':0, 'now':0, 'tomorrow':1, 'yesterday':-1}
    if s in timeDiff:
        return timeDiff[s]
    else:
        return 0

def getRelativeDatetime(timexString, relation, refDatetime):
    """Evaluate a realtive time based on time expression, relationship and time reference. """
    
    timexString = timexString.lower()
    intervals = " (minute|hour|day|morning|afternoon|evening|night|week|month|quarter|year|hr|min|wk|mo|yr)(s)?"
    
    vague = "(around|about|roughly|nearly|over|approximately|approximate|approx)"
    matches = re.findall(vague, timexString)
    if matches:
        s = matches[0]
        loc = timexString.find(s)
        timexString = timexString[:loc] + timexString[loc+len(s)+1:]

    newtime = refDatetime
    matches = re.findall(intervals, timexString)
    
    if matches:
        interval, ss = matches[0]
        loc = timexString.find(interval+ss)
        numstr = timexString[:loc] + timexString[loc+len(interval+ss):]
    else:
        return newtime
    
    distance = 0
    
    ##: 3-5 days
    if len(numstr.split())==1 and numstr.find('-')>0: 
        numstr = numstr[:numstr.find('-')]
    
    # handle number and fractions
    fractions = '([0-9]+ )?(([1-9]+)/([1-9]+))?'
    matches = re.findall(fractions, numstr)
    if matches:
        i, frac, num, den = matches[0]
        if i:
            distance += float(i)
        if frac:
            distance += float(num)/float(den)
    
    loc = numstr.find('and a')
    if loc>=0:
        numstr = numstr[:loc] + numstr[loc+5:]
        
    loc = numstr.find('and')
    if loc>=0:
        numstr = numstr[:loc] + numstr[loc+3:]
        
    ##: e.g., three to four days. Keep four days only
    loc = numstr.find(' to ')
    if loc>=0:
        numstr = numstr[loc+3:]
    
    if numstr.isdigit():
        distance = float(numstr)
    else:
        num = util.text2num.convert(numstr)
        if num:
            distance = float(num)
        
    if interval in ['year', 'yr']:
        delta = timedelta(days=365*distance)
    elif interval == 'quarter':
        delta = timedelta(weeks=12*distance)
    elif interval in ['month', 'mo']:
        delta = timedelta(days=30*distance)
    elif interval in ['week', 'wk']:
        delta = timedelta(weeks=distance)
    elif interval in ['day', 'morning', 'afternoon', 'evening', 'night']:
        delta = timedelta(days=distance)
    elif interval in ['hour', 'hr']:
        delta = timedelta(hours=distance)
    elif interval in ['minute', 'min']:
        delta = timedelta(minutes=distance)
    else:
        delta = timedelta()

    if relation.lower()=='after':
        newtime = refDatetime + delta
    elif relation.lower()=='before':
        newtime = refDatetime - delta
    else:
        newtime = refDatetime
    
    return newtime

def parse_string_complementary(timexString, referenceDate = None):
    """Parse time string that cannot be parsed with dateutil.parser. Called in annotateTimexes()"""
    
    fullyear = "19[0-9]{2}|20[0-3][0-9]"
    shortyear = "['|\-|/]([0-9]{2})"
    year2dthreshold = 30 # for 2 digit year, 19xx when y2d>30, 20xx for y2d<30
    daysMonth = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    shortmonth = "jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"    
    fullmonth = "january|february|march|april|may|june|july|august|september|october|november|december"
    monthspec = "(jan|feb|mar|apr|may|jun|jul|aug|sept|sep|oct|nov|dec|"+fullmonth+")"
        
    #################################################################################    
    #   date with format 23Apr2005, 3Apr2005, 23Apr05 or 3Apr05  
    #################################################################################
    day_month_year = "([0-3]?[0-9])(" + shortmonth + ")(" + fullyear + "|[0-9]{2})"
    
    matches = re.findall(day_month_year, timexString, re.I)
    if matches:
        (ds, ms, ys) = matches[0]
        if ys:
            if len(ys) == 2:
                if int(ys) > year2dthreshold:
                    y = 1900 + int(ys)
                else:
                    y = 2000 + int(ys)
            else:
                y = int(ys)
        if ms:
            m = months.index(ms[0:3].lower()) + 1
        if ds:
            d = int(ds)
        
        if d < 1:
            d = 1
        elif d > daysMonth[m-1]:
            d = daysMonth[m-1]

        outputDatetime = datetime(y, m, d)
        confidence = 1
        if len(matches)==1:
            return (outputDatetime, confidence)
    
        ##: 28JUL05-12AUG06 
        (ds, ms, ys) = matches[1]
        if ys:
            if len(ys) == 2:
                if int(ys) > year2dthreshold:
                    y = 1900 + int(ys)
                else:
                    y = 2000 + int(ys)
            else:
                y = int(ys)
        if ms:
            m = months.index(ms[0:3].lower()) + 1
        if ds:
            d = int(ds)
        
        if d < 1:
            d = 1
        elif d > daysMonth[m-1]:            
            d = daysMonth[m-1]

        outputDatetime2 = datetime(y, m, d)
        confidence = 1
        return ([outputDatetime, outputDatetime2], confidence)
    #################################################################################    
    #   date with format 3Nov, 12NOV  
    #################################################################################   
    day_month = "([0-3]?[0-9])(" + shortmonth + ")" # 13Nov or 3NOV
    
    if referenceDate:
        y = referenceDate.year
    else:
        y = 1900
        
    matches = re.findall(day_month, timexString, re.I)
    if matches:
        (ds, ms) = matches[0]

        if ms:
            m = months.index(ms[0:3].lower()) + 1
        if ds:
            d = int(ds)
        
        if d < 1:
            d = 1
        elif d > daysMonth[m-1]:
            d = daysMonth[m-1]
            
        outputDatetime = datetime(y, m, d)
        confidence = 0.8
        return (outputDatetime, confidence)

    #################################################################################    
    #   date with format # mon/day/year-mon/day/year, e.g., 10/22/98-1/13/99
    #################################################################################
    mon1_day1_year1_mon2_day2_year = "(" + shortmonth + "|[0-1]?[0-9])/([0-3]?[0-9])/(" + fullyear + "|[0-9]{2})-([0-1]?[0-9])/?([0-3]?[0-9])?/(" + fullyear + "|[0-9]{2})"
    matches = re.findall(mon1_day1_year1_mon2_day2_year, timexString, re.I)
    if matches:
        (ms1, ds1,ys1, ms2, ds2, ys2) = matches[0]

        if ys1:
            if len(ys1) == 2:
                if int(ys1) > year2dthreshold:
                    y1 = 1900 + int(ys1)
                else:
                    y1 = 2000 + int(ys1)
            else:
                y1 = int(ys1)
        if ys2:
            if len(ys2) == 2:
                if int(ys2) > year2dthreshold:
                    y2 = 1900 + int(ys2)
                else:
                    y2 = 2000 + int(ys2)
            else:
                y2 = int(ys2)
        if ms1:
            if ms1.isdigit():
                m1 = int(ms1)
            else:
                m1 = months.index(ms1[0:3].lower()) + 1
        if ms2:
            if ms2.isdigit():
                m2 = int(ms2)
            else:
                m2 = months.index(ms2[0:3].lower()) + 1     
        
        if m1 < 1:
            m1 = 1
        elif m1 > 12:
            m1 = 12
        if m2 < 1:
            m2 = 1
        elif m2 > 12:
            m2 = 12
            
        if ds1:
            d1 = int(ds1)
        else:
            d1 = 1
        if d1 < 1:
            d1 = 1
        elif d1 > daysMonth[m1-1]:
            d1 = daysMonth[m1-1]
            
        if ds2:
            d2 = int(ds2)
        else:
            d2 = 1
        if d2 < 1:
            d2 = 1
        elif d2 > daysMonth[m2-1]:
            d2 = daysMonth[m2-1]

        outputDatetime1 = datetime(y1, m1, d1)
        outputDatetime2 = datetime(y2, m2, d2)
        confidence = 1
        return ([outputDatetime1, outputDatetime2], confidence)
    
    
    #################################################################################    
    #   date with format # mon/day-mon/day/year, e.g., 10/02-11/13/99
    #################################################################################
    mon1_day1_mon2_day2_year = "(" + shortmonth + "|[0-1]?[0-9])/([0-3]?[0-9])-(" + shortmonth + "|[0-1]?[0-9])/([0-3]?[0-9])/(" + fullyear + "|[0-9]{2})"
    matches = re.findall(mon1_day1_mon2_day2_year, timexString, re.I)
    if matches:
        (ms1, ds1, ms2, ds2, ys) = matches[0]

        if ys:
            if len(ys) == 2:
                if int(ys) > year2dthreshold:
                    y = 1900 + int(ys)
                else:
                    y = 2000 + int(ys)
            else:
                y = int(ys)
        if ms1:
            if ms1.isdigit():
                m1 = int(ms1)
            else:
                m1 = months.index(ms1[0:3].lower()) + 1
        if ms2:
            if ms2.isdigit():
                m2 = int(ms2)
            else:
                m2 = months.index(ms2[0:3].lower()) + 1            
                
        if m1 < 1:
            m1 = 1
        elif m1 > 12:
            m1 = 12
        if m2 < 1:
            m2 = 1
        elif m2 > 12:
            m2 = 12
                            
        if ds1:
            d1 = int(ds1)
        if d1 < 1:
            d1 = 1
        elif d1 > daysMonth[m1-1]:
            d1 = daysMonth[m1-1]
            
        if ds2:
            d2 = int(ds2)
        if d2 < 1:
            d2 = 1
        elif d2 > daysMonth[m2-1]:
            d2 = daysMonth[m2-1]

        outputDatetime1 = datetime(y, m1, d1)
        outputDatetime2 = datetime(y, m2, d2)
        confidence = 1
        return ([outputDatetime1, outputDatetime2], confidence)

    #################################################################################    
    #   date with format # mon/day-day/year, e.g., 10/02-13/99
    #################################################################################
    mon_day2_year = "(" + shortmonth + "|[0-1]?[0-9])/([0-3]?[0-9])-([0-3]?[0-9])/(" + fullyear + "|[0-9]{2})" # mon/day-day/year, e.g., 10/02-13/99
    matches = re.findall(mon_day2_year, timexString, re.I)
    if matches:
        (ms, ds1, ds2, ys) = matches[0]

        if ys:
            if len(ys) == 2:
                if int(ys) > year2dthreshold:
                    y = 1900 + int(ys)
                else:
                    y = 2000 + int(ys)
            else:
                y = int(ys)
        if ms:
            if ms.isdigit():
                m = int(ms)
            else:
                m = months.index(ms[0:3].lower()) + 1
        if m < 1:
            m = 1
        elif m > 12:
            m = 12
                        
        if ds1:
            d1 = int(ds1)
        if d1 < 1:
            d1 = 1
        elif d1 > daysMonth[m-1]:
            d1 = daysMonth[m-1]
            
        if ds2:
            d2 = int(ds2)
        if d2 < 1:
            d2 = 1
        elif d2 > daysMonth[m-1]:
            d2 = daysMonth[m-1]

        outputDatetime1 = datetime(y, m, d1)
        outputDatetime2 = datetime(y, m, d2)
        confidence = 1
        return ([outputDatetime1, outputDatetime2], confidence)

    #################################################################################    
    #   date with format # day to/- day month year, e.g., 11 to 12 November 2008
    #################################################################################
    day2_mon_year = "([0-3]?[0-9])(-| to )([0-3]?[0-9])( |/)" + monthspec + '( |/)('+ fullyear + ")" # mon/day-day/year, e.g., 10/02-13/99
    matches = re.findall(day2_mon_year, timexString, re.I)
    if matches:
        (ds1, dummy, ds2, dummy, ms, dummy, ys) = matches[0]

        if ys:
            if len(ys) == 2:
                if int(ys) > year2dthreshold:
                    y = 1900 + int(ys)
                else:
                    y = 2000 + int(ys)
            else:
                y = int(ys)
        if ms:
            if ms.isdigit():
                m = int(ms)
            else:
                m = months.index(ms[0:3].lower()) + 1
        if m < 1:
            m = 1
        elif m > 12:
            m = 12
                        
        if ds1:
            d1 = int(ds1)
        if d1 < 1:
            d1 = 1
        elif d1 > daysMonth[m-1]:
            d1 = daysMonth[m-1]
            
        if ds2:
            d2 = int(ds2)
        if d2 < 1:
            d2 = 1
        elif d2 > daysMonth[m-1]:
            d2 = daysMonth[m-1]

        outputDatetime1 = datetime(y, m, d1)
        outputDatetime2 = datetime(y, m, d2)
        confidence = 1
        return ([outputDatetime1, outputDatetime2], confidence)
    
    return (None, None)


def parse_raw_time(timestring):    
    """ Break down time string like: "2 and 5 Dec 2019" """
    fullmonth = "january|february|march|april|may|june|july|august|september|october|november|december"
    monthspec = "(jan|feb|mar|apr|may|jun|jul|aug|sept|sep|oct|nov|dec|"+fullmonth+")"
    matches = re.findall('([0-3]?[0-9]) and ([0-3]?[0-9]) '+monthspec, timestring, re.I)
    timexStrings=[]
    if matches:
        (ds1, ds2, ms) = matches[0]
        pos = timestring.find(ms)
        timexStrings = [ds1 + ' ' + timestring[pos:], ds2 + ' ' + timestring[pos:]]
        print timexStrings
        
    if not timexStrings:
        return parse_single_raw_time(timestring)
    
    YMDs = []
    for s in timexStrings:
        YMDs.append(parse_single_raw_time(s))
    
    return YMDs
    
def parse_single_raw_time(timestring):    
    """This function is a hack of dateutil.parser.parse. It parses time string without adding default year or date, 
    so that the missing information can be filled in later. For example, '11/2'->(None, 11, 2) instead of 
    datetime(2014, 11, 2) from dateutil.parser.parse.
    
    IMPORTANT: This function is not compatible with python-dateutil 2.5. Must use version 2.4.2.
    """
    _CURRENT_YEAR = datetime.now().year
    try:
        parsed_result = parser._parse(parser(), StringIO(timestring))
    except:
        return None
    if not parsed_result: return None
    
#     if isinstance(parsed_result, list):
    if isinstance(parsed_result, tuple):
        parsed_date = parsed_result[0]
    else:
        parsed_date = parsed_result
    
    if parsed_date==None:
        return None
    
    YMD = {}
    ##: If any of obtained year, month or day is out of range, we think this date is invalid, 
    ##: and thus the whole YMD is set to 'None' 
    if parsed_date.year:
        YMD['year'] = parsed_date.year
#         if parsed_date.year >= 1960 and parsed_date.year <= _CURRENT_YEAR: 
#             YMD['year'] = parsed_date.year
#         else:
#             return None
    else:
        YMD['year'] = None
    
    if parsed_date.month: 
        if parsed_date.month >= 1 and parsed_date.month <= 12: 
            YMD['month'] = parsed_date.month
        else:
            return None
    else:
        YMD['month'] = None
    if parsed_date.day:
        if parsed_date.day >= 1 and parsed_date.day <= 31: 
            YMD['day'] = parsed_date.day
        else:
            return None
    else:
        YMD['day'] = None
    
    if not YMD['year'] and not YMD['month'] and not YMD['day']:
        YMD = None
        
    return YMD


def get_timexes_for_evaluation(text):   
    """This function is used for time annotation only"""
     
    longdays = "((mon|tues|wednes|thurs|fri|satur|sun)day)"
    dayspec = "("+longdays+"|(mon|tue|wed|thu|fri|sat|sun)\.? )"    
    
    times = "([012][0-9][\:][0-5][0-9](pm|am)?)"

    weekdayRx = re.compile(dayspec, re.I)
    timeRx = re.compile(times, re.I)
    
    timexList = annotateTimexes(text)
    for t in timexList:
        if t.getType()=='REL':
            if weekdayRx.search(t.getString()): # weekday
                t.setType('WEEKDAY')
        elif t.getType()=='OTHER':
                t.setType('DUR')
        elif t.getType()=='DATE':
            if timeRx.search(t.getString()):
                t.setType('TIME')
    
    dictTimeTypes = {'DATE':'Date', 'REL':'Relative', 'DUR':'Duration', 'WEEKDAY':'Weekday', 'FRQ':'Frequency', 'AGE':'Age', 'TIME':'Time'}
    for t in timexList:
        t.setType(dictTimeTypes[t.getType()])
    
    return timexList

def annotateTimexes(text, referenceDate = None):
    """This is the main function in this module. Extract timexes from the text. 
    It determines the time string, type, location, partial information and evaluates absolute date.
    
    Input -- The text to be processed
    Output -- A list of Timex3 objects. 
    """
    sentences = util.sentence_tokenize(text)
    tokens = [word for sent in sentences for word in word_tokenize(sent)]
    
    ###: find starting locations of all tokens
    n = len(tokens)
    lenText = len(text)
    locsTokenStarts = [-1] * n
    curpt = 0
    for i in range(n):
        pos = text[curpt:].find(tokens[i])
        
        if tokens[i]=='``' or tokens[i]=="''":
            pos2 = text[curpt:].find('"')
            if pos2>=0 and pos2<pos:
                tokens[i]='"'
                pos = pos2
                
        if pos < 0:
            locsTokenStarts[i] = curpt
            curpt += 1
        else:
            locsTokenStarts[i] = pos + curpt
            curpt = locsTokenStarts[i] + len(tokens[i])

    ###: convert to words[file][sent][word] = "token"
    words = {}
    words['stdin'] = {}
    words['stdin'][0] = {}

    offset = 0
    for token in tokens:
        words['stdin'][0][offset] = token
        offset += 1

    # get timexes
    timexes = findTimexes(words)    
    #timexes.sort(key=lambda t: t['start'])
    
    timexList = []

    id = 0;
    for t in timexes:        
        timexString0 = text[locsTokenStarts[t['start']]:locsTokenStarts[t['end']]+len(tokens[t['end']])]
        timexString = timexString0.strip(' ?-/,')
        if len(timexString0)!=len(timexString):
            loc = timexString0.find(timexString)
            locsTokenStarts[t['start']] = locsTokenStarts[t['start']]+loc
            tokens[t['start']] = tokens[t['start']][loc:]
            tokens[t['end']] = tokens[t['end']].rstrip(' ?-/,')
            
            
        ##: Some exceptions
        if timexString in ['may', 'HR']:
            continue

        ###: only annotate DATE timexes
        previous3Words = tokens[max(0,t['start']-3):t['start']]
        next2Words = tokens[t['end']+1:t['end']+3]
        strType = getTimexType(timexString,  previous3Words, next2Words)
        
        timexDate = None
        confidence = 0.5
        istart = locsTokenStarts[t['start']]
        iend = locsTokenStarts[t['end']] + len(tokens[t['end']])-1
        if strType == 'DATE':            
            if not ' to ' in timexString: 
                timexDate = parse_raw_time(timexString)
            
            if not timexDate:
                (timexDate, confidence) = parse_string_complementary(timexString)
                
                if timexDate:
                    if isinstance(timexDate, list) and len(timexDate)==2:
                        if '-' in timexString:
                            iend1 = timexString.find('-')-1
                            istart2 = iend1 + 2
                        elif ' to ' in timexString:
                            iend1 = timexString.find(' to ')-1
                            istart2 = iend1 + 5
                        else:
                            iend1 = iend - istart
                            istart2 = 0
                        
                        timex = Timex3(istart, iend1+istart, strType, timexDate[0], timexString[:iend1+1], confidence)
                        timexList.append(timex)
                        timexDate = timexDate[1]
                        istart = istart2 + istart
                        timexString = timexString[istart2:]
                        
                else:
                    continue

        timex = Timex3(istart, iend, strType, timexDate, timexString, confidence)
        timexList.append(timex)
            
    n = len(sentences)
    sentence_startPos = [-1] * n
    curpt = 0
    for i in range(n):
        pos = text[curpt:].find(sentences[i])
        sentence_startPos[i] = pos + curpt
        curpt = sentence_startPos[i] + len(sentences[i])
        
    for i, sent in enumerate(sentences):
        start_char_sent = sentence_startPos[i]
        
        end_char_sent = start_char_sent + len(sent)
        timexes = [timex for timex in timexList if timex.start >= start_char_sent and timex.end <= end_char_sent]
        for t in timexes:
            t.setSentenceNum(i)
    
    ###: Scan for partial timex, e.g., ..., in September, ..... Completment it with previous year 
    if referenceDate:
        preYear = referenceDate.year
        preMonth = referenceDate.month
    else:
        preYear = None
        preMonth = None
        
    for i, timex in enumerate(timexList):
        if timex.getType()!='DATE':
            continue
        
        if timex.getDateTime():
            preYear = timex.getDateTime().year
            preMonth = timex.getDateTime().month
            continue
        
        if not timex.YMD: continue 
        
        p = min(timex.getStartPos(), 18) ##: search back to cover 'beginning of the ...'
        preString = text[timex.getStartPos()-p:timex.getStartPos()]
        
        if timex.YMD['year']:
            year = timex.YMD['year']
        else:
            year = None
            ##: Firt find year within the same sentence
            for t in timexList[i+1:]:
                if t.getSentNum()>timex.getSentNum():
                    break
                if t.getDateTime():
                    year = t.getDateTime().year
                    break
                if t.YMD and t.YMD['year']:
                    year = t.YMD['year']
                    break
                
            if not year:
                year = preYear
            
        if timex.YMD['month']:
            month = timex.YMD['month']
        # when month is missing, there cannnot be both year and day. 
        elif timex.YMD['year']: # only year exists, previous month is meaningfulless, just use Jan.
            month = util.text2num.getInitialDate('year', None, preString)
            timex.YMD['day']=1
            #month = 1
        elif timex.YMD['day']:
            month = preMonth
            
        if timex.YMD['day']:
            day = timex.YMD['day']
        else:
            day = util.text2num.getInitialDate('month', month, preString)
            
        if year and month:
            try:
                newdate = datetime(year, month, day)
                timex.setDateTime(newdate)
                preYear = timex.getDateTime().year
                preMonth = timex.getDateTime().month
            except:
                pass
    
#     ##: Validate timex
#     for t in timexList:
#         if t.getString().lower()!=text[t.getStartPos():t.getEndPos()+1].lower():
#             s1 = re.sub(r'\s', '', t.getString().lower())
#             s2 = re.sub(r'\s', '', text[t.getStartPos():t.getEndPos()+1].lower())

    return timexList

def beautifyTimeInterval(timediff):
    seconds = int(timediff.total_seconds())
    mins = seconds/60
    if mins < 100:
        return str(mins) + ' minutes'
        
    hours = mins/60
    if hours < 48:
        return str(hours) + ' hours'
    
    days = hours/24
    if days < 90:
        return str(days) + ' days'
    
    months = days/30
    if months < 24:
        return str(months) + ' months'
    
    years = months/12
    mons = months - 12*years
    if mons < 3:
        return str(years) + ' years'
    else:
        return str(years) +  ' years and ' +str(mons) + ' months' 

    
def parse_time_string(time_string):        
    if time_string == '':
        return None
     
    try:
        dt = parser.parse(parser(), time_string)
    except:
        return None
        
    return dt
        
def isPartialDate(timexString):
    """Determine if the given time string represents a partial time"""
    
    fullyear = "19[0-9]{2}|20[0-3][0-9]"
    shortyear = "[ |'|\-|/]([0-9]{2})"    
    yearspec = "(" + fullyear + ")|" + shortyear + "$"    

    shortmonth = "jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"
    fullmonth = "january|february|march|april|may|june|july|august|september|october|november|december"
    monthspec = "(" + shortmonth + "|" + fullmonth + ")"
    
    isPartial = False
    date_separator = "[ |,|'|\-|/]"
    tokens = re.split(date_separator, timexString)
    tokens = [t for t in tokens if t!='']
    if len(tokens)==3:
        return (isPartial, None, None, None)
    
    isPartial = True
    #for t in tokens:
    if re.findall(monthspec, timexString, re.I):
        hasMonth = True
    else:
        hasMonth = False
            
    if re.findall(yearspec, timexString):
        hasYear = True
        hasDay = False
    else:
        hasYear = False
        m = re.findall('[0-3]?[0-9]', timexString)
        if m and len(m)==1: # len(m)==1 for avoid '47'=> ['4','7']
            hasDay = True
        else:
            hasDay = False
            
    return (isPartial, hasYear, hasMonth, hasDay)
            

def createTimexList(timexes, text, referenceDate = None):
    """This function is to create the list of Timex3 based on timex position. Used in ETHERNLP only."""
    
    sentences = util.sentence_tokenize(text)

    timexes.sort(key=lambda t: t['start'])
    
    timexList = []

    for t in timexes:        
        timexString = text[t['start']:t['end']+1]
            
        ##: Some exceptions
        if timexString in ['may', 'HR']:
            continue
        
        strType = t['type']
        
        timexDate = None
        confidence = 0.5
        istart = t['start']
        iend = t['end']
        if strType == 'DATE':            
            if 'Date' in t:
                timexDate =  parse_raw_time(t['Date'])
                
            if not timexDate and not ' to ' in timexString: 
                timexDate = parse_raw_time(timexString)
            
            if not timexDate:
                (timexDate, confidence) = parse_string_complementary(timexString)
                
                if timexDate:
                    if isinstance(timexDate, list) and len(timexDate)==2:

                        if '-' in timexString:
                            iend1 = timexString.find('-')-1
                            istart2 = iend1 + 2
                        elif ' to ' in timexString:
                            iend1 = timexString.find(' to ')-1
                            istart2 = iend1 + 5
                        else:
                            iend1 = iend - istart
                            istart2 = 0
                        
                        timex = Timex3(istart, iend1+istart, strType, timexDate[0], timexString[:iend1+1], confidence)
                        timex.setID(t['id'])
                        timexList.append(timex)
                        timexDate = timexDate[1]
                        istart = istart2 + istart
                        timexString = timexString[istart2:]
                        
                else:
                    continue

        timex = Timex3(istart, iend, strType, timexDate, timexString, confidence)
        timex.setID(t['id'])
        timexList.append(timex)
            
    n = len(sentences)
    sentence_startPos = [-1] * n
    curpt = 0
    for i in range(n):
        pos = text[curpt:].find(sentences[i])
        sentence_startPos[i] = pos + curpt
        curpt = sentence_startPos[i] + len(sentences[i])
        
    for i, sent in enumerate(sentences):
        start_char_sent = sentence_startPos[i]
        
        end_char_sent = start_char_sent + len(sent)
        timexes = [timex for timex in timexList if timex.start >= start_char_sent and timex.end <= end_char_sent]
        for t in timexes:
            t.setSentenceNum(i)
    
    ###: Scan for partial timex, e.g., ..., in September, ..... Completment it with previous year 
    if referenceDate:
        preYear = referenceDate.year
        preMonth = referenceDate.month
    else:
        preYear = None
        preMonth = None
        
    for i, timex in enumerate(timexList):
        if timex.getType()!='DATE':
            continue
        
        if timex.getDateTime():
            preYear = timex.getDateTime().year
            preMonth = timex.getDateTime().month
            continue
        
        if not timex.YMD: continue 
        
        p = min(timex.getStartPos(), 18) ##: search back to cover 'beginning of the ...'
        preString = text[timex.getStartPos()-p:timex.getStartPos()]
        
        if timex.YMD['year']:
            year = timex.YMD['year']
        else:
            year = None
            ##: Firt find year within the same sentence
            for t in timexList[i+1:]:
                if t.getSentNum()>timex.getSentNum():
                    break
                if t.getDateTime():
                    year = t.getDateTime().year
                    break
                if t.YMD and t.YMD['year']:
                    year = t.YMD['year']
                    break
                
            if not year:
                year = preYear
            
        if timex.YMD['month']:
            month = timex.YMD['month']
        # when month is missing, there cannnot be both year and day. 
        elif timex.YMD['year']: # only year exists, previous month is meaningfulless, just use Jan.
            month = util.text2num.getInitialDate('year', None, preString)
            timex.YMD['day']=1
        elif timex.YMD['day']:
            month = preMonth
            
        if timex.YMD['day']:
            day = timex.YMD['day']
        else:
            day = util.text2num.getInitialDate('month', month, preString)
            
        if year and month:
            try:
                newdate = datetime(year, month, day)
                timex.setDateTime(newdate)
                preYear = timex.getDateTime().year
                preMonth = timex.getDateTime().month
            except:
                pass
    
    return timexList

if __name__ == '__main__':
    
    s = parse_time_string('30 march 2017')
    s = getTimexType4Annotation('tomorrow', [], [])
    inputString = """ 1/2/2013 his. 05-08 fever. rash 2010"""
    inputString = """ on 12-19 May 2008 it. """
    inputString = "2 and 5 Dec 2019"
#     inputString = 'at 12:20pm '
    print 'len='+str(len(inputString))
    timexList = annotateTimexes(inputString)
    timexList = get_timexes_for_evaluation(inputString)
    for t in timexList:
        if t.getDateTime():
            print t.getString() + ',    ' + t.getDateTime().strftime('%m/%d/%Y') + ', type=' + t.getType() + ', ' + str(t.getStartPos())+ ', ' + str(t.getEndPos()) + ', "' + inputString[t.getStartPos():t.getEndPos()+1] + '"'
        else:
            print t.getString()  + ', type=' + t.getType()
     
    print 'finished!'
