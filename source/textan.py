#!/usr/bin python
# -*- coding: utf-8 -*-

"""Feature extraction and feature-time association 

This module extracts medical features of interest, and assigns time stamps to the features. 
The implementation borrows some code from Tarsqi toolkit [http://www.timeml.org/site/tarsqi/]

This module includes:
    class FeatureTextractor -- Main class provides functions to extract medical features and 
        associate features with time. 
    class Feature -- define medical feature
    class DocumentFeature – define features extracted from the text
"""
#
# Wei Wang, Engility, wei.wang@engility.com 
#

import nltk, re, StringIO, ast
import util
import timexan
from datetime import date, datetime, timedelta
from dateutil.parser import *

class Feature:
    """Feature class represents medical feature extracted from text"""
    def __init__(self, (ttype, sfeat, sentN, tags, startInText, endInText), inlinks=None):
        self.type = ttype
        self.string = sfeat
        self.sentNum = sentN
        self.startPos = startInText
        self.endPos = endInText
        self.tlink = inlinks
        
        self.id = -1
        self.confidence = 1
        if inlinks:
            if isinstance(inlinks, list):
                self.tlinks = inlinks
            else:
                self.tlinks = [inlinks]
        else:
            self.tlinks = None
            
        self.inclause = False
        
        tokens = nltk.word_tokenize(self.string)
#         self.tags = [(w, t) for (w, t) in tags if w in tokens]
        if tags:
            self.tags = [(w, [tg[1] for tg in tags if tg[0]==w][0]) for w in tokens if w in tokens]
        else:
            self.tags = []
        if len(self.tags)>0:
            self.cleanString = self._setCleanString(tokens)
        else:
            self.cleanString = self.string
            
    def getCleanString(self):
        return self.cleanString
    
    def _setCleanString(self, words):        
        """Clean feature text by removing some trigger words."""
        
        if self.type=='DIAGNOSIS':
            excludes = ['DX']
        elif self.type == 'SECOND_LEVEL_DIAGNOSIS':
            #excludes = ['Assessment','Impression', 'Possible', 'ModifierCertainty']
            excludes = ['Assessment','Impression']
        elif self.type == 'DRUG':
            excludes = ['Route']
        elif self.type == 'MEDICAL_HISTORY':
            excludes = ['History', 'MedicalHistory']
        elif self.type == 'FAMILY_HISTORY':
            excludes = ['History', 'FamilyHistory', 'Family']
        else:
            return self.string
        
        s = ''
        pretk = ','
        for i, w in enumerate(words):
            if self.tags[i][1] in excludes:
                continue
            elif self.tags[i][1]=='COMMA':
                if pretk==',': 
                    continue
                else:
                    s += w
                pretk = w
                continue
            elif s=='': 
                s += w
            else:
                s += ' ' + w
            pretk = w
                
        return  s

    def setInClause(self, flag):
        self.inclause = flag
    
    def inClause(self):
        return self.inclause
    
    def getType(self):
        return self.type
    
    def getSentNum(self):
        return self.sentNum
    
    def setSentNum(self, n):
        self.sentNum = n
        
    def getStartPos(self):
        return self.startPos
    
    def getEndPos(self):
        return self.endPos
    
    def getTlinks(self):
        return self.tlinks
            
    def getDateTime(self):        
        tlink = self.getTlink()
        if tlink and tlink.getDateTime():
            return tlink.getDateTime()
        return None
    
    def setDateTime(self, dt):     
        tm = timexan.Timex3(0, 0, 'VIRTUAL', dt, '')
        if self.getTlink():
            self.getTlink().insertTimex(0, tm)
        else:
            self.setTlink(TLink(tm))   
    
    def getTlink(self):
        return self.tlink
    
    def getTimex(self):
        tlink = self.getTlink()
        if tlink:    
            if tlink.getTimexes():
                return tlink.getTimexes()[0]
        else:
            return None
    
    def setTlinks(self, inlinks):
        self.tlinks = inlinks

    def setTlink(self, tlink):
        self.tlink = tlink
        
    def getString(self):
        return self.string
    
    def getTags(self):
        return self.tags
    
    def setTags(self, tags):
        self.tags = tags
        tokens = nltk.word_tokenize(self.string)
        if len(self.tags) > 0:
            self.cleanString = self._setCleanString(tokens)
        else:
            self.cleanString = self.string

    def setID(self, i):
        self.id = i
    
    def getID(self):
        return self.id
    
re_rule_header = re.compile('ruleNum=(\d+)-(\d+)')
re_attribute = re.compile('(.*)=(.*)')    
class BlinkerRule:

    """Implements the Blinker rule object."""
    
    def __init__(self, rule_type, rule_number):
        self.type = rule_type
        self.rule_number = rule_number
        self.id = "%s-%s" % (rule_type, rule_number)
        self.attrs = {}
        
    def set_attribute(self, attr, val):
        self.attrs[attr] = val

    def get_attribute(self, attr):
        return self.attrs.get(attr)

    def __str__(self):
        return '<BlinkerRule ' + self.id + '>'
    
    def pp(self):
        print "<BlinkerRule %s>" % self.id
        for attr, val in self.attrs.items():
            print "  %s=\"%s\"" % (attr, val)
            
def read_syntactic_rules(rule_file):
    
    """Read and return all the rules in the given rule file. All
    syntactic rule files need to adhere to the same syntax."""

    rules = []
    current_rule = None
    file = open(rule_file,'r')

    for line in file.readlines():
        # skip comments and empty lines
        line = line.strip()
        if line.startswith('#') or line == '':
            continue
        # find rule header
        match = re_rule_header.search(line)
        if match:
            if current_rule:
                # store previous rule and reset it
                rules.append(current_rule)
                current_rule = None
            (rule_type, rule_number) = match.group(1,2)
            current_rule = BlinkerRule(rule_type, rule_number)
            continue
        # find attributes
        match = re_attribute.search(line)
        if match:
            (att, val) = match.group(1,2)
            att = att.strip()
            val = val.strip()
            # value is now always a list of strings
            if val[0] != '(':
                val = [val]
            else:
                val = str.split(val[1:-1], '|')
            current_rule.set_attribute(att, val)
            continue

    # do not forget the very last rule
    if current_rule:
        rules.append(current_rule)

    return rules

class TLink:
    """Implements a TLink object. Note that this is not the same as the TLink is defined in TimeML.
    It was initially design to follow TimeML, but turned out to take a different approach. """
    
    def __init__(self, timexes=[]):
        if isinstance(timexes, list):
            self.timexes = timexes
        else:
            self.timexes = [timexes]
            
        self.type = "NORMAL"
        
        ##: this is used only when there are multiple durations: type=MULTI_DURATIONS
        ##: timexes2 stores the end time for each duration, while timexes stores the start time
        self.timexes2 = None 
    
    def copy(self):
        tk = TLink([])
        for t in self.timexes:
            if t.getType()=='DUR': # DUR timex could be altered to DATE. This will cause error when it is shared by multiple tlinks 
                tk.addTimex(t.copy())
            else:
                tk.addTimex(t)
        tk.setType(self.type)
        return tk
        
    def addTimex(self, timex):
        self.timexes.append(timex)
        
    def insertTimex(self, index, timex):
        self.timexes.insert(index, timex)
        
    def getTimexes(self):
        return self.timexes
    
    def getDateTime(self):
        for t in self.timexes:
            if t.getDateTime():
                return t.getDateTime()
    
    def setType(self, tp):
        self.type = tp
        
    def getType(self):
        return self.type
    
    def getStartPos(self):
        return self.timexes[0].getStartPos()
    
    def getEndPos(self):
        return self.timexes[-1].getEndPos()
    
    def reorderTimexes(self):
        self.timexes.sort(key=lambda t:t.getDateTime())
        
    def setTimexes2(self, ts):
        self.timexes2 = ts
        
    def getTimexes2(self):
        return self.timexes2
    
class DocumentFeature:
    """Class includes all extracted information for a give document. """
    
    def __init__(self, featList, timexes, expDate, onsetDate, receivedDate, expConfidence, expDateIn, onsetDateIn):
        self.timexList = timexes
        
        featList.sort(key= lambda f:f.getStartPos())
        self.featureList = featList
        
        self.exposeDate = expDate
        self.onsetDate = onsetDate
        self.receivedDate = receivedDate
        self.confidence = expConfidence
        
        if expDateIn:
            self.strExposeDateInput = expDateIn.isoformat().split('T')[0]
        else:
            self.strExposeDateInput = ''
            
        if onsetDateIn:
            self.strOnsetDateInput = onsetDateIn.isoformat().split('T')[0]
        else:
            self.strOnsetDateInput = ''
            
        if self.receivedDate:
            self.strReceivedDate = self.receivedDate.isoformat().split('T')[0]
        else:
            self.strReceivedDate = ''
        
        if expDate and onsetDate:
            dt = onsetDate - expDate
            hours = int(round(dt.total_seconds()/3600))
        else:
            hours = -1
            
        self.onsetHours = hours
        
    def getConfidenceLevel(self):
        return self.confidence
    
    def getCalculatedOnsetTimeHours(self):
        return self.onsetHours
    
    def isDatesInput(self):
        return self.stateDate=='Input'    # states: ['Extracted', 'Input', 'Estimated']
    
    def getReceivedDate(self):
        return self.strReceivedDate
    
    def getInputExpDate(self):
        return self.strExposeDateInput
    
    def getInputOnsetDate(self):
        return self.strOnsetDateInput
    
    def getExposeDate(self):
        return self.exposeDate
    
    def getOnsetDate(self):
        return self.onsetDate
            
    def print_document_features(self):
        if self.exposeDate:
            print 'expose = ' + self.exposeDate.isoformat().split('T')[0]
        if self.onsetDate:
            print 'onset = ' + self.onsetDate.isoformat().split('T')[0]
        
        print '\t'.join(['Timex', 'Start', 'End', 'Type', 'DateTime'])
        for t in self.timexList:
            if t.datetime: 
                #print '\t'.join([t.string, str(t.start), str(t.end), t.type, t.datetime.strftime('%m/%d/%Y %H:%M:%S')])
                print '\t'.join([t.string, str(t.start), str(t.end), t.type, t.datetime.isoformat()])
            else:
                print '\t'.join([t.string, str(t.start), str(t.end), t.type])
        
        print '\t'.join(['Type', 'Feature', 'Date', 'Relation'])
        features = self.getFeatureArray()
        for feature in features:
            print (feature[0], feature[1],  feature[3],  feature[4], feature[5],  feature[6]) # None holds MedDRA terms, last field is comment
                
    def print_document_features_tlinks(self):
        if self.exposeDate:
            print 'expose = ' + self.exposeDate.isoformat().split('T')[0]
        if self.onsetDate:
            print 'onset = ' + self.onsetDate.isoformat().split('T')[0]
        
        print '\t'.join(['Timex', 'Start', 'End', 'Type', 'DateTime'])
        for t in self.timexList:
            if t.datetime: 
                print '\t'.join([t.string, str(t.start), str(t.end), t.type, t.datetime.isoformat()])
            else:
                print '\t'.join([t.string, str(t.start), str(t.end), t.type])
        
        print '\t'.join(['Type', 'Feature', 'Date', 'Relation'])
        for feat in self.featureList:
            if feat.getTlink():
                timex_rel = feat.getTlink()['relation']
                timex_str = feat.getTlink()['timex'].string
                if feat.getTlink()['timex'].datetime:
                    timex_val = feat.getTlink()['timex'].datetime.isoformat().split('T')[0]
                else:
                    timex_val = ''
                if 'datetime2' in feat.getTlink():
                    timex_val2 = feat.getTlink()['datetime2'].isoformat().split('T')[0]
                else:
                    timex_val2 = ''
                        
                print "\t".join([feat.type, feat.string, timex_val, timex_val2, timex_rel])
            else:
                print "\t".join([feat.type, feat.string])
    
    def getDocTlinks(self):
        self.featureList.sort(key = lambda f:f.getStartPos())
        
        typeRanks = ['SIMULTANEOUS', 'OVERLAP', 'DURING', 'BEFORE_OVERLAP', 'BEGUN_BY', 'ENDED_BY', 'BEFORE', 'AFTER']

        tlinks = []
        tid = 0
        for feature in self.featureList:
            tlink = feature.getTlink()
            if not tlink:
                continue
                
            timexes = [t for t in tlink.getTimexes() if t.getDateTime()]
            if not timexes:                
                continue
                
            tkType = tlink.getType()
            if tkType=='MULTIPLE'  or tkType=='OR':
                for t in tlink.getTimexes():
                    dt = t.getDateTime()
                    tlk = (feature.type, feature.string, feature.startPos, feature.endPos, dt, 'SIMULTANEOUS')
                    tlinks.append(tlk)
                    tid += 1
                continue
            
            if tkType=='MULTI_DURATIONS':
                timexes2 = tlink.getTimexes2()
                for i, t in enumerate(timexes):
                    dt = t.getDateTime()
                    dt2 = timexes2[i].getDateTime()                    
                    tlk1 = (feature.type, feature.string, feature.startPos, feature.endPos, dt, 'BEGUN_BY')
                    tlk2 = (feature.type, feature.string, feature.startPos, feature.endPos, dt2, 'ENDED_BY')
                    tlinks.append(tlk1)
                    tlinks.append(tlk2)

                continue      
                            
            if tkType=='BETWEEN':
                tStart = timexes[0].getDateTime()
                if len(timexes)>1:
                    tEnd = timexes[1].getDateTime()
                    tlk1 = (feature.type, feature.string, feature.startPos, feature.endPos, tStart, 'BEGUN_BY')
                    tlk2 = (feature.type, feature.string, feature.startPos, feature.endPos, tEnd, 'ENDED_BY')
                    tlinks.append(tlk1)
                    tlinks.append(tlk2)
                else:
                    tlk1 = (feature.type, feature.string, feature.startPos, feature.endPos, tStart, 'SIMULTANEOUS')
                    tlinks.append(tlk1)
                continue
    
            else:   ##: NORMAL 
                timexes = tlink.getTimexes()
                tStart = timexes[0].getDateTime()                    
                tlk1 = (feature.type, feature.string, feature.startPos, feature.endPos, tStart, 'SIMULTANEOUS')
                tlinks.append(tlk1)
            
        return tlinks
    
    def getFeatureArray(self):
        self.featureList.sort(key = lambda f:f.getStartPos())
        
        features = []
        id = 0
        for feature in self.featureList:
            tlink = feature.getTlink()
            
            if not tlink:
                tStart = None
                tEnd = None
                feat = (feature.type, feature.string, feature.sentNum, tStart, tEnd, feature.startPos, feature.endPos, feature.confidence, None, id, '', 0, feature.cleanString) # None holds MedDRA terms, last field is comment
                features.append(feat)
                id += 1
                continue
                
            timexes = [t for t in tlink.getTimexes() if t.getDateTime()]
            if not timexes:                
                tStart = None
                tEnd = None
                feat = (feature.type, feature.string, feature.sentNum, tStart, tEnd, feature.startPos, feature.endPos, feature.confidence, None, id, '', 0, feature.cleanString) # None holds MedDRA terms, last field is comment
                features.append(feat)
                id += 1
                continue
                
            tkType = tlink.getType()
            if tkType=='MULTIPLE':
                for t in tlink.getTimexes():
                    dt = t.getDateTime()
                    feat = (feature.type, feature.string, feature.sentNum, dt, dt, feature.startPos, feature.endPos, feature.confidence, None, id, '', 0, feature.cleanString) # None holds MedDRA terms, last field is comment
                    features.append(feat)                
                    id += 1
                continue
            
            if tkType=='MULTI_DURATIONS':
                timexes2 = tlink.getTimexes2()
                for i, t in enumerate(timexes):
                    dt = t.getDateTime()
                    dt2 = timexes2[i].getDateTime()
                    feat = (feature.type, feature.string, feature.sentNum, dt, dt2, feature.startPos, feature.endPos, feature.confidence, None, id, '', 0, feature.cleanString) # None holds MedDRA terms, last field is comment
                    features.append(feat)                
                    id += 1
                continue      
                            
            if tkType=='BETWEEN':
                tStart = timexes[0].getDateTime()
                if len(timexes)>1:
                    tEnd = timexes[1].getDateTime()
                else:
                    tEnd = timexes[0].getDateTime()
            elif tkType=='OR':
                timexes = tlink.getTimexes()
                tStart = timexes[0].getDateTime()
                tEnd = tStart
            else:   ##: NORMAL 
                timexes = tlink.getTimexes()
                tStart = timexes[0].getDateTime()
                tEnd = tStart
                    
            feat = (feature.type, feature.string, feature.sentNum, tStart, tEnd, feature.startPos, feature.endPos, feature.confidence, None, id, '', 0, feature.cleanString) # None holds MedDRA terms, last field is comment
            features.append(feat)              
            id += 1
            
        return features
    
    def getMedicalFeatures(self):
        features = []
        for feature in self.featureList:
            
            feat = (feature.type, feature.string, feature.sentNum)
            features.append(feat)
        
        return features
        
        
    def getFeatureTLinks(self):
        tlinks = []
        for feature in self.featureList:            
            tlinks.append(feature.tlink)
        
        return tlinks
    
    def getTimexesDB(self):
        timexes = []
        for t in self.timexList:
            s = t.getString()
            istart = t.getStartPos()
            dt = t.getDateTime()
            if dt:
                sdate = dt.isoformat().split('T')[0]
            else:
                sdate = ''
            confid = t.getConfidence() 
            timexes.append((s, sdate, istart, confid))
        return timexes
    
    def getTimexes(self):
        return [timex.getTimexString() for timex in self.timexList]
        
        
class FastTagger:
    """Implements a tagger with lexicons"""
    def __init__(self, lexicon):
        self.pairs = []
        self.hashdict = {}
        db = re.compile("\.|\]")
        for lexis, tag in lexicon:
            if (db.search(lexis)):
                self.pairs.append((re.compile(lexis), tag))
            else:
                self.hashdict[lexis[:-1]] = tag

    def tag(self, words):
        word_tag = []
        for word in words:
            found_tag = 'no tag'
            if word in self.hashdict:
                found_tag = self.hashdict[word]
            else:
                for regexp, tag in self.pairs:
                    if regexp.match(word):
                        found_tag = tag
                        break
            word_tag.append((word, found_tag))
        return word_tag

def normalize_date_string(time_string):
    if time_string == '':
        return ''
    
    try:
        dt = parse(time_string)
    except:
        return ''
        
    return dt.isoformat().split('T')[0]

def report_reader(reports_string):
        #create line iterator for the reports string
        reader = StringIO.StringIO(reports_string)

        fieldnames = ['Report ID','Age','Date of Exposure','Date of Onset','Vaccines','Vaccine Names','MedDRA','Gender','Free Text', 'Lab Text']
        for line in reader:
            #drop initial '"' and trailing '"\n'. split on '" ,  "'
            fields = line[1:-2].split('", "', 9)
            
            if len(fields)==9:
                fields.append('')
            report = dict(zip(fieldnames, fields))
            yield report
    
class FeatureExtractor:
    """ Main class provides functions to extract medical features and 
        associate features with time. """
        
    def __init__(self, config=None, lexicon=None):
        
        if not config:
            config, lexicon = self.initialization()
            
        self.signal_rules_raw = read_syntactic_rules("./signal.syntactic.rules.txt")          
        self.signal_rules = self._populate_rules(self.signal_rules_raw)
        #self.signal_hints = self.readSignalHints("./signals.tab")        
        signal_string = '^('+'|'.join(self.signal_rules.keys())+')$'
        self.re_signal = re.compile(signal_string, re.I)
        self.cp_temporal = nltk.RegexpParser(r"""
            Backward: {<TimexSignal><.*>?<Timex><Punctuation>} # e.g., '...after 3 days.' 
                      {<Timex><TimexSignal><Punctuation>} # e.g., '...3 days after.'
                      {<Timex><.*>?<Punctuation>} # e.g., '...the same day.' or '... second day.'
            Forward:  {<Timex><TimexSignal>} # e.g., '...3 days after receiving VAX,...'
                     {<TimexSignal><.*>?<Timex>} # e.g., '...after 3 days of VAX,...'
            SingleTimex:   {<Timex>} # e.g., '...same day of VAX,...'
            """)
        self.clause_signals = ['after', 'before', 'prior', 'post', 'following']    
        
        self.config = config
        self.lexicon = lexicon          
        self.regexp_tagger = FastTagger(self.lexicon)
        self.cp = nltk.RegexpParser(self.config['grammar'])
        self.cp1 = nltk.RegexpParser(self.config['grammar1'])
        self.labels = self.config['features']
        self.labels_gram1 = self.config['features_grammar1']
        self.st_filter = set(self.labels) - set(self.labels_gram1)
        
        
        # regexp for trailing characters
        self.re_strip = re.compile(" +[,&%s%s ]*$" % ('and', 'or'))
        
        # regexp multiple commas
        self.re_commas = re.compile(",[,&%s%s ]*," % ('and', 'or'))
        
        # remove space before commas
        self.re_spacebeforecommas = re.compile(" ,")

        # regexp for removing digits
        self.re_noorphandigits = re.compile(",* +\d+ *,")
        self.re_nodigits = re.compile("^ *\d+ *,$| +\d+")
        
        #regexp for removing all these symbols and replacing it with whitespace to convert post-vac to post vac
        self.symbs = re.compile("[\:/-]")
        #regexp for replacing colon and semicolon with comma and whitespace to convert post-vac to post vac
        self.semis = re.compile("[,;]")
        #regexp for replacing all non printable and non ascii characters with whitespace
        self.nonprint = re.compile("[%s]" % ''.join(chr(ind) for ind in range(0, 10) + range(11,32) + range(127, 256)))
        
        self.token_timeline_breakers = ['considered', 'classified', 'documented', 'plan', 'released', 'administered', 'coded', 'commented', 'comment', 'company']
        
        self.re_weekday = re.compile('(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun)$', re.I)
    
        self.feature_exclusive_tags = ['DX', 'Assessment', 'Impression', 'rule_out_abbrev', 'Rule', 'Out', 'History', 'MedicalHistory',
                                       'FamilyModifier', 'FamilyHistory', 'Family', 'DeathIndicator', 'Cause']
    
    def initialization(self):    
        try:
            with open('config.py', 'r') as f:
                config = ast.literal_eval(f.read())
            
        except Exception as e:
            print str(e)

        try:
            with open('lexicon.txt', 'r') as f:
                lexicon = ast.literal_eval(f.read())
            
            with open('lexicon2nd.txt', 'r') as f:
                lexicon2 = ast.literal_eval(f.read())    

            with open('lexicon3rd.txt', 'r') as f:
                lexicon3 = ast.literal_eval(f.read())    
                
        except Exception as e:
            print str(e)
        lexicon = lexicon3 + lexicon + lexicon2 
        
        return (config, lexicon)
    
    def getSignalRelation(self,word):        
 
        word = word.lower()
        if word in self.signal_rules:
            return self.signal_rules[word][0]
        else: 
            return None    

    def _populate_rules(self,rules):
        """Rules of type 2 (timex-signal-event) can be simply put in a
        hash keyed on the signals."""
        rule2_index = {}
        for rule in rules:
            relation = rule.get_attribute('relation')[0]  # vals are now lists
            ##: Time signals of IS_INCLUDED should not be used in relative time evaluation. They may cause confusion.
            ##: E.g., ... after 3 days in hospital.... "3 days in" is picked instead of "after 3 days"  
            if relation=='IS_INCLUDED':
                continue
            
            signal = rule.get_attribute('signal')[0]
            confidence = float(rule.get_attribute('confidence')[0])
            rule2_index[signal] = (relation, confidence)
        return rule2_index
    
    
    def get_untagged(self, text):
        punctuations = ['."',"```","`","+","*","^","%","@","<",">","'","-",'!', '?', ';', ':', '"', '/', ')','(','.','?','?','?','|','_','~','#','[',']','{','}','$','?']
        all = self.regexp_tagger.tag([w.lower() for w in text if w not in punctuations])

        return [(word,tag) for word,tag in all if not tag == 'unimportant']
    
    def get_tags(self, text):
        return self.regexp_tagger.tag([w.lower() for w in text if w.lower()])

    def massage_features(self, subtree):
        line = ' '.join(nltk.tag.untag(subtree.leaves()))
        if not subtree.label() in ['TIME_TO_ONSET', 'LOT', 'SYMPTOM','VACCINE']:
            line = re.sub(self.re_noorphandigits, ' ,', line)
            line = re.sub(self.re_nodigits, '', line)
        line = re.sub(self.re_commas, ',', line)
        line = re.sub(self.re_strip, '', line)
        line = re.sub(self.re_spacebeforecommas, ',', line)
        
        return line

    def massage_feature_tags(self, subtree):
        line = ' '.join([t for (w, t) in subtree.leaves()])
        #logging.debug(line)
        if subtree.label() != 'TIME_TO_ONSET' and subtree.label() != 'LOT':
            line = re.sub(self.re_noorphandigits, ' ,', line)
            line = re.sub(self.re_nodigits, '', line)
        line = re.sub(self.re_commas, ',', line)
        line = re.sub(self.re_strip, '', line)
        line = re.sub(self.re_spacebeforecommas, ',', line)
        
        return line
    
    def clean_text(self, freetext):
        #here we replace the first string with the second throughout the document
        freetext = freetext.replace("hx.", "hx")
        freetext = freetext.replace("dx.", "dx")
        freetext = freetext.replace("h/o", "hx")
        freetext = freetext.replace("r/o", "ro")
        freetext = freetext.replace("w/o", "wo")
        freetext = freetext.replace("w/i", "wi")
        freetext = freetext.replace("b/p", "")
        freetext = freetext.replace("R/O", "ro")
        freetext = freetext.replace("W/O", "wo")
        freetext = freetext.replace("W/I", "wi")
        freetext = freetext.replace("B/P", "")

        #here we delete the apostrophe in order to convert r/o to ro or shouldnt to shouldnt
        freetext = freetext.replace("'", '')
        
        freetext = freetext.replace(";", ', ') # added by Wei Wang, agreed by Taxiarchis
        
        #here we delete all these symbols and replace it with whitespace to convert post-vac to post vac
        freetext = self.symbs.sub(' ', freetext)
        #here we delete semi-colon and comma and replace it with comma and whitespace
        #to convert post-vac to post vac
        freetext = self.semis.sub(', ', freetext)   
        #replace all non printable and non ascii characters with whitespace
        freetext = self.nonprint.sub(' ', freetext)
        
        return freetext

    def extract_features_temporal(self, text,  expDateStr = None, onsetDateStr = None, refExpDateStr = None, textType='vaers'):
        """Main function to extract feature and temporal information. 
        Arguments:
            text -- text to extract information from
            expDateStr -- exposure date in string format, may be None
            onsetDateStr -- onset date in string format, may be None
            refExpDateStr -- serves as a referene if the exposure date is not given
            reportType = 'vaers' or 'faers'"""
        
        featurelist = []
        
        sentences = util.sentence_tokenize(text)
        taggedSentences = []        
#         id = 0
        for sentnumber, sentence0 in enumerate(sentences):
            
            sentence = self.clean_text(sentence0)
                        
            # tokenize each sentence to have a list of words to be processed
            tokens = nltk.word_tokenize(sentence)
            #run the above procedure
            sentence_to_parse = self.get_untagged(tokens)
            
            # Save tagged sentences for later computing of expose date
            taggedSentences.append(sentence_to_parse)
                
            #only if the cleaned sentence is NOT empty we parse it
            if sentence_to_parse!=[]:
                tree = self.cp.parse(sentence_to_parse)
                tree1 = self.cp1.parse(sentence_to_parse)
                 
#                 new_sentence_to_parse = ','.join([' '.join(nltk.tag.untag(subtree.leaves())) + ' ' for subtree in tree.subtrees() if subtree.node in self.st_filter])
                new_sentence_to_parse = ','.join([' '.join(nltk.tag.untag(subtree.leaves())) + ' ' for subtree in tree.subtrees() if subtree.label() in self.st_filter])

                #here we delete the dash and replace it with whitespace to convert post-vac to post vac
                new_sentence_to_parse = new_sentence_to_parse.replace(', ,', ',')
                #here we delete the dash and replace it with whitespace to convert post-vac to post vac
                new_sentence_to_parse = new_sentence_to_parse.replace(',', ', ')

                new_sentence_to_parse = nltk.word_tokenize(new_sentence_to_parse)

                #run the above procedure
                new_sentence_to_parse = self.get_untagged(new_sentence_to_parse)
                
                if new_sentence_to_parse!=[]:
                    tree2 = self.cp.parse(new_sentence_to_parse)
                    for subtree in tree2.subtrees():
                        if subtree.label() in self.st_filter:                            
                            featString = self.massage_features(subtree)
                            featurelist.append((subtree.label(), featString, sentnumber, subtree.leaves()))
                            
                for subtree in tree1.subtrees():
                    if subtree.label() in self.labels_gram1:
                        featString = self.massage_features(subtree)
                        featurelist.append((subtree.label(), featString, sentnumber, subtree.leaves()))

        self.initialization_text_data(text, sentences, taggedSentences, textType)
        
        featObjList = self.initialize_feature_obj_list(featurelist)
        
        docFeature = self.extract_temporal_info(featObjList, expDateStr, onsetDateStr, refExpDateStr)
        
        return docFeature
    
    def initialization_text_data(self, text, sentences, taggedSentences, rptType='vaers'):
        """Initialize some gobal information for the text what will be used later."""
        
        self.text = text
        self.sentences = sentences
        self.reportType = rptType
        
        n = len(sentences)
        locsSentStarts = [-1] * n
        curpt = 0
        for i in range(n):
            pos = text[curpt:].find(sentences[i])
            locsSentStarts[i] = pos + curpt
            curpt = locsSentStarts[i] + len(sentences[i])
        self.sentence_startPos = locsSentStarts
        
        self.taggedSentences = taggedSentences
        self.exposureDate = None
        self.blockout_range = []
        self.clauseZones = []
        
        sent_tags = []
        ##: 'IGNORE' tag breaks the timeline continuity, i.e., stops time impact zone; 
        ##: 'SKIP' black out this sentence from time impact zone, and impact zone resumes after this sentence.
        for sentnumber, sentence in enumerate(sentences):
            tags = set([tg[1] for tg in taggedSentences[sentnumber]])
            
            tokens0 = nltk.word_tokenize(sentence.lower())            
            with_who_range = self.extract_standard_summary_pattern(tokens0, sentence)
            if with_who_range:
                r = (with_who_range[0]+self.sentence_startPos[sentnumber], with_who_range[1]+self.sentence_startPos[sentnumber])
                self.blockout_range.append(r)
                
                
            ##: Ignore dates in this sentence since it is about history or family
            if tags.intersection(['History', 'FamilyHistory', 'MedicalHistory']):
                #sent_tags.append('IGNORE')
                sent_tags.append('SKIP')
                continue
            
            ##: tags that breaks time continuity
            if tags.intersection(['Hospitalization']):
                sent_tags.append('IGNORE')
                continue
            
            tokens = set(tokens0)
            ##: Ignore dates in this sentence if it has a 'follow-up'
            if 'follow-up' in tokens or sentence.lower().find('follow up')>=0 or sentence.lower().find('f/u')>=0:
                sent_tags.append('IGNORE')
                continue
            
            ##: Unspecified/unknown date breaks time continuity, except this is a sentence for concomitant, which usually should not stop continuity.
            if tokens.intersection(['unknown', 'unspecified', 'unreported']) and tokens.intersection(['date', 'dates']):
            #if tokens.intersection(['unknown', 'unspecified']) and tokens.intersection(['date', 'dates']) and not tokens.intersection(['concomitant']):
                #unkSet=tokens.intersection(['unknown', 'unspecified', 'unreported'])
                sent_tags.append('IGNORE')
                continue
            
            ##: tokens that breaks time continuity
            if tokens.intersection(self.token_timeline_breakers):
                sent_tags.append('IGNORE')
                continue
            
            sent_tags.append('NORMAL')
        self.sentence_tags = sent_tags
    

    def extract_standard_summary_pattern(self, tokens, sentence):
        """ Identify the standard summary pattern: 
            A xx years old male/female with medical history of Medical History and family history 
            of Family History who presents with Primary Diagnosis/Second Level Diagnosis after Onset 
            Time after exposure to Vaccine and was treated with medications of Drugs.
            
            The pattern often appears in the beginning of the report, thus can be taken advantage of. 
        """
        if not set(tokens).intersection(['male', 'female']) or len(set(tokens).intersection(['with', 'who']))<2:
            return
        
        if 'old' in tokens:
            idx = tokens.index('old')
            if idx>=2 and util.isfloat(tokens[idx-2]):
                age = float(tokens[idx-2])
        
        pos_who = tokens.index('who')
        poses_with =[i for i,w in enumerate(tokens) if i<pos_who and w=='with']
        if poses_with:
            pos_with = poses_with[-1]
        else:
            return
        
        loc_who = sentence.find('who ')
        loc_with = sentence[:loc_who].rfind('with ')
        return (loc_with, loc_who)    
            

    def initialize_feature_obj_list(self, featurelist):
        """ Convert feature tuples to feature object list:
            1. clean up ill-shaped feature
            2. create feature with Feature Type, String, SentNum, StartPos and EndPos 
        """
        
        ###: clean feature text. e.g., ", pain ear", added by Wei Wang
        for i, feat in enumerate(featurelist):
            if feat[1][0]==',':
                newf = (feat[0], feat[1][2:], feat[2], feat[3])
                #newf = (feat[0], feat[1].strip(' ?-/,'), feat[2], feat[3])
                featurelist.pop(i)
                featurelist.insert(i, newf)
        
        sentences = self.sentences
        featObjList = []
        for feature in featurelist:
            if feature[0]=='LOT': continue
            
            sentNum = feature[2]
            sentence = sentences[sentNum]
            sent_start = self.sentence_startPos[sentNum] #self.text.find(sentence)          
            
            ##: remove the duplicated substring of the same feature strings, and save the location in 'sub_start'
            duplicates = [feat for feat in featObjList if feat.getSentNum()==sentNum and feat.getString()==feature[1]]
            sub_start = 0
            if duplicates:
                sub_start = duplicates[-1].getEndPos() - sent_start
                sentence = sentence[sub_start:]
            
            dictTags = dict(feature[3])
            words = nltk.word_tokenize(feature[1])
            feat_tags = [(w, dictTags[w]) for w in words if dictTags[w] not in self.feature_exclusive_tags]
            featText = ' '.join([ft[0] for ft in feat_tags])
            featText = featText.replace(' ,', ',')
                            
            (start_char_feat, end_char_feat) = util.find_sub_text_range(sentence, featText)
            start_char_feat += sent_start + sub_start
            end_char_feat += sent_start + sub_start
            
            featObjList.append(Feature((feature[0], featText, feature[2], feat_tags, start_char_feat, end_char_feat)))            
                    
        return featObjList
        
    def parse_time_string(self, time_string):        
        if time_string == '':
            return None
     
        try:
            dt = parse(time_string)
        except:
            return None
        
        return dt
    
    def create_timex_impact_zone(self, timexList):
        """Create impact zones for timex list"""
        
        timexList = [t for t in timexList if t.getDateTime() and t.getRole()!='IGNORE']
        timeZones=[]
        for timex in timexList:
            dtime = timex.getDateTime()
            if dtime and timex.getRole()!='IGNORE': 
                timeZone = self.get_timex_impact_zone(timex, timexList)
                if timeZone:
                    timeZones.append(timeZone)
    
        timeZones.sort(key = lambda t:t[0])
        
        ##: Take out skiped sentences (e.g., history sentence) from timexe impact zones. 
        ##: Skiped sentence is different from ignored sentence for not stop timeline continuity.
        for i, sent in enumerate(self.sentences): 
            if self.sentence_tags[i]!='SKIP': continue
            sent_pos = self.sentence_startPos[i]
            for j, r in enumerate(timeZones):
                if r[0]<sent_pos and r[1]>sent_pos:
                    nr = (r[0], sent_pos, r[2])
                    timeZones[j] = nr
                    if r[1] > sent_pos+len(sent):
                        nr2 = (sent_pos+len(sent), r[1], r[2])
                        timeZones.insert(j, nr2)
        
        timeZones.sort(key = lambda t:t[0])
        
        return timeZones
        
    def update_time_references_with_relative_timex(self, timex, timeReferences, timexList, featurelist):
        """ Update the time impact zone for the input relative timex after it obtains datetime
            Find features associated with this timex and add them into time reference if not yet.
        """

        if not timex.getDateTime() or timex.getRole()=='IGNORE':
            return timeReferences
        
        sentnum = timex.getSentNum()
        features = [feat for feat in featurelist if feat.getSentNum()==sentnum]
        coordFeatTypes = set(['VACCINE', 'DRUG']) 
        for feature in features:
            
            if not feature.getType() in coordFeatTypes:
                continue            
            if feature.inClause(): continue
                        
            if feature.getType()=='VACCINE':
                refType = 'Vaccine'
                confidence = 0.8
            else:
                refType = 'Drug'
                confidence = 0.7
            refs = [ref for ref in timeReferences if ref[0]==refType and ref[4]==feature.getStartPos()]
            
            if refs: ##: this feature has already been inserted
                continue
                     
            tlink = feature.getTlink()
            if tlink and timex in tlink.getTimexes():
                timeReferences[(refType, feature.getString(), 0, sentnum, feature.getStartPos(), feature.getEndPos(), confidence)] = timex.getDateTime()
                        #sentInCoord[sentnumber] = True
                        
        exposureSet = ['Vaccination', 'Injection']
        refs = [ref for ref in timeReferences if ref[0] in exposureSet and ref[3]==sentnum]
        if refs: ##: already in time references
            return timeReferences
            
        tags = set([tg[1] for tg in self.taggedSentences[sentnum]])
       
        intersect = tags.intersection(exposureSet)
        if intersect:
            tgs = [tg for tg in self.sentence_full_tags[sentnum] if tg[1] in exposureSet]
            if tgs:
                tgpos = self.sentence_startPos[sentnum] + tgs[0][2]
                if not self.is_in_clause(tgpos, sentnum):
                    timeReferences[(tgs[0][1], timex.getString(), None, sentnum, timex.getStartPos(), timex.getEndPos(), 0.85)] = timex.getDateTime()
            
        return timeReferences
    
    def update_timex_impact_zone_with_timex(self, timex, timeZones, timexList):
        """Update the time impact zone for the input timex."""
        
        if not timeZones:
            return self.create_timex_impact_zone([timex])
        
        ##: timex falls into one of existing zones
        tPos = timex.getStartPos()
        for i, r in enumerate(timeZones):
            if r[0]<tPos and r[1]>tPos:
                timeZones[i] = (r[0], tPos, r[2])
                timeZones.insert(i+1, (timex.getEndPos(), r[1], timex.getDateTime(), timex))
                return timeZones
        
        ##: timex create a new impact zone
        newZone = self.get_timex_impact_zone(timex, timexList)
        timeZones.append(newZone)
        ##: Take out skiped sentences (e.g., history sentence) from timexe impact zones. 
        ##: Skiped sentence is different from ignored sentence for not stop timeline continuity.
        for i, sent in enumerate(self.sentences): 
            if self.sentence_tags[i]!='SKIP': continue
            sent_pos = self.sentence_startPos[i]
            for j, r in enumerate(timeZones):
                if r[0]<sent_pos and r[1]>sent_pos:
                    nr = (r[0], sent_pos, r[2], r[3])
                    timeZones[j] = nr
                    if r[1] > sent_pos+len(sent):
                        nr2 = (sent_pos+len(sent), r[1], r[2], r[3])
                        timeZones.insert(j, nr2)
                        
        timeZones.sort(key = lambda t:t[0])
        return timeZones
    
    def create_sentence_full_tags(self, docFeatList, timexList):
        sentence_full_tags = []
        for sentNum, sentence in enumerate(self.sentences):
            timexStrings = [(t.getString(), t.getStartPos()) for t in timexList if t.getSentNum()==sentNum]
            
            tags = self.retag_full_sentence(timexStrings, sentence,  self.taggedSentences[sentNum])
            sentence_full_tags.append(tags)
                
        return sentence_full_tags     
    
    def estimate_onset_date(self, featureList):
        if self.onsetDate:
            return (self.onsetDate, 1)
        
        onsetDates = []
        for feature in featureList:
            if feature.getType() in ["SYMPTOM", "DIAGNOSIS", "SECOND_LEVEL_DIAGNOSIS", "RULE_OUT"]:
                dt = feature.getDateTime()
                if dt:
                    onsetDates.append(dt)
        if onsetDates:
            onsetDate = min(onsetDates)
            if self.exposureDate and onsetDate < self.exposureDate: 
                onsetDate = self.exposureDate
                return (onsetDate, 0.7)
            else:
                return (onsetDate, 0.9)
        else:
            return (None, 0)
        
    def estimate_exposure_date(self, timeReferences, timexList):
        if self.exposureDate:
            self.exposureDateConfidence = 1
            return (self.exposureDate, 1)
                
        exposureSet = ['Vaccination', 'Injection']
        refs = [ref for ref in self.timeReferences if ref[0] in exposureSet and ref[6]>0.6]        
        if refs:
            maxConf = max([ref[6] for ref in refs])
            refs = [ref for ref in refs if ref[6]==maxConf]
            refs.sort(key=lambda r:r[4])
            return (self.timeReferences[refs[0]], ref[6]) 
        
        if self.reportType == 'vaers':
            exposureSet = set(['Vaccine']) 
        else: # =='faers'
            exposureSet = set(['Drug', 'Vaccine']) 
        exposureSet = set(['Drug', 'Vaccine']) 
        refs = [ref for ref in self.timeReferences if ref[0] in exposureSet and ref[6]>0.6]    
        if refs:
            refs.sort(key=lambda r:r[4])
            return (self.timeReferences[refs[0]], refs[0][6]) 
        
        ###: When no valid exposure date is available, use the first mentioned date
        for timex in timexList:
            if timex.getType() == 'DATE' and timex.getDateTime() and timex.getRole()=='NORMAL':
                return (timex.getDateTime(), 0.5)
        
        return (None, 0)
    
    def update_time_references_with_impact_zones(self, docFeatList, timexList):      
        """Update time references after some features obtain their time from time impact zones
            The time refernce from time impact zone are less reliable. Set confidence = 0.6.
        """
        
        if not self.timexImpactZones:
            return self.timeReferences
        
        impactZoneStart = self.timexImpactZones[0][0]
        features = [feat for feat in docFeatList if feat.getStartPos() > impactZoneStart 
                    and self.sentence_tags[feat.getSentNum()]=='NORMAL' and not feat.inClause() 
                    and feat.getType() in ['VACCINE', 'DRUG']]   
        for feature in features:
            sentnumber = feature.getSentNum()
            if not feature.getTlink() or not feature.getTlink().getDateTime():
                if 'concomitant' in [tg[0] for tg in self.sentence_full_tags[sentnumber]]:
                    continue
                feature = self.assign_feature_time_with_impact_zones(feature, self.timexImpactZones)
                tlink = feature.getTlink()
                if tlink:
                    if feature.getType()=='VACCINE':
                        refType = 'Vaccine'
                        confidence = 0.6
                    else:
                        refType = 'Drug'
                        confidence = 0.6
                    
                    self.timeReferences[(refType, feature.getString(), 0, sentnumber, 
                                         feature.getStartPos(), feature.getEndPos(), confidence)] = tlink.getDateTime()
        
        ##: Too many false alarms. Disable this part for now.
        ##: E.g, in 3603565(4th). .... Before treatment, .... 
#         exposureSet = ['Vaccination', 'Injection']
#         for sentnum, sentence in enumerate(self.sentences):
#             timexes = [t for t in timexList if t.getDateTime() and t.getSentNum()==sentnum]
#             if timexes: ##: has been processed for time references
#                 continue
#             
#             tags = set([tg[1] for tg in self.taggedSentences[sentnum]])
#             intersect = tags.intersection(exposureSet)
#             if intersect:
#                 tgs = [tg for tg in self.taggedSentences[sentnum] if tg[1] in exposureSet]
#                 word = tgs[0][0]
#                 sentStartPos = self.sentence_startPos[sentnum]
#                 dtimes = [r[2] for r in self.timexImpactZones if sentStartPos >=r[0] and sentStartPos<=r[1]]
#                 if dtimes:
#                     self.timeReferences[(tgs[0][1], word, None, sentnum, sentStartPos, sentStartPos, 0.6)] = dtimes[0]
#         
        return self.timeReferences
    
    def create_time_references(self, docFeatList, timexList): 
        """Create time references based on timex list"""                    
        timeReferences = {}  
        
        confidence = 1 
        ##: confidence = 1: input exposure and onset date; 
        ##:            = 0.9: with tags of interest;
        ##:            = 0.8: obtained from extracted vaccines
        ##:            = 0.7: obtained from extracted drugs
        ##:            = 0.6: date of drug or vaccine is obtained from time impact zone
        if self.exposureDate: ##: input exposure date is available
            self.exposureDateConfidence = 1 
            timeReferences[('Vaccination', None, None, 0, None, None, confidence)] = self.exposureDate
            timeReferences[('Injection', None, None, 0, None, None, confidence)] = self.exposureDate
        if self.onsetDate:  ##: input onset date is available
            self.onsetDateConfidence = 1
            timeReferences[('Onset', None, None, 0, None, None, confidence)] = self.exposureDate
            
        if self.receiveDate:
            timeReferences[('Administration', None, None, None, None, None, 1)] = self.receiveDate
            
        coordFeatTypes = set(['VACCINE', 'DRUG']) 
        ##: add tags in features into coordinates
        for feature in docFeatList:
            
            if not feature.getType() in coordFeatTypes:
                continue
            
            if feature.inClause(): continue
            
            sentnumber = feature.getSentNum()
            
            if feature.getType()=='VACCINE':
                coordType = 'Vaccine'
                confidence = 0.8
            else: # DRUG
                coordType = 'Drug'
                confidence = 0.7
                
            tlink = feature.getTlink()
            if tlink:
                ##: Handle features with does number
                counts = []
                if 'DoseIndicator' in [tg[1] for tg in self.sentence_full_tags[sentnumber]]:
                    counts = [tg[0] for tg in self.sentence_full_tags[sentnumber] if tg[1]=='Count']
                    
                timexes = [t for t in tlink.getTimexes() if t.getDateTime() and t.getRole()!='IGNORE']
                
                if self.get_drug_dose_number(feature) and len(counts) == len(timexes):
                    for i, t in enumerate(timexes):
                        val = util.text2num.convertOrdinal(counts[i])
                        timeReferences[(coordType, feature.getString(), val, sentnumber, feature.getStartPos(), t.getStartPos(), confidence)] = t.getDateTime()
                else:
                    for t in timexes:
                        timeReferences[(coordType, feature.getString(), 0, sentnumber, feature.getStartPos(), t.getStartPos(), confidence)] = t.getDateTime()                         
                        
        exposureSet = ['Vaccination', 'Injection']
        anchorSet = ['Hospitalization', 'Administration']
        for sentnum, sentence in enumerate(self.sentences):
            tags = set([tg[1] for tg in self.taggedSentences[sentnum]])
            timexes = [t for t in timexList if t.getDateTime() and t.getSentNum()==sentnum and t.getRole()!='IGNORE']
            if timexes:
                sent_start = self.sentence_startPos[sentnum]
                intersect = tags.intersection(anchorSet)
                for st in intersect:
                    words = [tg[0] for tg in self.taggedSentences[sentnum] if tg[1]==st]
                    wordPos = [sentence.lower().find(word) for word in words]
                    validWords = [pos for pos in wordPos if not self.is_in_clause(pos+sent_start, sentnum)]
                    if not validWords:
                        continue                    
                    coord = (st, '', None, sentnum, None, None, 0.9)
                    if not coord in timeReferences:
                        timeReferences[coord] = timexes[0].getDateTime()
                                
                ref =[]
                if tags.intersection(exposureSet):
                    tgs = [tg for tg in self.taggedSentences[sentnum] if tg[1] in exposureSet]
                    ref = tgs[0]
                    
                if tags.intersection(['Treatment']):
                    tokens = set([tg[0].lower() for tg in self.sentence_full_tags[sentnum]])
                    intst = tokens.intersection(['started', 'starts', 'begins', 'began'])
                    if intst:
                        ref = (list(intst)[0], 'Injection')    
                
                if ref:
                    word = ref[0].lower()
                    wpos = sentence.lower().find(word) + sent_start
                    if self.is_in_clause(wpos, sentnum):
                        continue
                    leftTimexes = [t for t in timexes if t.getStartPos() <= wpos]
                    rightTimexes = [t for t in timexes if t.getStartPos() >= wpos]
                    if not leftTimexes:
                        dt = rightTimexes[0].getDateTime()
                    elif not rightTimexes:
                        dt = leftTimexes[-1].getDateTime()
                    else:
                        leftSeg = self.text[leftTimexes[-1].getEndPos():wpos]
                        rightSeg = self.text[wpos+len(word):rightTimexes[0].getStartPos()]
                
                        if self.is_next_separated(leftSeg, rightSeg):
                            dt = leftTimexes[-1].getDateTime()
                        else:
                            dt = rightTimexes[0].getDateTime()                   
                    timeReferences[(ref[1], word, None, sentnum, wpos, wpos+len(word), 0.9)] = dt
            
        return timeReferences
    
    def get_timex_impact_zone(self, timex, timexList):
        """Get the impact zone for a given timex"""
        
        index = timexList.index(timex)
        dtime = timex.getDateTime()
        
        nextTimex = None
        for t in timexList[index+1:]:
            if t.getDateTime():
                nextTimex = t
                break
            
        if nextTimex:
            nextSentNum = nextTimex.getSentNum()
            nextTimexPos =  nextTimex.getStartPos()
        else: ##: timex is at the end of the list
            nextSentNum = len(self.sentences)-1
            nextTimexPos = len(self.text)
            
        #nextTimex = timexList[index+1]
        k = timex.getSentNum()+1
        endPos = -1
        while k <= nextSentNum:
            ##: Ignored sentence breaks time continuity
            if self.sentence_tags[k]=='IGNORE':
                endPos = self.sentence_startPos[k] - 1
                break
                    
#             ##: Unspecified/unknown date breaks time continuity, except this is a sentence for concomitant, which usually should not stop continuity.  
#             tokens = set([tag[0].lower() for tag in self.sentence_full_tags[k]])
#             if tokens.intersection(['unknown', 'unspecified']) and tokens.intersection(['date', 'dates']) and not tokens.intersection(['concomitant']):
#                 #endPos = self.sentences[k].find(' date')
#                 endPos = self.sentence_startPos[k] - 1
#                 break
            
            k += 1
            
        if endPos < 0:
            endPos = nextTimexPos - 1
                    
        return (timex.getStartPos(), endPos, dtime, timex)
    
        
         
    def get_initial_exposure_date(self, timexList, expDateInput, onsetDateInput, strRefExpDate):
         
        ###: Use the input exposure date if available
        if expDateInput:
            expDate = expDateInput
            return (expDate, None)
        else:
            expDate = None
        
        ###: To estimate the exposure date if not provided
        cleanTimexList = []
        if self.reportType == 'vaers':
            exposureTagSet = set(['Vaccine', 'Vaccination', 'Injection']) 
        else: # =='faers'
            exposureTagSet = set(['Drug', 'Injection']) 
         
        if not expDate:
            expDates = []
            for sentnumber, sentence in enumerate(self.sentences):                
                if self.sentence_tags[sentnumber]=='IGNORE':
                    continue
                     
                tags = set([tg[1] for tg in self.taggedSentences[sentnumber]])
                 
                timexes = [t for t in timexList if t.getSentNum()==sentnumber]
                cleanTimexList += timexes
                if tags.intersection(exposureTagSet):
                    dates = [t.getDateTime() for t in timexes if t.getType()=='DATE' and t.getDateTime() and t.getRole()=='NORMAL']
                    if dates and dates[0]:
                        expDates.append((dates[0], sentnumber))
             
            cleanDates = [t.getDateTime() for t in cleanTimexList if t.getDateTime()]
            if cleanDates:
                earliest = min(cleanDates)
            else:
                earliest = None
 
            backup = []
            days_reporting_range = 0
            expDate = None
            for dtime, sentnum in expDates:
                if sentnum < days_reporting_range and earliest and dtime > earliest:
                    backup.append(dtime)
                    continue
 
                if not expDate: # assign the first mentioned date
                    expDate = dtime
                    break
                 
            if not expDate and backup:
                expDate = min(backup)
                 
        ###: When no valid exposure date is available, use some guess as reference 
        if not expDate:
            ###: find the first mentioned date
            ###: find the earliest date in text, not used anymore
            inDates = []
            inDate = None
            loc1 = 1000000
            for timex in timexList:
                if timex.getType() == 'DATE' and timex.getDateTime() and timex.getRole()=='NORMAL':
                    #inDates.append(timex.getDateTime())
                    if timex.getStartPos() < loc1:
                        inDate = timex.getDateTime()
                        loc1 = timex.getStartPos()
            if inDate:
                inDates.append(inDate)
                 
            # If onset date is provided, take onset date in consideratoin as reference exposure date
            onsetDate = onsetDateInput
            if onsetDate:
                inDates.append(onsetDate)
             
            if inDates:
                refExpDate = min(inDates)
            else:
                refExpDate = None
             
            # Use reference date as exposure date when out of options. The reference date is from the previous report in this date set.
            if not refExpDate and strRefExpDate:
                refDate = self.parse_time_string(strRefExpDate)
                if refDate:
                    refExpDate = refDate       
                     
        else:
            refExpDate = None
         
        return (expDate, refExpDate)
#             
    def _calculate_exposure_onset_dates(self, timexList, docFeatList, sentences, taggedSentences, expDateInput, onsetDateInput, refExpDate, reportType ='vaers'):
        expDatesEst = []        
        if reportType == 'vaers':
            exposureTagSet = set(['Vaccine', 'Vaccination', 'Injection']) 
        else: # =='faers'
            exposureTagSet = set(['Drug', 'Injection']) 
        for sentnumber, sentence in enumerate(sentences):
            tags = set([tg[1] for tg in taggedSentences[sentnumber]])
              
            ##: Ignore dates in this sentence since it is about history or family
            if tags.intersection(['History', 'FamilyHistory', 'MedicalHistory']):
                continue
                  
            ##: Ignore dates in this sentence if it has a 'follow-up'
            if 'follow-up' in nltk.word_tokenize(sentence.lower()):
                continue
                      
            timexes = [t for t in timexList if t.getSentNum()==sentnumber]
            if tags.intersection(exposureTagSet):                    
                timexes = [t for t in timexList if t.getSentNum()==sentnumber]
                dates = [t.getDateTime() for t in timexes if t.getDateTime()]
                if dates and dates[0]:
                    expDatesEst.append(dates[0])
#                     
        #expDatesEst = []
        for feature in docFeatList:
            if feature.type in ["VACCINE","DRUG"]:
                dt = feature.getDateTime()
                if dt:
                    expDatesEst.append(dt)
                     
        onsetDatesEst = []
        for feature in docFeatList:
            if feature.type in ["DIAGNOSIS","SECOND_LEVEL_DIAGNOSIS", "SYMPTOM"]:
                #onsets = [t.getDateTime() for t in timexList if t.getSentNum()==feature.sentNum and t.getDateTime()]
                dt = feature.getDateTime()
                if dt:
                    onsetDatesEst.append(dt)
         
        # Case 1: Both exposure and onset dates are input
        if expDateInput and onsetDateInput:
            return (expDateInput, onsetDateInput, 'Input')
         
        # Case 2: Only exposure date is provided 
        if expDateInput and onsetDatesEst:
            onsetDates =  [dt for dt in onsetDatesEst if dt >= expDateInput]
            if onsetDates:
                onsetDate = min(onsetDates)
                return (expDateInput, onsetDate, 'Extracted')
             
        # Case 3: Both exposure and onset dates can be extracted
        if expDatesEst and onsetDatesEst:
            expDate = min(expDatesEst)
            onsetDates = [dt for dt in onsetDatesEst if dt>=expDate]
            if onsetDates:
                onsetDate = min(onsetDates)
                return (expDate, onsetDate, 'Extracted')
         
        # Case 4: Only onset dates is provided
        if expDatesEst and onsetDateInput:
            expDates =  [dt for dt in expDatesEst if dt <= onsetDateInput]
            if expDates:
                expDate = min(expDates)
                return (expDate, onsetDateInput, 'Extracted')
            else:
                return (onsetDateInput, onsetDateInput, 'Extracted')
         
        # Case 5: 
        if expDateInput:
            expDate = expDateInput
        elif expDatesEst:
            expDate = min(expDatesEst)
        else:
            expDate = refExpDate
          
        if expDate:
            onsetDatesEst = [dt for dt in onsetDatesEst if dt>=expDate]
             
        if onsetDateInput:
            onsetDate = onsetDateInput
        elif onsetDatesEst:
            onsetDate = min(onsetDatesEst)
        else:
            onsetDate = None
         
        if expDate and onsetDate and expDate > onsetDate:
            if expDateInput:
                onsetDate = expDateInput
            else:
                expDate = onsetDate
         
        return (expDate, onsetDate, 'Extracted')
     
    def preprocess_timex_list(self, timexList, featurelist):
        """preprocessing on timex list. Cleaning up list by set undesired timex role as 'ignore', 
        such as in a sentence containing 'follow-up', and remove scales like '6/12' for measuring
        "visual acuity" or 'pain'"""
                        
        for sentNum, sentence in enumerate(self.sentences):
            
            sentence = sentence.lower()
            tokens = set(nltk.word_tokenize(sentence))
            intersect_info = tokens.intersection(['report', 'case', 'information', 'summary', 'records', 'info', 'evaluation', 'mr', 'f/u']) 
            if intersect_info and tokens.intersection(['received', 'obtained']):
                sent_has_received_info = True
                self.sentence_tags[sentNum] = 'IGNORE'
            else:
                sent_has_received_info = False                
            
            timexes = [t for t in timexList if t.getSentNum()==sentNum and t.getType()=='DATE'] 
            if timexes:
                        
                if 'follow-up' in tokens or sentence.find('follow up')>=0 or sentence.find('f/u')>=0:        
                    init_pos = sentence.find('follow') + 5   ##: add 10 to pass the ':' in the case of "follow up:xxxx..."                 
                    match_pos = [m.start() for m in re.finditer(',|;|:|who|that|concerning|regarding', sentence[init_pos:])]
                    if match_pos:
                        end_pos = match_pos[0]
                    else:
                        end_pos = len(sentence)
                                        
                    ts = [t for t in timexes if t.getStartPos() < end_pos+self.sentence_startPos[sentNum]]
                    
                    if len(ts) > 1 and ts[0].getStartPos()!=ts[1].getStartPos():
                        ##: e.g., follow-up is received on 1/2/2014 and 2/3/2014
                        if self.text[ts[0].getStartPos():ts[1].getStartPos()].split()[0]=='and': 
                            ts[1].setRole('IGNORE')
                        
                    if ts:
                        ts[0].setRole('IGNORE')

                if sent_has_received_info:
                    ##: If there is no features in this sentence, the dates in this senntence are most likely the date of receiving report
                    poses = [sentence.find(w) + 2 for w in intersect_info] ##: add 2 to pass the ':' in the case of "case:"  
                    init_pos = min(poses)
                    sent_start = self.sentence_startPos[sentNum]
                    match_pos = [m.start() for m in re.finditer(',|;|:|who|that|concerning|regarding', sentence[init_pos:])]
                    if match_pos:
                        end_pos = match_pos[0] + sent_start + init_pos
                    else:
                        end_pos = len(sentence) + sent_start
                    tms = [t for t in timexes if t.getStartPos()<end_pos]
                    if tms:
                        tms[0].setRole('IGNORE')
                        if not self.receiveDate:
                            self.receiveDate = tms[0].getDateTime()
                            
                        if len(tms) > 1:
                            ##: e.g., follow-up is received on 1/2/2014 and 2/3/2014
                            mid = self.text[tms[0].getStartPos():tms[1].getStartPos()].split()
                            if mid and mid[0]=='and': 
                                tms[1].setRole('IGNORE')
                    
                    ##: Ignore dates following "received/obtained on", e.g., "report was recieved on 2/3/2014"
                    ##: This is for FAERS only. For VAERS, it is very likely to have something like "VAX was received on 2/3/2014"
                    if self.reportType=='faers':
                        for t in timexes:
                            ll = len('received on')+2
                            tPos = t.getStartPos()-sent_start
                            if tPos > ll:
                                pre2words = sentence[tPos-ll:tPos].split()
                                if len(pre2words)>=2 and pre2words[-1]=='on' and pre2words[-2] in ['received', 'obtained']:
                                    t.setRole('IGNORE')
                                
                itset = tokens.intersection(['acuity', 'pain', 'ache', 'tsp', 'inch', 'strength', 'intensity', 'scale', 'score', 'scores', 'erection'])
                if itset:
                    itemLocs = [i for i, tg in enumerate(self.sentence_full_tags[sentNum]) if tg[0].lower() in itset]
                    words = [tg[0].lower() for tg in self.sentence_full_tags[sentNum]]
                    for t in timexes:
                        if t.getString().lower() in words:
                            tpos = words.index(t.getString().lower())
                        else:
                            continue
                        hasDeleted = False
                        for loc in itemLocs:
                            if abs(tpos-loc)<6 and re.findall("^[0-3]?[0-9]/[0-3]?[0-9]$", t.getString()): # visual acuity of 6/12
                                timexList.remove(t)
                                hasDeleted = True
                                break
                        if hasDeleted:
                            continue                                
                
                tgs = set([tg[1] for tg in self.taggedSentences[sentNum]])      
                if tgs.intersection(['Expiration', 'DOB', 'Death']):    
                    if 'Death' in tgs: ##: Special handling because 'expired' is tagged as 'Death' in the lexicon
                        tgsfull = [tg[1] for tg in self.sentence_full_tags[sentNum]]
                        if 'Death' in tgsfull:
                            deathLoc = tgsfull.index('Death')
                        else:
                            continue
                        if self.sentence_full_tags[sentNum][deathLoc][0]=='expired':
                            drugDist = [abs(i-deathLoc) for (i, tg) in enumerate(tgsfull) if tg=='Vaccine' or tg=='Drug']
                            if not drugDist or min(drugDist)>3:
                                continue
                    
                    match_pos = [m.start() for m in re.finditer('exp|DOB', sentence)]
                    if match_pos:
                        for pos in match_pos:
                            expPos = self.sentence_startPos[sentNum] + pos
                            tms = [t for t in timexes if t.getStartPos()>expPos and t.getStartPos()-expPos<25] ##: exp{iration date is reported in }June 2001
                            for t in tms:
                                t.setRole('IGNORE')
                        
        return timexList
    

    def extract_temporal_info(self, featurelist, strExpDate, strOnsetDate, strReceiveDate):
        """Main function to extract temporal information. 
        Arguments:
            featurelist -- list of extracted features
            strExpDate -- exposure date in string format
            strOnsetDate -- onset date in string format
            strReceiveDate -- date when the report is received in string format
            """
            
        expDateInput = self.parse_time_string(strExpDate)
        onsetDateInput = self.parse_time_string(strOnsetDate)  
        receiveDate = self.parse_time_string(strReceiveDate)  
        
        self.exposureDate = expDateInput
        self.onsetDate = onsetDateInput
        self.receiveDate = receiveDate
        self.exposureDateConfidence = 0
        self.onsetDateConfidence = 0
        
        ##: Obtain timex list
        timexList = timexan.annotateTimexes(self.text, expDateInput)        
        
        self.sentence_full_tags = self.create_sentence_full_tags(featurelist, timexList)
        
        timexList = self.preprocess_timex_list(timexList, featurelist)
                      
        ###: divide features that contain multiple timexes
        featurelist = self.divide_feature_containing_multiple_timexes(featurelist, timexList)
        
        featurelist = self.create_feature_timex_association(featurelist, timexList)
        
        timexList = self.construct_timeline(timexList, featurelist)
        
#         (expDate, onsetDate, state) = self.calculate_exposure_onset_dates(
#                                 timexList, featurelist, sentences, taggedSentences, expDateInput, onsetDateInput, expDate)
        
        featurelist = self.process_feature_durations(featurelist)
        
        featurelist = self.postprocess_features(featurelist)
        
        if self.exposureDateConfidence==1:
            if self.onsetDateConfidence==1:
                datesConfidence = 1
            else:
                datesConfidence = 0.9
        else:
            datesConfidence = 0.8
            
        ##: Create DocumentFeature object for return
        docFeature = DocumentFeature(featurelist, timexList, self.exposureDate, self.onsetDate, self.receiveDate, datesConfidence, expDateInput, onsetDateInput)     
            
        return docFeature
    
    def postprocess_features(self, featurelist):
        """Clean out features for special scenarios. """
        
        ##: To overwrite the time of features that are in a clause
        for feature in featurelist:
            if feature.inClause() or self.is_in_clause(feature.getStartPos(), feature.getSentNum()):
                feature = self.assign_feature_time_with_references(feature, self.timeReferences, feature.getStartPos(), True)
                        
        ##: To set time of features after death to none. Currently disabled.
#         deathDates = []
#         for feature in featurelist:
#             if 'Death' in [tg[1] for tg in feature.getTags()]:
#                 dt = feature.getDateTime()
#                 if dt and feature.getTlink().getTimexes()[0].getType()!='VIRTUAL': ##: only original date counts
#                     deathDates.append(dt)
#             
#             if feature.getType()=='CAUSE_OF_DEATH':
#                 feature.setTlink(None)
#             
#         if deathDates:
#             deathDate = min(deathDates)
#             for feature in featurelist:                
#                 dt = feature.getDateTime()
#                 if dt and dt>deathDate:
#                     feature.setTlink(None)
        
        ##: Remove time from features in the blockout range, 
        ##: e.g., A 34 years old male with{ history of leg pain }who on ....
        for feature in featurelist:
            posStart = feature.getStartPos()
            posEnd = feature.getEndPos()
            for r in self.blockout_range:
                if (posStart>r[0] and posStart<r[1]) or (posEnd>r[0] and posEnd<r[1]):
                    timex = feature.getTimex()
                    if timex:
                        tpos = timex.getStartPos()
                        if tpos>=r[0] and tpos<=r[1]:
                            continue
                    
                    feature.setTlink(None)
            
        return featurelist
    
    def get_drug_dose_number(self, feature):
        """Extract drug dose number."""
        
        if not feature.getType() in ['DRUG', 'VACCINE']:
            return None
        
        sentNum = feature.getSentNum()
        fulltags = self.sentence_full_tags[sentNum]
        tags = [tg[1] for tg in fulltags]
        if not 'DoseIndicator' in tags:
            return None
        
        sentStartPos = self.sentence_startPos[sentNum]
        featStartPos = feature.getStartPos()
        posFeat = 0
        for i, tg in enumerate(fulltags):
            if tg[2]+sentStartPos > featStartPos:
                break
            posFeat = i
        
        width = 5 # range within for searching dose number 
        il = max(0, posFeat-width)
        ir = min(len(tags), posFeat + width)
        tgs = tags[il : ir]
        if 'Count' in tgs and 'DoseIndicator' in tgs:
            posCount = il + tgs.index('Count')
            return util.text2num.convertOrdinal(fulltags[posCount][0])
        
        return None
                                
    def assign_feature_time_with_references(self, feature, timeReferences, searchEnd = -1, earlierDateOnly = False):    
        """Assign feature time with the time reference. This is called when feature has not been assigned a time earlier."""    
        
        if searchEnd < 0:
            searchEnd = len(self.text)
            
        ftime = None
        tags = [tg for tg in feature.getTags() if tg[1] in ['Drug', 'Vaccine']]
        
        doseNum = self.get_drug_dose_number(feature)
        if doseNum:
            refs = [(ref[5], self.timeReferences[ref]) for tg in tags for ref in self.timeReferences 
                    if ref[0]==tg[1] and tg[0] in ref[1] and ref[2]==doseNum and ref[6]>0.6 and ref[5] < searchEnd]        
        else:
            refs = [(ref[5], self.timeReferences[ref]) for tg in tags for ref in self.timeReferences 
                    if ref[0]==tg[1] and tg[0] in ref[1] and ref[6]>0.6 and ref[5] < searchEnd]     
        
        if refs:
            refs.sort(key=lambda x:x[0])
            ftime = refs[0][1]
            
        featType = feature.getType()    
        if not ftime:
            ##: For VAERS report, drug is used only after a symptom appears, so assign onset to it instead of exposure
            if featType in ['SYMPTOM', "DIAGNOSIS","SECOND_LEVEL_DIAGNOSIS", "RULE_OUT", 'DRUG'] and self.onsetDateConfidence==1 and self.reportType=='vaers':
                ftime = self.onsetDate
            elif self.exposureDate and self.exposureDateConfidence==1 and self.reportType=='vaers':
                ftime = self.exposureDate
            
        if ftime:
            if not (earlierDateOnly and feature.getDateTime() and ftime>feature.getDateTime()):  
                feature.setDateTime(ftime)
                
        return feature
    
    def assign_feature_time_with_impact_zones(self, feature, impactZones):
        """Assign feature time using time impact zone. This is called when feature has not been assigned a time earlier."""    

        if not impactZones:
            return feature
        
        ##: find the timex impact zone that contains the feature
        dtimes = [r[2] for r in impactZones if feature.getStartPos()>=r[0] and feature.getStartPos()<=r[1]]
        if dtimes:
            feature.setDateTime(dtimes[0])
            
        return feature
    
    def evaluate_all_relative_timexes(self, timexList, docFeatList):
        """Evaluate all relative timexes. """
        
        for timex in timexList:
            ##: Only process relative timex
            if timex.getType()!='REL' or timex.getRole()=='IGNORE': continue
            
            ###: evaluate timexes in formats of weekday (e.g. "Monday"), day # (e.g., "day 3", "day three") 
            time_day_count = self.evaluate_timex_in_day_count(timex, timexList)
            if time_day_count:
                timex.setDateTime(time_day_count)
                self.timexImpactZones = self.update_timex_impact_zone_with_timex(timex, self.timexImpactZones, timexList)
                continue
            
            sentNum = timex.getSentNum()

            tags = []
            full_tags = self.sentence_full_tags[sentNum]
            posTimex = []
            for i, tg in enumerate(full_tags):
                ##: Label other timexes as 'unimportant' for this timex to avoid mistakes
                if tg[1]=='Timex' and tg[0]!=timex.getString():
                    tags.append((tg[0], 'unimportant'))
                else:
                    tags.append((tg[0], tg[1]))
                
                if tg[0]==timex.getString():
                    posTimex.append(i)
                    
            (search_direction, rel) = self.find_ref_time_direction(tags)
            
            if not search_direction:
                continue
            
            ##: add to clause zone after TimexSignal 
            if search_direction == 'Forward':
                tpos = posTimex[0]
                signal = [tg[0] for tg in tags[max(0,tpos-1):] if tg[1]=='TimexSignal']
                if signal and signal[0] in self.clause_signals:
                    sentence = self.sentences[sentNum]
                    clause_start =  full_tags[tpos][2] + len(full_tags[tpos][0])
                    clause_end = len(sentence)
                    endPos = sentence[clause_start:clause_end].find(',')
                    if endPos >= 0:
                        clause_end = endPos + clause_start
                    self.clauseZones.append((self.sentence_startPos[sentNum] + clause_start, 
                                             self.sentence_startPos[sentNum] + clause_end, sentNum))
            
            ref_time = self.find_relative_time_reference(search_direction, tags, timex, posTimex[0])
            if not ref_time: 
                continue
            
            newtime = timexan.getRelativeDatetime(timex.string, rel, ref_time)
            
            timex.setDateTime(newtime)
            
            self.timexImpactZones = self.update_timex_impact_zone_with_timex(timex, self.timexImpactZones, timexList)
        
        for timex in timexList:
            ##: Only process relative timex
            if timex.getType()!='REL' or timex.getRole()=='IGNORE' or not timex.getDateTime(): continue
            
            self.timeReferences = self.update_time_references_with_relative_timex(timex, self.timeReferences, timexList, docFeatList)
            
        return timexList
    
    def evaluate_timex_in_day_count(self, timex, timexList):
        """evaluate timexes such as "day 3", "day three", and "Monday" """
        
        timexString = timex.getString().lower()
        
        weekdayMatches = self.re_weekday.findall(timexString)
        lastw = timexString.split()[-1]
        digits = "one|two|three|four|five|six|seven|eight|nine"
        
        if not (lastw in digits or lastw.isdigit() or weekdayMatches):  
            return None
        
        ##: Find reference time in the same sentence of this timex        
#         anchorTags = ['Vaccination', 'Injection', 'Hospitalization']
        anchorTags = ['Vaccination', 'Hospitalization']
        sentNum = timex.getSentNum()
        tags = self.sentence_full_tags[sentNum]
        afterTimex = False
        dist_after = 0
        ref_time = None
        for tg in tags:
            if tg[1]=='Timex' and tg[0]==timex.getString():
                if ref_time:
                    break
                afterTimex = True
                
            if not afterTimex: ##: Before this timex appears
                if tg[1] in anchorTags:
                    ref_time = self.find_time_reference_with_tag(tg[1], tg[0], sentNum)
                elif tg[1]=='Timex':
                    ts = [t for t in timexList if t.getSentNum()==sentNum and t.getType()=='DATE' and t.getString()==tg[0]]
#                     ts = [t for t in timexList if t.getSentNum()==sentNum and t.getDateTime() and t.getString()==tg[0]]
                    if ts:
                        ref_time = ts[0].getDateTime()
            else: ##: After this timex appears
                if tg[0] in [',', ';'] or dist_after > 10:
                    break
                if tg[1] in anchorTags:
                    ref_time = self.find_time_reference_with_tag(tg[1], tg[0], sentNum)
                    break
                
        sentIndices = range(sentNum)
        sentIndices.reverse()
        for sentid in sentIndices:
            tags = self.sentence_full_tags[sentid]
            tids = range(len(tags))
            tids.reverse() 
            for tid in tids:
                tg = tags[tid]
                if tg[1] in anchorTags:
                    ref_time = self.find_time_reference_with_tag(tg[1], tg[0], sentNum)
                elif tg[1]=='Timex':
                    ts = [t for t in timexList if t.getSentNum()==sentid and t.getType()=='DATE' and t.getString()==tg[0]]
#                     ts = [t for t in timexList if t.getSentNum()==sentid and t.getDateTime() and t.getString()==tg[0]]
                    if ts:
                        ref_time = ts[0].getDateTime()
                if ref_time:
                    break
            if ref_time:
                break
        
        if not ref_time:
            if self.exposureDate:
                ref_time = self.exposureDate
            elif self.onsetDate:
                ref_time = self.onsetDate
        
        if not ref_time:
            return None
        
        newtime = None
        if weekdayMatches:
            sday = weekdayMatches[0]
            idx = ['mon','tue','wed','thu','fri','sat','sun'].index(sday[:3])
            day0 = ref_time.weekday()
            if idx >= day0:
                delta = idx-day0
            else:
                delta = idx - day0 + 7
            newtime = ref_time + timedelta(days=delta)
        else:
            if lastw.isdigit():
                count = int(lastw)
            else:
                count = util.text2num.convert(lastw)
                if not count:
                    return None
            count -= 1
            newtime = ref_time + timedelta(days=count)
        
        return newtime
                
    
    def construct_timeline(self, timexList, docFeatList):
        """A main function to construct time line"""
        if not docFeatList:
            return timexList     
       
            
        self.timeReferences = self.create_time_references(docFeatList, timexList)
        
        self.timexImpactZones = self.create_timex_impact_zone(timexList)
        
        timexList = self.evaluate_all_relative_timexes(timexList, docFeatList)
        
#         (expDate, expConf) = self.estimate_exposure_date(self.timeReferences, timexList)
        ##: expDate is obtained based on the first time. 
        ##: Update time reference and re-estimate exposure time
        
        
        ##: Update time references after some features obtain their time from time impact zones
        self.timeReferences = self.update_time_references_with_impact_zones(docFeatList, timexList)
        
        (expDate, expConf) = self.estimate_exposure_date(self.timeReferences, timexList)
        
        if expDate:
            self.exposureDate = expDate
            self.exposureDateConfidence = expConf 
            self.timeReferences[('Vaccination', None, None, None, None, None, expConf)] = self.exposureDate
            self.timeReferences[('Injection', None, None, None, None, None, expConf)] = self.exposureDate
            
        (onsetDate, onsetConf) = self.estimate_onset_date(docFeatList)
        if onsetDate:
            self.onsetDate = onsetDate
            self.onsetDateConfidence = onsetConf 
            
        ##: Final scan for all features without assigned date time        
        for feat in docFeatList:
            if self.sentence_tags[feat.getSentNum()]!='NORMAL': continue
            if not feat.getTlink() or not feat.getTlink().getDateTime():
                ##: feautures in clause should not be assigned a time. They should have been given a time somewhere else
                if feat.inClause():
                    feat = self.assign_feature_time_with_references(feat, self.timeReferences, feat.getStartPos())
                    ##: TLink could still be None if no reference is found. Then use the time from time impact zones
                    if feat.getTlink():
                        continue
                
                if feat.getType()=='DRUG' and 'concomitant' in [tg[0] for tg in self.sentence_full_tags[feat.getSentNum()]]:
                    feat = self.assign_time_to_concomitant_drug(feat, docFeatList)
                    if feat.getTlink():
                        continue
                
                if not self.timexImpactZones or feat.getStartPos() < self.timexImpactZones[0][0]: ##: feature locates before any time zones
                    ##: Assignment on features in the begining for VAERS
                    if self.reportType == 'vaers': 
                        feat = self.assign_feature_time_with_references(feat, self.timeReferences)                        
                    continue
        
                feat = self.assign_feature_time_with_impact_zones(feat, self.timexImpactZones)
            
        return timexList
        
    def assign_time_to_concomitant_drug(self, feature, featurelist):
        """Assigne time to concomitant drugs."""
        
        index = featurelist.index(feature)-1
        while index >= 0:
            if featurelist[index].getType() in ['DRUG', 'VACCINE'] and featurelist[index].getDateTime():
                feature.setDateTime(featurelist[index].getDateTime())
                return feature
            else:
                index = index - 1
        
        if self.exposureDate:
            feature.setDateTime(self.exposureDate)
            
        return feature
        

    def flag_features_in_associate_clause(self, docFeatList):
        """flag features in a clause of assiciate tlink.  
           E.g, On 03 July 2012, 10 days after Priorix, child reveloped rash on face,..."""
        for feat in docFeatList:
            tlink = feat.getTlink()
            if not tlink or tlink.getType()!='ASSOCIATE':
                continue
            
            sentNum = feat.getSentNum()
            sentence = self.sentences[sentNum]
            sent_start = self.sentence_startPos[sentNum]
            startClause = tlink.getTimexes()[1].getStartPos()
            endPos = sentence[startClause - sent_start:].find(',')
            if endPos < 0: #: No comma is found, skip to be safe
                continue
            else:
                endClause = startClause + endPos
            
            zone = (startClause, endClause, sentNum)
            if not zone in self.clauseZones:
                self.clauseZones.append(zone)
            
            if feat.getStartPos() > startClause and feat.getStartPos() < endClause:
                feat.setInClause(True)
                feat.setTlink(None)
                
        return docFeatList
        
    def process_feature_durations(self, docFeatList):
        """Handle durations such as "for 5 days" """
        
        for feat in docFeatList:
            tlink = feat.getTlink()
            if not tlink or tlink.getType()!='DURATION':
                continue
#             
            tdurs = [t for t in tlink.getTimexes() if t.getType()=='DUR']
            if not tdurs: continue
                
            timexes = [t for t in tlink.getTimexes() if t.getDateTime()]
            if not timexes: continue
                
            tdur = tdurs[0]
                
            if len(timexes)==1:
                dt = timexan.getRelativeDatetime(tdur.getString(), 'after', timexes[0].getDateTime())
                tdur.setDateTime(dt) 
                tlink.setType('BETWEEN')
                continue
            
            timexes2 = []
            for t in timexes:
                dt = timexan.getRelativeDatetime(tdur.getString(), 'after', t.getDateTime())
                timexes2.append(timexan.Timex3(0, 0, '', dt, tdur.getString()))
            tlink.setTimexes2(timexes2)
            tlink.setType('MULTI_DURATIONS')
        
        return docFeatList
    
        
    def find_time_reference_with_tag(self, tag, word, sentNum, doseNum=0):  
        """Find the time reference with give tag."""
        
        timeReferences = self.timeReferences
        if tag=='Drug' or tag=='Vaccine':
            refs = []
            refDoses = []
            for ref in timeReferences:
                if ref[0]==tag and word in ref[1] and ref[3]<=sentNum:
                    refs.append((ref[4], timeReferences[ref]))
                    if doseNum>0 and ref[2]==doseNum: 
                        refDoses.append((ref[4], timeReferences[ref]))  
                        
            ##: if there is matching does number, return it first 
            if refDoses:
                ##: return the closet time
                refDoses.sort(key=lambda x:x[0])
                return refDoses[-1][1]
            
            if refs:
                ##: return the closet time
                refs.sort(key=lambda x:x[0])
                return refs[-1][1]
            
        if tag in ['Vaccination', 'Injection', 'Hospitalization', 'Administration']:
            refs = []
            for ref in timeReferences:
                if ref[0]==tag: 
                    if ref[6]==1: ##: input Vaccination date 
                        return timeReferences[ref]
                    refs.append((ref[4], timeReferences[ref]))
            if refs:
                ##: return the closet time
                refs.sort(key=lambda x:x[0])
                return refs[-1][1]
            
            ##: if there is no explict 'Vaccination' or 'Injeciton' tag in the time reference,
            ##: then look for 'Drug' and 'Vaccine' instead
            if tag=='Vaccination':
                tagSet = ['Vaccine']
            elif tag=='Injection':
                tagSet = ['Vaccine', 'Drug']
            else:
                return None
                                
            refs = []
            for ref in timeReferences:
                if ref[0] in tagSet: 
                    refs.append((ref[4], timeReferences[ref]))
            if refs:
                ##: return the closet time
                refs.sort(key=lambda x:x[0])
                return refs[-1][1]
        
        return None
    
    def is_in_clause(self, loc, sentNum):
        zones = [r for r in self.clauseZones if r[2]==sentNum]
        for r in zones:
            if loc>=r[0] and loc<=r[1]:
                return True
            
        return False
    
    def find_relative_time_reference(self, search_direction, tags, timex, timesIndex):
        """Find the time reference for the input timex"""
                
        if search_direction == 'Backward':
            ts = [r[2] for r in self.timexImpactZones if r[0]<=timex.getStartPos() and r[1]>=timex.getEndPos()]
            if ts:
                return ts[-1]
            else:
                return None
        
        parts = tags[timesIndex+1:]
            
        anchorTagSet = set(['Vaccine', 'Drug', 'Vaccination', 'Injection', 'Hospitalization', 'Administration']) 
        doseNum = 0
        doseTag = [tg for tg in parts if tg[1]=='DoseIndicator']
        counts = []
        doseTagRange = 5
        if doseTag:
            counts = [(i, tg[0]) for i, tg in enumerate(parts) if tg[1]=='Count']        
        for i, tag in enumerate(parts):
            if tag[1]=='Drug' or tag[1]=='Vaccine':
                if counts:
                    dist = 10000
                    doseword = None
                    for k, w in counts:
                        if abs(k-i) < dist:
                            dist = abs(k-i)
                            doseword = w
                    if doseword and dist<doseTagRange:
                        doseNum = util.text2num.convertOrdinal(doseword)                
                
                t = self.find_time_reference_with_tag(tag[1], tag[0], timex.getSentNum(), doseNum)
                if t:
                    return t
                
            if tag[1] in ['Hospitalization', 'Administration']:
                t = self.find_time_reference_with_tag(tag[1], tag[0], timex.getSentNum())
                if t:
                    return t
                
            if tag[1] in ['Vaccination', 'Injection']:
                if i+2<len(parts) and parts[i+1][0] in ['with', 'of', 'to'] and parts[i+2][1] in ['Drug', 'Vaccine']:
                    continue
                t = self.find_time_reference_with_tag(tag[1], tag[0], timex.getSentNum())
                if t:
                    return t
                
        ##: No reference tag is found, search backward for a valid time range
        ##: In ideal case, this should "return None" directly. However, considering that the current lexicon is not 
        ##: complete enough, it's very likely some Vaccines or drugs are not tagged, we return the previous time
        ##: in the current development stage.
        ts = [r[2] for r in self.timexImpactZones if r[0]<=timex.getStartPos() and r[1]>=timex.getEndPos()]
        if ts:
            return ts[-1]
        
        return None
                
    def find_ref_time_direction(self, tags):
        """Find the direction and relationship of the time reference. 
           Return: 
            direction -- direction to serach for time reference (Forward, Backward or SingleTimex) 
            relationship -- After or Before (the time reference)
           
            Backward: {<TimexSignal><.*>?<Timex><Punctuation>} # e.g., '...after 3 days.' 
                      {<Timex><TimexSignal><Punctuation>} # e.g., '...3 days after.'
                      {<Timex><.*>?<Punctuation>} # e.g., '...the same day.' or '... second day.'
            Forward:  {<Timex><TimexSignal>} # e.g., '...3 days after receiving VAX,...'
                     {<TimexSignal><.*>?<Timex>} # e.g., '...after 3 days of VAX,...'
            SingleTimex:   {<Timex>} # e.g., '...same day of VAX,...'
            )
        """

        p = self.cp_temporal.parse(tags)
        for sub in p:
            if type(sub) is nltk.tree.Tree:
                direct = sub.label()   # 'Backward', 'Forward' or 'SingleTimex'
                if direct=='SingleTimex':           
                    child = sub.leaves()[0]         
                    if 'same' in child[0].lower() or 'time' in child[0].lower():
                        rel = 'IS_INCLUDED'
                        return ('Forward', rel)
                    if set(child[0].lower().split()).intersection(['following', 'next']):
                        return ('Backward', 'AFTER')
                else:
                    hasNoSignal = True
                    for child in sub.leaves():
                        if child[1]=='TimexSignal':
                            rel = self.getSignalRelation(child[0])
                            if child[0].lower() in ['later', 'ago', 'earlier']: ##: cases that are always backward
                                direct = 'Backward'
                            return (direct, rel)
                    ##: <Timex><.*>?<Punctuation>} # e.g., '...the same day.' or '... second day.'
                    if hasNoSignal:
                        return (direct, 'AFTER')
                    
        return (None, None)
    
    def retag_full_sentence(self, timexes, sentence, tagged):
        """Build tags for full sentence and return starting locations of all tokens. 
        The input 'tagged' contains no punctuations and 'unimportant' tags. The reason 
        not tagging the full sentence again is that tagging is rather costy since it 
        scans all wild pattern in the lexcon. 
        return (token, tag, position) 
        """
        
        timexStrings = [t[0] for t in timexes]
        
        tokens, indices = util.tokenize_with_reserved_strings(sentence, timexStrings)        

        tags = []
        ip = 0
        curchar = 0
        for i, w in enumerate(tokens):
            pos = sentence[curchar:].find(w)
            tPos = pos + curchar
            curchar = tPos + len(w)
            
            if w in timexStrings:
                tags.append((w, 'Timex', tPos))
            elif w in [',', '.', ';']:
                tags.append((w, 'Punctuation', tPos))
            elif self.re_signal.findall(w):
                tags.append((w, 'TimexSignal', tPos))
            else:
                t = [(i, tg) for i, tg in enumerate(tagged[ip:]) if tg[0]==w.lower()]
                if t:
                    tags.append((t[0][1][0],t[0][1][1], tPos))
                    ip = t[0][0]             
                else:
                    tags.append((w, 'unimportant', tPos))                         
        
        return tags

    def divide_feature_containing_multiple_timexes(self, featurelist, timexList):
        """Divide features that contain multiple timexes into mulitple shorter features."""
        
        if not timexList:
            return featurelist
        if not featurelist:
            return []

        #sentences = util.sentence_tokenize(text)
        text = self.text.lower()
        
        extraFeatureList = []
        for index, feature in enumerate(featurelist):
            start_char_feat = feature.getStartPos()
            end_char_feat = feature.getEndPos()
            #timexes = [t for t in timexList if t.getRole()!='IGNORE' and t.getType()=='DATE' and t.getStartPos()>=feature.getStartPos() and t.getStartPos()<=end_char_feat]
            timexes = [t for t in timexList if t.getRole()!='IGNORE' and (t.getType()=='DATE' or t.getType()=='REL')
                        and t.getStartPos()>=feature.getStartPos() and t.getStartPos()<=end_char_feat]
            
            if timexes:
                strFeat = feature.getString()
                words_feat = nltk.word_tokenize(strFeat)
                ptFeat = 0
                cur = start_char_feat
                lastPos = end_char_feat
                ##: add a fake timex so that the feature scan can go to the end 
                timexes.append(timexan.Timex3(lastPos, lastPos, None, None, ''))
                newFeatureStringList = []
                for t in timexes:
                    tpos = t.getStartPos() 
                    txt = self.clean_text(text[cur:tpos])
                    words_sent =  nltk.word_tokenize(txt)
                    newFeats = []
                    for w in words_sent:
                        if w in words_feat: # and not w in newFeats:
                            newFeats.append(w)
                            words_feat.remove(w)
                    newFeatStr = ' '.join(newFeats)
                            
                            
                    ##: although 'cur' is not necessarily the exact position of this feature segment, 
                    ##: it doesn't change its relative position with other features and timexes
                    newFeatStr = newFeatStr.strip(', ')
                    newFeatStr = newFeatStr.replace(' , ', ', ')
                    if newFeatStr.startswith('and '):
                        newFeatStr = newFeatStr[4:]
                    if newFeatStr!='':
                        newFeatureStringList.append(newFeatStr)
                        
                    cur = tpos + len(t.getString())
        
                if len(newFeatureStringList) > 1:
                    featObjList = []
                    for featStr in newFeatureStringList:
                        (start_new_feat, end_new_feat) = util.find_sub_text_range(text[start_char_feat:end_char_feat], featStr)
                        start_new_feat += start_char_feat
                        end_new_feat += start_char_feat
                        tks = re.split(', | ',featStr)
                        tks = nltk.word_tokenize(featStr)
                        tags = [(w, t) for (w,t) in feature.getTags() for tg in tks if w==tg]
                        featObjList.append(Feature((feature.getType(), featStr, feature.getSentNum(), tags, start_new_feat, end_new_feat)))
                    
                    featurelist[index] = featObjList[0]
                    for i in range(1, len(featObjList)):
                        extraFeatureList.append(featObjList[i])
        
        for f in extraFeatureList:
            featurelist.append(f)
        
        featurelist.sort(key= lambda f:f.getStartPos())
        
        return featurelist
    
    def get_feature_bundles(self, features, timexes):
        """Group features that are closely realted and thus to be assigned with the same time"""
        if len(features) < 2:
            return [features]
        
        bundles = []
        cur = [features[0]]
        nn = range(len(features)-1)
        for idx in nn:
            if features[idx+1].getType()==features[idx].getType():
                tms = [t for t in timexes if t.getStartPos()>features[idx].getStartPos() and t.getStartPos()<features[idx+1].getStartPos()]
                if not tms:
                    cur.append(features[idx+1])
                else:
                    bundles.append(cur)
                    cur = [features[idx+1]]
            else:
                bundles.append(cur)
                cur = [features[idx+1]]

        bundles.append(cur)
        
        return bundles
    
    def create_tlinks_from_timexes(self, timexes, sentence):
        """Create TLink based on given timexes."""
        
        if not timexes:
            return []
        
        if len(timexes)==1:
            return [TLink(timexes[0])]
        
        timexStrs = [t.getString() for t in timexes]
        sentence = sentence.lower()
        tokens, indices = util.tokenize_with_reserved_strings(sentence, timexStrs)
        numTK = len(tokens)
        
        tlinkList = []
        tlink = TLink(timexes[0])
        nn = range(1, len(timexes))
        for ind in nn:
            if indices[ind]-indices[ind-1]==2:
                midword = tokens[indices[ind]-1]
                #########################################################
                ###: Search for case: on xxx or xxx
                #########################################################
                if midword=='or':
                    tlink.addTimex(timexes[ind])
                    tlink.setType('OR')
                    timexes[ind].setRole('IGNORE')
                    continue
                        
                #########################################################
                ###: Search for case: from xxx to xxx, between xxx and xxx
                #########################################################
                isTimeRange = False
                if tokens[indices[ind]-1] in ['to', 'until', 'till']:
                    isTimeRange = True
                if not isTimeRange and indices[ind-1]>0 and midword=='and' and tokens[indices[ind-1]-1]=='between':
                    isTimeRange = True
                    
                if isTimeRange:
                    tlink.addTimex(timexes[ind])
                    tlink.setType('BETWEEN')
                    continue
            
            #########################################################
            ###: Search for case: 5/12-15/2014 or May/12-15/2014, where two timexes share the same string
            #########################################################
            if timexes[ind].getStartPos() == timexes[ind-1].getStartPos():
                tlink.addTimex(timexes[ind])
                tlink.setType('BETWEEN')
                continue
            
            #########################################################
            ###: Search for case: 5/12-15/2014 or May/12-15/2014, where two timexes share the same string
            #########################################################
            if timexes[ind].getType()=='DATE' and timexes[ind-1].getType()=='DATE' and tokens[indices[ind]-1]=='-':
                tlink.addTimex(timexes[ind])
                tlink.setType('BETWEEN')
                continue
            
            #########################################################
            ###: Search for case: 5/12/14, 5/13/14, and 5/16/14; or case: 5/12/14 and on 5/13/14
            #########################################################
            if  timexes[ind].getType()=='DATE' and timexes[ind-1].getType()==timexes[ind].getType() and (
                (indices[ind]-indices[ind-1]==2 and tokens[indices[ind]-1] in [',', 'and', '&']) 
                or (indices[ind]-indices[ind-1]==3 and tokens[indices[ind]-2]==',' and tokens[indices[ind]-1] in ['and' ,'&'])
                or (indices[ind]-indices[ind-1]==3 and tokens[indices[ind]-2]=='and' and tokens[indices[ind]-1]=='on') 
                or (indices[ind]-indices[ind-1]==3 and tokens[indices[ind]-2]==',' and tokens[indices[ind]-1]=='on')): 
                tlink.addTimex(timexes[ind])
                tlink.setType('MULTIPLE')
                continue
        
            #########################################################
            ###: Search for the case: ...5/12/2014, 3 days after vaccination, ...; ...5/12/2014, less than 3 days after vaccination, ...;  
            ##:                       or ...5/12/2014, after 3 days of vaccination, ...
            #########################################################
            if timexes[ind-1].getType()=='DATE' and timexes[ind].getType()=='REL':
                if (indices[ind]-indices[ind-1]==2 and tokens[indices[ind]-1] ==',') \
                    or (indices[ind]-indices[ind-1]==3 and tokens[indices[ind]-1] =='after' and tokens[indices[ind]-2] ==',') \
                    or (indices[ind]-indices[ind-1]<=4 and indices[ind]+1<numTK and tokens[indices[ind]+1] =='after' \
                        and tokens[indices[ind-1]+1] ==',') and tokens[indices[ind]-1] !='and':
                    tlink.addTimex(timexes[ind])
                    tlink.setType('ASSOCIATE')
                    timexes[ind].setRole('IGNORE')
                    continue
                        
            ##: Start a new TLink
            tlinkList.append(tlink)
            tlink = TLink(timexes[ind])
            
        tlinkList.append(tlink)
        
        return tlinkList

    def create_feature_timex_association(self, featurelist, timexList):
        """Create tlinks for features. Assign timexes to the corresponding feature."""
        
        if not timexList or not featurelist:
            return featurelist
                    
        text = self.text
        sentences = self.sentences
        
        for sentNum, sentence in enumerate(sentences):
            timexes = [t for t in timexList if t.getSentNum()==sentNum and t.getRole()!='IGNORE']
            features = [feat for feat in featurelist if feat.getSentNum()==sentNum]
            if not timexes or not features:
                continue
            
            timexes_valid = [t for t in timexes if t.getType() in ['DATE', 'REL']]
            tlinks = self.create_tlinks_from_timexes(timexes_valid, sentence)
            featureBundles = []
            nn = len(tlinks)
            if nn==1:
                for feat in features:
                    feat.setTlink(tlinks[0].copy())
            elif nn > 1:
                featureBundles = self.get_feature_bundles(features, timexes_valid)
                for i in range(nn-1):
                    leftTK = tlinks[i]
                    rightTK = tlinks[i+1]
                    fbs = [fb for fb in featureBundles if fb[0].getStartPos()>leftTK.getStartPos() 
                           and fb[-1].getStartPos()<rightTK.getStartPos()]
                    
                    for fb in fbs:
                        segPre = text[leftTK.getEndPos():fb[0].getStartPos()]
                        segNext = text[fb[-1].getEndPos():rightTK.getStartPos()]
                    
                        if leftTK and self.is_next_separated(segPre, segNext, leftTK.getTimexes()[-1], rightTK.getTimexes()[0]):
                            chosenTK = leftTK
                        else:
                            chosenTK = rightTK
                            
                        for feat in fb:
                            ##: set all tlink with copy to avoid the case that two paris share the same tlink.
                            ##: this would make an extra copy in the first one, but can reduce the complexity of the code
                            feat.setTlink(chosenTK.copy())
                            
                ##: assign the first tlink to features in the begining, and last tlink to those at the end
                feats = [feat for feat in features if not feat.getTlink()]
                if feats:
                    for ft in feats:
                        if ft.getStartPos() < tlinks[0].getStartPos():
                            ft.setTlink(tlinks[0].copy())
                        else:
                            ft.setTlink(tlinks[-1].copy())
                            
            ##: assign the duration timex to the feature in front of it, except feature type is BETWEEN already        
            timexes_dur = [t for t in timexes if t.getType()=='DUR']
            for t in timexes_dur:
                featsLeft = [ft for ft in features if ft.getEndPos() < t.getStartPos()]
                if featsLeft:
                    featleft = featsLeft[-1]
                else:
                    break
                
                if featleft.getTlink() and featleft.getTlink().getType()=='BETWEEN': 
                    continue
                
                featInBundle = False
                for fb in featureBundles:
                    if featleft in fb:
                        for ft in fb:
                            if ft.getTlink():
                                ft.getTlink().addTimex(t.copy())
                            else:
                                ft.setTlink(TLink(t))
                            ft.getTlink().setType('DURATION')
                        featInBundle = True
                        break
                    
                if not featInBundle:
                    if featleft.getTlink():
                        featleft.getTlink().addTimex(t)
                    else:
                        featleft.setTlink(TLink(t))
                    featleft.getTlink().setType('DURATION')
                    
        ##: Set flag to indicate if the feature is in a clause 
        featurelist = self.flag_features_in_associate_clause(featurelist)
        
        return featurelist    

    def is_next_separated(self, segPre, segNext, timexPre=None, timexNext=None):
        """Determine if the next segment containing signs of separation """
        ##: Search for seperator
        match = re.findall(';|and| & ', segNext, re.I)
        if match:
            return True
        
        match = re.findall(';|and', segPre, re.I)
        #match = re.findall(';|and| & ', segPre, re.I)
        if match:
            return False       
        
        rankPre = 0
        rankNext = 0
        ##: a date with all year, month and day has rank 3
        if timexPre:
            rankPre = timexPre.getDateCompleteness()
        if timexNext:
            rankNext = timexNext.getDateCompleteness()
        
        ##: Compare number of comma
        nCommasPre = len(re.findall(', ', segPre))
        nCommasNext = len(re.findall(', ', segNext))
        rankPre -= nCommasPre
        rankNext -= nCommasNext
        
        if rankPre > rankNext:
            return True
        elif rankPre < rankNext:
            return False
        
        ##: Compare location
        if len(segPre) <= len(segNext):
            return True
        else:
            return False
            
        return False
     
     
    def extract_annotation_temporal(self, text,  annotationStartPos, annotationEndPos, annotationType, 
                                    expDateStr = None, onsetDateStr = None, refExpDateStr = None, textType='vaers'):
        """Main function to extract feature and temporal information. 
        Arguments:
            text -- text to extract information from
            reportType = 'vaers' or 'faers'"""
        
        sentences = util.sentence_tokenize(text)
        
        n = len(sentences)
        locsSentStarts = [-1] * n
        curpt = 0
        for i in range(n):
            pos = text[curpt:].find(sentences[i])
            locsSentStarts[i] = pos + curpt
            curpt = locsSentStarts[i] + len(sentences[i])
        locsSentStarts.append(len(text))
        self.sentence_startPos = locsSentStarts
        
        AnnSent = None
        for sentnum, pos in enumerate(self.sentence_startPos):
            if annotationStartPos>=pos and annotationStartPos<=self.sentence_startPos[sentnum+1]-1:
                AnnSent = sentnum
                break
        
        featText = text[annotationStartPos:annotationEndPos]
        tags = self.regexp_tagger.tag(nltk.word_tokenize(featText))
        feat = Feature((annotationType, featText, AnnSent, tags, annotationStartPos, annotationEndPos))
            
        featurelist = [feat]

        taggedSentences = []        
        for sentnumber, sentence in enumerate(sentences):

            # tokenize each sentence to have a list of words to be processed
            tokens = nltk.word_tokenize(sentence)
            #run the above procedure
            sentence_to_parse = self.get_untagged(tokens)
            
            # Save tagged sentences for later computing of expose date
            taggedSentences.append(sentence_to_parse)
                

        self.initialization_text_data(text, sentences, taggedSentences, textType)
        
        expDateInput = self.parse_time_string(expDateStr)
        onsetDateInput = self.parse_time_string(onsetDateStr)  
        receiveDate = self.parse_time_string(refExpDateStr)  
        
        self.exposureDate = expDateInput
        self.onsetDate = onsetDateInput
        self.receiveDate = receiveDate
        self.exposureDateConfidence = 0
        self.onsetDateConfidence = 0
        
        ##: Obtain timex list
        timexList = timexan.annotateTimexes(self.text, expDateInput)        
        
        self.sentence_full_tags = self.create_sentence_full_tags(featurelist, timexList)
        
        timexList = self.preprocess_timex_list(timexList, featurelist)
                      
        ###: divide features that contain multiple timexes
        featurelist = self.divide_feature_containing_multiple_timexes(featurelist, timexList)
        
        featurelist = self.create_feature_timex_association(featurelist, timexList)
        
        timexList = self.construct_timeline(timexList, featurelist)
        
        featurelist = self.process_feature_durations(featurelist)
        
        featurelist = self.postprocess_features(featurelist)
        
        feature = featurelist[0]
        tlink = feature.getTlink()
        if not tlink:
            return ('', '')
        
        timexes = [t for t in tlink.getTimexes() if t.getDateTime()]
        if not timexes:
            return ('', '')
            
        if len(timexes)==1:
            tStart = timexes[0].getDateTime()
            tEnd = tStart
        else:
            tStart = timexes[0].getDateTime()
            tEnd = timexes[1].getDateTime()
            
        strTimeStart = tStart.isoformat().split('T')[0]
        strTimeEnd = tEnd.isoformat().split('T')[0]
            
        return (strTimeStart, strTimeEnd)
      

    def extract_features_only(self, text):
        """Function to extract features. Used for ETHERNLP. 
        Arguments:
            text -- text to extract information from
            expDateStr -- exposure date in string format, may be None
            onsetDateStr -- onset date in string format, may be None
            refExpDateStr -- serves as a referene if the exposure date is not given
            reportType = 'vaers' or 'faers'"""
        
        featurelist = []
        
        sentences = util.sentence_tokenize(text)
        taggedSentences = []        
        for sentnumber, sentence0 in enumerate(sentences):
            
            sentence = self.clean_text(sentence0)
                        
            # tokenize each sentence to have a list of words to be processed
            tokens = nltk.word_tokenize(sentence)
            #run the above procedure
            sentence_to_parse = self.get_untagged(tokens)
            
            # Save tagged sentences for later computing of expose date
            taggedSentences.append(sentence_to_parse)
                
            #only if the cleaned sentence is NOT empty we parse it
            if sentence_to_parse!=[]:
                tree = self.cp.parse(sentence_to_parse)
                tree1 = self.cp1.parse(sentence_to_parse)
                 
#                 new_sentence_to_parse = ','.join([' '.join(nltk.tag.untag(subtree.leaves())) + ' ' for subtree in tree.subtrees() if subtree.node in self.st_filter])
                new_sentence_to_parse = ','.join([' '.join(nltk.tag.untag(subtree.leaves())) + ' ' for subtree in tree.subtrees() if subtree.label() in self.st_filter])

                #here we delete the dash and replace it with whitespace to convert post-vac to post vac
                new_sentence_to_parse = new_sentence_to_parse.replace(', ,', ',')
                #here we delete the dash and replace it with whitespace to convert post-vac to post vac
                new_sentence_to_parse = new_sentence_to_parse.replace(',', ', ')

                new_sentence_to_parse = nltk.word_tokenize(new_sentence_to_parse)

                #run the above procedure
                new_sentence_to_parse = self.get_untagged(new_sentence_to_parse)
                
                if new_sentence_to_parse!=[]:
                    tree2 = self.cp.parse(new_sentence_to_parse)
                    for subtree in tree2.subtrees():
                        if subtree.label() in self.st_filter:                            
                            featString = self.massage_features(subtree)
                            featurelist.append((subtree.label(), featString, sentnumber, subtree.leaves()))
                            
                for subtree in tree1.subtrees():
                    if subtree.label() in self.labels_gram1:
                        featString = self.massage_features(subtree)
                        featurelist.append((subtree.label(), featString, sentnumber, subtree.leaves()))

        self.sentences = sentences
        
        n = len(sentences)
        locsSentStarts = [-1] * n
        curpt = 0
        for i in range(n):
            pos = text[curpt:].find(sentences[i])
            locsSentStarts[i] = pos + curpt
            curpt = locsSentStarts[i] + len(sentences[i])
        self.sentence_startPos = locsSentStarts
        
        featObjList = self.initialize_feature_obj_list(featurelist)
        
        featList = [(feat.getType(), feat.getStartPos(), feat.getEndPos(), feat.getString()) for feat in featObjList]
        return featList

    def extract_feature_time_associations(self, featurelist, timexList, text, strExpDate='', strOnsetDate='', strReceiveDate='', textType = 'vaers'):
        """Main function to extract temporal information. Used for ETHERNLP. 
        Arguments:
            featurelist -- list of extracted features
            strExpDate -- exposure date in string format
            strOnsetDate -- onset date in string format
            strReceiveDate -- date when the report is received in string format
            """
            
        sentences = util.sentence_tokenize(text)
        
        taggedSentences = []        
        for sentnumber, sentence0 in enumerate(sentences):
            sentence = self.clean_text(sentence0)
            # tokenize each sentence to have a list of words to be processed
            tokens = nltk.word_tokenize(sentence)
            #run the above procedure
            sentence_to_parse = self.get_untagged(tokens)
            
            # Save tagged sentences for later computing of expose date
            taggedSentences.append(sentence_to_parse)
            
        self.initialization_text_data(text, sentences, taggedSentences, textType)
        
        ##: reconstruct missing fields (sentNum and tags) for features
        sentNum = 0
        self.sentence_startPos.append(len(text)+1)
        for feat in featurelist:
            while not (feat.getStartPos() >= self.sentence_startPos[sentNum] 
                       and feat.getEndPos() < self.sentence_startPos[sentNum+1]):
                sentNum += 1
            feat.setSentNum(sentNum)
            
            words = nltk.word_tokenize(feat.getString())
            dictTags = dict(self.regexp_tagger.tag(words))
            
            feat_tags = [(w, dictTags[w]) for w in words]
            
            feat.setTags(feat_tags)
            
        sentNum = 0
        if timexList and timexList[0].getSentNum()<0:
            for timex in timexList:
                while not (timex.getStartPos() >= self.sentence_startPos[sentNum] 
                       and timex.getEndPos() < self.sentence_startPos[sentNum+1]):
                    sentNum += 1
                timex.setSentenceNum(sentNum)
        
        expDateInput = self.parse_time_string(strExpDate)
        onsetDateInput = self.parse_time_string(strOnsetDate)  
        receiveDate = self.parse_time_string(strReceiveDate)  
        
        self.exposureDate = expDateInput
        self.onsetDate = onsetDateInput
        self.receiveDate = receiveDate
        self.exposureDateConfidence = 0
        self.onsetDateConfidence = 0
        
        ##: Obtain timex list
        self.sentence_full_tags = self.create_sentence_full_tags(featurelist, timexList)
        
        timexList = self.preprocess_timex_list(timexList, featurelist)
                      
        ###: divide features that contain multiple timexes
        featurelist = self.create_feature_timex_association(featurelist, timexList)
        
        timexList = self.construct_timeline(timexList, featurelist)

        featurelist = self.process_feature_durations(featurelist)
        
        featurelist = self.postprocess_features(featurelist)
        
        if self.exposureDateConfidence==1:
            if self.onsetDateConfidence==1:
                datesConfidence = 1
            else:
                datesConfidence = 0.9
        else:
            datesConfidence = 0.8
            
        ##: Create DocumentFeature object for return
        docFeature = DocumentFeature(featurelist, timexList, self.exposureDate, self.onsetDate, self.receiveDate, datesConfidence, expDateInput, onsetDateInput)     
            
        return docFeature

if __name__ == '__main__':

    text = "Pain at vaccination site. Started 11/8/15. Shot was given 9/30/15. Off and on ache, pain since that date."
    
    textType='vaers'
    expDate = ''
    onsetDate = ''
    receiveDate = ''
#     expDate = '4/9/2004'
    onsetDate = '4/19/2004'
    
    try:
        with open('config.py', 'r') as f:
            config = ast.literal_eval(f.read())
            
        with open(config['localpath']+'reports.txt', 'r') as f:
            reports_string = f.read()
    except Exception as e:
        print str(e)

    try:
        with open('lexicon.txt', 'r') as f:
            lexicon = ast.literal_eval(f.read())
        with open('lexicon2nd.txt', 'r') as f:
            lexicon2 = ast.literal_eval(f.read())    
        with open('lexicon3rd.txt', 'r') as f:
            lexicon3 = ast.literal_eval(f.read())    
    except Exception as e:
#         QMessageBox.critical(None, "VaeTM", str(e))
        print str(e)
#     lexicon = lexicon + lexicon2
    lexicon = lexicon3 + lexicon + lexicon2  

    print text
    fe = FeatureExtractor(config, lexicon)
    
    textFeatures = fe.extract_features_temporal(text, expDate, onsetDate, receiveDate, textType=textType)
        
    if textFeatures:
        textFeatures.print_document_features()
    
    etherTlinks = textFeatures.getDocTlinks()
    
    if textFeatures:
        textFeatures.print_document_features()
    
    print 'Program finished!'
