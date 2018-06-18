#!/usr/bin python
# -*- coding: utf-8 -*-

"""Graphical User Interface for ETHER: Event-based Text-mining of Health Electronic Records

ETHER has single window GUI with multiple tabs for interacting with adverse event reports.  
The GUI is implemented in the class MainWindow in the file ether.py and is organized into five tabs.  
Each tab is an instance of the class ReviewTab and contains a widget that displays information about the current report.  

The ETHER software displays reports, basic metadata, and extracted features in four tabs: 
Summarized Cases, Case Narrative & Features, Case Features over Time, and MedDRA Terms. 
There are four major widget class:  
    ReportLimitedFeatures, ReportTextAndFeatures, and ReportTemporal.  
These correspond to the similarly named tabs in the user interface.  
Each class has a reference to the in-memory list of report data and when the user changes the current report a Qt Signal 
is sent to these widgets to update the report they are currently displaying.  
All tabs also have a header that displays structured information from the adverse event reports.  
This header is implemented in the Structured class.

"""
#
# Wei Wang, Engility, wei.wang@engility.com
#

import os, sys, uuid, getpass, logging, ast, time, datetime, nltk, re, StringIO, csv, traceback, os.path
import math, copy
from PySide.QtCore import *
from PySide.QtGui import *
from dbstore import *
import util, textan, timexan
# import labanalyzer, metamapTranslator, ETHERNLP
# from evaluation import EventEvaluation
from dateutil.parser import *
import gc, json
import subprocess, cProfile
import codecs
# from unidecode import unidecode
#from subprocess import *   
 
# import lxml.html
import Tkinter as tk
import tkFont
import matplotlib
import matplotlib.cm as cm
from matplotlib._png import read_png 
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.patches import FancyBboxPatch
from matplotlib.backends.qt_editor.formlayout import ColorButton

matplotlib.rcParams['backend.qt4']='PySide'
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_pdf import PdfPages

from threading import Thread

# from reportlab.platypus import Flowable
# from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_RIGHT, TA_CENTER
# from reportlab.lib.pagesizes import letter, landscape
# from reportlab.pdfgen import canvas
# from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image, PageBreak
# from reportlab.lib import colors
# from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
# from reportlab.lib.units import inch, mm
# from reportlab.lib import utils
 
dictFeatureNames = {"Symptom":"SYMPTOM", "Vaccine":"VACCINE", "Primary Diagnosis":"DIAGNOSIS", 
                "Second Level Diagnosis":"SECOND_LEVEL_DIAGNOSIS", "Cause of Death":"CAUSE_OF_DEATH", 
                "Drug":"DRUG", "Family History":"FAMILY_HISTORY", 
                "Medical History":"MEDICAL_HISTORY", "Rule out":"RULE_OUT"}
dictFeatureNamesInv = {"SYMPTOM":"Symptom", "VACCINE":"Vaccine", "DIAGNOSIS": "Primary Diagnosis", 
                "SECOND_LEVEL_DIAGNOSIS":"Second Level Diagnosis", "CAUSE_OF_DEATH":"Cause of Death", 
                "DRUG":"Drug", "FAMILY_HISTORY":"Family History", 'TIME_TO_ONSET':'Time to Onset',
                "MEDICAL_HISTORY":"Medical History", "RULE_OUT":"Rule out", "LOT":'Lot Number'}
dictFeatureAbr = {"SYMPTOM":"SYM", "VACCINE":"VAX", "DIAGNOSIS": "pDx", 
                "SECOND_LEVEL_DIAGNOSIS":"sDx", "CAUSE_OF_DEATH":"CoD", 
                "DRUG":'Tx', "FAMILY_HISTORY":"FHx", 'TIME_TO_ONSET':'',
                "MEDICAL_HISTORY":"MHx", "RULE_OUT":"R/O", "LOT":''}     
features2Translate = ["DIAGNOSIS", "CAUSE_OF_DEATH", "SECOND_LEVEL_DIAGNOSIS", "SYMPTOM"]        
        
def datetime_strftime(datetimeIn, resolution = 'day', resolution_only = False):
    if not datetimeIn:
        return ''
    
    resolution =  resolution.lower()
    
    if resolution=='m/d':
        return str(datetimeIn.month) + '/' + str(datetimeIn.day)
    
    if resolution_only:
        if resolution=='day' or resolution=='d':
            return str(datetimeIn.day)
        elif resolution=='month' or resolution=='m':
            return str(datetimeIn.month)
        elif resolution=='year' or resolution=='y':
            return str(datetimeIn.year)
        else:
            return ''
    
    if datetimeIn.year>=1900:
        if resolution=='day' or resolution=='d':
            strdate = datetimeIn.strftime("%m/%d/%y")
        elif resolution=='month' or resolution=='m':
            strdate = datetimeIn.strftime('%m/%y')
        elif resolution=='year' or resolution=='y':
            strdate = datetimeIn.strftime("%Y")
        elif resolution=='week' or resolution=='w':
            days = (datetimeIn - datetime.datetime(datetimeIn.year,1,1)).days
            weeks = int(days/7.)
            strdate = str(weeks).zfill(2) + '/' + datetimeIn.strftime("%y")
        else:
            return ''
    else:
        if resolution=='day' or resolution=='d':
            strdate = str(datetimeIn.month) + '/' + str(datetimeIn.day) + '/' + str(datetimeIn.year)
        elif resolution=='month' or resolution=='m':
            strdate = str(datetimeIn.month) +'/' + str(datetimeIn.year)
        elif resolution=='year' or resolution=='y':
            strdate = str(datetimeIn.year)
        else:
            return ''
            
    return strdate

def elide(text, length):
    if len(text) > (length-3):
        return text[0:(length-3)] + "..."
    else:
        return text

class SystemPreferences():
    def __init__(self, mWindow = None):
        self.mainWindow = mWindow
        self.filename = 'preferences.json'
        self.load_config()
                     
    def toggleHideNarrative(self):
        if self.hideNarrative:
            self.hideNarrative = False
        else:
            self.hideNarrative = True
        self.mainWindow.update_temporal_setting()
        
    def toggleEvaluationMode(self):
        if self.evaluationMode:
            self.evaluationMode = False
        else:
            self.evaluationMode = True
        tab_feat = self.mainWindow.get_mainWindow_tab("Case Narrative && Features")
        if tab_feat:
            tab_feat.central.update_layout()      
            
                
    def toggleCodingSummary(self):
        if self.codeSummary:
            self.codeSummary = False
        else:
            self.codeSummary = True
            
        tab_feat = self.mainWindow.get_mainWindow_tab("Case Narrative && Features")
        if tab_feat:
            tab_feat.central.update_ether_summary()
            
    def toggleTimeHighlight(self):
        if self.highlightTime:
            self.highlightTime = False
        else:
            self.highlightTime = True
        tab_feat = self.mainWindow.get_mainWindow_tab("Case Narrative && Features")
        if tab_feat:
            tab_feat.central.text.update_setting_highlight(self.highlightTime)      
                
        tab_feat = self.mainWindow.get_mainWindow_tab("Case Features over Time")
        if tab_feat:
            tab_feat.central.text.update_setting_highlight(self.highlightTime)      
                
    def toggleHideSettings(self):
        if self.hideSettings:
            self.hideSettings = False
        else:
            self.hideSettings = True
        self.mainWindow.update_temporal_setting()
        
    def toAdjustYScaleAggregated(self):
        return self.adjustYScaleAggregated
    
    def toHideNarrative(self):
        return self.hideNarrative
        
    def toHideSettings(self):
        return self.hideSettings
    
    def getFontSize(self):
        return self.fontSize
    
    def toOverwriteDB(self):
        return self.overwriteDB

    def toSortLasagna(self):
        return self.sortLasagna
    
    def toShowConsolidation(self):
        return self.showConsolidation
    
    def toCodeSummary(self):
        return self.codeSummary
    
    def toHighlightTime(self):
        return self.highlightTime
    
    def toShowTimeAnnotationTab(self):
        return self.showTimeAnnotationTab
    
    def toShowFeatureEvaluationTab(self):
        return self.showFeatureEvaluationTab
    
    def toShowLabDataTab(self):
        return self.showLabDataTab

    def getColorScheme(self):
        return self.color_scheme
    
    def setColorScheme(self, col):
        self.color_scheme = col
        
    def getEvaluationMode(self):
        return self.evaluationMode
    
    def getAnnotationSettings(self):
        return self.annotations
        
    def load_config(self):
        self.setToDefaultConfiguration()
        try:
            with open(self.filename, 'r') as json_data:
                config = json.load(json_data)
        except Exception as e:
            QMessageBox.critical(None, "ETHER", str(e)+"\nCoundn't find preferences.json! Default parameters will be used.")
            return

        self.hideNarrative = config['hideNarrative']
        self.hideSettings = config['hideSettings']
        self.fontSize = config['fontSize']
        self.adjustYScaleAggregated = config['adjustYScaleAggregated']
        self.overwriteDB = config['overwriteDB']
        self.sortLasagna = config['sortLasagna']
        self.showConsolidation = config['showConsolidation']
        self.evaluationMode = config['evaluationMode']
        self.highlightTime = config['highlightTime']
        self.color_scheme = config['colorScheme']
        self.showTimeAnnotationTab = config['showTimeAnnotationTab']
        self.showFeatureEvaluationTab = config['showFeatureEvaluationTab']
        self.showLabDataTab = config['showLabDataTab']
        self.annotations = config['annotations']
        self.codeSummary = config['codeSummary']
        
    def setToDefaultConfiguration(self):
        self.color_scheme = 'Blues'
        self.hideNarrative = False
        self.hideSettings = False
        self.fontSize = 12
        self.adjustYScaleAggregated = True
        self.overwriteDB = False
        self.sortLasagna = True
        self.showConsolidation = False
        self.evaluationMode = False
        self.highlightTime = True
        self.showTimeAnnotationTab = False
        self.showFeatureEvaluationTab = False
        self.showLabDataTab = False
        self.codeSummary = False
        
        self.annotations = {"Category": ["Feature", "Time"], 
                            "Summarization": ["Diagnosis", "Secondary Outcome", "Cause of Death", "Symptom", "Vaccine", "Drug"], 
                            "Feature": ["SYM", "VAX", "pDx", "sDx", "CoD", "Tx", "FHx", "MHx", "R/O", "Status", "Lab", "History"], 
                            "Time": ["Date", "Relative", "Duration", "Weekday", "Frequency", "Age", "Time", "Anchor", "Other"], 
                            "TimeRelations":["OVERLAP", "BEFORE", "AFTER", "BEFORE_OVERLAP", "AFTER_OVERLAP"]}

    def save_config(self):
        config = {}
        config['hideNarrative'] = self.hideNarrative
        config['hideSettings'] = self.hideSettings
        config['fontSize'] = self.fontSize
        config['adjustYScaleAggregated'] = self.adjustYScaleAggregated
        config['overwriteDB'] = self.overwriteDB
        config['sortLasagna'] = self.sortLasagna
        config['showConsolidation'] = self.showConsolidation
        config['evaluationMode'] = self.evaluationMode
        config['highlightTime'] = self.highlightTime
        config['colorScheme'] = self.color_scheme
        config['showTimeAnnotationTab'] = self.showTimeAnnotationTab
        config['showFeatureEvaluationTab'] = self.showFeatureEvaluationTab 
        config['showLabDataTab'] = self.showLabDataTab
        config['annotations'] = self.annotations 
        config['codeSummary'] = self.codeSummary 
        
        with open(self.filename, 'w') as outfile:
            json.dump(config, outfile)
        
        return 
    
class FeatureStruct():
    def __init__(self, (ftype, fstring, sentNum, tStart, tEnd, startPos, endPos, confidence, medDRA, featid, comment, matchid, cleanString)):
        self.type = ftype
        self.string = fstring
        self.sentNum = sentNum
        
        if not tStart or tStart=='':
            self.timeStart = None
        elif isinstance(tStart, basestring):
            self.timeStart = parse(tStart)
        else:
            self.timeStart = tStart
            
        if not tEnd or tEnd=='':
            self.timeEnd = None
        elif isinstance(tEnd, basestring):
            self.timeEnd = parse(tEnd) 
        else:
            self.timeEnd = tEnd                      
            
        self.startPos = startPos
        self.endPos = endPos
        self.confidence = confidence
        self.medDRA = medDRA
        self.featureID = featid
        
        self.comment = comment
        self.matchlevel = matchid
        self.cleanString = cleanString
    
    def copy(self):
        param = (self.type, self.string, self.sentNum, self.timeStart, self.timeEnd, self.startPos, self.endPos, self.confidence, 
                 self.medDRA, self.featureID, self.comment, self.matchlevel, self.cleanString)
        featStruct = FeatureStruct(param)
        return featStruct
    
    ##: this is called in consolidation. both string and clean string are set to be the new string
    def setString(self, s):
        self.cleanString = s
        self.string = s
    
    def setStartTime(self, tStart):
        if not tStart or tStart=='':
            self.timeStart = None
        elif isinstance(tStart, basestring):
            try:
                self.timeStart = parse(tStart)
            except:
                self.timeStart = None
        else:
            self.timeStart = tStart
    
    def setEndTime(self, tEnd):
        if not tEnd or tEnd=='':
            self.timeEnd = None
        elif isinstance(tEnd, basestring):
            try:
                self.timeEnd = parse(tEnd) 
            except:
                self.timeEnd = None
        else:
            self.timeEnd = tEnd       
                 
    def getFeatureID(self):
        return self.featureID
    
    def setFeatureID(self, idx):
        self.featureID = idx
    
    ##: for report generation
    def getFeatureDescription(self):
        if self.timeStart:
            strDateStart = self.timeStart.isoformat().split('T')[0]
        else:
            strDateStart = ''
        
        if self.timeEnd:
            strDateEnd = self.timeEnd.isoformat().split('T')[0]
        else:
            strDateEnd = ''                           

        if strDateStart==strDateEnd:
            a = [dictFeatureNamesInv[self.type], self.string, strDateStart]
        else:
            a = [dictFeatureNamesInv[self.type], self.string, strDateStart+'~'+strDateEnd]
        return a
            
    ##: for report generation
    def getFeatureDescription_split(self):
        if self.timeStart:
            strDateStart = self.timeStart.isoformat().split('T')[0]
        else:
            strDateStart = ''
        
        if self.timeEnd:
            strDateEnd = self.timeEnd.isoformat().split('T')[0]
        else:
            strDateEnd = ''                           

        negationSet = set([r'disappeared', r'excluded', r'unlikely', r'non', r'no', r'not', r'denies',
                       r'denied', r'without', r'wo', r'any', r'none', r'negative', r'neg', r'nothing', r'gone'])
        
        rows = []
        fts = re.split(', | and ', self.getString())
        meddra = self.getMedDRA()
        if meddra:
            pts = meddra.split(';; ')
        else:
            pts = ['']*len(fts)
            
        for i, ft in enumerate(fts):
            if strDateStart==strDateEnd:
                row = [dictFeatureNamesInv[self.type], ft, pts[i], strDateStart]
            else:
                row = [dictFeatureNamesInv[self.type], ft, pts[i], strDateStart+'~'+strDateEnd]
                
            wds = re.split(' |-', ft)
            if set(wds).intersection(negationSet):
                row.append('Y')
            else:
                row.append('')
            
            rows.append(row)
            
        return rows
        
    def getCleanString(self):
        return self.cleanString
    
    def setPositions(self, (start, end)):
        self.startPos = start
        self.endPos = end
    
    def getStartPos(self):
        return self.startPos
    
    def getEndPos(self):
        return self.endPos
    
    def hasStartTime(self):
        if self.timeStart:
            return True
        else:
            return False
        
    def hasEndTime(self):
        if self.timeEnd:
            return True
        else:
            return False
        
    def getSentNum(self):
        return self.sentNum
    
    def getStartDate(self):
        return datetime.date(self.timeStart.year, self.timeStart.month, self.timeStart.day)
     
    def getEndDate(self):
        return datetime.date(self.timeEnd.year, self.timeEnd.month, self.timeEnd.day)
    
    def getStartTime(self):
        return self.timeStart
    
    def getEndTime(self):
        return self.timeEnd
    
    def getType(self):
        return self.type
    
    def setType(self, t):
        self.type = t
    
    def getString(self):
        return self.string
    
    def getConfidence(self):
        return self.confidence
    
    def setComment(self, s):
        self.comment = s
    
    def setMatchlevel(self, s):
        self.matchlevel = s
        
    def setMedDRA(self, s):
        self.medDRA = s
        
    def getMedDRA(self):
        if self.medDRA:
            return self.medDRA
        else:
            return ''

    def getMatchlevel(self):
        return self.matchlevel

    def getDBFeatureTableRow(self):        
        if self.timeStart:
            strDateStart = self.timeStart.isoformat().split('T')[0]
        else:
            strDateStart = ''
        
        if self.timeEnd:
            strDateEnd = self.timeEnd.isoformat().split('T')[0]
        else:
            strDateEnd = ''           

        a = (self.type, self.string, self.sentNum, strDateStart, strDateEnd, self.startPos, self.endPos, self.medDRA, self.featureID, self.cleanString)
        return a
        
    def getTableRow(self):
        if self.timeStart:
            if self.timeEnd - self.timeStart < datetime.timedelta(days=1):
                strDate = self.timeStart.isoformat().split('T')[0]
            else:
                strDate = self.timeStart.isoformat().split('T')[0] + ' ~ ' + self.timeEnd.isoformat().split('T')[0]
        else:
            strDate = ''

        strRow = [str(self.sentNum).zfill(3), dictFeatureAbr[self.type], self.string, strDate, self.comment, str(self.featureID).zfill(3), str(self.matchlevel)]
        
        return strRow

    def getSummarizationTableRow(self):
        if self.timeStart:
            if self.timeEnd - self.timeStart < datetime.timedelta(days=1):
                strDate = self.timeStart.isoformat().split('T')[0]
            else:
                strDate = self.timeStart.isoformat().split('T')[0] + ' ~ ' + self.timeEnd.isoformat().split('T')[0]
        else:
            strDate = ''
        
        ftype = SummaryElement.dictElemAbr[SummaryElement.dictFeat2Elem[self.type]]
        strRow = [str(self.featureID).zfill(3), ftype, self.string, self.medDRA, 
                        strDate, self.comment, self.matchlevel, str(self.startPos), str(self.endPos)]
                
#         self.headers = ['FeatureID', 'Type', 'Element Text', 'Preferred Term', 'Date', 'Comment', 'Feedback']

        return strRow


class FeatureAnnotation(): 
    def __init__(self, (annotationID, ftext, ftype, ferror, comment, startPos, endPos, featID, timeID, timeRel)):
        self.annotationID = annotationID
        self.text = ftext
        self.type = ftype
        self.errorType = ferror
        self.comment = comment
        self.startPos = startPos
        self.endPos = endPos
        self.featureID = featID
        self.timeID = timeID
        self.timeRel = timeRel
        
        self.preAnnotation = False
        self.postAnnotation = False
    
    def __eq__(self, other):
        if self.annotationID != other.annotationID \
            or self.text != other.text \
            or self.type != other.type \
            or self.errorType != other.errorType \
            or self.comment != other.comment \
            or self.startPos != other.startPos \
            or self.endPos != other.endPos \
            or self.featureID != other.featureID \
            or self.timeID != other.timeID \
            or self.timeRel != other.timeRel:
            return False
        else:
            return True
        
    def getFeatureID(self):
        return self.featureID
    
    def getText(self):
        return self.text
    
    def setText(self, s):
        self.text = s
    
    def setPreAnnotation(self, pre):
        self.preAnnotation = pre
        
    def setPostAnnotation(self, post):
        self.postAnnotation = post
    
    def setType(self, tp):
        self.type = tp
        
    def getType(self):
        return self.type
    
    def getID(self):
        return self.annotationID
    
    def getIDName(self):
        sid = 'f'+str(self.annotationID)
        if self.preAnnotation:
            sid = sid + '*'
        elif self.postAnnotation:
            sid = sid + '+'
        
        return sid
    
    def setID(self, i):
        self.annotationID = i
    
    def setTimeID(self, i):
        self.timeID = i
        if i==-1:
            self.timeRel = ''
    
    def getTimeID(self):
        return self.timeID
    
    def getTimeRelation(self):
        return self.timeRel
    
    def getErrorType(self):
        return self.errorType
    
    def getStartPos(self):
        return self.startPos
    
    def getEndPos(self):
        return self.endPos
    
    def getPositions(self):
        return (self.startPos, self.endPos)
    
    def setPositions(self, (startPos, endPos)):
        self.startPos = startPos
        self.endPos = endPos
        
    def getTableRow(self):
        ##:header = ['ID', 'Feature Text', 'StartPos', 'Type', 'TimeID', 'Relation', 'Comment']        
        sid = 'f'+str(self.annotationID)
        if self.preAnnotation:
            sid = sid + '*'
        elif self.postAnnotation:
            sid = sid + '+'
        
        if self.timeID and self.timeID>0:
            tid = 't'+str(self.timeID)
        else:
            tid = ''
        strRow = (sid, self.text, str(self.startPos), str(self.endPos), self.type, tid, self.timeRel, self.comment, str(self.featureID))
        return strRow
    
    def getDBRecord(self):
        record = (self.annotationID, self.text, self.type, self.errorType, self.comment, 
                self.startPos, self.endPos, '', self.featureID, self.timeID, self.timeRel)
         
        return record
    
class TimeAnnotation():
    types = ["", "Date", "Relative", "Duration", "Weekday", "Frequency", "Age", "Time", "Anchor", "Other"]
    
    def __init__(self, (annotationID, ftext, ftype, dtime, startPos, endPos, confidence, comment, timeID, timeRel)):
        self.annotationID = annotationID
        self.string = ftext
        self.datetime = dtime
        self.confidence = confidence
        self.comment = comment
        self.startPos = startPos
        self.endPos = endPos
        self.timeID = timeID
        self.timeRel = timeRel
        
        if isinstance(ftype, int):
            self.type = TimeAnnotation.types[ftype]
        else:
            self.type = ftype
            
        self.preAnnotation = False
    
    def __eq__(self, other):
        if self.annotationID != other.annotationID \
            or self.string != other.string \
            or self.datetime != other.datetime \
            or self.type != other.type \
            or self.confidence != other.confidence \
            or self.comment != other.comment \
            or self.timeID != other.timeID \
            or self.timeRel != other.timeRel \
            or self.endPos != other.endPos \
            or self.startPos != other.startPos:
            return False
        else:
            return True

    def setPreAnnotation(self, pre):
        self.preAnnotation = pre
    
    def setDate(self, dt):
        self.datetime = dt
    
    def getDate(self):
        return self.datetime
    
    def setType(self, ftype):
        if isinstance(ftype, int):
            self.type = ftype
        else:
            self.type = TimeAnnotation.types.index(ftype)
    
    def getID(self):
        return self.annotationID
    
    def setID(self, i):
        self.annotationID = i
    
    def setTimeID(self, i):
        self.timeID = i
        if i==-1:
            self.timeRel = ''
    
    def getTimeID(self):
        return self.timeID
    
    def getTimeRelation(self):
        if not self.timeRel:
            return ''
        return self.timeRel
    
    def setString(self, s):
        self.string = s
    
    def getString(self):
        return self.string
    
    def getStartPos(self):
        return self.startPos
    
    def getEndPos(self):
        return self.endPos
    
    def getPositions(self):
        return (self.startPos, self.endPos)
    
    def setPositions(self, (startPos, endPos)):
        self.startPos = startPos
        self.endPos = endPos
    
    def getTableRow(self):
        ##: header = ['TimeID', 'Time Text', 'StartPos', 'Type', 'Date', 'Comment']          
        sid = 't'+str(self.annotationID)
        if self.preAnnotation:
            sid = sid + '*'
        
        if self.timeID and self.timeID>0:
            tid = 't'+str(self.timeID)
        else:
            tid = ''

        ttp = self.type
        strRow = (sid, self.string, str(self.startPos), str(self.endPos), ttp, self.datetime, tid, self.timeRel, self.comment)
        return strRow
    
    def getRecord(self):
        rec = (self.annotationID, self.string, self.startPos, self.endPos, self.type, self.datetime, self.confidence, self.comment, self.timeID, self.timeRel)
        return rec   
    
    def getTypeIndex(self):
        if self.type in TimeAnnotation.types:
            return TimeAnnotation.types.index(self.type)
        else:
            return 0
    
    def getType(self):
        return self.type
    
    def getTypeID(self):
        return self.type
              
class SummaryElement():
    errorTypes = ['', 'Text incomplete', 'Text redundant']
    featureTypes = ["DIAGNOSIS", "CAUSE_OF_DEATH", "SECOND_LEVEL_DIAGNOSIS", "SYMPTOM", 
                       "RULE_OUT", "MEDICAL_HISTORY", "FAMILY_HISTORY", "DRUG", "VACCINE"]
    elementTypes =  ["Diagnosis", "Secondary Outcome", "Cause of Death", "Symptom", "Vaccine", "Drug"]
    dictElem2Feat = {"Diagnosis":"DIAGNOSIS", "Secondary Outcome":'SECOND_LEVEL_DIAGNOSIS', 
                              "Cause of Death":"CAUSE_OF_DEATH", "Symptom":"SYMPTOM", "Vaccine":"VACCINE", "Drug":"DRUG"}
    dictElemAbr = {"Diagnosis":"Dx", "Secondary Outcome":"S/O", "Cause of Death":"CoD", "Symptom":"SYM",
                             "Vaccine":"VAX", "Drug":"Tx"}
    dictFeat2Elem = dict((v,k) for k, v in dictElem2Feat.iteritems())

    def __init__(self, (annotationID, ftext, ftype, ferror, comment, startPos, endPos, pt, featID, tStart, tEnd, timeID, timeRel)):
        self.annotationID = annotationID
        self.text = ftext
        self.type = ftype
        self.errorType = ferror
        self.comment = comment
        self.startPos = startPos
        self.endPos = endPos
        self.preferTerm = pt
        self.featureID = featID
        self.timeID = timeID
        self.timeRel = timeRel
        self.startTime = tStart
        self.endTime = tEnd
    
    def getFeatureID(self):
        return self.featureID
    
    def getText(self):
        return self.text
    
    def getPreferTerm(self):
        return self.preferTerm
    
    def getStartTime(self):
        return self.startTime
    
    def getEndTime(self):
        return self.endTime
    
    def getType(self):
        return self.type
    
    def getErrorType(self):
        return self.errorType
    
    def getPositions(self):
        return (self.startPos, self.endPos)
    
    def isElement(self):
        if self.type in FeatureAnnotation.elementTypes:
            return True
        else:
            return False
    
    def isFeature(self):
        if self.type in FeatureAnnotation.featureTypes:
            return True
        else:
            return False
    
    def summarizationDBRecord(self):
        record = (self.annotationID, self.text, self.type, self.errorType, self.comment, 
                  self.startPos, self.endPos, self.preferTerm, self.featureID, self.startTime, self.endTime)
        
        return record
    
    def getFeatureObj(self):
        feat = FeatureStruct((self.dictElem2Feat[self.type], self.text, -1, self.startTime, self.endTime, self.startPos, 
                              self.endPos, -1, self.preferTerm, -1, self.comment, -1, self.text))
        return feat


class Structured(QWidget):
    def __init__(self, reports, parent=None):
        super(Structured, self).__init__(parent)
        self.reports = reports
        self.setLayout(QHBoxLayout())
        
        self.id_label = QLabel(self)
        self.id_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.age_label = QLabel(self)
        self.gender_label = QLabel(self)
        self.doe_label = QLabel(self)
        self.doo_label = QLabel(self)
        self.dor_label = QLabel(self)
        self.vaccines_label = QLabel(self)
        self.meddra_label = QLabel(self)
 
        self.id_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.age_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.gender_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.doe_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.doo_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.dor_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.vaccines_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.meddra_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        
        self.id_label.setFixedWidth(120)
        self.age_label.setFixedWidth(70)
        self.gender_label.setFixedWidth(60)
        self.doe_label.setFixedWidth(190)
        self.doo_label.setFixedWidth(180)
        self.dor_label.setFixedWidth(180)

        self.layout().addWidget(self.id_label, 1)
        self.layout().addWidget(self.age_label, 1)
        
        self.layout().addWidget(self.gender_label, 1)
        self.layout().addWidget(self.doe_label, 2)
        self.layout().addWidget(self.doo_label, 2)
        self.layout().addWidget(self.dor_label, 2)
        self.layout().addWidget(self.vaccines_label, 3)
        self.layout().addWidget(self.meddra_label, 3)
        
    def wrap_words(self, text, fontMetrics, width):
        if fontMetrics.boundingRect(text).width() <= width:
            return text
        
        while fontMetrics.boundingRect(text).width() >= width:
            text = text[:-1]
        text = text[:-4]+'...'
        return text

    def set_current_report(self, current):
        self.current_report = current
        if  current >= 0 and current < len(self.reports):
            self.id_label.setText("<b>{0}:</b>  {1}".format('Case ID', self.reports[self.current_report]['Report ID']))
            self.age_label.setText("<b>{0}:</b>  {1}".format('Age', self.reports[self.current_report]['Age']))
            if not self.reports[self.current_report]['Gender']:
                self.gender_label.setText("<b>{0}:</b>  {1}".format('Sex', ''))
            else:
                self.gender_label.setText("<b>{0}:</b>  {1}".format('Sex', self.reports[self.current_report]['Gender'][0].upper()))
            self.doe_label.setText("<b>{0}:</b>  {1}".format('Date of Exposure', self.reports[self.current_report]['Date of Exposure']))
            self.doo_label.setText("<b>{0}:</b>  {1}".format('Date of Onset', self.reports[self.current_report]['Date of Onset']))        
            self.dor_label.setText("<b>{0}:</b>  {1}".format('Received Date', self.reports[self.current_report]['Received Date']))   
            self.vaccines_label.setText("<b>{0}:</b>  {1}".format('Product Names', elide(self.reports[self.current_report]['Vaccine Names'], 60)))
            self.meddra_label.setText("<b>{0}:</b>  {1}".format('MedDRA', elide(self.reports[self.current_report]['MedDRA'],60)))   
            self.vaccines_label.setToolTip('\n'.join(self.reports[self.current_report]['Vaccine Names'].split(', ')))
            self.meddra_label.setToolTip('\n'.join(self.reports[self.current_report]['MedDRA'].split('; ')))
        else:
            self.id_label.setText("<b>{0}:</b>  {1}".format('Case ID', ''))
            self.age_label.setText("<b>{0}:</b>  {1}".format('Age', ''))
            self.gender_label.setText("<b>{0}:</b>  {1}".format('Sex', ''))
            self.doe_label.setText("<b>{0}:</b>  {1}".format('Date of Exposure', ''))
            self.doo_label.setText("<b>{0}:</b>  {1}".format('Date of Onset', ''))      
            self.dor_label.setText("<b>{0}:</b>  {1}".format('Received Date', ''))            
            self.vaccines_label.setText("<b>{0}:</b>  {1}".format('Vaccine Names', ''))
            self.meddra_label.setText("<b>{0}:</b>  {1}".format('MedDRA', ''))   
            self.vaccines_label.setToolTip('')
            self.meddra_label.setToolTip('')
    
class MouseToggleTreeWidget(QTreeWidget):
    focusLost = Signal()
    keyReleased = Signal(QKeyEvent)
    
    def __init__(self, parent=None):
        super(MouseToggleTreeWidget, self).__init__(parent)
        self.mouse_enabled = True
    
    def mousePressEvent(self, event):
        logging.debug('captured mouse press event')
        if self.mouse_enabled == True:
            super(MouseToggleTreeWidget, self).mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        logging.debug('captured mouse release event')
        if self.mouse_enabled == True:
            super(MouseToggleTreeWidget, self).mouseReleaseEvent(event)
        
    def mouseMoveEvent(self, event):
        logging.debug('captured mouse move event')
        if self.mouse_enabled == True:
            super(MouseToggleTreeWidget, self).mouseMoveEvent(event)
            
    def focusOutEvent(self,event):
        self.focusLost.emit()
        
    def keyReleaseEvent(self, event):
        self.keyReleased.emit(event)

class TreeWidgetItem(QTreeWidgetItem):
    def __init__(self, parent, strings):
        QTreeWidgetItem.__init__(self, parent, strings)

    def __lt__(self, otherItem):
        column = self.treeWidget().sortColumn()
        if self.data(column, Qt.UserRole).canConvert(QCheckBox):
            return self.data(column, Qt.UserRole).checkStart() < otherItem.data(column, Qt.UserRole).checkStart()
        else:
            return self.text(column) < otherItem.text(column)        
        
class FilterCriteriaRow(QFrame):
    def __init__(self, medDict, isFirstRow, dateRangePython, parent = None):
        super(FilterCriteriaRow, self).__init__(parent)
        self.medDict = medDict
        self.dialog = parent
        self.isFirstRow = isFirstRow
        pDateFrom = dateRangePython[0]
        pDateTo = dateRangePython[1]
        qDateFrom = QDate(pDateFrom.year, pDateFrom.month, pDateFrom.day)
        qDateTo = QDate(pDateTo.year, pDateTo.month, pDateTo.day)
        self.dateRange = (qDateFrom, qDateTo)
        
        layout = QHBoxLayout()
        self.setLayout(layout)        
        layout.setContentsMargins(0,0,0,0)
        
        self.comboxOperator = QComboBox()
        if self.isFirstRow:
            self.strOperators = ['', 'NOT']
        else:
            self.strOperators = ['AND', 'OR', 'NOT']
        self.comboxOperator.addItems(self.strOperators)
        self.comboxOperator.setFixedWidth(60)
        self.comboxOperator.currentIndexChanged.connect(self.queryChanged)
        
        labelFirst = QLabel('')
        labelFirst.setFixedWidth(60)
        
        self.comboxField = QComboBox()
        strFeatures = ["DIAGNOSIS", "CAUSE_OF_DEATH", "SECOND_LEVEL_DIAGNOSIS", "SYMPTOM", 
                       "RULE_OUT", "MEDICAL_HISTORY", "FAMILY_HISTORY", "DRUG", "VACCINE"]
        self.strFields = ['All Fields']
        for feat in strFeatures:
            featname = dictFeatureNamesInv[feat]
            self.strFields.append(featname)
        self.comboxField.addItems(self.strFields)                     
        self.comboxField.currentIndexChanged.connect(self.fieldChanged)
        
        self.comboxFeature = QComboBox()
        self.comboxFeature.setEditable(True)
        self.comboxFeature.setMinimumWidth(180)
        self.comboxFeature.textChanged.connect(self.queryChanged)
        
        verticalLine = QFrame()
        verticalLine.setFrameStyle(QFrame.VLine)
        verticalLine.setFrameShadow(QFrame.Sunken)
        verticalLine.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        
        self.comboxFrom = QComboBox()
        self.comboxFrom.addItems(["", "From"])
        self.comboxFrom.currentIndexChanged.connect(self.onComboxFromChanged)
        self.comboxTo = QComboBox()
        self.comboxTo.addItems(["", "To"])
        self.comboxTo.currentIndexChanged.connect(self.onComboxToChanged)
    
        self.spinFrom = QSpinBox()
        self.spinFrom.setMinimum(-1)     
        self.spinFrom.setMaximum(30000)        
        self.spinFrom.setPrefix('Day ')
        self.spinFrom.setSpecialValueText(' ')
        self.spinFrom.setValue(-1)      
        self.spinTo = QSpinBox()
        self.spinTo.setMinimum(-1)   
        self.spinTo.setMaximum(30000)           
        self.spinTo.setPrefix('Day ')
        self.spinTo.setSpecialValueText(' ')
        self.spinTo.setValue(-1)
        
        self.dateFrom = QDateEdit()
        self.dateFrom.setCalendarPopup(True)
        self.dateFrom.setDisplayFormat('MM/dd/yyyy')
        
        self.dateFrom.setDateRange(self.dateRange[0], self.dateRange[1])
        self.dateFrom.setDate(self.dateFrom.minimumDate())
        
        self.dateTo = QDateEdit()
        self.dateTo.setCalendarPopup(True)
        self.dateTo.setDisplayFormat('MM/dd/yyyy')

        self.dateTo.setDateRange(self.dateRange[0], self.dateRange[1])
        self.dateTo.setDate(self.dateTo.maximumDate())
        
        self.spinFrom.valueChanged.connect(self.queryChanged)
        self.spinTo.valueChanged.connect(self.queryChanged)
        self.dateFrom.dateChanged.connect(self.dateFromChanged)
        self.dateTo.dateChanged.connect(self.dateToChanged)
        
        self.stackedFrom = QStackedWidget()
        self.stackedFrom.addWidget(self.spinFrom)
        self.stackedFrom.addWidget(self.dateFrom)
        self.stackedFrom.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.stackedFrom.setCurrentIndex(0)
        self.stackedFrom.setDisabled(True)
        
        self.stackedTo = QStackedWidget()
        self.stackedTo.addWidget(self.spinTo)
        self.stackedTo.addWidget(self.dateTo)
        self.stackedTo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.stackedTo.setCurrentIndex(0)    
        self.stackedTo.setDisabled(True)
        self.comboxAxis = QComboBox()
        
        self.axisStrings = ['', 'Vax', 'Age', 'Date']
        self.comboxAxis.addItems(self.axisStrings)
        self.comboxAxis.currentIndexChanged.connect(self.onTimeAxisChanged)
        btnDel = QToolButton()
        btnDel.setIcon(QIcon('./minus.png'))
        btnDel.setAutoRaise(False)
        btnDel.clicked.connect(self.deleteRow)
        
        layout.addWidget(self.comboxOperator)
        layout.addWidget(self.comboxField)
        layout.addWidget(self.comboxFeature)
        layout.addWidget(verticalLine)
        layout.addWidget(self.comboxFrom)
        layout.addWidget(self.stackedFrom)
        layout.addWidget(self.comboxTo)
        layout.addWidget(self.stackedTo)
        layout.addWidget(self.comboxAxis)
        
        if isFirstRow:
            label = QLabel('  ')
            label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            layout.addWidget(label)
        else:
            layout.addWidget(btnDel)
    
    def queryChanged(self):
        self.dialog.updateQuery()
    
    def populateFields(self, (operator, field, feature, tFrom, tTo, axis)):
        operator = operator.upper()
        if self.isFirstRow and operator=='AND':
            operator = ''
        if operator not in self.strOperators:
            return
        
        field = field.lower()
        fldnames = [dictFeatureNamesInv[p] for p in dictFeatureNamesInv if p.lower()==field]
        if not fldnames:
            return 
        else:
            fldname = fldnames[0]
            if not fldname in self.strFields:
                return            
            
        opIdx = self.strOperators.index(operator)
        self.comboxOperator.setCurrentIndex(opIdx)
        fldIdx = self.strFields.index(fldname)
        self.comboxField.setCurrentIndex(fldIdx)
        
        if fldname in dictFeatureNames:
            featType = dictFeatureNames[fldname].lower()
            if featType in self.medDict:                
                if self.medDict[featType]:
                    features = ['Any']+self.medDict[featType]
                else:
                    features = ['Any']
        featIdx = [idx for (idx, feat) in enumerate(features) if feat==feature]
        if featIdx:
            self.comboxFeature.setCurrentIndex(featIdx[0])

        if not axis:
            return
        else:
            axes = [s for s in self.axisStrings if s.lower()==axis.lower()]
            if axes:
                axis = axes[0]
            else:
                return
        
        axisIdx = self.axisStrings.index(axis)
        self.comboxAxis.setCurrentIndex(axisIdx)
        
        if tFrom!=None:
            if self.comboxAxis.currentText()=='Date' and isinstance(tFrom, QDate):
                self.dateFrom.setDate(tFrom)
            elif isinstance(tFrom, int):
                self.spinFrom.setValue(tFrom)
            if self.comboxFrom.currentIndex()!=1:
                self.comboxFrom.setCurrentIndex(1)
        if tTo!=None:
            if self.comboxAxis.currentText()=='Date' and isinstance(tTo, QDate):
                self.dateTo.setDate(tTo)
            elif isinstance(tTo, int):
                self.spinTo.setValue(tTo)
            if self.comboxTo.currentIndex()!=1:
                self.comboxTo.setCurrentIndex(1)
    
    def dateFromChanged(self):
        if self.dateTo.date()==self.dateTo.minimumDate():
            self.dateTo.setDate(self.dateFrom.date())
        self.queryChanged()
        
    def dateToChanged(self):
        if self.dateFrom.date()==self.dateFrom.minimumDate():
            self.dateFrom.setDate(self.dateTo.date())
        self.queryChanged()
    
    def validityCheck(self):
        if self.comboxFrom.currentText()=='From' and self.comboxTo.currentText()=='To':
            if self.comboxAxis.currentText()=='Date':
                tFrom = self.dateFrom.dateTime()
                tTo = self.dateTo.dateTime()            
                if tFrom > tTo:
                    return "Time Range Invalid!"
                 
            else:
                tFrom = self.spinFrom.value()
                tTo = self.spinTo.value()
                if tFrom > tTo and tFrom!=self.spinFrom.minimum() and tTo!=self.spinTo.minimum():
                    return "Time Range Invalid!"
        return ''
        
    def getQuery(self):
        if (self.comboxFeature.currentText()=='' 
                and self.comboxFrom.currentText()!='From' 
                and self.comboxTo.currentText()==''):
            return ''
        
        s = self.comboxFeature.currentText()
        s = s.strip()
        if self.comboxField.currentText()!='All Fields':
            s += '['+self.comboxField.currentText()+']'
        
        sFrom = ''
        if self.comboxFrom.currentText()=='For':
            if self.spinFrom.value() != self.spinFrom.minimum():
                s += '&' + str(self.spinFrom.value()) + '[For]'
        elif self.comboxFrom.currentText()=='From':
            if self.comboxAxis.currentText()=='Date':
                if self.stackedFrom.isEnabled():
                    tFrom = self.dateFrom.dateTime().toPython()
                    sFrom = tFrom.strftime('%d/%m/%Y') + '[From]'
                    
            else: 
                if self.stackedFrom.isEnabled() and self.spinFrom.value()!=self.spinFrom.minimum():             
                    sFrom = str(self.spinFrom.value()) + '[From]'

        sTo = ''
        if self.comboxTo.currentText()=='To':
            if self.comboxAxis.currentText()=='Date':
                tTo = self.dateTo.dateTime().toPython()
                sTo = tTo.strftime('%d/%m/%Y')+'[To]'
            else: 
                if self.spinTo.value()!=self.spinTo.minimum():
                        sTo = str(self.spinTo.value()) + '[To]'
        
        if sFrom!='' or sTo!='':
            s += '&' + sFrom + sTo +  '['+self.comboxAxis.currentText()+']'
        
        if s!='' and self.comboxOperator.currentText()!='': 
            s = self.comboxOperator.currentText() + ' ' + s
            
        return s
        
    def deleteRow(self):
        self.dialog.deleteRow(self)
    
    def onTimeAxisChanged(self):
        axis = self.comboxAxis.currentText()
        if axis=='Date':
            self.stackedFrom.setCurrentIndex(1)
            self.stackedTo.setCurrentIndex(1)
        else:
            self.stackedFrom.setCurrentIndex(0)
            self.stackedTo.setCurrentIndex(0)
            if axis=='Age':
                self.spinFrom.setPrefix('Year ')
                self.spinTo.setPrefix('Year ')
            else:
                self.spinFrom.setPrefix('Day ')
                self.spinTo.setPrefix('Day ')
                
        self.queryChanged()
        
    def onComboxFromChanged(self):
        text = self.comboxFrom.currentText()
        currentAxis = self.comboxAxis.currentText()
        if text=='For':
            self.comboxAxis.setCurrentIndex(0)
            self.stackedFrom.setDisabled(False)
            self.stackedTo.setDisabled(True)
            self.comboxTo.setDisabled(True) 
            self.comboxAxis.clear()
            self.comboxAxis.addItems(['Vax', 'Age'])
            newID = self.comboxAxis.findText(currentAxis)
            if newID>=0:
                self.comboxAxis.setCurrentIndex(newID)
        else:
            self.stackedTo.setDisabled(False)
            self.comboxTo.setDisabled(False)    
            
            id00 = self.comboxAxis.findText('')
            if id00>=0:
                self.comboxAxis.removeItem(id00)
                self.comboxAxis.setCurrentIndex(0)

            if text=='':
                self.stackedFrom.setDisabled(True)
            elif text=='From':
                self.stackedFrom.setDisabled(False)
                newID = self.comboxAxis.findText(currentAxis)
                if newID>=0:
                    self.comboxAxis.setCurrentIndex(newID)
        
        self.queryChanged()
        
    def onComboxToChanged(self):
        text = self.comboxTo.currentText()
        currentAxis = self.comboxAxis.currentText()
        if text=='':
            self.stackedTo.setDisabled(True)
        elif text == 'To':
            id00 = self.comboxAxis.findText('')
            if id00>=0:
                self.comboxAxis.removeItem(id00)
                self.comboxAxis.setCurrentIndex(0)
            self.stackedTo.setDisabled(False)
            newID = self.comboxAxis.findText(currentAxis)
            if newID>=0:
                self.comboxAxis.setCurrentIndex(newID)
   
        self.queryChanged()
        
    def fieldChanged(self):
        self.comboxFeature.clear()
        fldname = self.comboxField.currentText()
        if fldname in dictFeatureNames:
            featType = dictFeatureNames[fldname].lower()
            if featType in self.medDict:
                if self.medDict[featType]:
                    self.comboxFeature.addItems(['Any']+self.medDict[featType])
                else:
                    self.comboxFeature.addItems(['Any'])
        self.queryChanged()
        
class RadioDialog(QDialog):
    def __init__(self, RadioTexts = [], message = '', title = '', parent = None):
        super(RadioDialog, self).__init__(parent, )
        self.setLayout(QVBoxLayout())
        self.setWindowTitle(title)

        self.radiogroup = QButtonGroup()
        self.radios = []
        for txt in RadioTexts:
            radio = QRadioButton(txt)
            self.radios.append(radio)
            self.radiogroup.addButton(radio)
        
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
        Qt.Horizontal, self)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        frmRadio = QFrame()
        frmRadio.setLayout(QHBoxLayout())
        frmRadio.layout().addWidget(QLabel(message))
        for radio in self.radios:
            frmRadio.layout().addWidget(radio)
            
        self.layout().addWidget(frmRadio)
        self.layout().addWidget(buttonBox)
        self.choice = -1
        
    def accept(self):
        for i, radio in enumerate(self.radios):
            if radio.isChecked():
                self.choice = i
                break
        self.close()

    def getChoice(self):
        return self.choice

class FilterLocalDBDialog(QDialog):
    def __init__(self, parent = None):
        super(FilterLocalDBDialog, self).__init__(parent, )        
        self.setWindowTitle('Retrieve Reports from Local Database')
        self.setLayout(QVBoxLayout())

        frmDBFile = QGroupBox()
        frmDBFile.setTitle('Local Database File')
        frmDBFile.setLayout(QHBoxLayout())
        self.txtFileName = QLineEdit('.\\etherlocal.db')
        btnFileDialog = QPushButton('...')
        btnFileDialog.setFixedWidth(30)
        btnFileDialog.clicked.connect(self.onBtnDBFileClicked)
        
        frmDBFile.layout().addWidget(QLabel('File Name: '))
        frmDBFile.layout().addWidget(self.txtFileName)
        frmDBFile.layout().addWidget(btnFileDialog)
        frmDBFile.layout().setStretch(0, 1)
        frmDBFile.layout().setStretch(1, 50)
        frmDBFile.layout().setStretch(2, 1)
        
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        
        self.layout().addWidget(frmDBFile)
        self.layout().addWidget(QLabel(''))
        self.layout().addWidget(buttonBox)
        self.layout().setStretch(0, 1)
        self.layout().setStretch(1, 2)
        self.layout().setStretch(2, 1)
        self.layout().setStretch(3, 2)
        self.layout().setStretch(4, 1)
#
        self.dbfilename = None
        self.sql = None
    
    def onBtnDBFileClicked(self):
        dbfilename = QFileDialog.getOpenFileName(self, "Load local Database file", './etherlocal.db', "Database File (*.db)")[0]        
        if dbfilename:
            self.txtFileName.setText(dbfilename) 
               
            
    def accept(self):
        self.dbfilename = self.txtFileName.text()        
        self.sql=None

        self.close()
    
    def getDBSQL(self):
        return (self.dbfilename, self.sql)
        
class PreferenceDialog(QDialog):
    def __init__(self, configInfo, parent = None):
        super(PreferenceDialog, self).__init__(parent)
        self.setLayout(QVBoxLayout())
        self.setWindowTitle('Preferences')
        self.resize(800, 500)
        #self.setModal(True)
        self.config = configInfo
        self.mainWindow = parent
        
        grpConsolidation = QGroupBox('Consolidation')
        grpConsolidation.setLayout(QHBoxLayout())
        self.radioOriginal = QRadioButton("Original Report") 
        self.radioConsolidated = QRadioButton("Consolidated Report") 
        grpConsolidation.layout().addWidget(self.radioOriginal)
        grpConsolidation.layout().addWidget(self.radioConsolidated)
        
        grpAppearance = QGroupBox('Appearance')
        grpAppearance.setLayout(QVBoxLayout())
        self.checkHideNarrative = QCheckBox('Hide narrative in the Case Feature over Time tab (Ctrl+T)')
        self.checkHideSettings = QCheckBox('Hide settings panel in the Case Feature over Time tab (Ctrl+H)')      
        self.checkHighlightTime = QCheckBox('Highlight time in the narrative')         
       
        self.comboxFontSize = QComboBox()
        self.comboxFontSize.addItems([str(i) for i in [10, 12, 14, 16, 18, 20, 22, 24]])
        self.comboxFontSize.setEditable(True)
        self.comboxFontSize.setFixedWidth(45)
        frmFont = QFrame()
        frmFont.setLayout(QHBoxLayout())
        frmFont.layout().addWidget(QLabel('Font size in the time plot: '))
        frmFont.layout().addWidget(self.comboxFontSize)
        frmFont.layout().addWidget(QLabel(''))
        frmFont.layout().setStretch(2, 100)
        frmFont.layout().setContentsMargins(0,0,0,0)
        
        self.comboxColorScheme = QComboBox()
        self.colors = self.get_color_list()        
        self.comboxColorScheme.addItems(self.colors)        
        self.comboxColorScheme.setFixedWidth(90)
        frmColor = QFrame()
        frmColor.setLayout(QHBoxLayout())
        lbl = QLabel('Color scheme for Lasagna plot: ')
        lbl.setFixedWidth(150)
        frmColor.layout().addWidget(lbl)
        frmColor.layout().addWidget(self.comboxColorScheme)
        frmColor.layout().addWidget(QLabel(''))
        frmColor.layout().setStretch(2, 100)
        frmColor.layout().setContentsMargins(0,0,0,0)
        grpAppearance.layout().addWidget(self.checkHideNarrative)
        grpAppearance.layout().addWidget(self.checkHideSettings)
        grpAppearance.layout().addWidget(self.checkHighlightTime)
        grpAppearance.layout().addWidget(frmColor)
        grpAppearance.layout().addWidget(frmFont)        
        
        grpBehavior = QGroupBox('Behavior')
        grpBehavior.setLayout(QVBoxLayout())
        self.checkOverwriteDB = QCheckBox('Overwrite the local database')
        self.checkLasagnaSorting = QCheckBox('Sort cases in the Lasagna plot')
        self.checkAdjustYScaleAggregated = QCheckBox('Adjust Y-axis scale in the group line plot when features are aggregated')       
        self.checkCodeSummary = QCheckBox('Use code for case summarization')       
        grpBehavior.layout().addWidget(self.checkAdjustYScaleAggregated)
        grpBehavior.layout().addWidget(self.checkLasagnaSorting)
        grpBehavior.layout().addWidget(self.checkOverwriteDB)
#         grpBehavior.layout().addWidget(self.checkCodeSummary)
        
        btnFrame = QFrame()
        btnFrame.setLayout(QHBoxLayout())
        
        btnRestore = QPushButton('Restore Defaults')
        btnRestore.clicked.connect(self.onBtnRestoreClicked)
        btnOK = QPushButton('OK')
        btnOK.clicked.connect(self.onBtnOKClicked)
        btnCancel = QPushButton('Cancel')
        btnCancel.clicked.connect(self.onBtnCancelClicked)
        
        btnFrame.layout().addWidget(btnRestore)
        btnFrame.layout().addWidget(QLabel(''))
        btnFrame.layout().addWidget(btnOK)
        btnFrame.layout().addWidget(btnCancel)
        btnFrame.layout().setStretch(0, 1)
        btnFrame.layout().setStretch(1, 20)
        btnFrame.layout().setStretch(2, 1)
        btnFrame.layout().setStretch(3, 1)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Raised)

        self.layout().addWidget(grpAppearance)
        self.layout().addWidget(grpBehavior)
        self.layout().addWidget(separator)
        self.layout().addWidget(btnFrame)
        self.layout().setStretch(0, 1)
        self.layout().setStretch(1, 1)
        self.layout().setStretch(2, 1)
        self.layout().setStretch(3, 1)
        
        self.populateSettings(self.config)
    
    def get_color_list(self):
        cmaps = [('Sequential',     ['binary', 'Blues', 'BuGn', 'BuPu', 'gist_yarg',
                             'GnBu', 'Greens', 'Greys', 'Oranges', 'OrRd',
                             'PuBu', 'PuBuGn', 'PuRd', 'Purples', 'RdPu',
                             'Reds', 'YlGn', 'YlGnBu', 'YlOrBr', 'YlOrRd']),
         ('Sequential (2)', ['afmhot', 'autumn', 'bone', 'cool', 'copper',
                             'gist_gray', 'gist_heat', 'gray', 'hot', 'pink',
                             'spring', 'summer', 'winter']),
         ('Diverging',      ['BrBG', 'bwr', 'coolwarm', 'PiYG', 'PRGn', 'PuOr',
                             'RdBu', 'RdGy', 'RdYlBu', 'RdYlGn', 'seismic']),
         ('Qualitative',    ['Accent', 'Dark2', 'hsv', 'Paired', 'Pastel1',
                             'Pastel2', 'Set1', 'Set2', 'Set3', 'spectral']),
         ('Miscellaneous',  ['gist_earth', 'gist_ncar', 'gist_rainbow',
                             'gist_stern', 'jet', 'brg', 'CMRmap', 'cubehelix',
                             'gnuplot', 'gnuplot2', 'ocean', 'rainbow',
                             'terrain', 'flag', 'prism'])]
        colors = cmaps[0][1] + cmaps[4][1] + cmaps[1][1] + cmaps[2][1] + cmaps[3][1]        
        return colors
            
    
    def populateSettings(self, config):
        self.checkHideNarrative.setChecked(config.toHideNarrative())
        self.checkHideSettings.setChecked(config.toHideSettings())
        self.comboxFontSize.setEditText(str(config.getFontSize()))
        self.checkAdjustYScaleAggregated.setChecked(config.toAdjustYScaleAggregated())
        self.checkOverwriteDB.setChecked(config.toOverwriteDB())
        self.checkLasagnaSorting.setChecked(config.toSortLasagna())
        self.checkHighlightTime.setChecked(config.toHighlightTime())
        
        self.comboxColorScheme.setCurrentIndex(self.colors.index(config.getColorScheme()))
        self.checkCodeSummary.setChecked(config.toCodeSummary())
            
    def onBtnOKClicked(self):
        
        if self.config.toHideNarrative() != self.checkHideNarrative.isChecked():
            self.config.toggleHideNarrative()
        if self.config.toHideSettings() != self.checkHideSettings.isChecked():
            self.config.toggleHideSettings()
            
        if self.config.toHighlightTime() != self.checkHighlightTime.isChecked():
            self.config.toggleTimeHighlight()     
            
        if self.config.toCodeSummary() != self.checkCodeSummary.isChecked():
            self.config.toggleCodingSummary()     
            
        if self.comboxColorScheme.currentText() != self.config.getColorScheme():        
            self.config.color_scheme = self.comboxColorScheme.currentText()
            grouptab = self.mainWindow.get_mainWindow_tab('Group Plot')
            if grouptab:
                grouptab.plot()
        
        try:
            fontsize = int(self.comboxFontSize.currentText())
        except:
            QMessageBox.critical(QMessageBox(), "ETHER", 'Font size invalid!')
            return    
        self.config.fontSize = fontsize
        
        self.config.adjustYScaleAggregated = self.checkAdjustYScaleAggregated.isChecked()
        self.config.overwriteDB = self.checkOverwriteDB.isChecked()
        self.config.sortLasagna = self.checkLasagnaSorting.isChecked()
        
        self.config.save_config()
        self.close()
        
    def onBtnRestoreClicked(self):
        config = SystemPreferences()
        config.setToDefaultConfiguration()
        self.populateSettings(config)
        
    def onBtnCancelClicked(self):
        self.close()
    
class FilterDialog(QDialog):
    def __init__(self, medDict, dateRange, strQuery = None, parent = None):
        super(FilterDialog, self).__init__(parent)
        self.setLayout(QVBoxLayout())
        self.setWindowTitle('Case Filter')
        self.medDict = medDict
        self.dateRange = dateRange
        
        self.frameQuery = QFrame()
        self.frameQuery.setLayout(QHBoxLayout())
        self.editQuery = QLineEdit()
        self.btnParseQueryString = QPushButton('Parse')
        self.btnParseQueryString.clicked.connect(self.onParseBtnClicked)
        self.frameQuery.layout().addWidget(self.editQuery)

        self.paramFrame = QGroupBox()
        self.paramFrame.setTitle('Builder')
        self.paramFrame.setLayout(QVBoxLayout())
        self.firstCriteriaRow = FilterCriteriaRow(self.medDict, True, self.dateRange, self)
        self.paramFrame.layout().addWidget(self.firstCriteriaRow)

        btnFrame = QFrame()
        btnFrame.setLayout(QHBoxLayout())
        
        # OK and Cancel buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok,
            Qt.Horizontal, self)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        
        btnAdd = QPushButton('Add')
        btnAdd.clicked.connect(self.onAddBtnClicked)
        
        btnFrame.layout().addWidget(btnAdd)
        btnFrame.layout().addWidget(QLabel(''))
        btnFrame.layout().addWidget(buttonBox)
        btnFrame.layout().setStretch(0, 1)
        btnFrame.layout().setStretch(1, 1)
        btnFrame.layout().setStretch(2, 10)
        btnFrame.layout().setStretch(3, 3)

        self.layout().addWidget(self.frameQuery)
        self.layout().addWidget(self.paramFrame)
        self.layout().addWidget(btnFrame)
        
        if strQuery:
            self.criteria = self.populate_query(strQuery)
        else:
            self.criteria = None
    
    def populate_query(self, strQuery):
        criteria = FilterDialog.parseQueryString(strQuery)
        self.firstCriteriaRow.populateFields(criteria[0])
        for c in criteria[1:]:
            newrow = FilterCriteriaRow(self.medDict, False, self.dateRange, self)
            newrow.populateFields(c)
            self.paramFrame.layout().addWidget(newrow)
        
        self.adjustSize()
        self.updateQuery()
        
    def updateQuery(self):
        s = ''
        for i in range(self.paramFrame.layout().count()): 
            if s=='':
                s += self.paramFrame.layout().itemAt(i).widget().getQuery()
            else:
                s += ' ' + self.paramFrame.layout().itemAt(i).widget().getQuery()
                
        self.editQuery.setText(s)
    
    def getQueryString(self):
        return self.editQuery.text()
    
    def deleteRow(self, rowWidget):
        index = self.paramFrame.layout().indexOf(rowWidget)
        item = self.paramFrame.layout().takeAt(index)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()    
                 
        self.adjustSize()
        self.updateQuery()
        
    def getCriteria(self):        
        return self.criteria
        
    def criteriaValidityCheck(self):
        for i in range(self.paramFrame.layout().count()): 
            msg = self.paramFrame.layout().itemAt(i).widget().validityCheck()
            if msg!='':
                QMessageBox.critical(QMessageBox(), "VaeTM", 'Query #' + str(i+1)+':'+ msg)
                return False
        return True
        
    def accept(self):
        if not self.criteriaValidityCheck():
            return
        
        strQuery = self.editQuery.text()   
        self.criteria = self.parseQueryString(strQuery)
        self.close()
        
    @staticmethod
    def parseQueryString(strQuery):
        criteria = []     
        if strQuery[:3]=='NOT':
            op1st = 'NOT '
            strQuery = strQuery[4:]
        else:
            op1st = 'AND '
            
        queries = re.split(' AND | OR | NOT ', strQuery)
        operators = re.findall(' AND | OR | NOT ', strQuery)
        operators = [op1st] + operators
        for i, query in enumerate(queries):
            query = query.strip()
            
            loctime = query.find('&')
            if loctime >-1:
                s = query[:loctime].strip()
                sTime =  query[loctime+1:].strip()
            else:
                s = query
                sTime = None
            
            fields = re.findall('\[(.*)\]', s)
            if not fields:
                field = 'ALL'
                feature = s
            else:
                field = fields[0]
                feature = s[:s.find('[')]
            
            tFrom = None
            tTo = None
            axis = None
            if sTime:
                axes = re.findall('Vax|Age|Date', sTime)
                if axes:
                    axis = axes[0]
                else:
                    continue
                
                sFrom = re.findall('(.*)\[From\]', sTime)
                if sFrom:
                    sTo = re.findall('\[From\](.*)\[To\]', sTime)
                else:
                    sTo = re.findall('(.*)\[To\]', sTime)
                
                if sFrom:
                    if axis=='Date':
                        tFrom = parse(sFrom[0])
                    else:
                        tFrom = int(sFrom[0])
                    
                if sTo:
                    if axis=='Date':
                        tTo = parse(sTo[0])
                    else:
                        tTo = int(sTo[0])
            
            if field in dictFeatureNames:
                field = dictFeatureNames[field]
            criterion = (operators[i].strip(), field, feature, tFrom, tTo, axis)
            criteria.append(criterion)
        
        return criteria
        
    def featureTypeChanged(self,comboxFeatureType, comboxFeature):
        comboxFeature.clear()
        featType = comboxFeatureType.currentText().lower()
        if featType in self.medDict:
            comboxFeature.addItems(self.medDict[featType])

    def onParseBtnClicked(self):
        self.populate_query(self.editQuery.text())
        
    def onAddBtnClicked(self):
        self.paramFrame.layout().addWidget(FilterCriteriaRow(self.medDict, False, self.dateRange, self))
        self.adjustSize()
        
    def AddNewRow(self):
        #row = self.paramFrame.layout().count()
        self.paramFrame.layout().addWidget(FilterCriteriaRow(self.medDict, False, self.dateRange, self))
        self.adjustSize()

class ReportLimitedFeatures(QGroupBox):
    def __init__(self, reports = [], parent=None):
        super(ReportLimitedFeatures, self).__init__(parent)
        
        self.reports = reports
        self.dict_reportID_index={}
        for i, report in enumerate(reports):
            self.dict_reportID_index[report['Report ID']] = i 
        
        self.mainWindow = parent
        
        self.setTitle("Total " + str(len(reports)) + " cases")
        self.setLayout(QVBoxLayout())
        
        #create tree/table to select documents
        self.feature_table = MouseToggleTreeWidget(self)
        self.feature_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.feature_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        ###: set header labels and specify column widths
        header = ['OriginalIndex', 'Flag', 'Index', 'Case ID', 'Age', 'Sex', 'Products', 'OnsetTimeSort', 'Calculated Onset', 'Diagnosis', 'Secondary Diagnosis', 'Medical History', 'Concomitant Medications', 'Mark']

        self.col_hidden_diagnosis = 0
        self.col_index = 2
        self.col_case_id = 3
        self.col_hidden_onset = 7
        self.col_calculated_onset = 8
        self.col_diagnosis = 10
        self.col_check_mark = 1
        self.col_hidden_mark = 13
        
        self.feature_table.setColumnCount(len(header))
        self.feature_table.setHeaderLabels(header)       
        self.feature_table.setColumnHidden(self.col_hidden_diagnosis, True)  
        self.feature_table.setColumnHidden(self.col_hidden_onset, True)
        self.feature_table.setColumnHidden(self.col_hidden_mark, True)

        self.feature_table.header().resizeSection(1,35)
        self.feature_table.header().resizeSection(2,40)
        self.feature_table.header().resizeSection(3,60)
        self.feature_table.header().resizeSection(4,60)
        self.feature_table.header().resizeSection(5,60)
        self.feature_table.header().resizeSection(6,150)
        self.feature_table.header().resizeSection(7,100)
        self.feature_table.header().resizeSection(8,150)
        self.feature_table.header().resizeSection(10,150)
        self.feature_table.header().setResizeMode(6, QHeaderView.Interactive)     
        self.feature_table.header().setResizeMode(7, QHeaderView.Interactive)     
        self.feature_table.header().setResizeMode(8, QHeaderView.Interactive)    
        
        #connect selection changed signal
        self.feature_table.itemSelectionChanged.connect(self.selection_changed)
        self.feature_table.itemClicked.connect(self.on_item_clicked)
        
        #insert reports into selector widget
        self.populate_reports()

        self.feature_table.setSortingEnabled(True)
        self.feature_table.sortItems(0, Qt.AscendingOrder)
        self.update_selected_report_indices()
        #self.feature_table.header().sectionClicked.connect(self.update_selected_report_indices)
        self.feature_table.header().sectionClicked.connect(self.header_clicked)
        self.feature_table.header().sectionPressed.connect(self.header_pressed)
        self.current_sorted_column = (-1, Qt.AscendingOrder)

        del_action = QAction("Delete", self) 
        del_action.setStatusTip("Delete selected report")
        del_action.setShortcut("Ctrl+D")
        del_action.triggered.connect(self.delete_reports)        
        self.feature_table.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.feature_table.addAction(del_action)
        
        frmCmd = QFrame()
        frmCmd.setLayout(QHBoxLayout())
        prompt = QLabel('*Onset time extracted from narrative, may be more or less reliable than that from fields.')        
        btnGroup = QPushButton('Group Plot...')
        btnGroup.clicked.connect(self.onGroupBtnClicked)
        btnGroup.setMaximumWidth(80)
        
        frmCmd.layout().addWidget(prompt)
        frmCmd.layout().addWidget(btnGroup)
        frmCmd.layout().setStretch(0,50)
        frmCmd.layout().setStretch(0,1)
        
        self.layout().addWidget(self.feature_table)
        self.layout().addWidget(frmCmd)
        
    def on_item_clicked(self, item, column):
        if column!=self.col_check_mark:
            return
        
        report = self.reports[self.dict_reportID_index[item.text(self.col_case_id)]]
        if item.checkState(column)==Qt.Checked:
            report['Mark'] = True
        else:
            report['Mark'] = False
      
        tab_feature = self.mainWindow.get_mainWindow_tab("Case Narrative && Features")
        if tab_feature:
            if item.checkState(column)==Qt.Checked:
                tab_feature.central.chkboxRevisit.setCheckState(Qt.Checked)
            else:
                tab_feature.central.chkboxRevisit.setCheckState(Qt.Unchecked)
                
        tab_medDRA = self.mainWindow.get_mainWindow_tab("MedDRA Terms")
        if tab_medDRA:
            if item.checkState(column)==Qt.Checked:
                tab_medDRA.central.chkboxRevisit.setCheckState(Qt.Checked)
            else:
                tab_medDRA.central.chkboxRevisit.setCheckState(Qt.Unchecked)
                
    def onGroupBtnClicked(self):
        if self.mainWindow.get_mainWindow_tab('Group Plot'):
            QMessageBox.critical(QMessageBox(), "ETHER", "A group plot already exists!")       
            return

        index = self.mainWindow.centralWidget().count()
        self.mainWindow.centralWidget().insertTab(index, ReportGroupAnalysisPlot(self.reports, self.mainWindow), 'Group Plot over Time')
        self.mainWindow.centralWidget().setCurrentIndex(index)
    
    def header_pressed(self, index):
        if index == self.col_index:
            self.pre_sorting_column = (self.feature_table.sortColumn(), self.current_sorted_column[1])
        
    def header_clicked(self, index):
        if index == self.col_index: ##: Sort with the last sorting column and order
            self.feature_table.sortItems(self.pre_sorting_column[0], self.pre_sorting_column[1])
        elif index == self.col_diagnosis: # Diagnosis
            if self.current_sorted_column[0] == self.col_diagnosis:
                if self.current_sorted_column[1] == Qt.AscendingOrder:
                    order = Qt.DescendingOrder
                else:
                    order = Qt.AscendingOrder
            else:
                order = Qt.DescendingOrder
                
            self.feature_table.sortItems(self.col_hidden_diagnosis, order)
            self.current_sorted_column = (self.col_diagnosis, order)
        elif index == self.col_calculated_onset: # Calculated Onset            
            if self.current_sorted_column[0]==self.col_calculated_onset:
                if self.current_sorted_column[1] == Qt.AscendingOrder:
                    order = Qt.DescendingOrder
                else:
                    order = Qt.AscendingOrder
            else:
                order = Qt.AscendingOrder
            self.feature_table.sortItems(self.col_hidden_onset, order)
            self.current_sorted_column = (self.col_calculated_onset, order)
        elif index == self.col_check_mark:
            for i in range(self.feature_table.topLevelItemCount()):
                item = self.feature_table.topLevelItem(i)
                if item.checkState(self.col_check_mark)==Qt.Checked:
                    item.setText(self.col_hidden_mark,'T')
                else:
                    item.setText(self.col_hidden_mark,'F')
                    
            if self.current_sorted_column[0] == self.col_check_mark:
                if self.current_sorted_column[1] == Qt.AscendingOrder:
                    order = Qt.DescendingOrder
                else:
                    order = Qt.AscendingOrder
            else:
                order = Qt.DescendingOrder
            self.feature_table.sortItems(self.col_hidden_mark, order)
            self.current_sorted_column = (self.col_check_mark, order)
        else:
            self.current_sorted_column = (index, self.feature_table.header().sortIndicatorOrder())
        
        for i in range(self.feature_table.topLevelItemCount()):
            item = self.feature_table.topLevelItem(i)
            item.setText(self.col_index,str(i+1))
        
        selected = self.feature_table.selectedItems()
        if selected:        
            current = selected[0]
            report_id = self.feature_table.indexOfTopLevelItem(current)
            if report_id < 0:
                report_id = 0
            report_index = report_id
        self.mainWindow.current_report = report_index
        
        self.update_selected_report_indices()
    
    def update_selected_report_indices(self):
        selected = []
        for i in range(self.feature_table.topLevelItemCount()):
            item = self.feature_table.topLevelItem(i)
            selected.append(self.dict_reportID_index[item.text(self.col_case_id)])
        del self.mainWindow.selectedReportIndices[:]
        self.mainWindow.selectedReportIndices = selected
        
    def delete_reports(self):
        selected = self.feature_table.selectedItems()
        if not selected:
            return
        
        minloc = 1e10
        for current in selected:
            report_idx = self.feature_table.indexOfTopLevelItem(current)
            del self.mainWindow.selectedReportIndices[report_idx]
            if report_idx < minloc:
                minloc = report_idx
                
        self.update_report_list()
        
        if minloc < len(self.mainWindow.selectedReportIndices):
            newid = self.mainWindow.selectedReportIndices[minloc]
            self.set_current_report(newid)
            self.selection_changed()
        
        self.mainWindow.data_all_action.setChecked(False)
        
    def populate_reports(self):
        for i, index in enumerate(self.mainWindow.selectedReportIndices):
            report = self.reports[index]
                        
            (strOnsetSort, strOnsetDisp) = util.ReportUtil.get_report_onset_time(report)
            features = report['Features']
            diagnosis = util.ReportUtil.getSummaryString([feat.getCleanString() for feat in features if feat.getType()=='DIAGNOSIS' or feat.getType()=='CAUSE_OF_DEATH'])
            diagnosis2nd = util.ReportUtil.getSummaryString([feat.getCleanString() for feat in features if feat.getType()=='SECOND_LEVEL_DIAGNOSIS'])
            
            mhx = '; '.join([feat.getString() for feat in features if feat.getType()=='MEDICAL_HISTORY'])
            medications = '; '.join(set([feat.getString() for feat in features if feat.getType()=='DRUG']))
            
            if report['Mark']:
                mark = 'T'
            else:
                mark = 'F'
            columns = [str(i).zfill(6), '', str(i+1), report['Report ID'], report['Age'], report['Gender'], report['Vaccines'], strOnsetSort, strOnsetDisp, diagnosis, diagnosis2nd, mhx, medications, mark]
            
            item = QTreeWidgetItem(self.feature_table, columns)
            if report['Mark']:
                item.setCheckState(self.col_check_mark, Qt.Checked)
            else:
                item.setCheckState(self.col_check_mark, Qt.Unchecked)
                
    def check_revisit_box(self, report_global_id):
        if not report_global_id in self.mainWindow.selectedReportIndices:
            return
        
        index = self.mainWindow.selectedReportIndices.index(report_global_id)
        item = self.feature_table.topLevelItem(index)
        if self.reports[report_global_id]['Mark']:
            item.setCheckState(self.col_check_mark, Qt.Checked)
        else:
            item.setCheckState(self.col_check_mark, Qt.Unchecked)
            
    def update_report_list(self):
        ##: set feature unsorted to avoid table being sorted everytime item is inserted
        self.feature_table.setSortingEnabled(False)
        root = self.feature_table.invisibleRootItem()
        child_count = root.childCount()
        rr = range(child_count)
        rr.reverse()
        for i in rr:
            root.removeChild(root.child(i))
        
        self.populate_reports()
        
        self.feature_table.setSortingEnabled(True)
        self.update_selected_report_indices()
        
        strFilters = '; '.join([ft for ft in self.mainWindow.filters_current])
        if strFilters:
            strFilters = ': ' + strFilters
        
        ncur = len(self.mainWindow.selectedReportIndices)
        nall = len(self.mainWindow.reports)
        if ncur == nall:
            s0 = "Total " + str(nall) + " cases" 
        else:
            s0 = str(ncur) + " out of " + str(nall) + " cases"
            
        self.setTitle(s0 + strFilters)
        
    def set_current_report(self, current_report):
        report_id = self.reports[current_report]['Report ID']
        items = self.feature_table.findItems(report_id, Qt.MatchExactly, self.col_case_id)
        if len(items) > 0:
            self.feature_table.setCurrentItem(items[0])
    
    def selection_changed(self):
        selected = self.feature_table.selectedItems()
        if not selected:
            return
        
        current = selected[0]
        report_id = self.feature_table.indexOfTopLevelItem(current)
        if report_id < 0:
            report_id = 0
        report_index = report_id

        if self.isVisible():
            self.mainWindow.set_current_report(report_index)
            
    def save_report_marks(self):
        for i in range(self.feature_table.topLevelItemCount()):
            item = self.feature_table.topLevelItem(i)
            report_global_index = self.mainWindow.selectedReportIndices[i]
            report = self.reports[report_global_index]
            if item.checkState(self.col_check_mark)==Qt.Checked:
                report['Mark'] = True
            else:
                report['Mark'] = False

class ReportText(QGroupBox):
    def __init__(self, reports = [], parent=None, hiTimex=False, searchable = False, showLabText = False, researchMode = False):
        super(ReportText, self).__init__(parent)
        
        self.reports = reports
        self.tabTextAndFeature = parent
        self.parent = parent
        self.highlightTimex = hiTimex
        self.showLabText = showLabText
        self.searchText = searchable
        self.researchMode = researchMode
        
        self.setLayout(QVBoxLayout())
        
        if len(self.reports)>=0 and self.showLabText:
            self.report_text = QTextEdit(self.reports[0]['Lab Text'], self, readOnly=True)
            self.setTitle("Lab Test")
        else:
            self.report_text = QTextEdit(self.reports[0]['Free Text'], self, readOnly=True)
            self.setTitle("Narrative")
        
        if self.researchMode:
            self.annotations = self.tabTextAndFeature.mainWindow.sysPreferences.getAnnotationSettings()
            categories = self.annotations['Category']
            self.report_text.setContextMenuPolicy(Qt.ActionsContextMenu)
            for cate in categories:
                tags = self.annotations[cate]
                for tag in tags:
                    actionTag = QAction(tag, self) 
                    actionTag.triggered.connect(lambda: self.annotate_text(tag))
                    self.report_text.addAction(actionTag)
                    
                menu_separator = QAction(self)
                menu_separator.setSeparator(True)
                self.report_text.addAction(menu_separator)

        self.layout().addWidget(self.report_text)
        self.layout().setStretch(0,50)
        
        self.editFinder = QLineEdit()
        if self.searchText:
            self.layout().addWidget(self.editFinder)
            self.layout().setStretch(2,1)
            if self.showLabText:
                self.editFinder.setPlaceholderText('Search Lab Tests')
            else:
                self.editFinder.setPlaceholderText('Search Narrative')
            self.editFinder.textChanged.connect(self.onSearchTextChanged)
            
#        self.report_text.setStyleSheet('selection-background-color: #3399FF');
        self.report_text.setStyleSheet('selection-background-color: #5CB3FF');
        
        self.feature_highlight_range = (0, 0)
        self.timexes_covered = []
    
    def annotate_text(self, tag):
        selectedText = self.report_text.textCursor().selectedText()
        posStart = self.report_text.textCursor().selectionStart()
        posEnd = self.report_text.textCursor().selectionEnd()
        self.tabTextAndFeature.annotation_table.add_annotation([selectedText, posStart, posEnd])
    
    def onSearchTextChanged(self):
        s = self.editFinder.text()
        current_cursor = self.report_text.textCursor()
        extraSelections = []
        self.report_text.moveCursor(QTextCursor.Start)
        while self.report_text.find(s):
            extra = QTextEdit.ExtraSelection()
            extra.cursor = self.report_text.textCursor()
            #extra.format.setBackground(Qt.blue)
            extra.format.setBackground(QColor('#306EFF'))
            extraSelections.append(extra)

        self.report_text.setExtraSelections(extraSelections)
        self.report_text.setTextCursor(current_cursor)

        
    def set_current_report(self, current_report):
        if  current_report < 0 or current_report > len(self.reports):
            self.report_text.setText('')
            return
        
        self.current_report = current_report
        if self.showLabText:            
            self.report_text.setText(self.reports[current_report]['Lab Text'])
        else:
            self.report_text.setText(self.reports[current_report]['Free Text'])
        
        self.clear_highlight()
        if self.highlightTimex:
            self.highlight_timxes()
        
        self.onSearchTextChanged()
                
    def highlight_timxes(self):
        fmt = QTextCharFormat()            
        cursor = QTextCursor(self.report_text.document())
            
        fmt.setBackground(Qt.yellow)
        if 'Timexes' in self.reports[self.current_report]:          
            timexes = self.reports[self.current_report]['Timexes']
            for t, start, end, dt in timexes:
                cursor.setPosition(start)
                cursor.setPosition(end+1, QTextCursor.KeepAnchor)
                cursor.setCharFormat(fmt)
    
    def highlight_feature_text(self, pstart, pend):
        self.clear_current_feature_highlight()
        
        #prepare to highlight current sentence
        doc = self.report_text.document()
        cursor = QTextCursor(doc)
        cf = QTextCharFormat()
        
        ##: Highlight
        cursor.setPosition(pstart)
        cursor.setPosition(pend, QTextCursor.KeepAnchor)            
        cf.setBackground(QColor('#d3d3d3'))
        cursor.setCharFormat(cf)            
        self.report_text.setTextCursor(cursor)
        
        ##: Save the current feature and covered timex location
        self.feature_highlight_range = (pstart, pend)
        self.timexes_covered = []
        if 'Timexes' in self.reports[self.current_report]:          
            timexes = self.reports[self.current_report]['Timexes']
            for t, start, end, dt in timexes:
                if (start>=pstart and start<=pend) or (end>=pstart and end<=pend):
                    self.timexes_covered.append((start, end))
    
    def clear_current_feature_highlight(self):
        fmt = QTextCharFormat()            
        cursor = QTextCursor(self.report_text.document())
#             
        ##: Clear the highlight of the current feature
        fmt.setBackground(Qt.white)
        cursor.setPosition(self.feature_highlight_range[0])
        cursor.setPosition(self.feature_highlight_range[1], QTextCursor.KeepAnchor)
        cursor.setCharFormat(fmt)
        
        ##: Redraw timex highlight covered by the current feature
        fmt.setBackground(Qt.yellow)
        for (tstart, tend) in self.timexes_covered:
            cursor.setPosition(tstart)
            cursor.setPosition(tend, QTextCursor.KeepAnchor)
            cursor.setCharFormat(fmt)
        
    def clear_highlight(self):
        fmt = QTextCharFormat()            
        cursor = QTextCursor(self.report_text.document())

        text = self.report_text.toPlainText()
        fmt.setBackground(Qt.white)
        cursor.setPosition(0)
        cursor.setPosition(len(text), QTextCursor.KeepAnchor)
        cursor.setCharFormat(fmt)
    
    def update_setting_highlight(self, toHighlightTime):
        self.highlightTimex = toHighlightTime
        if self.highlightTimex:
            self.highlight_timxes()
        else:
            self.clear_highlight()
        
    def highlight_text_segment(self, istart, iend, fmt=None):
        text = self.report_text.toPlainText()
        if istart>=0 and iend<=len(text):
            if not fmt:
                fmt = QTextCharFormat()        
                fmt.setBackground(Qt.yellow)    
            cursor = QTextCursor(self.report_text.document())

            cursor.setPosition(istart)
            cursor.setPosition(iend, QTextCursor.KeepAnchor)
            cursor.setCharFormat(fmt)

class ButtonLineEdit(QLineEdit):
    buttonClicked = Signal()

    def __init__(self, iconimg, parent=None, mode=''):
        super(ButtonLineEdit, self).__init__(parent)

        self.button = QToolButton(self)
        self.button.setIcon(QIcon(iconimg))
        self.button.setStyleSheet('border: 0px; padding: 0px;')
        self.button.setCursor(Qt.ArrowCursor)
        self.button.clicked.connect(self.buttonClicked.emit)

        frameWidth = self.style().pixelMetric(QStyle.PM_DefaultFrameWidth)
        buttonSize = self.button.sizeHint()

        self.setStyleSheet('QLineEdit {padding-right: %dpx; }' % (buttonSize.width() + frameWidth + 1))
        self.setMinimumSize(max(self.minimumSizeHint().width(), buttonSize.width() + frameWidth*2 + 2),
                            max(self.minimumSizeHint().height(), buttonSize.height() + frameWidth*2 + 2))

        flags = mode.split('|')
        if 'read-only' in flags:
            self.setReadOnly(True)
            
    def resizeEvent(self, event):
        buttonSize = self.button.sizeHint()
        frameWidth = self.style().pixelMetric(QStyle.PM_DefaultFrameWidth)
        self.button.move(self.rect().right() - frameWidth - buttonSize.width(),
                         (self.rect().bottom() - buttonSize.height() + 1)/2)
        super(ButtonLineEdit, self).resizeEvent(event)
        
class CalendarDialog(QDialog):
    def __init__(self, curDate, parent=None):
        super(CalendarDialog, self).__init__(parent)
        self.setLayout(QVBoxLayout())
        self.setWindowTitle("Select a Date")
        self.calendar = QCalendarWidget(self)
        self.calendar.setSelectedDate(curDate)
        self.layout().addWidget(self.calendar)
    
        # OK and Cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout().addWidget(buttons)

    def getDate(self):
        return self.calendar.selectedDate()    
                            
class ReportFeatures_Evaluation(QGroupBox):
    def __init__(self, reports = [], parent=None, evaluation_mode = False):
        super(ReportFeatures_Evaluation, self).__init__(parent)
        
        self.reports = reports
        self.tabTextAndFeature = parent
        self.mainWindow = self.tabTextAndFeature.mainWindow
        
        self.setTitle("Extracted Information")
        
        self.setLayout(QVBoxLayout())
        self.feature_table = MouseToggleTreeWidget(self)
        self.feature_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.feature_table.setSelectionBehavior(QAbstractItemView.SelectRows)        
        self.feature_table.setHeaderLabels(['Sentence', 'Type', 'Feature Text', 'Date', 'Comment', 'FeatureID', 'Feedback'])
        self.feature_table.setColumnHidden(0, True)
        self.feature_table.setColumnHidden(5, True)
        self.feature_table.header().resizeSection(1,50)
        self.feature_table.header().resizeSection(2,350)
        self.feature_table.header().setResizeMode(2, QHeaderView.Interactive)
        self.feature_table.header().resizeSection(3,150)
        
        if not evaluation_mode:
            self.feature_table.setColumnHidden(4, True)
            self.feature_table.setColumnHidden(6, True)
        else:
            self.feature_table.header().resizeSection(6,40)
            annotation_action = QAction("Annotate", self) 
            annotation_action.setStatusTip("Annotate selected feature")
            annotation_action.triggered.connect(self.annotate_text)        
            self.feature_table.setContextMenuPolicy(Qt.ActionsContextMenu)
            self.feature_table.addAction(annotation_action)
        
        self.feature_table.setSortingEnabled(True)

        self.layout().addWidget(self.feature_table)          
        self.allFeatures = ["DIAGNOSIS", "CAUSE_OF_DEATH", "SECOND_LEVEL_DIAGNOSIS", "SYMPTOM", 
                       "RULE_OUT", "MEDICAL_HISTORY", "FAMILY_HISTORY", "DRUG", "VACCINE"]
        s = '<html><b>pDx</b></html>:Primary Diagnosis; ' \
            + '<html><b>CoD</b></html>:Cause of Death; ' \
            + '<html><b>sDx</b></html>:Second Level Diagnosis; ' \
            + '<html><b>SYM</b></html>:Symptom; ' \
            + '<html><b>R/O</b></html>:Rule out; ' \
            + '<html><b>MHx</b></html>:Medical History; ' \
            + '<html><b>FHx</b></html>:Family History; ' \
            + '<html><b>Tx</b></html>:Drug; ' \
            + '<html><b>VAX</b></html>:Vaccine' 
        labelAbr = QLabel(s)
        labelAbr.setWordWrap(True)
        self.layout().addWidget(self.feature_table)       
        self.layout().addWidget(labelAbr)  
        self.layout().setStretch(0, 20)
        self.layout().setStretch(1, 1)     
        
        self.existing_comment_feat_ids = []
        
    def annotate_text(self):
        item = self.feature_table.currentItem()
        
        featID = int(item.text(5))
        curFeat = self.reports[self.current_report]['Features'][featID]
        pstart = curFeat.getStartPos()
        pend = curFeat.getEndPos()
            
        strRow = [item.text(2), pstart, pend, item.text(1), '']
        self.tabTextAndFeature.annotation_table.add_annotation(strRow)
        
    def set_current_report(self, current_report):
        self.current_report = current_report
        
        self.feature_table.clear()
        if  current_report < 0 or current_report > len(self.reports):
            return
        
        features = self.reports[current_report]['Features']
        if not features:
            return
        
        self.existing_comment_feat_ids = []
        for (irow, feature) in enumerate(features):
            if not feature.getType() in self.allFeatures:
                continue
                 
            strRow = feature.getTableRow()
            treeitems = QTreeWidgetItem(self.feature_table, strRow)
            treeitems.setFlags(treeitems.flags()|Qt.ItemIsEditable)
            combo_box = QComboBox(self.feature_table)
            combo_box.addItems(['Match','Partial','Mismatch'])
            combo_box.setCurrentIndex(feature.getMatchlevel())
            combo_box.currentIndexChanged.connect(self.on_match_changed)
            self.feature_table.setItemWidget(treeitems, 6, combo_box)
            
            if strRow[4]!='' or int(strRow[6])!=0:
                featID = int(strRow[5])
                self.existing_comment_feat_ids.append(featID)

        self.feature_table.sortItems(5, Qt.AscendingOrder)        
    
    def on_match_changed(self):
        selected = self.feature_table.selectedItems()
        if not selected:
            return
        current = selected[0]
        self.feature_table.editItem(current, 4)#.openPersistentEditor(current, 4)            
        
    def update_feature_evaluation(self):
        comments = []
        for i in range(self.feature_table.topLevelItemCount()):
            item = self.feature_table.topLevelItem(i)
            comment = item.text(4)
            cbox = self.feature_table.itemWidget(item, 6)
            matchid = cbox.currentIndex()
            
            featID = int(item.text(5))
            
            if comment=='' and matchid==0 and featID not in self.existing_comment_feat_ids: 
                continue
            
            comments.append((featID, comment, matchid))
            
            self.reports[self.current_report]['Features'][featID].setComment(comment)
            self.reports[self.current_report]['Features'][featID].setMatchlevel(matchid)

        if len(comments) > 0:
            self.mainWindow.updateFeatureComment(self.reports[self.current_report]['Report ID'], comments)        
                        
class ReportAnnotation(QGroupBox):
    def __init__(self, reports = [], parent=None):
        super(ReportAnnotation, self).__init__(parent)
        
        self.reports = reports
        self.tabTextAndFeature = parent
        self.mainWindow = self.tabTextAndFeature.mainWindow
        
        self.setTitle("Annotation")
        
        self.setLayout(QVBoxLayout())
        self.annotation_table = MouseToggleTreeWidget(self)
        self.annotation_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.annotation_table.setSelectionBehavior(QAbstractItemView.SelectRows)        
        self.annotation_table.itemSelectionChanged.connect(self.selection_changed)

        self.annotation_table.setHeaderLabels(['AnnotationID', 'Feature Text', 'Feature Type', 'Error Type', 'Comment', 'StartPos', 'EndPos', 'FeatureID'])
        self.annotation_table.setColumnHidden(0, True)
        self.annotation_table.setColumnHidden(5, True)
        self.annotation_table.setColumnHidden(6, True)
        self.annotation_table.setColumnHidden(7, True)
        self.annotation_table.header().resizeSection(0,50)
        self.annotation_table.header().resizeSection(1,300)
        self.annotation_table.header().setResizeMode(1, QHeaderView.Interactive)
        self.annotation_table.header().resizeSection(2,80)
        self.annotation_table.header().resizeSection(3,160)
         
        frmButtons = QFrame()
        frmButtons.setLayout(QGridLayout())
        self.btnAdd = QPushButton('Add')
        self.btnAdd.setToolTip('Add an annotation')
        self.btnAdd.clicked.connect(self.add_annotation)
        self.btnDelete = QPushButton('Delete')
        self.btnDelete.setToolTip('Delete annotation')
        self.btnDelete.clicked.connect(self.delete_annotation)

        frmButtons.layout().addWidget(self.btnAdd, 0, 1) #  alignment = Qt.AlignRight)
        frmButtons.layout().addWidget(self.btnDelete, 0, 2) #alignment = Qt.AlignRight)
        frmButtons.layout().setColumnStretch(0,100)
        frmButtons.layout().setColumnStretch(1,1)
        frmButtons.layout().setColumnStretch(2,1)

        self.layout().addWidget(self.annotation_table)       
        self.layout().addWidget(frmButtons)   

        self.strFeatureTypes = ['pDx','CoD','sDx','SYM','R/O','MHx','FHx','Tx','VAX']
        self.strErrorTypes = ['','Product name incomplete', 'Product name missing', 'Feature text incomplete', 
                              'Medical term incomplete', 'Medical term incorrect', 'Medical term not extracted', 
                              'Feature text not extracted', 'Feature type & text missing']        
        self.previous_selected_idx = -1
    
    def add_annotation(self, inRow=None):            
        n = self.annotation_table.topLevelItemCount()
        typeID = 0
        if not inRow:
            strRow = [str(n+1), '', '', '', '', '']
        else:
            curPosStart = inRow[1]
            curPosEnd = inRow[2]
            s0 = inRow[0]
            featString = s0.strip(' .?-/,:')
            if len(featString)!=len(s0):
                sl = s0.lstrip(' .?-/,:')
                curPosStart += len(s0)-len(sl)
                sr = s0.rstrip(' .?-/,:')
                curPosEnd -= len(s0)-len(sr)
            if len(inRow)>3 and inRow[3] in self.strFeatureTypes:
                typeID = self.strFeatureTypes.index(inRow[3]) 
            
            strRow = [str(n+1), featString, typeID, '', '', str(curPosStart), str(curPosEnd)]
       
        treeitems = QTreeWidgetItem(self.annotation_table, strRow)
        treeitems.setFlags(treeitems.flags()|Qt.ItemIsEditable)
        combo_box = QComboBox(self.annotation_table)
        combo_box.addItems(self.strFeatureTypes)
        combo_box.setCurrentIndex(typeID)
        comboErrors = QComboBox(self.annotation_table)
        comboErrors.addItems(self.strErrorTypes)
        
        self.annotation_table.setItemWidget(treeitems, 2, combo_box)
        self.annotation_table.setItemWidget(treeitems, 3, comboErrors)
        
        if strRow[1]=='':
            self.annotation_table.editItem(treeitems, 1)    
    
    def delete_annotation(self):
        item = self.annotation_table.currentItem()
        if item:       
            idx = self.annotation_table.indexOfTopLevelItem(item)
            itm = self.annotation_table.takeTopLevelItem(idx)
            del itm
                
    def set_current_report(self, current_report):
        self.current_report = current_report
        
        self.annotation_table.clear()
        if  current_report < 0 or current_report > len(self.reports):
            return
        
        report = self.reports[current_report] 
        if not 'Annotations' in report:
            return
        
        annotations = self.reports[current_report]['Annotations']
        if not annotations:
            return
        
        for (irow, annt) in enumerate(annotations):
            if annt[5]:
                strRow = [str(annt[0]), annt[1], annt[2], annt[3], annt[4], str(annt[5]), str(annt[6]), str(annt[7])]
            else:
                strRow = [str(annt[0]), annt[1], annt[2], annt[3], annt[4], '', '', str(annt[7])]
                
            treeitems = QTreeWidgetItem(self.annotation_table, strRow)
            treeitems.setFlags(treeitems.flags()|Qt.ItemIsEditable)
            combo_box = QComboBox(self.annotation_table)
            combo_box.addItems(self.strFeatureTypes)
            combo_box.setCurrentIndex(annt[2])
            combo_box_error = QComboBox(self.annotation_table)
            combo_box_error.addItems(self.strErrorTypes)
            combo_box_error.setCurrentIndex(annt[3])
#             combo_box.currentIndexChanged.connect(self.on_featureType_changed)
            self.annotation_table.setItemWidget(treeitems, 2, combo_box)
            self.annotation_table.setItemWidget(treeitems, 3, combo_box_error)

    def selection_changed(self):
        selected = self.annotation_table.selectedItems()
        if not selected:
            return
         
        current = selected[0]
        if not current: 
            return

        if not current.text(5):
            return
        
        iStart = int(current.text(5))
        iEnd = int(current.text(6))
        fmt = QTextCharFormat()        
        fmt.setBackground(QColor('#5CB3FF'))
        
        self.tabTextAndFeature.text.highlight_text_segment(iStart, iEnd, fmt)  
              
        ##: Recover the highlight of the previous time string
        if self.previous_selected_idx>=0:
            item = self.annotation_table.topLevelItem(self.previous_selected_idx)
            if item.text(5):
                iStart = int(item.text(5))
                iEnd = int(item.text(6))
                fmt.setBackground(Qt.white)
                self.tabTextAndFeature.text.highlight_text_segment(iStart, iEnd, fmt)    
         
        self.previous_selected_idx = self.annotation_table.indexOfTopLevelItem(current)
        
    def update_annotation(self):
        annotations = []
        for i in range(self.annotation_table.topLevelItemCount()):
            item = self.annotation_table.topLevelItem(i)
            antID = int(item.text(0))
            featText = item.text(1)
            comment = item.text(4)
            cboxFeatType = self.annotation_table.itemWidget(item, 2)
            featTypeID = cboxFeatType.currentIndex()
            cboxErrorType = self.annotation_table.itemWidget(item, 3)
            errorID = cboxErrorType.currentIndex()
            if item.text(5):
                startPos = int(item.text(5))
                endPos = int(item.text(6))
            else:
                startPos = None
                endPos = None
            featID = int(item.text(7))
            annotations.append((antID, featText, featTypeID, errorID, comment, startPos, endPos, featID))
            
        self.reports[self.current_report]['Annotations']= annotations            
        if len(annotations) > 0:
            self.mainWindow.updateAnnotation(self.reports[self.current_report]['Report ID'], annotations)

class ReportTimeETHER(QGroupBox):
    def __init__(self, reports = [], parent=None):
        super(ReportTimeETHER, self).__init__(parent)
        
        self.reports = reports
        self.tabTextAndFeature = parent
        self.mainWindow = self.tabTextAndFeature.mainWindow
        
        self.setTitle("ETHER Time")
        
        self.setLayout(QVBoxLayout())
        #self.feature_table = QTreeWidget(self)
        self.annotation_table = MouseToggleTreeWidget(self)
        self.annotation_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.annotation_table.setSelectionBehavior(QAbstractItemView.SelectRows)        
        self.annotation_table.itemSelectionChanged.connect(self.selection_changed)

        self.annotation_table.setHeaderLabels(['AnnotationID', 'Time Text', 'Type', 'PosStart', 'Comment'])
        self.annotation_table.setColumnHidden(0, True)
        self.annotation_table.setColumnHidden(3, True)
        self.annotation_table.header().resizeSection(0,50)
        self.annotation_table.header().resizeSection(1,300)
        self.annotation_table.header().setResizeMode(1, QHeaderView.Interactive)
        self.annotation_table.header().resizeSection(2,80)
        self.annotation_table.header().resizeSection(3,100)

        self.layout().addWidget(self.annotation_table)       

        self.strTimeTypes = ['', 'Date', 'Relative', 'Duration', 'Weekday', 'Frequency', 'Age', 'Time']
        self.dictTimeTypes = {'DATE':'Date', 'REL':'Relative', 'DUR':'Duration', 'WEEKDAY':'Weekday', 'FRQ':'Frequency', 'AGE':'Age', 'TIME':'Time'}
        
        self.previous_selected_idx = -1
            
    def set_current_report(self, current_report):
        self.current_report = current_report
        
        self.annotation_table.clear()
        if  current_report < 0 or current_report > len(self.reports):
            return
        
        report = self.reports[current_report] 
        if not 'TimexDisplay' in report:
            timexList = timexan.get_timexes_for_evaluation(report['Free Text'])        
            report['TimexDisplay'] = timexList
        
        timexes = self.reports[current_report]['TimexDisplay']
        if not timexes:
            return
        
        for (irow, timex) in enumerate(timexes):
            strRow = [str(irow), timex.getString(), timex.getType(), str(timex.getStartPos()), '']
            treeitems = QTreeWidgetItem(self.annotation_table, strRow)

    def selection_changed(self):
        selected = self.annotation_table.selectedItems()
        if not selected:
            return
         
        current = selected[0]
        if not current: 
            return

        timeText = current.text(1)
        iStart = int(current.text(3))
        iEnd = iStart + len(timeText)
        fmt = QTextCharFormat()        
        fmt.setBackground(QColor('#5CB3FF'))
        
        self.tabTextAndFeature.text.highlight_text_segment(iStart, iEnd, fmt)  
              
        ##: Recover the highlight of the previous time string
        if self.previous_selected_idx>=0:
            item = self.annotation_table.topLevelItem(self.previous_selected_idx)
            if item:
                timeText = item.text(1)
                iStart = int(item.text(3))
                iEnd = iStart + len(timeText)
                self.tabTextAndFeature.text.highlight_text_segment(iStart, iEnd)    
        
        self.previous_selected_idx = self.annotation_table.indexOfTopLevelItem(current)
    
    def update_feature_evaluation(self):
        return
    
    def update_annotation(self):
        annotations = []
        for i in range(self.annotation_table.topLevelItemCount()):
            item = self.annotation_table.topLevelItem(i)
            antID = i
            timeText = item.text(1)
            posStart = int(item.text(3))
            comment = item.text(4)
            cboxTimeType = self.annotation_table.itemWidget(item, 2)
            typeID = cboxTimeType.currentIndex()
            
            annotations.append((antID, timeText, typeID, '', posStart, 0, comment))
                    
        self.reports[self.current_report]['TimeAnnotations']= annotations            
        if len(annotations) > 0:
            self.mainWindow.updateTimeAnnotation(self.reports[self.current_report]['Report ID'], annotations)     
            
class ReportTimeAnnotation(QGroupBox):
    def __init__(self, reports = [], parent=None):
        super(ReportTimeAnnotation, self).__init__(parent)
        
        self.reports = reports
        self.tabTextAndFeature = parent
        self.mainWindow = self.tabTextAndFeature.mainWindow
        
        self.setTitle("Annotation")
        
        self.setLayout(QVBoxLayout())
        self.annotation_table = MouseToggleTreeWidget(self)
        self.annotation_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.annotation_table.setSelectionBehavior(QAbstractItemView.SelectRows)        
        self.annotation_table.itemSelectionChanged.connect(self.selection_changed)

        self.annotation_table.setHeaderLabels(['AnnotationID', 'Time Text', 'Type', 'PosStart', 'Comment'])
        self.annotation_table.setColumnHidden(0, True)
        self.annotation_table.setColumnHidden(3, True)
        self.annotation_table.header().resizeSection(0,50)
        self.annotation_table.header().resizeSection(1,300)
        self.annotation_table.header().setResizeMode(1, QHeaderView.Interactive)
        self.annotation_table.header().resizeSection(2,80)
        self.annotation_table.header().resizeSection(3,100)
         
        frmButtons = QFrame()
        frmButtons.setLayout(QGridLayout())
        self.btnDelete = QPushButton('Delete')
        self.btnDelete.setToolTip('Delete annotation')
        self.btnDelete.clicked.connect(self.delete_annotation)
   
        frmButtons.layout().addWidget(self.btnDelete, 0, 2) #alignment = Qt.AlignRight)
        frmButtons.layout().setColumnStretch(0,100)
        frmButtons.layout().setColumnStretch(1,1)
        frmButtons.layout().setColumnStretch(2,1)

        self.layout().addWidget(self.annotation_table)       
        self.layout().addWidget(frmButtons)   

        self.strTimeTypes = ['', 'Date', 'Relative', 'Duration', 'Weekday', 'Frequency', 'Age', 'Time']
        self.previous_selected_idx = -1
    
    def add_annotation(self, inRow):
        ##: Validation check for time annotations
        curPosStart = inRow[1]
        curPosEnd = inRow[2]
        
        s0 = inRow[0]
        timeString = s0.strip(' .?-/,:')
        if len(timeString)!=len(s0):
            sl = s0.lstrip(' .?-/,:')
            curPosStart += len(s0)-len(sl)
            sr = s0.rstrip(' .?-/,:')
            curPosEnd -= len(s0)-len(sr)
        
        for i in range(self.annotation_table.topLevelItemCount()):
            item = self.annotation_table.topLevelItem(i)
            timeText = item.text(1)
            iStart = int(item.text(3))
            iEnd = iStart + len(timeText) - 1
            
            if (iStart>=curPosStart and iStart<=curPosEnd) or (iEnd>=curPosStart and iEnd<=curPosEnd) or (iStart<=curPosStart and iEnd>=curPosEnd):
                s = 'Overlaped with #' + str(i) +': "' + timeText + '". Either delete it or ignore the current annotation.'
                QMessageBox.critical(QMessageBox(), "ETHER", s)
                return
            
        n = self.annotation_table.topLevelItemCount()
        strRow =[str(n+1), timeString, 0, str(curPosStart), '']
        treeitems = QTreeWidgetItem(self.annotation_table, strRow)
        treeitems.setFlags(treeitems.flags()|Qt.ItemIsEditable)
        combo_box = QComboBox(self.annotation_table)
        combo_box.addItems(self.strTimeTypes)
        combo_box.setCurrentIndex(0) 
        self.annotation_table.setItemWidget(treeitems, 2, combo_box)        
        
        self.highlight_annotations()
    
    def delete_annotation(self):
        item = self.annotation_table.currentItem()
        if item:       
            idx = self.annotation_table.indexOfTopLevelItem(item)
            itm = self.annotation_table.takeTopLevelItem(idx)
            del itm
            if self.previous_selected_idx >= idx:
                self.previous_selected_idx -= 1
        
        self.tabTextAndFeature.text.clear_highlight()
        self.highlight_annotations()
            
    def set_current_report(self, current_report):
        self.current_report = current_report
        
        self.annotation_table.clear()
        if  current_report < 0 or current_report > len(self.reports):
            return
        
        report = self.reports[current_report] 
        if not 'Annotations' in report:
            return
        
        annotations = self.reports[current_report]['TimeAnnotations']
        if not annotations:
            return
        
        for (irow, annt) in enumerate(annotations):
            strRow = [str(annt[0]), annt[1], annt[2], str(annt[4]), annt[6]]
            treeitems = QTreeWidgetItem(self.annotation_table, strRow)
            treeitems.setFlags(treeitems.flags()|Qt.ItemIsEditable)
            combo_box = QComboBox(self.annotation_table)
            combo_box.addItems(self.strTimeTypes)
            combo_box.setCurrentIndex(annt[2])
            self.annotation_table.setItemWidget(treeitems, 2, combo_box)
            
        self.highlight_annotations()


    def selection_changed(self):
        selected = self.annotation_table.selectedItems()
        if not selected:
            return
         
        current = selected[0]
        if not current: 
            return

        timeText = current.text(1)
        iStart = int(current.text(3))
        iEnd = iStart + len(timeText)
        fmt = QTextCharFormat()        
#         fmt.setBackground(QColor('#d3d3d3'))
        fmt.setBackground(QColor('#5CB3FF'))
        
        self.tabTextAndFeature.text.highlight_text_segment(iStart, iEnd, fmt)  
              
        ##: Recover the highlight of the previous time string
        if self.previous_selected_idx>=0:
            item = self.annotation_table.topLevelItem(self.previous_selected_idx)
            if item:
                timeText = item.text(1)
                iStart = int(item.text(3))
                iEnd = iStart + len(timeText)
                self.tabTextAndFeature.text.highlight_text_segment(iStart, iEnd)    
        
        self.previous_selected_idx = self.annotation_table.indexOfTopLevelItem(current)

    def highlight_annotations(self):
                
        for i in xrange(self.annotation_table.topLevelItemCount()):
            item = self.annotation_table.topLevelItem(i)
            timeText = item.text(1)
            iStart = int(item.text(3))
            iEnd = iStart + len(timeText)
            
            self.tabTextAndFeature.text.highlight_text_segment(iStart, iEnd)
            
    def update_annotation(self):
        annotations = []
        for i in range(self.annotation_table.topLevelItemCount()):
            item = self.annotation_table.topLevelItem(i)
            antID = i
            timeText = item.text(1)
            posStart = int(item.text(3))
            comment = item.text(4)
            cboxTimeType = self.annotation_table.itemWidget(item, 2)
            typeID = cboxTimeType.currentIndex()
            
            annotations.append((antID, timeText, typeID, '', posStart, 0, comment))
                    
        self.reports[self.current_report]['TimeAnnotations']= annotations            
        if len(annotations) > 0:
            self.mainWindow.updateTimeAnnotation(self.reports[self.current_report]['Report ID'], annotations)                
        
class QColorButton(QPushButton):
    '''
    Custom Qt Widget to show a chosen color.

    Left-clicking the button shows the color-chooser, while
    right-clicking resets the color to None (no-color).    
    '''
    colorChanged = Signal()

    def __init__(self, *args, **kwargs):
        super(QColorButton, self).__init__(*args, **kwargs)

        self._color = None
        self.setMaximumWidth(32)
        self.pressed.connect(self.onColorPicker)

    def setColor(self, color):
        if color != self._color:
            self._color = color
            self.colorChanged.emit()

        if self._color:
            self.setStyleSheet("background-color: %s;" % self._color)
        else:
            self.setStyleSheet("")

    def color(self):
        return self._color

    def onColorPicker(self):
        '''
        Show color-picker dialog to select color.

        Qt will use the native dialog by default.

        '''
        dlg = QColorDialog(self)
        dlg.setStyleSheet("background-color: Window;");
        if self._color:
            dlg.setCurrentColor(QColor(self._color))

        if dlg.exec_():
            self.setColor(dlg.currentColor().name())

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            self.setColor(None)

        return super(QColorButton, self).mousePressEvent(e)
            
class ControlGroupBox(QGroupBox):
    def __init__(self, parent=None):
        super(ControlGroupBox, self).__init__(parent)
        self.tabAnnotation = parent
        self.mainWindow = self.tabAnnotation.mainWindow
        self.annotations = self.mainWindow.sysPreferences.getAnnotationSettings()
        
        self.setTitle('Control Panel')
        self.setLayout(QVBoxLayout())
        
        colors = ['yellow', 'red', 'skyblue', 'green', 'blue', 'cyan', 'magenta',  'gray', 'darkcyan',  'lightGray',
                  'lightblue', 'lightgreen',
                  'yellow', 'red', 'green', 'blue', 'cyan', 'magenta',  'gray', 'lightYellow',  'lightGray']
        
        self.treeTags = QTreeWidget()
        self.treeTags.setColumnCount(2)
        self.treeTags.header().hide()
        self.treeTags.header().resizeSection(0,200)
        self.treeTags.header().resizeSection(1,20)
        self.layout().addWidget(self.treeTags)
        
        self.treeTags.itemClicked.connect(self.on_item_clicked)
        
        categories = self.annotations['Category']
        count = 0
        self.topCategoryItems = []
        for cate in categories:
            topItem =  QTreeWidgetItem(self.treeTags, [cate, ''])
            self.topCategoryItems.append(topItem)
            topItem.setCheckState(0, Qt.Unchecked)
            tags = self.annotations[cate]
            for i, tag in enumerate(tags):
                tagItem = QTreeWidgetItem(topItem, [tag, ''])
                tagItem.setCheckState(0, Qt.Unchecked)
            
                cb = QColorButton(self.treeTags, '')
                ii = count%len(colors)
                count += 1
                cb.setColor(colors[ii])
                cb.setFixedSize(18, 18)
                self.treeTags.setItemWidget(tagItem, 1, cb)
                cb.colorChanged.connect(self.on_color_button_clicked)
        
                topItem.addChild(tagItem)
        
        grpPreAnn = QGroupBox('Pre-annotations')
        grpPreAnn.setLayout(QVBoxLayout())
        self.chkShowFeaturePreAnnotation = QCheckBox('Show feature pre-annotations')
        self.chkShowTimePreAnnotation = QCheckBox('Show time pre-annotations')
        self.chkShowFeaturePreAnnotation.clicked.connect(lambda: self.preAnnotation_clicked('Feature'))
        self.chkShowTimePreAnnotation.clicked.connect(lambda: self.preAnnotation_clicked('Time'))
        grpPreAnn.layout().addWidget(self.chkShowFeaturePreAnnotation)
        grpPreAnn.layout().addWidget(self.chkShowTimePreAnnotation)
        
        self.annotationClass = [''] + self.annotations['Feature']
        self.dictFeatureAbr = copy.deepcopy(dictFeatureAbr)
        for annt in self.annotationClass:
            if annt not in self.dictFeatureAbr:
                self.dictFeatureAbr[annt] = annt
        self.dictAbbr2Feat = dict((v,k) for k, v in self.dictFeatureAbr.iteritems())
        
    def preAnnotation_clicked(self, annotationType):
        self.tabAnnotation.update_pre_annotations(annotationType)
        
    def get_coloring_scheme(self):
        dictColoringScheme = {}
        for item in self.topCategoryItems:
            scheme = {}
            num = item.childCount()
            for i in range(num):
                child = item.child(i)
                if child.checkState(0)==Qt.Checked:
                    colorButton = self.treeTags.itemWidget(child, 1)
                    color = colorButton.color()
                    scheme[child.text(0)] = color
            dictColoringScheme[item.text(0)] = scheme
        
        return dictColoringScheme
    
    def on_item_clicked(self, item, column):
        if column != 0:
            return
        
        if item.text(0) in ['Feature', 'Time']:
            num = item.childCount()
            if item.checkState(0)==Qt.Checked:
                for i in range(num):
                    childItem = item.child(i)
                    childItem.setCheckState(0, Qt.Checked)
            else:
                for i in range(num):
                    childItem = item.child(i)
                    childItem.setCheckState(0, Qt.Unchecked)
        
        for item in self.topCategoryItems:
            num = item.childCount()
            unchecked = [item.child(i) for i in range(num) if item.child(i).checkState(0)==Qt.Unchecked]
            if len(unchecked)>0:
                item.setCheckState(0, Qt.Unchecked)
            else:
                item.setCheckState(0, Qt.Checked)

        self.tabAnnotation.text.show_all_highlights()
        
    def on_color_button_clicked(self):
        self.tabAnnotation.text.show_all_highlights()

class AnnotationTimeTableBox(QGroupBox):
    def __init__(self, reports = [], parent=None):
        super(AnnotationTimeTableBox, self).__init__(parent)
        
        self.reports = reports
        self.tabAnnotation = parent
        self.mainWindow = self.tabAnnotation.mainWindow
        self.annotationSettings = self.mainWindow.sysPreferences.getAnnotationSettings()
        self.annotationClass = [''] + self.annotationSettings['Time']
        self.class_ranks = {"Date":0, "Relative":8, "Duration":4, "Weekday":7, "Frequency":6, "Age":5, "Time":2, "Anchor":1, "Other":3, "":5}
        
        if 'TimeRelations' in self.annotationSettings:
            self.timeRelations = [''] + self.annotationSettings['TimeRelations']
        else:
            self.timeRelations = ['', "OVERLAP", "BEFORE", "AFTER", "BEFORE_OVERLAP", "AFTER_OVERLAP"]
        
        TimeAnnotation.types = self.annotationClass
        
        self.setTitle("Time Annotation")
        self.setLayout(QVBoxLayout())
        self.annotation_table = MouseToggleTreeWidget(self)
        self.annotation_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.annotation_table.setSelectionBehavior(QAbstractItemView.SelectRows)        
        self.annotation_table.itemSelectionChanged.connect(self.selection_changed)  
        self.annotation_table.itemClicked.connect(self.selection_changed)
        self.annotation_table.itemChanged.connect(self.on_table_item_changed)
        self.annotation_table.itemDoubleClicked.connect(self.onTreeWidgetItemDoubleClicked)
        self.annotation_table.setEditTriggers(self.annotation_table.NoEditTriggers)
        self.annotation_table.keyReleased.connect(self.on_key_released)

        self.header = ['TimeID', 'Time Text', 'StartPos', 'EndPos', 'Type', 'Date',  'RefID', "Relation", 'Comment']         
        self.headerIndex = dict([(h, i) for i, h in enumerate(self.header)]) 
        
        self.annotation_table.setHeaderLabels(self.header)
        self.annotation_table.setColumnHidden(self.columnIndex('StartPos'), True)
        self.annotation_table.setColumnHidden(self.columnIndex('EndPos'), True)

        self.annotation_table.header().resizeSection(0,60)
        self.annotation_table.header().resizeSection(1,130)
        self.annotation_table.header().setResizeMode(1, QHeaderView.Interactive)
        self.annotation_table.header().resizeSection(self.columnIndex('Date'),100)
#         self.annotation_table.header().resizeSection(self.columnIndex('Comment'),110)
        self.annotation_table.header().resizeSection(self.columnIndex('RefID'), 50)
        self.annotation_table.header().resizeSection(self.columnIndex('Relation'),120)
        
        self.annotation_table.setContextMenuPolicy(Qt.ActionsContextMenu)                    
        del_action = QAction("Delete Time", self.annotation_table) 
        del_action.setStatusTip("Delete the selected item")
        del_action.setShortcut("Alt+D")
        del_action.triggered.connect(self.delete_annotation)               
        del_link_action = QAction("Delete Link", self.annotation_table) 
        del_link_action.setStatusTip("Delete time-time link of the selected item")
        del_link_action.setShortcut("Alt+R")
        del_link_action.triggered.connect(self.delete_time2time_link)               
        link_action = QAction("Link time-time", self.annotation_table) 
        link_action.setStatusTip("Delete the selected item")
        link_action.setShortcut("Alt+L")
        link_action.triggered.connect(self.link_time2time)
        self.annotation_table.addAction(del_action)
        self.annotation_table.addAction(link_action)
        self.annotation_table.addAction(del_link_action)
        
        frmButtons = QFrame()
        frmButtons.setLayout(QGridLayout())
        self.btnSave = QPushButton('Save')
        self.btnSave.setToolTip('Save annotations')
        self.btnSave.clicked.connect(self.save_annotations)
        self.btnAdd = QPushButton('Add')
        self.btnAdd.setToolTip('Add an annotation')
        self.btnAdd.clicked.connect(self.on_btn_add_clicked)
        self.btnDelete = QPushButton('Delete Time')
        self.btnDelete.setToolTip('Delete annotation')
        self.btnDelete.clicked.connect(self.delete_annotation)        
        
        self.btnLink = QPushButton('Link Time-Time')
        self.btnLink.setToolTip('Link selected times')
        self.btnLink.clicked.connect(self.link_time2time)
        self.btnDeleteLink = QPushButton('Delete Link')
        self.btnDeleteLink.setToolTip('Delete Time-Time link')
        self.btnDeleteLink.clicked.connect(self.delete_time2time_link)
        
        self.chkShowPreAnnotation = QCheckBox('Time pre-annotations')
        self.chkShowPreAnnotation.clicked.connect(self.populate_pre_annotations)
        frmButtons.layout().addWidget(self.chkShowPreAnnotation, 0, 0) #  alignment = Qt.AlignRight)
        frmButtons.layout().addWidget(self.btnSave, 0, 1) #  alignment = Qt.AlignRight)
        frmButtons.layout().addWidget(self.btnAdd, 0, 2) #  alignment = Qt.AlignRight)
        frmButtons.layout().addWidget(self.btnDelete, 0, 3) #alignment = Qt.AlignRight)
        frmButtons.layout().addWidget(self.btnLink, 0, 4) #  alignment = Qt.AlignRight)
        frmButtons.layout().addWidget(self.btnDeleteLink, 0, 5) #  alignment = Qt.AlignRight)
        frmButtons.layout().setColumnStretch(0,100)
        frmButtons.layout().setColumnStretch(1,1)
        frmButtons.layout().setColumnStretch(2,1)        
        frmButtons.layout().setColumnStretch(3,1)        
        
        self.layout().addWidget(self.annotation_table)       
        self.layout().addWidget(frmButtons)   
        
        self.preAnnotations = []
        self.annotations = []

        self.previous_selected_idx = -1
    
    def columnIndex(self, h):
        return self.headerIndex[h]
    
    def on_key_released(self, event):
        if event.key()==Qt.Key_Up:
            self.selection_changed()         
        elif event.key()==Qt.Key_Down:
            self.selection_changed() 
        
    def on_table_item_changed(self, item, column):
        if column==self.columnIndex('RefID'):
            text = item.text(column)
            if text!='' and not re.match('^t\d+$', text):
                QMessageBox.critical(QMessageBox(), "ETHER", 'The time reference ID has to be a integer following letter "t"!')
                item.setText(column, '')
                return
        
        if column!=self.columnIndex('Time Text'):
            return
        
        pre_startPos = int(item.text(self.columnIndex('StartPos')))
        pre_endPos = int(item.text(self.columnIndex('EndPos')))
        narrative = self.reports[self.current_report]['Free Text']
        pre_text = narrative[pre_startPos:pre_endPos].lower()
        pre_tokens = nltk.word_tokenize(pre_text)
        
        text = item.text(self.columnIndex('Time Text'))
        text = text.rstrip(' .?-/,:').lower()
        tokens = nltk.word_tokenize(text)
        
        if not set(tokens).issubset(set(pre_tokens)):      
            ##: If new text is not within the initial range, enlarge search range to the sentences 
            ##: covering the original text       
            pos = narrative[pre_endPos:].find('. ')
            if pos<0:
                pre_endPos = len(narrative)
            else:
                pre_endPos = pre_endPos + pos
            
            pos = narrative[:pre_startPos].rfind('. ')
            if pos<0:
                pre_startPos = 0
            else:
                pre_startPos = pos + 2
            
            pre_text = narrative[pre_startPos:pre_endPos].lower()
                    
        (start_char_feat, end_char_feat) = util.find_sub_text_range(pre_text, text)
        startPos = pre_startPos + start_char_feat
        endPos = pre_startPos + end_char_feat
            
        self.annotation_table.blockSignals(True)
        item.setText(self.columnIndex('StartPos'), str(startPos))
        item.setText(self.columnIndex('EndPos'), str(endPos))
        self.annotation_table.blockSignals(False)
        
        idx = self.annotation_table.indexOfTopLevelItem(item)
        self.annotations[idx].setString(text)
        self.selection_changed()
        
    def onTreeWidgetItemDoubleClicked(self, item, column):
        if column==self.columnIndex('Comment') or column==self.columnIndex('RefID'):
            self.annotation_table.editItem(item, column)
        elif column==self.columnIndex('Time Text') and self.annotation_table.indexOfTopLevelItem(item) > 0:
            self.annotation_table.editItem(item, column)
            
    def link_time2time(self):
        selectedItems = self.annotation_table.selectedItems()
        if len(selectedItems) != 2:
            QMessageBox.critical(QMessageBox(), "ETHER", "There must be two time items selected!")
            return
        
        selectedItems.sort(key=lambda item:self.class_ranks[self.annotation_table.itemWidget(item, self.columnIndex('Type')).currentText()])
        
        itemRel = selectedItems[1]
        itemOther = selectedItems[0]
        
        tid = itemOther.text(self.columnIndex('TimeID')).strip('*')
        itemRel.setText(self.columnIndex('RefID'), tid)
        idx = self.annotation_table.indexOfTopLevelItem(itemRel)
        self.annotations[idx].setTimeID(int(tid.strip('t')))
        
    def delete_time2time_link(self):
        item = self.annotation_table.currentItem()
        if item:
            item.setText(self.columnIndex('RefID'), '')    
            cboxRel = self.annotation_table.itemWidget(item, self.columnIndex('Relation'))
            cboxRel.setCurrentIndex(0)
            
            idx = self.annotation_table.indexOfTopLevelItem(item)
            self.annotations[idx].setTimeID(-1)
            
    def on_btn_add_clicked(self):
        selectedText = self.tabAnnotation.text.report_text.textCursor().selectedText()
        posStart = self.tabAnnotation.text.report_text.textCursor().selectionStart()
        text, offset = util.strip_with_position(selectedText)
        tag = timexan.getTimexType4Annotation(text, [], [])
                
        self.tabAnnotation.add_annotation(text, posStart + offset, tag)
        
    def add_annotation(self, selectedText = None, posStart = None, tag = None, posEnd = None, strDate = None):            
        n = self.annotation_table.topLevelItemCount()
        typeID = 0
        ncol = len(self.header)
        if not selectedText:
            return
        
        if tag in self.annotationClass:
            typeID = self.annotationClass.index(tag) 
        else:
            print "Tag is not one of annotation classes! Something is Wrong!"
            assert False
        
        curPosStart = posStart
        s0 = selectedText
        timeString = s0.strip(' .?-/,:')
        if len(timeString)!=len(s0):
            sl = s0.lstrip(' .?-/,:')
            curPosStart += len(s0)-len(sl)
        
        if strDate:
            sdt = strDate
        elif tag=='Date':
            dt = self.tabAnnotation.mainWindow.parse_time_string(timeString)
            if dt:
                sdt = dt.isoformat().split('T')[0]
            else:
                sdt = ''
        else:
            sdt = ''
        
        if not posEnd:
            curPosEnd = curPosStart+len(timeString)
        else:
            curPosEnd = posEnd
        
        ##: Find proper index to insert
        idx = len(self.annotations)
        for i, annt in enumerate(self.annotations):
            pStart, pEnd = annt.getPositions()
            if pStart == curPosStart:
                if pEnd > curPosEnd:
                    idx = i
                else:
                    idx = i + 1
            elif pStart >= curPosStart:
                idx = i
                break
        
        annotation = TimeAnnotation((idx+1, timeString, typeID, sdt, curPosStart, curPosEnd, 0, '', -1, ''))
        self.annotations.insert(idx, annotation)
        
        timeID2update = []
        for i, annt in enumerate(self.annotations):
            if annt.getID() != i:
                timeID2update.append((annt.getID(), i))
                annt.setID(i)

        self.tabAnnotation.feature_table.update_timeIDs(timeID2update)

        strRow = annotation.getTableRow()             
        treeitem = QTreeWidgetItem(strRow)
        self.annotation_table.insertTopLevelItem(idx, treeitem)
        treeitem.setFlags(treeitem.flags()|Qt.ItemIsEditable)
            
        combo_box = QComboBox(self.annotation_table)
        combo_box.addItems(self.annotationClass)
        combo_box.setCurrentIndex(annotation.getTypeIndex())
        self.annotation_table.setItemWidget(treeitem, self.columnIndex('Type'), combo_box)
             
        edit_date = ButtonLineEdit('./calendar.ico', self.annotation_table, 'date')
        edit_date.setText(strRow[self.columnIndex('Date')])
        edit_date.buttonClicked.connect(lambda dft = self.reports[self.current_report]['Exposure Date'], editbox=edit_date: 
                                            self.btnDateClicked(editbox, dft))
        self.annotation_table.setItemWidget(treeitem, self.columnIndex('Date'), edit_date)   
        
        combo_rel = QComboBox(self.annotation_table)
        combo_rel.addItems(self.timeRelations)
        combo_rel.setCurrentIndex(self.timeRelations.index(annt.getTimeRelation()))
        self.annotation_table.setItemWidget(treeitem, self.columnIndex('Relation'), combo_rel)
                   
        combo_box.currentIndexChanged.connect(lambda event, itm=treeitem, cb = combo_box: self.on_timeType_changed(event, itm, cb))
          
        self.annotation_table.setCurrentItem(treeitem)
        
        for i in range(idx+1, len(self.annotations)):
            antid = self.annotations[i].getID()
            
            item = self.annotation_table.topLevelItem(i)
            sID = item.text(self.columnIndex('TimeID'))
            s = 't' + str(antid)
            if sID[-1]=='*':
                s += '*'
            item.setText(self.columnIndex('TimeID'), s)
    
    def delete_annotation(self, item=None):
        if not item:
            item = self.annotation_table.currentItem()
            
        timeID2update = []        
        if item:       
            idx = self.annotation_table.indexOfTopLevelItem(item)
            if idx==0:  ##: Exposure Date
                return
            
            sID = item.text(self.columnIndex('TimeID'))
            antID = int(sID.strip('t*'))
            itm = self.annotation_table.takeTopLevelItem(idx)
            del itm
            del self.annotations[idx]
            timeID2update.append((antID, -1))
    
        for i in range(self.annotation_table.topLevelItemCount()):
            item = self.annotation_table.topLevelItem(i)
            sID = item.text(self.columnIndex('TimeID'))
            antID = int(sID.strip('t*'))
            if antID != i:
                sID = sID.replace(str(antID), str(i))
                item.setText(self.columnIndex('TimeID'), sID)
                self.annotations[i].setID(i)
                timeID2update.append((antID, i))
        
        self.tabAnnotation.feature_table.update_timeIDs(timeID2update)
        self.update_timeIDs(timeID2update)   

    def update_timeIDs(self, pairs):
        """ pairs in (newID, oldID)"""
        ids = dict(pairs)

        for i in range(self.annotation_table.topLevelItemCount()):
            item = self.annotation_table.topLevelItem(i)
            colTimeID = self.columnIndex('RefID')
            sid = item.text(colTimeID)
            if sid=='':
                continue
            tid = int(sid[1:])
            if tid in ids:
                newID = ids[tid]  
                if newID < 0: ##: Time ID deleted
                    cboxRel = self.annotation_table.itemWidget(item, self.columnIndex('Relation'))
                    cboxRel.setCurrentIndex(0)        
                    item.setText(colTimeID, '')   
                else:
                    item.setText(colTimeID, 't'+str(newID))           
        
    def set_current_report(self, current_report):
        self.current_report = current_report
        
        self.annotation_table.clear()
        if  current_report < 0 or current_report > len(self.reports):
            return
        
        report = self.reports[current_report]
        
        if not 'Annotations' in report:
            return
        
        self.annotations = self.reports[current_report]['TimeAnnotations']
        if len(self.annotations)==0 or self.annotations[0].getString()!='EXPOSURE DATE':
            expDate = report['Exposure Date']
            if not expDate:
                expDate = timexan.parse_time_string(report['Date of Exposure'])
                
            if expDate:
                strExpDate = expDate.isoformat().split('T')[0]
            else:
                strExpDate = ''
            annt = TimeAnnotation((0, 'EXPOSURE DATE', 'Date', strExpDate, 0, 0, 0, '', -1, ''))
            self.annotations = [annt] + self.annotations
        
        self.annotations_pre = copy.deepcopy(self.annotations)

        self.draw_annotation_table()
        
        self.chkShowPreAnnotation.setChecked(False)
        
        self.isModified = False
    
    def get_pre_annotations_old(self):
        text = self.reports[self.current_report]['Free Text']
        timexes = self.reports[self.current_report]['Timexes']
        rel_signals = timexan.relTimeSignals
        strTimes = [t[0] for t in timexes]
        
        sentences = util.sentence_tokenize(text)
        locStart = 0
        types = []
        for sentence in sentences:
            locEnd = locStart + len(sentence)
            strTimes = [t[0] for t in timexes if locStart<=t[1] and locEnd>=t[1]]
            (words, locs) = util.tokenize_with_reserved_strings(sentence, strTimes)
            
            for i, loc in enumerate(locs):
                pre3 = [p for p in range(loc-3, loc) if p>=0]
                next2 = [p for p in range(loc+1, loc+3) if p<len(words)]
                previous3Words = [words[p] for p in pre3]
                next2Words = [words[p] for p in next2]
                tp = timexan.getTimexType4Annotation(strTimes[i],  previous3Words, next2Words)
                
                if next2Words and (next2Words[0] in rel_signals or next2Words[0].split('-')[0] in rel_signals):
                    info = (tp, '', next2Words[0])
                elif previous3Words and previous3Words[-1] in rel_signals:
                    info = (tp, previous3Words[-1], '')
                else:
                    info = (tp, '', '')
                    
                types.append(info)
            
            locStart = locEnd + 1
        
        num = len(self.annotations) + 1
        preAnnotations = []
        for i, t in enumerate(timexes):
            tp = types[i][0]
            timeString = t[0]
            posStart = t[1]
            sdt = ''
            if t[3]!= '':
                dt = self.tabAnnotation.mainWindow.parse_time_string(t[3])
                if dt:
                    sdt = dt.isoformat().split('T')[0]
                    
            if tp =='Relative':
                if types[i][2]!='':
                    timeString += ' ' + types[i][2]
                elif types[i][1]!='':
                    timeString = types[i][1] + ' ' + timeString 
                    posStart = posStart - len(types[i][1]) -1

            annt = TimeAnnotation((num, timeString, tp, sdt, posStart, posStart + len(timeString), 0, ''))
            
            if self.is_annotation_existing(annt, self.annotations) >= 0:
                continue
            
            annt.setPreAnnotation(True)
            preAnnotations.append(annt)
            num += 1
        
        return preAnnotations
    
    def get_pre_annotations(self):
        text = self.reports[self.current_report]['Free Text']
        timexes = self.reports[self.current_report]['Timexes']        
        rel_signals = ['before','after','prior','later','earlier','post','ago','next', 'following', 'until']    
        
        num = len(self.annotations) + 1
        preAnnotations = []
        for i, t in enumerate(timexes):
            timeString, posStart, posEnd, dtime = t
            previous3Words, next2Words = util.find_neighboring_words(text, posStart, posEnd, 3, 2)
            ttype = timexan.getTimexType4Annotation(t[0],  previous3Words, next2Words)
            
            if ttype =='Relative':
                if next2Words and (next2Words[0] in rel_signals or next2Words[0].split('-')[0] in rel_signals):
                    timeString += ' ' + next2Words[0]
                elif previous3Words and previous3Words[-1] in rel_signals:
                    timeString = previous3Words[-1] + ' ' + timeString 
                    posStart = posStart - len(previous3Words[-1]) -1
                    
            sdt = ''
            if dtime!= '':
                dt = self.tabAnnotation.mainWindow.parse_time_string(dtime)
                if dt:
                    sdt = dt.isoformat().split('T')[0]
                    
            annt = TimeAnnotation((num, timeString, ttype, sdt, posStart, posStart + len(timeString), 0, '', -1, ''))
            
            if self.is_annotation_existing(annt, self.annotations) >= 0:
                continue
            
            annt.setPreAnnotation(True)
            preAnnotations.append(annt)
            num += 1
        
        return preAnnotations
    
    def draw_annotation_table(self):
        self.annotation_table.blockSignals(True)
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        
        self.annotation_table.clear()     
        
        for annt in self.annotations:
            strRow = annt.getTableRow()             
                
            treeitems = QTreeWidgetItem(self.annotation_table, strRow)
            treeitems.setFlags(treeitems.flags()|Qt.ItemIsEditable)
            
            combo_box = QComboBox(self.annotation_table)
            combo_box.addItems(self.annotationClass)
            combo_box.setCurrentIndex(annt.getTypeIndex())
            self.annotation_table.setItemWidget(treeitems, self.columnIndex('Type'), combo_box)
             
            edit_date = ButtonLineEdit('./calendar.ico', self.annotation_table, 'date')
            edit_date.setText(strRow[self.columnIndex('Date')])
            edit_date.buttonClicked.connect(lambda dft = self.reports[self.current_report]['Exposure Date'], 
                                                editbox = edit_date, at = annt: 
                                            self.btnDateClicked(editbox, dft, at))
            self.annotation_table.setItemWidget(treeitems, self.columnIndex('Date'), edit_date)   
                   
            combo_rel = QComboBox(self.annotation_table)
            combo_rel.addItems(self.timeRelations)
            combo_rel.setCurrentIndex(self.timeRelations.index(annt.getTimeRelation()))
            self.annotation_table.setItemWidget(treeitems, self.columnIndex('Relation'), combo_rel)
            
            combo_box.currentIndexChanged.connect(lambda event, itm=treeitems, cb = combo_box: self.on_timeType_changed(event, itm, cb))
        
        self.annotation_table.blockSignals(False)        
        QApplication.restoreOverrideCursor()    

    def on_timeType_changed(self, index, item, cb):
        if item:       
            idx = self.annotation_table.indexOfTopLevelItem(item)
            self.annotations[idx].setType(cb.currentText())
    
        self.tabAnnotation.text.show_all_highlights()
    
    def btnDateClicked(self, editbox, defautDate, annotation):
        
        date_pre = editbox.text()
        if date_pre=='':
            curDate = defautDate
        else:
            curDate = parse(editbox.text())
            
        dialog = CalendarDialog(curDate)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            selectedDate = dialog.getDate()
            txt = selectedDate.toString('yyyy-MM-dd')
            editbox.setText(txt)
            
            if txt!=date_pre:
                self.isModified = True
                annotation.setDate(txt)
    
    def is_annotation_existing(self, newAnnt, annotations):
        (startPos, endPos) = newAnnt.getPositions()
        
        for i, annt in enumerate(annotations):
            (iStart, iEnd) = annt.getPositions()
            if iStart >= startPos and iStart <= endPos:
                return i
            elif iEnd >= startPos and iEnd <= endPos:
                return i
            elif iStart <= startPos and iEnd >= endPos:
                return i
            elif iStart >= startPos and iEnd <= endPos:
                return i
        
        return -1            
    
    def merge_annotations_by_positions(self, annotations1, annotations2):
        annotations = []
        p1 = 0
        p2 = 0
        n1 = len(annotations1)
        n2 = len(annotations2)
        while True:
            if annotations1[p1].getStartPos() < annotations2[p2].getStartPos():
                annotations.append(annotations1[p1])
                p1 += 1
            elif annotations1[p1].getStartPos() > annotations2[p2].getStartPos():
                annotations.append(annotations2[p2])
                p2 += 1
            else:
                if annotations1[p1].getPositions()[1] > annotations2[p2].getPositions()[1]:
                    annotations.append(annotations2[p2])
                    p2 += 1
                else:
                    annotations.append(annotations1[p1])
                    p1 += 1
            
            if p1==n1 or p2==n2:
                break
        
        annotations += annotations1[p1:n1] + annotations2[p2:n2]
        
        timeID2update = []
        for i, annt in enumerate(annotations):
            if annt.getID() != i:
                timeID2update.append((annt.getID(), i))
                annt.setID(i)
        
        self.tabAnnotation.feature_table.update_timeIDs(timeID2update)   
            
        return annotations 
    
    def populate_pre_annotations(self, flag=True):
        flag = self.chkShowPreAnnotation.isChecked()
        if flag==True:
            num = self.annotation_table.topLevelItemCount()      
            
            ##: Check if pre-annotations already populated  
            for i in range(num):
                item = self.annotation_table.topLevelItem(i)
                if '*' in item.text(0):
                    return
            
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            preAnnotations = self.get_pre_annotations()
            QApplication.restoreOverrideCursor()    
            
            self.annotations = self.merge_annotations_by_positions(self.annotations, preAnnotations)

            self.draw_annotation_table()
                
        else:
            ids = range(self.annotation_table.topLevelItemCount())
            ids.reverse()
            for i in ids:
                item = self.annotation_table.topLevelItem(i)
                if '*' in item.text(0):
                    self.delete_annotation(item)
                    
        self.tabAnnotation.text.show_all_highlights()
        
    def selection_changed(self):
        selected = self.annotation_table.selectedItems()
        if not selected:
            return
         
        current = selected[0]
        if not current: 
            return
        
        colPos = self.columnIndex('StartPos')
        colPosEnd = self.columnIndex('EndPos')
        if not current.text(colPos):
            return
        
        iStart = int(current.text(colPos))
        iEnd = int(current.text(colPosEnd))
        
        self.tabAnnotation.text.highlight_annotation_selection(iStart, iEnd, 'Time')
        self.tabAnnotation.text.show_all_highlights()
    
    def save_annotations(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))

        annotations = []
        for i in range(self.annotation_table.topLevelItemCount()):
            item = self.annotation_table.topLevelItem(i)
            sID = item.text(self.columnIndex('TimeID'))
            antID = int(sID.strip('t*'))
            item.setText(self.columnIndex('TimeID'), sID.strip('*'))
            
            timeText = item.text(self.columnIndex('Time Text'))
            comment = item.text(self.columnIndex('Comment'))
            
            cboxTimeType = self.annotation_table.itemWidget(item, self.columnIndex('Type'))
            typeID = cboxTimeType.currentIndex()
            
            strStartPos = item.text(self.columnIndex('StartPos'))
            if strStartPos:
                startPos = int(strStartPos)
            else:
                startPos = None
            
            strEndPos = item.text(self.columnIndex('EndPos'))
            if strEndPos:
                endPos = int(strEndPos)
            else:
                endPos = None
            
            tID = item.text(self.columnIndex('RefID'))
            if tID=='':
                refID = None
            else:
                refID = int(tID.strip('t*'))
            cboxTimeRel = self.annotation_table.itemWidget(item, self.columnIndex('Relation'))
            rel = cboxTimeRel.currentText()
            
            btnDate = self.annotation_table.itemWidget(item, self.columnIndex('Date'))
            strDate = btnDate.text()
            annotations.append(TimeAnnotation((antID, timeText, typeID, strDate, startPos, endPos, 0, comment, refID, rel)))
                        
        self.reports[self.current_report]['TimeAnnotations'] = annotations            
        self.mainWindow.updateTimeAnnotation(self.reports[self.current_report]['Report ID'], annotations)        
        
        self.annotations = annotations
        self.annotations_pre = copy.deepcopy(self.annotations)
        self.isModified = False
        
        QApplication.restoreOverrideCursor()    
        
    def discard_annotations(self):
        self.reports[self.current_report]['TimeAnnotations'] = self.annotations_pre
    
    def is_current_report_changed(self):
        if self.isModified==True:
            return True
        
        if len(self.annotations)!=len(self.annotations_pre):
            return True
        
        for i in range(len(self.annotations)):
            if not self.annotations[i]==self.annotations_pre[i]:
                return True
        
        return False        


class AnnotationFeatureTableBox(QGroupBox):
    def __init__(self, reports = [], parent=None):
        super(AnnotationFeatureTableBox, self).__init__(parent)
        
        self.reports = reports
        self.tabAnnotation = parent
        self.mainWindow = self.tabAnnotation.mainWindow
        self.annotationSettings = self.mainWindow.sysPreferences.getAnnotationSettings()
        self.annotationClass = [''] + self.annotationSettings['Feature']
        if 'TimeRelations' in self.annotationSettings:
            self.timeRelations = [''] + self.annotationSettings['TimeRelations']
        else:
            self.timeRelations = ['', "OVERLAP", "BEFORE", "AFTER", "BEFORE_OVERLAP", "AFTER_OVERLAP"]
        
        self.setTitle("Feature Annotation")
        self.setLayout(QVBoxLayout())
        self.annotation_table = MouseToggleTreeWidget(self)
        self.annotation_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.annotation_table.setSelectionBehavior(QAbstractItemView.SelectRows)        
        self.annotation_table.itemClicked.connect(self.selection_changed)
        self.annotation_table.itemChanged.connect(self.on_table_item_changed)
        self.annotation_table.keyReleased.connect(self.on_key_released)
        
        self.header = ['ID', 'Feature Text', 'StartPos', 'EndPos', 'Type', 'TimeID', 'Relation', 'Comment', 'FeatID']        
        self.headerIndex = dict([(h, i) for i, h in enumerate(self.header)]) 
        
        self.annotation_table.setHeaderLabels(self.header)
        self.annotation_table.setColumnHidden(self.columnIndex('StartPos'), True)
        self.annotation_table.setColumnHidden(self.columnIndex('EndPos'), True)
        self.annotation_table.setColumnHidden(self.columnIndex('FeatID'), True)

        self.annotation_table.header().resizeSection(0,60)
        self.annotation_table.header().resizeSection(1,200)
        self.annotation_table.header().setResizeMode(1, QHeaderView.Interactive)
        self.annotation_table.header().resizeSection(4,100)
        self.annotation_table.header().resizeSection(5,110)        
        self.annotation_table.header().resizeSection(self.columnIndex('Relation'),120)
        
        frmButtons = QFrame()
        frmButtons.setLayout(QGridLayout())
        self.btnSave = QPushButton('Save')
        self.btnSave.setToolTip('Save annotations')
        self.btnSave.clicked.connect(self.save_annotations)
        self.btnAdd = QPushButton('Add')
        self.btnAdd.setToolTip('Add an annotation')
        self.btnAdd.clicked.connect(self.on_btn_add_clicked)
        
        self.btnLink = QPushButton('Link Feature-Time')
        self.btnLink.setToolTip('Link feature to the current time')
        self.btnLink.clicked.connect(self.link_feature_time)
        frmButtons.layout().setColumnStretch(3,1)
            
        self.annotation_table.setContextMenuPolicy(Qt.ActionsContextMenu)                    
        del_action = QAction("Delete Feature", self.annotation_table) 
        del_action.setStatusTip("Delete the selected item")
        del_action.setShortcut("Shift+D")
        del_action.triggered.connect(self.delete_annotation)                
        del_link_action = QAction("Delete Link", self.annotation_table) 
        del_link_action.setStatusTip("Delete the feature-time link")
        del_link_action.setShortcut("Shift+R")
        del_link_action.triggered.connect(self.delete_feat_time_link)
        link_action = QAction("Link Feature-Time", self.annotation_table) 
        link_action.triggered.connect(self.link_feature_time)
        link_action.setStatusTip('Link feature to the current time')
        link_action.setShortcut("Shift+L")
        anchor_action = QAction("Tag as an anchor", self.annotation_table) 
        anchor_action.triggered.connect(self.tag_feature_time_anchor)
        anchor_action.setStatusTip('Tag this feature as an anchor')
        anchor_action.setShortcut("Shift+A")
        self.annotation_table.addAction(del_action)
        self.annotation_table.addAction(link_action)
        self.annotation_table.addAction(del_link_action)
        self.annotation_table.addAction(anchor_action)
        
        self.btnDeleteLink = QPushButton('Delete Link')
        self.btnDeleteLink.setToolTip('Delete Feature Time link')
        self.btnDeleteLink.clicked.connect(self.delete_feat_time_link)
        
        self.btnDelete = QPushButton('Delete Feature')
        self.btnDelete.setToolTip('Delete annotation')
        self.btnDelete.clicked.connect(self.delete_annotation)
        
        self.chkShowPreAnnotation = QCheckBox('Feature pre-annotations')
        self.chkShowPreAnnotation.clicked.connect(self.populate_pre_annotations)
        self.chkShowPostAnnotation = QCheckBox('Post-annotations')
        self.chkShowPostAnnotation.stateChanged.connect(self.populate_post_annotations)
        frmButtons.layout().addWidget(self.chkShowPreAnnotation, 0, 0) #  alignment = Qt.AlignRight)
        frmButtons.layout().addWidget(self.chkShowPostAnnotation, 0, 1) #  alignment = Qt.AlignRight)
        frmButtons.layout().addWidget(QLabel(''), 0, 2) #  alignment = Qt.AlignRight)
        frmButtons.layout().addWidget(self.btnSave, 0, 3) #  alignment = Qt.AlignRight)
        frmButtons.layout().addWidget(self.btnAdd, 0, 4) #  alignment = Qt.AlignRight)
        frmButtons.layout().addWidget(self.btnDelete, 0, 5) #alignment = Qt.AlignRight)
        frmButtons.layout().addWidget(self.btnLink, 0, 6) #alignment = Qt.AlignRight)
        frmButtons.layout().addWidget(self.btnDeleteLink, 0, 7) #alignment = Qt.AlignRight)
        frmButtons.layout().setColumnStretch(2,100)
        
        self.layout().addWidget(self.annotation_table)       
        self.layout().addWidget(frmButtons)   
        
        self.preAnnotations = []
        self.annotations = []
        
        self.dictFeatureAbr = copy.deepcopy(dictFeatureAbr)
        for annt in self.annotationClass:
            if annt not in self.dictFeatureAbr.values():
                self.dictFeatureAbr[annt] = annt
        self.dictAbbr2Feat = dict((v,k) for k, v in self.dictFeatureAbr.iteritems())
                
        self.previous_selected_idx = -1
    
    def columnIndex(self, h):
        return self.headerIndex[h]
    
    def on_key_released(self, event):
        if event.key()==Qt.Key_Up:
            self.selection_changed()         
        elif event.key()==Qt.Key_Down:
            self.selection_changed() 
        
    def link_feature_time(self):
        featItem = self.annotation_table.currentItem()
        if not featItem:
            QMessageBox.critical(QMessageBox(), "ETHER", "Please select a feature before create a feature-time link!")
            return
            
        selectedItems = self.tabAnnotation.timex_table.annotation_table.selectedItems()
        if len(selectedItems)==0:
            QMessageBox.critical(QMessageBox(), "ETHER", "Please select a time item before create a link to  feature!")
            return
        elif len(selectedItems)>1:            
            QMessageBox.critical(QMessageBox(), "ETHER", "Please select one time item one to create the feature-time link!")
            return
        else:
            timeItem = selectedItems[0]
            
        tid = timeItem.text(0)
        tid = tid.strip('*')
        
        if featItem.text(self.columnIndex('TimeID'))=='':        
            featItem.setText(self.columnIndex('TimeID'), tid)
            idx = self.annotation_table.indexOfTopLevelItem(featItem)
            self.annotations[idx].setTimeID(int(tid.strip('t')))
        elif featItem.text(self.columnIndex('TimeID'))==tid:
            QMessageBox.critical(QMessageBox(), "ETHER", "This link already exists!")
            return
        else:
            strRow = [featItem.text(i) for i in range(len(self.header))]
#             newitem = QTreeWidgetItem(self.annotation_table, strRow)
            newitem = QTreeWidgetItem(strRow)
            newitem.setFlags(newitem.flags()|Qt.ItemIsEditable)
            idx = self.annotation_table.indexOfTopLevelItem(featItem)
            self.annotation_table.insertTopLevelItem(idx+1, newitem)
            
            combo_box = QComboBox(self.annotation_table)
            combo_box.addItems(self.annotationClass)
            cboxFeatType = self.annotation_table.itemWidget(featItem, self.columnIndex('Type'))
            combo_box.setCurrentIndex(cboxFeatType.currentIndex())
            self.annotation_table.setItemWidget(newitem, self.columnIndex('Type'), combo_box)
             
            combo_rel = QComboBox(self.annotation_table)
            combo_rel.addItems(self.timeRelations)
            combo_rel.setCurrentIndex(0)
            self.annotation_table.setItemWidget(newitem, self.columnIndex('Relation'), combo_rel)
            combo_box.currentIndexChanged.connect(lambda event, itm=newitem, cb = combo_box: self.on_featType_changed(event, itm, cb))

            newitem.setText(self.columnIndex('TimeID'), tid)
            newAnnotation = copy.deepcopy(self.annotations[idx])
            newAnnotation.setTimeID(int(tid.strip('t*')))
            self.annotations.insert(idx+1, newAnnotation)
        
    def onTreeWidgetItemDoubleClicked(self, item, column):
        if column==self.columnIndex('Comment'):
            self.annotation_table.editItem(item, column)

    def on_table_item_changed(self, item, column):
        if column!=self.columnIndex('Feature Text'):
            return
        
        pre_startPos = int(item.text(self.columnIndex('StartPos')))
        pre_endPos = int(item.text(self.columnIndex('EndPos')))
        narrative = self.reports[self.current_report]['Free Text']
        pre_text = narrative[pre_startPos:pre_endPos].lower()
        pre_tokens = nltk.word_tokenize(pre_text)
        
        text = item.text(self.columnIndex('Feature Text')).lower()
        text = text.rstrip(' .?-/,:')
        tokens = nltk.word_tokenize(text)
        if not set(tokens).issubset(set(pre_tokens)):      
            ##: If new text is not within the initial range, enlarge search range to the sentences 
            ##: covering the original text       
            pos = narrative[pre_endPos:].find('. ')
            if pos<0:
                pre_endPos = len(narrative)
            else:
                pre_endPos = pre_endPos + pos
            
            pos = narrative[:pre_startPos].rfind('. ')
            if pos<0:
                pre_startPos = 0
            else:
                pre_startPos = pos + 2
            
            pre_text = narrative[pre_startPos:pre_endPos].lower()
                    
        (start_char_feat, end_char_feat) = util.find_sub_text_range(pre_text, text)
        startPos = pre_startPos + start_char_feat
        endPos = pre_startPos + end_char_feat
            
        self.annotation_table.blockSignals(True)
        item.setText(self.columnIndex('StartPos'), str(startPos))
        item.setText(self.columnIndex('EndPos'), str(endPos))
        self.annotation_table.blockSignals(False)
        
        idx = self.annotation_table.indexOfTopLevelItem(item)
        self.annotations[idx].setText(text)
        self.selection_changed()
        
    def on_btn_add_clicked(self):
        selectedText = self.tabAnnotation.text.report_text.textCursor().selectedText()
        posStart = self.tabAnnotation.text.report_text.textCursor().selectionStart()
        text, offset = util.strip_with_position(selectedText)
                
        self.add_annotation(text, posStart + offset, '')
    
    def tag_feature_time_anchor(self):
        
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        
        item = self.annotation_table.currentItem()
        ftext = item.text(self.columnIndex('Feature Text'))
        startPos = int(item.text(self.columnIndex('StartPos')))
        endPos = int(item.text(self.columnIndex('EndPos')))
                
        cboxFeatType = self.annotation_table.itemWidget(item, self.columnIndex('Type'))
        featType = self.dictAbbr2Feat[cboxFeatType.currentText()]
        strStartTime = ''
        if featType not in dictFeatureAbr:
            self.tabAnnotation.timex_table.add_annotation(ftext, startPos, 'Anchor', endPos, strStartTime)
            QApplication.restoreOverrideCursor()    
            return
        
        report = self.reports[self.current_report]
        
        if len(report['Report ID'].split('-')[0])<=6:
            reportType = 'vaers'
        else:
            reportType = 'faers'
        
        try:
            if self.mainWindow.extractor == None:
                self.mainWindow.extractor = textan.FeatureExtractor()
            (strStartTime, strEndTime) = self.mainWindow.extractor.extract_annotation_temporal(
                                        report['Free Text'], startPos, endPos, featType,
                                        report['Date of Exposure'], report['Date of Onset'], 
                                        report['Received Date'], reportType)
        except Exception as e:
            strStartTime = ''
        
        self.tabAnnotation.timex_table.add_annotation(ftext, startPos, 'Anchor', endPos, strStartTime)
            
        QApplication.restoreOverrideCursor()    
        
    def insert_annotations(self, annotation):  
        curPosStart, curPosEnd = annotation.getPositions()
        
        ##: Find proper index to insert
        idx = len(self.annotations)
        for i, annt in enumerate(self.annotations):
            pStart, pEnd = annt.getPositions()
            if pStart == curPosStart:
                if pEnd > curPosEnd:
                    idx = i
                else:
                    idx = i + 1
                break
            elif pStart >= curPosStart:
                idx = i
                break
        
        if idx==0:
            antid = 1
        else:
            antid = self.annotations[idx-1].getID()+1 
        
        annotation.setID(antid)
        self.annotations.insert(idx, annotation) 
                
        strRow = annotation.getTableRow()  
        treeitem = QTreeWidgetItem(strRow)
        self.annotation_table.insertTopLevelItem(idx, treeitem)
        treeitem.setFlags(treeitem.flags()|Qt.ItemIsEditable)
            
        combo_box = QComboBox(self.annotation_table)
        combo_box.addItems(self.annotationClass)
#         ftp = self.dictFeatureAbr[annotation.getType()]
        ftp = annotation.getType()
        combo_box.setCurrentIndex(self.annotationClass.index(ftp))
        self.annotation_table.setItemWidget(treeitem, self.columnIndex('Type'), combo_box)
             
        combo_rel = QComboBox(self.annotation_table)
        combo_rel.addItems(self.timeRelations)
        combo_rel.setCurrentIndex(self.timeRelations.index(annotation.getTimeRelation()))
        self.annotation_table.setItemWidget(treeitem, self.columnIndex('Relation'), combo_rel)
        
        combo_box.currentIndexChanged.connect(lambda event, itm=treeitem, cb = combo_box: self.on_featType_changed(event, itm, cb))

        self.annotation_table.setCurrentItem(treeitem)
        
        for i in range(idx+1, len(self.annotations)):
            antid = self.annotations[i].getID()
            self.annotations[i].setID(antid+1)
            
            item = self.annotation_table.topLevelItem(i)
            item.setText(self.columnIndex('ID'), self.annotations[i].getIDName())
        
    def add_annotation(self, selectedText = None, posStart = None, ftype = None):            
        n = self.annotation_table.topLevelItemCount()
        typeID = 0
        ncol = len(self.header)
        if not selectedText:
            return
        
        if ftype in self.annotationClass:
            typeID = self.annotationClass.index(ftype) 
        else:
            print "Tag is not one of annotation classes! Something is Wrong!"
            assert False
        
        curPosStart = posStart
        s0 = selectedText
        ftext = s0.strip(' .?-/,:')
        if len(ftext)!=len(s0):
            sl = s0.lstrip(' .?-/,:')
            curPosStart += len(s0)-len(sl)
        curPosEnd = curPosStart+len(ftext)

        ##: Find proper index to insert
        idx = len(self.annotations)
        for i, annt in enumerate(self.annotations):
            pStart, pEnd = annt.getPositions()
            if pStart == curPosStart:
                if pEnd > curPosEnd:
                    idx = i
                else:
                    idx = i + 1
                break
            elif pStart >= curPosStart:
                idx = i
                break
        
        if idx==0:
            antid = 1
        else:
            antid = self.annotations[idx-1].getID()+1 
        annotation = FeatureAnnotation((antid, ftext, ftype, '', '', curPosStart, curPosStart+len(ftext), -1, -1, ""))
        self.annotations.insert(idx, annotation) 
                
        strRow = annotation.getTableRow()  
        treeitem = QTreeWidgetItem(strRow)
        self.annotation_table.insertTopLevelItem(idx, treeitem)
        treeitem.setFlags(treeitem.flags()|Qt.ItemIsEditable)
            
        combo_box = QComboBox(self.annotation_table)
        combo_box.addItems(self.annotationClass)
        ftp = annotation.getType()
        combo_box.setCurrentIndex(self.annotationClass.index(ftp))
        self.annotation_table.setItemWidget(treeitem, self.columnIndex('Type'), combo_box)
             
        combo_rel = QComboBox(self.annotation_table)
        combo_rel.addItems(self.timeRelations)
        combo_rel.setCurrentIndex(self.timeRelations.index(annotation.getTimeRelation()))
        self.annotation_table.setItemWidget(treeitem, self.columnIndex('Relation'), combo_rel)
        
        combo_box.currentIndexChanged.connect(lambda event, itm=treeitem, cb = combo_box: self.on_featType_changed(event, itm, cb))

        self.annotation_table.setCurrentItem(treeitem)
        
        for i in range(idx+1, len(self.annotations)):
            antid = self.annotations[i].getID()
            self.annotations[i].setID(antid+1)
            
            item = self.annotation_table.topLevelItem(i)
            sID = item.text(self.columnIndex('ID'))
            s = 'f' + str(antid+1)
            if sID[-1]=='*':
                s += '*'
            item.setText(self.columnIndex('ID'), s)
        
        if self.chkShowPostAnnotation.isChecked():
            postAnnotations = self.get_post_annotations([annotation])
            for annt in postAnnotations:
                self.insert_annotations(annt)
            self.annotation_table.setCurrentItem(treeitem)
        
    def update_timeID(self, newID, oldID):
        if newID<0:
            tNewID = ''
        else:
            tNewID = 't' + str(newID)
        tOldID = 't' + str(oldID)
        for i in range(self.annotation_table.topLevelItemCount()):
            item = self.annotation_table.topLevelItem(i)
            colTimeID = self.columnIndex('TimeID')
            tid = item.text(colTimeID)
            if tid == tOldID:
                item.setText(colTimeID, tNewID)        
                if newID < 0: ##: Time ID deleted
                    cboxRel = self.annotation_table.itemWidget(item, self.columnIndex('Relation'))
                    cboxRel.setCurrentIndex(0)        
                    
    def update_timeIDs(self, pairs):
        """ pairs in (newID, oldID)"""
        ids = dict(pairs)
        
        for i in range(self.annotation_table.topLevelItemCount()):
            item = self.annotation_table.topLevelItem(i)
            colTimeID = self.columnIndex('TimeID')
            sid = item.text(colTimeID)
            if sid=='':
                continue
            tid = int(sid[1:])
            if tid in ids:
                newID = ids[tid]  
                if newID < 0: ##: Time ID deleted
                    cboxRel = self.annotation_table.itemWidget(item, self.columnIndex('Relation'))
                    cboxRel.setCurrentIndex(0)        
                    item.setText(colTimeID, '')   
                else:
                    item.setText(colTimeID, 't'+str(newID))   
    
    def delete_annotation(self, item = None):
        if not item:
            item = self.annotation_table.currentItem()
            
        if item:       
            idx = self.annotation_table.indexOfTopLevelItem(item)
            itm = self.annotation_table.takeTopLevelItem(idx)
            del itm
            del self.annotations[idx]
    
        for i in range(self.annotation_table.topLevelItemCount()):
            item = self.annotation_table.topLevelItem(i)
            sID = item.text(self.columnIndex('ID'))
            antID = int(sID.strip('f+*'))
            if antID != i+1:
                sID = sID.replace(str(antID), str(i+1))
                item.setText(self.columnIndex('ID'), sID)
                self.annotations[i].setID(i+1)
            
        self.tabAnnotation.text.show_all_highlights()
        
    def set_current_report(self, current_report):
        self.current_report = current_report
        
        self.annotation_table.clear()
        if  current_report < 0 or current_report > len(self.reports):
            return
        
        report = self.reports[current_report]
        
        if not 'Annotations' in report:
            return
        
        self.annotations = self.reports[current_report]['Annotations']
        self.annotations_pre = copy.deepcopy(self.annotations)

        self.draw_annotation_table()
        
        self.chkShowPreAnnotation.setChecked(False)
        self.chkShowPostAnnotation.setChecked(False)

    def delete_feat_time_link(self):
        item = self.annotation_table.currentItem()
        if item:
            item.setText(self.columnIndex('TimeID'), '')    
            
            cboxRel = self.annotation_table.itemWidget(item, self.columnIndex('Relation'))
            cboxRel.setCurrentIndex(0)
            
            idx = self.annotation_table.indexOfTopLevelItem(item)
            self.annotations[idx].setTimeID(-1)
    
    def has_post_annotations(self):
        """Find if there are post-annotations existing"""
        narrative = self.reports[self.current_report]['Free Text']
        narrative = narrative.lower()
        postAnnotations = []
        for annotation in self.annotations:
            seg = narrative[annotation.getStartPos():annotation.getEndPos()]
            rseg = re.escape(seg)
            matches = re.finditer(rseg, narrative)
            for m in matches:
                startPos = m.start()
                endPos = m.end()
                
                exists = False
                for annt in self.annotations + postAnnotations:
                    if annt.getStartPos()==startPos and annt.getEndPos()==endPos:
                        exists = True
                        break
                    
                if not exists:
                    return True
                
        return False
        
    def get_post_annotations(self, annotations):
        """Find strings that not annotated but the same text is annotated somewhere else."""
        narrative = self.reports[self.current_report]['Free Text']
        narrative = narrative.lower()
        postAnnotations = []
        for annotation in annotations:
            seg = narrative[annotation.getStartPos():annotation.getEndPos()]
            rseg = re.escape(seg)

            matches = re.finditer(rseg, narrative)
            for m in matches:
                startPos = m.start()
                endPos = m.end()
                
                exists = False
                for annt in self.annotations + postAnnotations:
                    if annt.getStartPos()==startPos and annt.getEndPos()==endPos:
                        exists = True
                        break
                    
                if not exists:
                    ##: (annotationID, ftext, ftype, ferror, comment, startPos, endPos, featID, timeID, timeRel)
                    newAnnt = FeatureAnnotation((-1, annotation.getText(), annotation.getType(), '', '', startPos, endPos, -1, -1, ''))
                    newAnnt.setPostAnnotation(True)
                    postAnnotations.append(newAnnt)
        
        postAnnotations.sort(key=lambda f:f.getStartPos())

        return postAnnotations
        
    def get_post_annotations_old(self):
        """Find strings that not annotated but the same text is annotated somewhere else."""
        narrative = self.reports[self.current_report]['Free Text']
        narrative = narrative.lower()
        postAnnotations = []
        for annotation in self.annotations:
            seg = narrative[annotation.getStartPos():annotation.getEndPos()]
            
            matches = re.finditer(seg, narrative)
            for m in matches:
                startPos = m.start()
                endPos = m.end()
                exists = False
                for annt in self.annotations:
                    if annt.getStartPos()==startPos and annt.getEndPos()==endPos:
                        exists = True
                        break
                if not exists:
                    ##: (annotationID, ftext, ftype, ferror, comment, startPos, endPos, featID, timeID, timeRel)
                    newAnnt = FeatureAnnotation((-1, annotation.getText(), annotation.getType(), '', '', startPos, endPos, -1, -1, ''))
                    newAnnt.setPreAnnotation(True)
                    postAnnotations.append(newAnnt)
        
        return postAnnotations
        
    def get_pre_annotations(self):
        narrative = self.reports[self.current_report]['Free Text']
        features = self.reports[self.current_report]['Features']
        
        num = len(self.annotations) + 1
        preAnnotations = []
        for feat in features:
            
            featType = feat.getType()
            antType = self.dictFeatureAbr[featType]
            splited = re.split(', | and ', feat.getString())
            if len(splited)==1:
                annt = FeatureAnnotation((num, feat.getString(), antType, '', '', feat.getStartPos(), 
                                      feat.getEndPos(), feat.getFeatureID(), None, ''))
                annt.setPreAnnotation(True)
                preAnnotations.append(annt)
                num += 1
                continue
                
            startPos = 0
            ftext = narrative[feat.getStartPos():feat.getEndPos()]
            fid = feat.getFeatureID()
            for seg in splited:
                (start_char_feat, end_char_feat) = util.find_sub_text_range(ftext[startPos:], seg)
                iStart = startPos + start_char_feat
                iEnd = startPos + end_char_feat
                annt = FeatureAnnotation((num, seg, antType, '', '', iStart + feat.getStartPos(), 
                                          iEnd + feat.getStartPos(), fid, None, ''))                
                annt.setPreAnnotation(True)
                preAnnotations.append(annt)
                num += 1
                startPos = iEnd + 1
                
        return preAnnotations
    
    def draw_annotation_table(self):
        self.annotation_table.blockSignals(True)
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        
        self.annotation_table.clear()        
        for annt in self.annotations:
            strRow = annt.getTableRow()             
                
            treeitem = QTreeWidgetItem(self.annotation_table, strRow)
            treeitem.setFlags(treeitem.flags()|Qt.ItemIsEditable)
            combo_box = QComboBox(self.annotation_table)
            combo_box.addItems(self.annotationClass)
            ftp = annt.getType()
            
            ##: This conversion is just for annotation type changes. It used to save feature full name, but now just tags defined in the preference.json. 
            ##: This is added to load in old annotation data in database. This won't be necessary for future ETHER versions.
            if ftp not in self.annotationClass:
                ftp = self.dictFeatureAbr[ftp]
                
            combo_box.setCurrentIndex(self.annotationClass.index(ftp))
            self.annotation_table.setItemWidget(treeitem, self.columnIndex('Type'), combo_box)
             
            combo_rel = QComboBox(self.annotation_table)
            combo_rel.addItems(self.timeRelations)
            combo_rel.setCurrentIndex(self.timeRelations.index(annt.getTimeRelation()))
            self.annotation_table.setItemWidget(treeitem, self.columnIndex('Relation'), combo_rel)

            combo_box.currentIndexChanged.connect(lambda event, itm=treeitem, cb = combo_box: self.on_featType_changed(event, itm, cb))

        self.annotation_table.blockSignals(False)
        QApplication.restoreOverrideCursor()    
        
    def on_featType_changed(self, index, item, cb):
        if item:       
            idx = self.annotation_table.indexOfTopLevelItem(item)
            self.annotations[idx].setType(cb.currentText())
    
        self.tabAnnotation.text.show_all_highlights()
    
    def is_annotation_existing(self, newAnnt, annotations):
        (startPos, endPos) = newAnnt.getPositions()
        
        for i, annt in enumerate(annotations):
            (iStart, iEnd) = annt.getPositions()
            if iStart >= startPos and iStart <= endPos:
                return i
            elif iEnd >= startPos and iEnd <= endPos:
                return i
            elif iStart <= startPos and iEnd >= endPos:
                return i
            elif iStart >= startPos and iEnd <= endPos:
                return i
        
        return -1            
    
    def merge_annotations_by_positions(self, annotations1, annotations2):
        annotations = []
        p1 = 0
        p2 = 0
        n1 = len(annotations1)
        n2 = len(annotations2)
        while p1<n1 and p2<n2:
            if annotations1[p1].getStartPos() < annotations2[p2].getStartPos():
                annotations.append(annotations1[p1])
                p1 += 1
            elif annotations1[p1].getStartPos() > annotations2[p2].getStartPos():
                annotations.append(annotations2[p2])
                p2 += 1
            else:
                if annotations1[p1].getPositions()[1] > annotations2[p2].getPositions()[1]:
                    annotations.append(annotations2[p2])
                    p2 += 1
                else:
                    annotations.append(annotations1[p1])
                    p1 += 1
            
        
        annotations += annotations1[p1:n1] + annotations2[p2:n2]
        for i, annt in enumerate(annotations):
            annt.setID(i+1)
            
        return annotations 
        
    def populate_pre_annotations(self, flag=True):
        flag = self.chkShowPreAnnotation.isChecked()
        if flag==True:
            num = self.annotation_table.topLevelItemCount()      
            
            ##: Check if pre-annotations already populated  
            for i in range(num):
                item = self.annotation_table.topLevelItem(i)
                if '*' in item.text(0):
                    return
            
            preAnnotations = self.get_pre_annotations()

            self.annotations = self.merge_annotations_by_positions(self.annotations, preAnnotations)
            
            if self.chkShowPostAnnotation.isChecked():
                postAnnotations = self.get_post_annotations(self.annotations)
                self.annotations = self.merge_annotations_by_positions(self.annotations, postAnnotations)
            
            self.draw_annotation_table()
        else:
            ids = range(self.annotation_table.topLevelItemCount())
            ids.reverse()
            for i in ids:
                item = self.annotation_table.topLevelItem(i)
                if '*' in item.text(0):
                    self.delete_annotation(item)
                    
        self.tabAnnotation.text.show_all_highlights()
                     
                     
    def populate_post_annotations(self, flag=True):
        flag = self.chkShowPostAnnotation.isChecked()
        if flag==True:
            num = self.annotation_table.topLevelItemCount()      
            
            postAnnotations = self.get_post_annotations(self.annotations)
            self.annotations = self.merge_annotations_by_positions(self.annotations, postAnnotations)

            self.draw_annotation_table()
        else:
            ids = range(self.annotation_table.topLevelItemCount())
            ids.reverse()
            for i in ids:
                item = self.annotation_table.topLevelItem(i)
                if '+' in item.text(0):
                    self.delete_annotation(item)
                    
        self.tabAnnotation.text.show_all_highlights()

    def selection_changed(self):
        selected = self.annotation_table.selectedItems()
        if not selected:
            return
         
        current = selected[0]
        if not current: 
            return
        
        iStart = int(current.text(self.columnIndex('StartPos')))
        iEnd = int(current.text(self.columnIndex('EndPos')))
        
        self.tabAnnotation.text.highlight_annotation_selection(iStart, iEnd, 'Feature')
        self.tabAnnotation.text.show_all_highlights()
    
    def save_annotations(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        
        has_link = False
        annotations = []
        for i in range(self.annotation_table.topLevelItemCount()):
            item = self.annotation_table.topLevelItem(i)
            sID = item.text(self.columnIndex('ID'))
            antID = int(sID.strip('f*+'))
            item.setText(self.columnIndex('ID'), sID.strip('*+'))
            
            tID = item.text(self.columnIndex('TimeID'))
            if tID=='':
                timeID = None
            else:
                timeID = int(tID.strip('t*'))
                has_link = True                
            
            ftext = item.text(self.columnIndex('Feature Text'))
            comment = item.text(self.columnIndex('Comment'))
            
            cboxFeatType = self.annotation_table.itemWidget(item, self.columnIndex('Type'))
            ftype = cboxFeatType.currentText()
            
            cboxTimeRel = self.annotation_table.itemWidget(item, self.columnIndex('Relation'))
            rel = cboxTimeRel.currentText()
            
            strStartPos = item.text(self.columnIndex('StartPos'))
            if strStartPos:
                startPos = int(strStartPos)
            else:
                startPos = None
            
            strEndPos = item.text(self.columnIndex('EndPos'))
            if strEndPos:
                endPos = int(strEndPos)
            else:
                endPos = None
                            
            featID = int(item.text(self.columnIndex('FeatID')))
            
            record = (antID, ftext, ftype, '', comment, startPos, endPos, featID, timeID, rel)
            annotations.append(FeatureAnnotation(record))
        
        self.reports[self.current_report]['Annotations'] = annotations            

        self.mainWindow.updateFeatureAnnotation(self.reports[self.current_report]['Report ID'], annotations)        

        self.annotations = annotations
        self.annotations_pre = copy.deepcopy(self.annotations)
    
        QApplication.restoreOverrideCursor()    
        
        if has_link and self.tabAnnotation.timex_table.is_current_report_changed():
            self.tabAnnotation.timex_table.save_annotations()
            QMessageBox.critical(QMessageBox(), "ETHER", "Time annotations have also been saved to ensure\
            feature-time links are valid!")
        
    def discard_annotations(self):
        self.reports[self.current_report]['Annotations'] = self.annotations_pre
    
    def is_current_report_changed(self):
        if len(self.annotations)!=len(self.annotations_pre):
            return True
        
        for i in range(len(self.annotations)):
            if not self.annotations[i]==self.annotations_pre[i]:
                return True
        
        return False        
            
                        
class AnnotationReportText(QGroupBox):
    def __init__(self, reports = [], parent=None, hiTimex=False, showLabText = False, inAnnotationTab = False):
        super(AnnotationReportText, self).__init__(parent)
        
        if inAnnotationTab:
            self.tabAnnotation = parent
        else:
            self.tabTextAndFeature = parent
        self.parent = parent
        self.mainWindow = self.parent.mainWindow
        self.reports = reports
        self.highlightTimex = hiTimex
        self.showLabText = showLabText
        self.searchText = True
        self.inAnnotationTab = inAnnotationTab
            
        self.setLayout(QVBoxLayout())

        self.report_text = QTextEdit(self.reports[0]['Free Text'], self, readOnly=True)
        self.setTitle("Narrative")
        
        self.annotationTags = self.parent.mainWindow.sysPreferences.getAnnotationSettings()
        if self.inAnnotationTab: ##: Used in Annotation Tab
            categories = self.annotationTags['Category']
            self.report_text.setContextMenuPolicy(Qt.ActionsContextMenu)
            for cate in categories:
                tags = self.annotationTags[cate]
                for tag in tags:
                    if tag=='Anchor':
                        continue
                    actionTag = QAction(tag, self) 
                    actionTag.triggered.connect(lambda t=tag: self.annotate_text(t))
                    self.report_text.addAction(actionTag)
                    
                menu_separator = QAction(self)
                menu_separator.setSeparator(True)
                self.report_text.addAction(menu_separator)
        else: ##: Used in Feature&Narrative Tab
            tags = self.annotationTags['Summarization']
            self.report_text.setContextMenuPolicy(Qt.ActionsContextMenu)
            for tag in tags:
                actionTag = QAction(tag, self) 
                actionTag.triggered.connect(lambda t=tag: self.annotate_text(t))
                self.report_text.addAction(actionTag)

        self.layout().addWidget(self.report_text)
        self.layout().setStretch(0,50)
        
        self.editFinder = QLineEdit()
        if self.searchText:
            self.layout().addWidget(self.editFinder)
            self.layout().setStretch(2,1)
            self.editFinder.setPlaceholderText('Search Narrative')
            self.editFinder.textChanged.connect(self.onSearchTextChanged)

        self.report_text.setStyleSheet('selection-background-color: #5CB3FF');
        
        self.feature_highlight_range = (0, 0)
        self.time_highlight_range = (0, 0)
        self.timexes_covered = []
    
    def annotate_text(self, tag):
        selectedText = self.report_text.textCursor().selectedText()
        posStart = self.report_text.textCursor().selectionStart()
        
        text, offset = util.strip_with_position(selectedText)
        
        self.parent.add_annotation(text, posStart + offset, tag)
            
    def onSearchTextChanged(self):
        s = self.editFinder.text()
        
        current_cursor = self.report_text.textCursor()
        extraSelections = []
        self.report_text.moveCursor(QTextCursor.Start)
        while self.report_text.find(s):
            extra = QTextEdit.ExtraSelection()
            extra.cursor = self.report_text.textCursor()
            #extra.format.setBackground(Qt.blue)
            extra.format.setBackground(QColor('#306EFF'))
            extraSelections.append(extra)

        self.report_text.setExtraSelections(extraSelections)
        self.report_text.setTextCursor(current_cursor)

        
    def show_all_highlights(self):
        self.clear_highlight()
        
        if self.inAnnotationTab:
            colorSchemes = self.tabAnnotation.controlPanel.get_coloring_scheme()
            if 'Time' in colorSchemes:
                scheme = colorSchemes['Time']
                self.highlight_annotations(self.tabAnnotation.timex_table.annotations, scheme)
        
            if 'Feature' in colorSchemes:
                scheme = colorSchemes['Feature']
                self.highlight_annotations(self.tabAnnotation.feature_table.annotations, scheme)
                                
    def set_current_report(self, current_report):
        if  current_report < 0 or current_report > len(self.reports):
            self.report_text.setText('')
            return
        
        self.current_report = current_report
        self.report_text.setText(self.reports[current_report]['Free Text'])
    
        self.clear_highlight()
        
        self.show_all_highlights()
        
        self.feature_highlight_range = (0, 0)
        self.time_highlight_range = (0, 0)

    def highlight_annotations(self, annotations, colorScheme):
        fmt = QTextCharFormat()            
        cursor = QTextCursor(self.report_text.document())
        
        for annt in annotations:
            atp = annt.getType()
            if not atp in colorScheme:
                continue
            color = colorScheme[atp]
            (istart, iend) = annt.getPositions()
            fmt.setBackground(QColor(color))
            cursor.setPosition(istart)
            cursor.setPosition(iend, QTextCursor.KeepAnchor)
            cursor.setCharFormat(fmt)
    
    def highlight_annotation_selection(self, pstart, pend, mode = 'Feature'):
        
        fmt = QTextCharFormat()            
        cursor = QTextCursor(self.report_text.document())
        
        ##: Clear the highlight of the current annotation
        if mode=='Feature':
            hrange = self.feature_highlight_range
            self.feature_highlight_range = (pstart, pend)
        else:
            hrange = self.time_highlight_range
            self.time_highlight_range = (pstart, pend)
            
        fmt.setBackground(Qt.white)
        cursor.setPosition(hrange[0])
        cursor.setPosition(hrange[1], QTextCursor.KeepAnchor)
        cursor.setCharFormat(fmt)
        
        ##: Highlight
        cursor.setPosition(pstart)
        cursor.setPosition(pend, QTextCursor.KeepAnchor)            
        fmt.setBackground(QColor('#d3d3d3'))
        cursor.setCharFormat(fmt)            
        self.report_text.setTextCursor(cursor)
                    
    def highlight_feature_text(self, pstart, pend):
        self.clear_current_feature_highlight()
        
        #prepare to highlight current sentence
        doc = self.report_text.document()
        cursor = QTextCursor(doc)
        cf = QTextCharFormat()
        
        ##: Highlight
        cursor.setPosition(pstart)
        cursor.setPosition(pend, QTextCursor.KeepAnchor)            
        cf.setBackground(QColor('#d3d3d3'))
        cursor.setCharFormat(cf)            
        self.report_text.setTextCursor(cursor)
        
        ##: Save the current feature and covered timex location
        self.feature_highlight_range = (pstart, pend)
        self.timexes_covered = []
        if 'Timexes' in self.reports[self.current_report]:          
            timexes = self.reports[self.current_report]['Timexes']
            for t, start, end, dt in timexes:
                if (start>=pstart and start<=pend) or (end>=pstart and end<=pend):
                    self.timexes_covered.append((start, end))
                
    def clear_current_feature_highlight(self):
        fmt = QTextCharFormat()            
        cursor = QTextCursor(self.report_text.document())

        ##: Clear the highlight of the current feautre
        fmt.setBackground(Qt.white)
        cursor.setPosition(self.feature_highlight_range[0])
        cursor.setPosition(self.feature_highlight_range[1], QTextCursor.KeepAnchor)
        cursor.setCharFormat(fmt)
        
        ##: Redraw timex highlight covered by the current feature
        fmt.setBackground(Qt.yellow)
        for (tstart, tend) in self.timexes_covered:
            cursor.setPosition(tstart)
            cursor.setPosition(tend, QTextCursor.KeepAnchor)
            cursor.setCharFormat(fmt)
#         self.highlight_timxes()
        
    def clear_highlight(self):
        fmt = QTextCharFormat()            
        cursor = QTextCursor(self.report_text.document())

        text = self.report_text.toPlainText()
        ##: clean text background before highlighting
        fmt.setBackground(Qt.white)
        cursor.setPosition(0)
        cursor.setPosition(len(text), QTextCursor.KeepAnchor)
        cursor.setCharFormat(fmt)
        
    def update_setting_highlight(self, toHighlightTime):
        self.highlightTimex = toHighlightTime
    
    def highlight_text_segment(self, istart, iend, fmt=None):
        text = self.report_text.toPlainText()
        if istart>=0 and iend<=len(text):
            if not fmt:
                fmt = QTextCharFormat()        
                fmt.setBackground(Qt.yellow)    
            cursor = QTextCursor(self.report_text.document())

            cursor.setPosition(istart)
            cursor.setPosition(iend, QTextCursor.KeepAnchor)
            cursor.setCharFormat(fmt)

class AnnotationTab(QSplitter):
    def __init__(self, reports = [], parent=None):
        super(AnnotationTab, self).__init__(parent)
        
        self.mainWindow = parent
        self.reports = reports
        
        self.annotationSetting = self.mainWindow.sysPreferences.getAnnotationSettings()
        self.categories = self.annotationSetting['Category']
        toHighlightTime = False        
        self.feature_table = AnnotationFeatureTableBox(reports, self)
        self.timex_table = AnnotationTimeTableBox(reports, self)
        self.controlPanel = ControlGroupBox(self)
        self.text = AnnotationReportText(reports, self, toHighlightTime, True, True)       
        
        frmAnnotation = QSplitter(Qt.Horizontal)
        frmAnnotation.addWidget(self.feature_table)
        frmAnnotation.addWidget(self.timex_table)       
        frmAnnotation.addWidget(self.controlPanel)        
        frmAnnotation.setStretchFactor(0, 4)
        frmAnnotation.setStretchFactor(1, 3)
        frmAnnotation.setStretchFactor(2, 1)
        
        self.setOrientation(Qt.Vertical)
        self.addWidget(self.text)
        self.addWidget(frmAnnotation)
                
    def selection_changed(self):
        selected = self.features.feature_table.selectedItems()
        if not selected:
            return
         
        current = selected[0]
        if current and not self.features_initialization_stage:
            logging.debug('current feature changed, extracted from sentence: {0}'.format(current.text(0)))
            
            featID = int(current.text(5))
            curFeat = self.reports[self.current_report]['Features'][featID]
            pstart = curFeat.getStartPos()
            pend = curFeat.getEndPos()
            
            self.text.highlight_feature_text(pstart, pend)
        
    def set_current_report(self, current_report):
        self.current_report = current_report

        self.feature_table.set_current_report(current_report)
        self.timex_table.set_current_report(current_report)
        self.text.setFocus()
        self.text.set_current_report(current_report)
       
    def update_pre_annotations(self, annotationType):
        if annotationType=='Time':
            self.timex_table.populate_pre_annotations(self.controlPanel.chkShowTimePreAnnotation.isChecked())
        else:
            self.feature_table.populate_pre_annotations(self.controlPanel.chkShowFeaturePreAnnotation.isChecked())
    
    def add_annotation(self, selectedText, posStart, tag):
        for category in self.categories:
            if tag in self.annotationSetting[category]:
                break
        
        if category=='Time':
            self.timex_table.add_annotation(selectedText, posStart, tag)
        else:
            self.feature_table.add_annotation(selectedText, posStart, tag)               
    
        self.text.show_all_highlights()
        
    def update_layout(self):
        if self.mainWindow.sysPreferences.getEvaluationMode():            
            self.annotation_table = ReportAnnotation(self.reports, self)
            self.featureFrame.layout().addWidget(self.annotation_table)
            self.featureFrame.layout().setStretch(0, 3)
            self.featureFrame.layout().setStretch(1, 1)
            self.annotation_table.show()
            self.annotation_table.set_current_report(self.current_report)
        else:
            self.annotation_table.hide()
        
    def current_report_changed(self):
        
        if self.timex_table.is_current_report_changed():
            time_modified = True
        else:
            time_modified = False
            
        if self.feature_table.is_current_report_changed():
            feature_modified = True
        else:
            feature_modified = False
        
        if not time_modified and not feature_modified:
            return
        elif time_modified and feature_modified:
            msg = "Both time and feature"
        elif time_modified:
            msg = 'Time'
        else:
            msg = 'Feature'
        
        choice = QMessageBox.question(None, "ETHER", msg + " annotations have been modified. \
            \n\nDo you want to save it before move to another report?", QMessageBox.Discard| QMessageBox.Cancel|QMessageBox.Save)
        if choice == QMessageBox.Save:
            if time_modified:
                self.timex_table.save_annotations()
            if feature_modified:
                self.feature_table.save_annotations()
        elif choice == QMessageBox.Cancel:
            self.mainWindow.to_continue_change_current_report = False
            return
        else:
            if time_modified:
                self.timex_table.discard_annotations()
            if feature_modified:
                self.feature_table.discard_annotations()
            return
        
        if self.feature_table.has_post_annotations():
            choice = QMessageBox.question(None, "ETHER", "There are text similar to annotations not annotated. \
                    \n\nDo you want to check post-annotations before move to another report?", QMessageBox.Yes|QMessageBox.No)
            if choice == QMessageBox.Yes:
                self.mainWindow.to_continue_change_current_report = False
                self.feature_table.chkShowPostAnnotation.setChecked(True)
            return
            
class Editor(QTextEdit):
    keyPressed = Signal() 
    
    def __init__(self, parent=None):
        super(Editor, self).__init__(parent)

    def zoom(self, delta):
        if delta < 0:
            self.zoomOut(1)
        elif delta > 0:
            self.zoomIn(1)

    def wheelEvent(self, event):
        if (event.modifiers() & Qt.ControlModifier):
            self.zoom(event.delta())
        else:
            QTextEdit.wheelEvent(self, event)
    
    def keyPressEvent(self, *args, **kwargs):
        self.keyPressed.emit()
        return QTextEdit.keyPressEvent(self, *args, **kwargs)


class ReportTextAndFeatures(QFrame):
    def __init__(self, reports = [], parent=None, researchMode = None):
        super(ReportTextAndFeatures, self).__init__(parent)
        
        self.mainWindow = parent
        self.reports = reports
        self.researchMode = researchMode
        
        self.setLayout(QHBoxLayout())
            
        toHighlightTime = self.mainWindow.sysPreferences.toHighlightTime()
#         self.text = ReportText(reports, self, toHighlightTime, True, False, True)
        if self.researchMode:
            self.text = ReportText(reports, self, toHighlightTime, True, False, True)
        else:
            self.text = ReportText(reports, self, toHighlightTime, True)
            
            
        frmInput = QGroupBox()
        #frmInput = QFrame()
        frmInput.setTitle('Review')
        frmInput.setLayout(QVBoxLayout())       
        frmInput.setContentsMargins(0,0,0,0) 
        
        boxSummary = QGroupBox()
        boxSummary.setTitle('Case Summary')
#         self.textSummary = QTextEdit('', self, readOnly=False)
#         self.textSummary.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.textSummary = Editor(self)
        self.current_report = -1

#         self.textSummary = QPlainTextEdit()
        boxSummary.setLayout(QVBoxLayout())
        boxSummary.layout().addWidget(self.textSummary)
        self.textSummary.textChanged.connect(self.on_review_changed)
        
        frmButtons = QFrame()
        frmButtons.setLayout(QHBoxLayout())
        self.btnRestoreSavedSummary = QPushButton('ETHER summary')
        self.btnRestoreSavedSummary.setToolTip('Create ETHER summary')
        self.btnRestoreSavedSummary.clicked.connect(self.update_ether_summary)
        self.btnClear = QPushButton('Clear case summary')
        self.btnClear.setToolTip('Clear case summary text')
        self.btnClear.clicked.connect(self.clear_summary_text_box)
        self.btnSave = QPushButton('Save')
        self.btnSave.setToolTip('Save case summary')
        self.btnSave.clicked.connect(self.save_summary)
        self.btnRestoreSavedSummary.setFixedWidth(150)
        self.btnClear.setFixedWidth(150)
        self.btnSave.setFixedWidth(80)
        frmButtons.layout().addWidget(self.btnRestoreSavedSummary)
        frmButtons.layout().addWidget(self.btnClear)
#         frmButtons.layout().addWidget(self.btnSave)
        boxSummary.layout().addWidget(frmButtons)
        frmInput.layout().addWidget(boxSummary)
        #frmInput.layout().addWidget(frmButtons)
        frmInput.layout().setStretch(0, 1)
        frmInput.layout().setStretch(1, 5)
        
        frmText = QFrame()
        frmText.setLayout(QVBoxLayout())
        
        self.chkboxRevisit = QCheckBox('Flag this case')
        self.chkboxRevisit.clicked.connect(self.on_revisit_clicked)
                
        if not researchMode:
            self.features = ReportFeatures_Evaluation(reports, self)
            self.featureFrame = QFrame()
            self.featureFrame.setLayout(QVBoxLayout())       
            self.featureFrame.layout().addWidget(self.features)        
        
            frmText.layout().addWidget(self.chkboxRevisit)
            frmText.layout().addWidget(self.text)
            frmText.layout().addWidget(boxSummary)
            frmText.layout().setStretch(0, 1)
            frmText.layout().setStretch(1, 50)
            frmText.layout().setStretch(2, 30)
                        
        self.layout().addWidget(frmText)
        self.layout().addWidget(self.featureFrame)
        self.layout().setStretch(0, 3)
        self.layout().setStretch(1, 2)
        
        self.features.feature_table.itemSelectionChanged.connect(self.selection_changed)


    def on_revisit_clicked(self):            
        if self.chkboxRevisit.isChecked():
            self.reports[self.current_report]['Mark'] = True
        else:
            self.reports[self.current_report]['Mark'] = False
                
        tab_summary = self.mainWindow.get_mainWindow_tab("Summarized Cases").central
        if tab_summary:
            tab_summary.check_revisit_box(self.current_report)
                
        tab_medDRA = self.mainWindow.get_mainWindow_tab("MedDRA Terms")
        if tab_medDRA:
            if self.chkboxRevisit.isChecked():
                tab_medDRA.central.chkboxRevisit.setCheckState(Qt.Checked)
            else:
                tab_medDRA.central.chkboxRevisit.setCheckState(Qt.Unchecked)
            
    def on_review_changed(self):
        self.reviewDataChanged = True
        
    def clear_summary_text_box(self):
        self.textSummary.clear()
        
    def update_ether_summary(self):
        if len(self.reports[self.current_report]['Report ID'].split('-')[0])<=6:
            reportType = 'vaers'
        else:
            reportType = 'faers'
        summary = util.ReportUtil.getReportSummary(self.reports[self.current_report], reportType, False)

        self.textSummary.setText(summary)
        
    def save_summary(self):
        if self.reviewDataChanged:
            review = self.textSummary.toPlainText()
            self.mainWindow.updateReportReview(self.reports[self.current_report]['Report ID'], review, 0, '')
            self.reports[self.current_report]['Review'] = review
            
    def selection_changed(self):
        selected = self.features.feature_table.selectedItems()
        if not selected:
            return
         
        current = selected[0]
        if current and not self.features_initialization_stage:
            logging.debug('current feature changed, extracted from sentence: {0}'.format(current.text(0)))
            
            featID = int(current.text(5))
            curFeat = self.reports[self.current_report]['Features'][featID]
            pstart = curFeat.getStartPos()
            pend = curFeat.getEndPos()
            
            self.text.highlight_feature_text(pstart, pend)
        
    def set_current_report(self, current_report):
        self.current_report = current_report
        self.text.setFocus()
        self.text.set_current_report(current_report)
        
        # When in features_initialization_stage, feature_changed() slot is disabled, 
        # to avoid error caused by previous text.
        self.features_initialization_stage = True
        self.features.set_current_report(current_report)
        self.features_initialization_stage = False
        
        if  current_report < 0:
            self.textSummary.clear()
            return
        
        summary = self.reports[current_report]['Review']
        if summary=='':
            if len(self.reports[self.current_report]['Report ID'].split('-')[0])<=6:
                reportType = 'vaers'
            else:
                reportType = 'faers'
            summary = util.ReportUtil.getReportSummary(self.reports[self.current_report], reportType, False)

        self.textSummary.setText(summary)
            
        self.current_review = self.textSummary.toPlainText()   
        
        if self.reports[current_report]['Mark']:
            self.chkboxRevisit.setChecked(True)
        else:
            self.chkboxRevisit.setChecked(False)
            
    def update_layout(self):
        if self.mainWindow.sysPreferences.getEvaluationMode():            
            self.annotation_table = ReportAnnotation(self.reports, self)
#             self.annotation_table = ReportTimeAnnotation(self.reports, self)
            self.featureFrame.layout().addWidget(self.annotation_table)
            self.featureFrame.layout().setStretch(0, 3)
            self.featureFrame.layout().setStretch(1, 1)
            self.annotation_table.show()
            self.annotation_table.set_current_report(self.current_report)
        else:
            self.annotation_table.hide()
    
    def current_report_changed(self):
        if self.reviewDataChanged:
            self.save_summary()

class ReportTemporalPlot(QFrame):
    def __init__(self, reports = [], mainWindow = None, parent=None):
        super(ReportTemporalPlot, self).__init__(parent)
        self.reports = reports
        self.mainWindow = mainWindow
        self.parent = parent
        self.current_report = 0
        
        self.setLayout(QHBoxLayout())
        
        self.plotFrame = QFrame()

        self.optionFrame = QGroupBox()
        self.optionFrame.setLayout(QVBoxLayout())
        self.optionFrame.setTitle('Setting Panel')
        self.optionFrame.setToolTip('Setting Panel (Ctrl+H to hide)')
        
        self.featureGroup = QGroupBox()
        self.featureGroup.setLayout(QVBoxLayout())
        self.featureGroup.setTitle("Feature types")
        self.featureGroup.setToolTip('Select features to plot')
        
        ############################
        self.timeGroup = QGroupBox()
        self.timeGroup.setLayout(QGridLayout())
        self.timeGroup.setTitle("Time Axis (Feature Occurrence)")
        self.timeGroup.setToolTip("Set time axis options")
        
        self.comboAxis = QComboBox()
        self.comboAxis.addItems(['From Exposure', 'Date'])
        self.comboAxis.setToolTip('Select time axis type')
        self.comboAxis.currentIndexChanged.connect(self.on_timeaxis_changed)
        self.comboAxis.setCurrentIndex(0)   
        
        self.checkCompressAxis = QCheckBox('Compressed')
        self.checkCompressAxis.setToolTip('Compress time axis by removing large intervals')
        self.checkCompressAxis.setChecked(True)
        self.checkCompressAxis.clicked.connect(self.plot)
        self.textRangeFrom = QDateEdit()
        self.textRangeFrom.setCalendarPopup(True)
        self.textRangeFrom.setDisplayFormat('MM/dd/yyyy')
        self.textRangeTo = QDateEdit()
        self.textRangeTo.setCalendarPopup(True)
        self.textRangeTo.setDisplayFormat('MM/dd/yyyy')
        
        self.spinDayFrom = QSpinBox()
        self.spinDayFrom.setPrefix('Day ')
        self.spinDayFrom.setMinimum(-36000)
        self.spinDayFrom.setMaximum(36000)
        self.spinDayTo = QSpinBox()
        self.spinDayTo.setPrefix('Day ')
        self.spinDayTo.setMinimum(-36000)
        self.spinDayTo.setMaximum(36000)
        
        self.stackedFrom = QStackedWidget()
        self.stackedFrom.addWidget(self.spinDayFrom)
        self.stackedFrom.addWidget(self.textRangeFrom)
        self.stackedFrom.setCurrentIndex(0)
        
        self.stackedTo = QStackedWidget()
        self.stackedTo.addWidget(self.spinDayTo)
        self.stackedTo.addWidget(self.textRangeTo)
        self.stackedTo.setCurrentIndex(0)    

        self.btnRestoreRange = QPushButton('Full Range')
        self.btnRestoreRange.setToolTip('Restore time axis to full range')
        self.btnApplyRange = QPushButton('Apply')
        self.btnApplyRange.setToolTip('Apply time range to time axis')
        self.btnApplyRange.clicked.connect(self.apply_time_range)
        self.btnRestoreRange.clicked.connect(self.restore_time_range)
        self.comboAxisUnit = QComboBox()
        self.comboAxisUnit.addItems(['Day', 'Week', 'Month', 'Year'])
        self.comboAxisUnit.setToolTip('Select time axis unit')
        self.comboAxisUnit.setCurrentIndex(0)
        self.comboAxisUnit.currentIndexChanged.connect(self.onTimeUnitChanged)
        self.comboAxisUnit.setVisible(False)

        self.timeGroup.layout().addWidget(QLabel('Axis:'), 0, 0)
        self.timeGroup.layout().addWidget(self.comboAxis, 0, 1)
        self.timeGroup.layout().addWidget(self.comboAxisUnit, 0, 2)
        self.timeGroup.layout().addWidget(self.checkCompressAxis, 0, 3)
        self.timeGroup.layout().addWidget(QLabel('From:'), 1, 0)
        self.timeGroup.layout().addWidget(QLabel('To:'), 2, 0)
        self.timeGroup.layout().addWidget(self.stackedFrom, 1, 1, 1, 2)
        self.timeGroup.layout().addWidget(self.stackedTo, 2, 1, 1, 2)
        self.timeGroup.layout().addWidget(self.btnRestoreRange, 1, 3)
        self.timeGroup.layout().addWidget(self.btnApplyRange, 2, 3)
        self.timeGroup.layout().setColumnStretch(0,1)
        self.timeGroup.layout().setColumnStretch(1,20)
        self.timeGroup.layout().setColumnStretch(2,1)
        self.timeGroup.layout().setColumnStretch(3,1)
        
        ####################################################
        typeFrame = QFrame()
        typeFrame.setLayout(QHBoxLayout())
        self.comboPlotContent = QComboBox()
        self.comboPlotContent.addItems(["Medical Features", "Split Feature Text", "Line Plot"])
        self.comboPlotContent.setToolTip('Select plot content')
        self.comboPlotContent.setCurrentIndex(0)
        self.comboPlotContent.currentIndexChanged.connect(self.onPlotContentChanged)

        typeFrame.layout().addWidget(QLabel('Plot:'))
        typeFrame.layout().addWidget(self.comboPlotContent)
        typeFrame.layout().setStretch(0, 1)
        typeFrame.layout().setStretch(1, 10)
        
        ####################################################
        self.optionFrame.layout().addWidget(self.featureGroup)
        self.optionFrame.layout().addWidget(typeFrame)
        self.optionFrame.layout().addWidget(self.timeGroup)
        self.optionFrame.layout().setStretch(0, 10)
        self.optionFrame.layout().setStretch(1, 1)
        self.optionFrame.layout().setStretch(2, 2)
        
        self.layout().addWidget(self.plotFrame)
        self.layout().addWidget(self.optionFrame)
        self.layout().setStretch(0, 10)
        self.layout().setStretch(1, 1)
        
        if self.mainWindow.reportType=='faers':
            self.defaut_day_range = 120
        else: 
            self.defaut_day_range = 28
        self.spinDayFrom.setValue(0)
        self.spinDayTo.setValue(self.defaut_day_range)        
        self.is_time_range_applied = True
        self.timeline = None
        
        # Initialize plot area
        self.dpi = 72          
        self.fontsize = self.mainWindow.sysPreferences.getFontSize()
        self.textfontsize = self.mainWindow.sysPreferences.getFontSize()
        self.x_offset = 0.05
        self.y_offset = 0.2
        self.allFeatures = ["DIAGNOSIS", "CAUSE_OF_DEATH", "SECOND_LEVEL_DIAGNOSIS", "SYMPTOM", 
                       "RULE_OUT", "MEDICAL_HISTORY", "FAMILY_HISTORY", "DRUG", "VACCINE"]
        self.linewidth = 4
        self.textFontManager = tkFont.Font(root=tk.Tk(), family='sans-serif', size=self.textfontsize)

        self.fig = Figure(dpi=self.dpi, facecolor='w', tight_layout=True)
        self.canvas = FigureCanvas(self.fig)        
        
        layout=QVBoxLayout()
        self.plotFrame.setLayout(layout)
        layout.addWidget(self.canvas)
        
#         im_syringe = read_png("./rx.png")
        im_syringe = mpimg.imread("./rx.png")
        self.imbox_syringe = OffsetImage(im_syringe, zoom=0.2)
        im_sick = mpimg.imread("./sad.png")
        self.imbox_sick = OffsetImage(im_sick, zoom=0.2)
        
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_motion)
        #self.canvas.mpl_connect('scroll_event', self.zoom_fun)
        self.canvas.mpl_connect('resize_event', self.on_resize)
        self.canvas.mpl_connect('button_press_event', self.on_mouse_release)

    def on_resize(self, event):
        self.plot()        
        
        # because tooltip data is based on axes information, which is not totally created yet in the first call
        # after resizing, thus call second time to adjust tooltip data to be more accurate         
        #self.plot() 
    
    def zoom_fun(self, event):
        # get the current x and y limits
        base_scale = 1.5
        ax = self.fig.axes[0]
        cur_xlim = ax.get_xlim()
        cur_ylim = ax.get_ylim()
        cur_xrange = (cur_xlim[1] - cur_xlim[0])*.5
        cur_yrange = (cur_ylim[1] - cur_ylim[0])*.5
        xdata = event.xdata # get event x location
        ydata = event.ydata # get event y location
        if event.button == 'up':
            # deal with zoom in
            scale_factor = 1/base_scale
        elif event.button == 'down':
            # deal with zoom out
            scale_factor = base_scale
        else:
            # deal with something that should never happen
            scale_factor = 1
            print event.button
        # set new limits
        ax.set_xlim([xdata - cur_xrange*scale_factor,
                     xdata + cur_xrange*scale_factor])
        ax.set_ylim([ydata - cur_yrange*scale_factor,
                     ydata + cur_yrange*scale_factor])
        #ax.grid(True)
        self.canvas.draw()
        
    def on_mouse_release(self, event):

        if not event.xdata or not event.ydata:
            self.parent.highlight_sentence_timexes(-1)
                
        text = self.comboPlotContent.currentText()
        if text == "Medical Features" or text=="Split Feature Text":
            
            xs = [xt for xt in self.time_ticks if xt<=event.xdata]
            ys = [yt for yt in self.feature_ticks if yt>=event.ydata]
            if not xs or not ys:
                return
                
            x = max(xs)
            y = min(ys)
            if (x,y) in self.data:
                pickid =-1
                for i, box in enumerate(self.data[(x,y)]):
                    if event.x >= box[1] and event.x <= box[1]+box[3] and event.y <= box[2] and event.y >= box[2]-box[4]:
                        if i > pickid:
                            pickid = i
                    else: 
                        if pickid >= 0: # if box increased out of mouse region, no need to continue
                            break
                if pickid>=0:
                    sentNum = self.data[(x,y)][pickid][5]
                    tiptext = self.data[(x,y)][pickid][0]
                    loc1 = tiptext.find('<p>')
                    loc2 = tiptext.find('</p>')
                    featString = tiptext[loc1+4:loc2-1]
                    self.parent.highlight_sentence_timexes(sentNum, featString)
                    return

        self.parent.highlight_sentence_timexes(-1)
        
    def on_mouse_motion(self, event):
        
        if not event.xdata or not event.ydata:
            self.canvas.setToolTip(None)
            return
        
        self.canvas.setToolTip(None)
        for box in self.tooltipData_addon:
            #if event.xdata >= box[0] and event.xdata <= box[0]+box[2] and event.ydata <= box[1] and event.ydata >= box[1]-box[3]:
            if event.xdata >= box[0]-box[2]/2 and event.xdata <= box[0]+box[2]/2 and event.ydata <= box[1]+box[3]/2 and event.ydata >= box[1]-box[3]/2:
                if self.reports[self.current_report]['DatesConfidence']==0:
                    self.canvas.setToolTip(self.tooltipData_addon[box]+' (from field)')
                elif self.reports[self.current_report]['DatesConfidence']==1:
                    self.canvas.setToolTip(self.tooltipData_addon[box]+' (from narrative)')
                else:
                    self.canvas.setToolTip(self.tooltipData_addon[box]+' (estimated)')
                return        
        
        text = self.comboPlotContent.currentText()
        if text == "Medical Features" or text=="Split Feature Text":
            xs = [xt for xt in self.time_ticks if xt<=event.xdata]
            ys = [yt for yt in self.feature_ticks if yt>=event.ydata]
            if not xs or not ys:
                return
                
            x = max(xs)
            y = min(ys)
            if (x,y) in self.data:
                pickid =-1
                for i, box in enumerate(self.data[(x,y)]):
                    if event.x >= box[1] and event.x <= box[1]+box[3] and event.y <= box[2] and event.y >= box[2]-box[4]:
                        if i > pickid:
                            pickid = i
                    else: 
                        if pickid >= 0: # if box increased out of mouse region, no need to continue
                            break
                if pickid>=0:
                    tx = self.data[(x,y)][pickid][0]
                    self.canvas.setToolTip(tx)
                    return
        elif text=='Line Plot':# or text=='Medical Feature Count':
            (rx, ry) = self.pickRadius
            dmin = 1e10
            minloc = None
            for loc in self.tooltipData:
                #loc = self.tooltipData[data]
                if abs(event.xdata-loc[0])<=rx and abs(event.ydata-loc[1])<=ry:
                    d = (event.xdata-loc[0])*(event.xdata-loc[0]) + (event.ydata-loc[1])*(event.ydata-loc[1])
                    if d < dmin:
                        dmin = d
                        minloc = loc
            if minloc:
                tooltip =  self.tooltipData[minloc]
                self.canvas.setToolTip(tooltip)
                return
            
        self.canvas.setToolTip(None)
        
    def apply_time_range(self):
        self.is_time_range_applied = True
        self.plot()
        
    def restore_time_range(self):
        self.time_range = None
        self.is_time_range_applied = False
        self.plot()
        return
        
    def update_time_range_widget(self):
        expDate = self.reports[self.current_report]['Exposure Date']
        secDay = datetime.timedelta(days=1).total_seconds()             
        if self.comboAxis.currentText()=='Date of Occurrence':
            self.stackedFrom.setCurrentIndex(1)
            self.stackedTo.setCurrentIndex(1)
            
            self.textRangeFrom.setDate(self.time_range[0])
            self.textRangeTo.setDate(self.time_range[1])
        elif self.comboAxis.currentText()=='From Exposure':
            self.stackedFrom.setCurrentIndex(0)
            self.stackedTo.setCurrentIndex(0)
            
            dayFrom = int((self.time_range[0]-expDate).total_seconds()/secDay)
            dayTo = int((self.time_range[1]-expDate).total_seconds()/secDay)
            
            self.spinDayFrom.setValue(dayFrom)
            self.spinDayTo.setValue(dayTo)
            
        if self.time_range[0]==self.timeline[0] and  self.time_range[1]==self.timeline[-1]:
            self.btnRestoreRange.setDisabled(True)
        else:
            self.btnRestoreRange.setDisabled(False)
    
    def update_time_range_widget_unit(self, timeUnit):
        if self.comboAxis.currentText()=='Date of Occurrence' and self.comboAxisUnit!='Week':
            self.stackedFrom.setCurrentIndex(1)
            self.stackedTo.setCurrentIndex(1)

            self.textRangeFrom.setDate(self.time_range[0])
            self.textRangeTo.setDate(self.time_range[1])
        else: #if self.comboAxis.currentText()=='Exposure':
            self.stackedFrom.setCurrentIndex(0)
            self.stackedTo.setCurrentIndex(0)
            
            tFrom = int(self.time_range[0]/timeUnit)
            tTo = int(self.time_range[1]/timeUnit)
            
            self.spinDayFrom.setValue(tFrom)
            self.spinDayTo.setValue(tTo)
            
    def on_timeaxis_changed(self):
        # when Group checkbox is check, time axis switch between Exposure and Age, 
        # which are not compatible, thus the time range has to be reset
#         if self.checkBoxGroup.isChecked():
#             self.time_range = None
#         else:
        self.update_time_range_widget()
            
        self.plot()
        
    def onTimeUnitChanged(self):
        strUnit = self.comboAxisUnit.currentText()
        self.spinDayFrom.setPrefix(strUnit + ' ')
        self.spinDayTo.setPrefix(strUnit + ' ')
        self.plot()
        
    def onPlotContentChanged(self):
        if self.comboPlotContent.currentText()=='Line Plot':
            self.checkAggregated.setEnabled(True)
        else:
            self.checkAggregated.setEnabled(False)
        self.plot()
            
    def plot(self):  
        self.tooltipData_addon = []
        
        text = self.comboPlotContent.currentText()        
        if text == "Medical Features":
            self.plot_temporal_main()
        elif text=="Split Feature Text":
            self.plot_multibox_split()
        else:
            self.plot_numbers_of_features()
             
    def plot_numbers_of_features(self):
        
        self.fig.clf()
        axes = self.fig.add_subplot(111)
        
        if  self.current_report < 0 or self.current_report > len(self.reports):
            self.canvas.draw()
            return
        
        lineCols = ['b-','r--','k-.','g:', 'y-', 'm--', 'c-.'] 
        lineMarkers = ['o','d','s','H','v', '^', '8','<','>','p']
         
        features = self.reports[self.current_report]['Features']
        expDate = self.reports[self.current_report]['Exposure Date']
        onsetDate = self.reports[self.current_report]['Onset Date']
        
        featLists = []
        plotNames = []
        if not self.checkAggregated.isChecked():
            for i in range(self.featureGroup.layout().count()-2): 
                if self.featureGroup.layout().itemAt(i).widget().checkState():
                    text = self.featureGroup.layout().itemAt(i).widget().text()
                    loc = text.find('(')
                    if loc>=0:
                        text = text[:loc-1]
                    strFeat = dictFeatureNames[text]
                    featLists.append([strFeat])
                    plotNames.append(text)
        else:
            featList = []
            for i in range(self.featureGroup.layout().count()-2): 
                if self.featureGroup.layout().itemAt(i).widget().checkState():
                    text = self.featureGroup.layout().itemAt(i).widget().text()
                    loc = text.find('(')
                    if loc>=0:
                        text = text[:loc-1]
                    strFeat = dictFeatureNames[text]
                    featList.append(strFeat)                    
#                     featList.append(dictFeatureNames[self.featureGroup.layout().itemAt(i).widget().text()])
            featLists.append(featList)
            plotNames.append('Selected Features')
        
        ### Compute number of selected features
        allCurves=[]
        tooltips = {}
        featSetAll = []
        for curveid, featList in enumerate(featLists):
            featSetAll += featList
            
            dicts = {}
            for feature in features:
                if not feature.getType() in featList: continue
                
                if feature.hasStartTime():
                    singles = re.split(', | and ', feature.getString())
                    singles = [feature.getType()+': '+s for s in singles]
                    if not feature.getStartTime() in dicts:
                        dicts[feature.getStartTime()]= singles
                    else:
                        dicts[feature.getStartTime()] += singles
        
            if not expDate in dicts:
                dicts[expDate] = []
            if onsetDate and not onsetDate in dicts:
                dicts[onsetDate] = []
            
            time_severity = [(k, dicts[k]) for k in dicts]
            time_severity.sort(key=lambda ts:ts[0])
            ti = [severity[0] for severity in time_severity]
            yi = [len(severity[1]) for severity in time_severity]
            si = [severity[1] for severity in time_severity]
            
            plotName = plotNames[curveid]
            for i, t in enumerate(ti):    
                tooltip = '<b> '+ plotName +' </b>'    
                if si[i]==[]:
                    continue
                
                tooltip += '<ul>'
                for s in si[i]:
                    tooltip += '<li> ' + s
            
                tooltip += '</ul>'
                
                if (t, yi[i]) in tooltips:
                    tooltips[(t, yi[i])] += tooltip
                else:
                    tooltips[(t, yi[i])] = tooltip
            
            allCurves.append((ti,yi, plotName))
               
        # if there is not curve at all 
        if len(allCurves)==0:
            self.canvas.draw()
            return
        
        legends = ()
        for curve in allCurves:
            legends = legends + (curve[2],)
        
        ## create time axis
        featSetAll = list(set(featSetAll))
        (xmap, xticks, xticklabels, xlim) = self.time_axis_process_2layer_label(featSetAll)     
        if xticks==None:
            self.canvas.draw()
            return
           
        axes.set_xticks(xticks)
        if xticklabels[-1]=='':
            axes.set_xticklabels(xticklabels, size=self.fontsize)
        else:
            if xticklabels[-1]=='Day':
                xticklabels[-1]=''
            axes.set_xticklabels(xticklabels, size=self.fontsize)
        axes.set_xlim(xlim)
         
        ## set y axis range
        ymax = [max(curve[1]) for curve in allCurves]
        yticks = range(max(ymax) + 1)
        axes.set_yticks(yticks)
        dy = min(yticks[-1]*0.2, 1)
        ylim = [0, yticks[-1]+dy]        
        if ylim[1]==0:
            ylim[1]=1
        axes.set_ylim(ylim)
        
        ###### Plot ############################################
        self.tooltipData = {}
        markerSize = 8
        for i, curve in enumerate(allCurves):
            ti = curve[0]
            yi = curve[1]
            linecol = lineCols[i%len(lineCols)]
            linemarker = lineMarkers[i%len(lineMarkers)]
            xi = [xmap[t]+0.5 for t in ti]
            axes.plot(xi, yi, linemarker+linecol, markersize = markerSize, linewidth = self.linewidth)
            
            for j, x in enumerate(xi):
                if (ti[j], yi[j]) in tooltips:
                    self.tooltipData[(x,yi[j])] = tooltips[(ti[j], yi[j])]
                            
        xy = axes.transData.inverted().transform([(0,0), (markerSize, markerSize)])
        self.pickRadius = (abs(xy[1][0]-xy[0][0]), abs(xy[1][1]-xy[0][1]))
        
        if len(legends)==1:
            axes.set_ylabel(legends[0],size=self.fontsize)
        else:
            hleg = axes.legend(legends, loc=4, fontsize=10)
            hleg.draggable(state=True)
        
        self.plot_addon(axes, expDate, onsetDate, xmap)
        
        axes.yaxis.grid(True)
        [axes.axvline(t-0.5, linestyle=':', color='g') for t in xticks[:-1]]
        self.canvas.draw()   
        
        
    def combine_tooltips(self, tip, newtip):
        p1 = tip.find('<b>')
        p2 = tip.find('</b>')
        title1 = tip[p1+3:p2]
        
        p1 = newtip.find('<b>')
        p2 = newtip.find('</b>')
        title2 = newtip[p1+3:p2]
        
        
        if title2==title1:
            tooltip = tip + newtip[p2+4:]
        else:
            tooltip = tip + newtip
            
        return tooltip
                
    def create_coord_mapping(self, ti, axisType, strTimeUnit):
        ####################################################################
        ## create time axis
        #################################################################
        timeUnit = self.get_time_unit_days(strTimeUnit)
        num = len(ti)
        if axisType == 'Date':
            if strTimeUnit == 'Day' or strTimeUnit =='Week':
                t0 = ti[0]
                tni = [(t-t0).days/timeUnit for t in ti]
            elif strTimeUnit == 'Month':
                days =[31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
                tni = [ti[0].month + (ti[0].day-1.)/days[ti[0].month-1]]
                yearcount = 0
                for i in range(1, num):
                    if ti[i].month < ti[i-1].month:
                        yearcount += 1
                    tni.append(yearcount*12 + ti[i].month + (ti[i].day-1.)/days[ti[0].month-1])
            elif strTimeUnit == 'Year':
                tni = []
                for i in range(0, num):
                    days = (ti[i]-datetime.datetime(ti[i].year, 1, 1)).days
                    tni.append(ti[i].year + days/365.)
            t0 = int(tni[0])
            tni = [t-t0 for t in tni]
        else:
            tni = [t/timeUnit for t in ti] # normalized ti 
            
        coord_mapping = {}
        if not self.checkCompressAxis.isChecked():
            ticks = [0]
            ticklabels = ['0']
            for i in range(num):
                coord_mapping[ti[i]] = tni[i]
                fl = int(tni[i])
                if fl!=ticks[-1]:
                    ticks.append(fl)
                    if axisType=='Date':
                        ticklabels.append(datetime_strftime(ti[i]))
                    else:
                        ticklabels.append(str(fl))
        else:
            # assume the minimum delta is 1 (day)
            interval_allowed = 2    

            if axisType == 'Date':
                coord_mapping[ti[0]] = 0
                ticks = [0]
                if strTimeUnit=='Day':
                    ticklabels = [datetime_strftime(ti[0])]
                elif strTimeUnit=='Week':
                    ticklabels = ['0']
                elif strTimeUnit=='Month':
                    ticklabels = [datetime_strftime(ti[0], 'm')]
                elif strTimeUnit=='Year':
                    ticklabels = [datetime_strftime(ti[0], 'y')]
            else:
                tn0 = int(math.floor(tni[0]))
                ticks = [0]
                ticklabels = [str(tn0)]
                if tn0 == tni[0]:
                    coord_mapping[ti[0]] = 0
                else:
                    coord_mapping[ti[0]-(tni[0]-tn0)*timeUnit] = 0
                    coord_mapping[ti[0]] = tni[0]-tn0
                    
            for i in range(1,num):
                if int(tni[i]) - int(tni[i-1]) <= interval_allowed:
                    coord_mapping[ti[i]] = coord_mapping[ti[i-1]] + tni[i] - tni[i-1]
                    
                    if int(math.floor(coord_mapping[ti[i]])) != ticks[-1]:
                        ticks.append(int(math.floor(coord_mapping[ti[i]])))
                        
                        if axisType == 'Date':
                            if strTimeUnit=='Day':
                                ticklabels.append(datetime_strftime(ti[i]))
                            if strTimeUnit=='Week':
                                ticklabels.append(str(int(math.floor(tni[i]))))
                            elif strTimeUnit=='Month':
                                if ti[i].year!=ti[i-1].year:
                                    ticklabels.append(datetime_strftime(ti[i],'m'))
                                else:
                                    ticklabels.append(datetime_strftime(ti[i],'m', True))
                            elif strTimeUnit=='Year':
                                ticklabels.append(datetime_strftime(ti[i],'y'))
                                
                        else:
                            ticklabels.append(str(int(math.floor(tni[i]))))
                else:
                    ticks.append(ticks[-1] + 1)
                    #ticklabels.append('${\mathbf{\sim}}$')
                    #ticklabels.append(r'${\longrightarrow}$')
                    ticklabels.append(r'${\rightarrow}$')
                    coord_mapping[ti[i]] = ticks[-1] + 1 + tni[i]-int(math.floor(tni[i]))
                    ticks.append(int(math.floor(coord_mapping[ti[i]])))
                    
                    if axisType == 'Date':
                        if strTimeUnit=='Day':
                            ticklabels.append(datetime_strftime(ti[i],'y'))
                        if strTimeUnit=='Week':
                            ticklabels.append(str(int(math.floor(tni[i]))))
                        elif strTimeUnit=='Month':
                            if ti[i].year!=ti[i-1].year:
                                ticklabels.append(datetime_strftime(ti[i],'m'))
                            else:
                                ticklabels.append(datetime_strftime(ti[i],'m', True))
                        else:
                            ticklabels.append(datetime_strftime(ti[i],'y'))
                    else:
                        ticklabels.append(str(int(math.floor(tni[i]))))
        
        ticks.append(ticks[-1] + 1)
        ticklabels.append(' ')
        xlim = self.set_time_range_unit(ti, ticks, coord_mapping, timeUnit)
        
        return (coord_mapping, ticks, ticklabels, xlim)
        
    def plot_temporal_main(self):
        self.fig.clf()
        
        axes = self.fig.add_subplot(111)
        
        if  self.current_report < 0 or self.current_report > len(self.reports):
            self.canvas.draw()
            return
     
        features = self.reports[self.current_report]['Features']
        expDate = self.reports[self.current_report]['Exposure Date']
        onsetDate = self.reports[self.current_report]['Onset Date']
         
        # Convert tlinks information into list of dots and segments
        featDict = self.reports[self.current_report]['SelectedFeatures']
        
        feats = [(feat, self.allFeatures.index(feat)) for feat in featDict 
                 if featDict[feat] and feat in dictFeatureNames.values()]
        feats.sort(key = lambda f:f[1], reverse= True)
        selectedFeatures = [feat[0] for feat in feats]
        
        #########################################################
        ## create plot axes        
        #########################################################
        (xmap, xticks, xticklabels, xlim) = self.time_axis_process_2layer_label(selectedFeatures)
        if xticks==None:
            self.canvas.draw()
            return
                            
        axes.set_xticks(xticks)
        if xticklabels[-1]=='':
            axes.set_xticklabels(xticklabels, size=self.fontsize)
        else:
            if xticklabels[-1]=='Day':
                xticklabels[-1]=''
            axes.set_xticklabels(xticklabels, size=self.fontsize)
        axes.set_xlim(xlim)
        tlabels= axes.xaxis.get_ticklabels()
        for tl in tlabels:
            tt = tl.get_text()
            if len(tt) and tt[0]=='$':
                tl.set_fontsize(15)
        
        (yticks, yticklabels, ylim) = self.feature_axis_process(selectedFeatures)      
        axes.set_yticks(yticks)
        axes.set_yticklabels(yticklabels, size=self.fontsize)                   
        axes.set_ylim(ylim)

        
        ######################################################
        # Plot texts
        padPixel = 3
        padData = axes.transData.inverted().transform([(0,0), (padPixel, padPixel)])
        xpad = padData[1][0]-padData[0][0]
        ypad = padData[1][1]-padData[0][1]

        numpixel = padPixel/xpad
  
        render = self.canvas.get_renderer()
        self.data = {}
        occupied={}
        self.y_offset = 0
        for feat in features:
            if not feat.getType() in selectedFeatures or not feat.hasStartTime():
                continue
            
            yi = yticks[selectedFeatures.index(feat.getType())+1]
            xi = xmap[feat.getStartTime()]
            if (xi,yi) in occupied:
                occupied[(xi,yi)] += 1
            else:
                occupied[(xi,yi)] = 1
            tx = self.chop_string(feat.getString(), numpixel)
                
            xloc = xi + xpad/2
            if xloc < xlim[0] or xloc >= xlim[1]:
                continue
                
            yloc = yi-ypad/2-self.y_offset*(occupied[(xi,yi)]-1)
            h = axes.text(xloc, yloc, tx, size=self.textfontsize, va='top', ha='left', bbox=dict(fc=[1, 0.8, 1], pad=padPixel))
                
            bbox = h.get_window_extent(renderer=render)                
            widthpixel = bbox.width
            heightpixel = bbox.height
            if self.y_offset == 0:
                yy = axes.transData.inverted().transform([(0,0), (0, heightpixel+padPixel)])
                self.y_offset = yy[1][1]-yy[0][1]             
                
            tooltip = '<b> '+ feat.getType() +' </b>' 
            tooltip += '<p> ' + feat.getString() +' </p>'
            
            locPixel = axes.transData.transform((xloc,yloc))
            if (xi, yi) in self.data:
                self.data[(xi, yi)].append((tooltip, locPixel[0], locPixel[1], widthpixel+padPixel, heightpixel+padPixel, feat.getSentNum())) 
            else:
                self.data[(xi, yi)] = [(tooltip, locPixel[0], locPixel[1], widthpixel+padPixel, heightpixel+padPixel, feat.getSentNum())] 
                
        self.plot_addon(axes, expDate, onsetDate, xmap)
        
        axes.yaxis.grid(True)
        [axes.axvline(t-0.5, linestyle=':', color='k', linewidth=0.5) for t in xticks[:-1]]
        self.canvas.draw()
        
    def save_temporal_main_pdf(self, fname):
        with PdfPages(fname) as pdf:
            pdf.savefig(figure=self.fig)  # saves the current figure into a pdf page            
    
    def plot_multibox_split(self):
  
        self.fig.clf()
        
        axes = self.fig.add_subplot(111)
     
        if  self.current_report < 0 or self.current_report > len(self.reports):
            self.canvas.draw()
            return
        
        features = self.reports[self.current_report]['Features']
        expDate = self.reports[self.current_report]['Exposure Date']
        onsetDate = self.reports[self.current_report]['Onset Date']

        # Convert tlinks information into list of dots and segments
        featDict = self.reports[self.current_report]['SelectedFeatures']
        feats = [(feat, self.allFeatures.index(feat)) for feat in featDict 
                 if featDict[feat] and feat in dictFeatureNames.values()]
        feats.sort(key = lambda f:f[1], reverse= True)
        selectedFeatures = [feat[0] for feat in feats]
        #------------------------------------------------------------
        # create plot axes        
        #------------------------------------------------------------
        (xmap, xticks, xticklabels, xlim) = self.time_axis_process_2layer_label(selectedFeatures)   
        if xticks==None:
            self.canvas.draw()
            return
             
        self.time_coord_map = xmap 
            
        axes.set_xticks(xticks)
        if xticklabels[-1]=='':
            axes.set_xticklabels(xticklabels, size=self.fontsize)
        else:
            axes.set_xticklabels(xticklabels, size=self.fontsize)
        axes.set_xlim(xlim)
        
        (yticks, yticklabels, ylim) = self.feature_axis_process(selectedFeatures)      
        axes.set_yticks(yticks)
        axes.set_yticklabels(yticklabels, size=self.fontsize)                   
        axes.set_ylim(ylim)
        
        #------------------------------------------------------------
        # Plot texts
        padPixel = 3
        padData = axes.transData.inverted().transform([(0,0), (padPixel, padPixel)])
        xpad = padData[1][0]-padData[0][0]
        ypad = padData[1][1]-padData[0][1]

        numpixel = padPixel/xpad
  
        render = self.canvas.get_renderer()
        self.data = {}
        occupied={}
        self.y_offset = 0
        for feat in features:
            if not feat.getType() in selectedFeatures or not feat.hasStartTime():
                continue
            
            yi = yticks[selectedFeatures.index(feat.getType())+1]
            xi = xmap[feat.getStartTime()]
            
            singles = re.split(', | and ', feat.getString())
            
            for s in singles:
                tx = self.chop_string(s, numpixel)
                
                if (xi,yi) in occupied:
                    occupied[(xi,yi)] += 1
                else:
                    occupied[(xi,yi)] = 1
                xloc = xi + xpad/2
                if xloc < xlim[0] or xloc >= xlim[1]:
                    continue
                
                yloc = yi-ypad/2-self.y_offset*(occupied[(xi,yi)]-1)
                h = axes.text(xloc, yloc, tx, size=self.textfontsize, va='top', ha='left', bbox=dict(fc=[1, 0.8, 1], pad=padPixel))
                              
                bbox = h.get_window_extent(renderer=render)
                widthpixel = bbox.width
                heightpixel = bbox.height            
                if self.y_offset == 0:
                    yy = axes.transData.inverted().transform([(0,0), (0, heightpixel+padPixel)])
                    self.y_offset = yy[1][1]-yy[0][1]     
                       
                tooltip = '<b> '+ feat.getType() +' </b>' 
                tooltip += '<p> ' + s +' </p>'
              
                locPixel = axes.transData.transform((xloc,yloc))
                if (xi, yi) in self.data:
                    self.data[(xi, yi)].append((tooltip, locPixel[0], locPixel[1], widthpixel+padPixel, heightpixel+padPixel, feat.getSentNum())) 
                else:
                    self.data[(xi, yi)] = [(tooltip, locPixel[0], locPixel[1], widthpixel+padPixel, heightpixel+padPixel, feat.getSentNum())] 
                
        self.plot_addon(axes, expDate, onsetDate, xmap)
        
        axes.yaxis.grid(True)
        [axes.axvline(t-0.5, linestyle=':', color='g') for t in xticks[:-1]]
        self.canvas.draw()
        
    def plot_addon(self, axes, expDate, onsetDate, xmap):
        
        self.tooltipData_addon = {}
        sideBoxPixel = 32        
        
        padData = axes.transData.inverted().transform([(0,0), (sideBoxPixel, sideBoxPixel)])
        dx = padData[1][0]-padData[0][0]
        dy = padData[1][1]-padData[0][1]
        # draw exposure image
        if expDate:
            xExp =  xmap[expDate] + 0.25
            ylim = axes.get_ylim()
            yExp = ylim[1]-0.3
            yExp = ylim[1]*0.92
            if self.reports[self.current_report]['DatesConfidence']==0:
                ab = AnnotationBbox(self.imbox_syringe, [xExp, yExp], frameon=True, pad=0.1)
            else:
                ab = AnnotationBbox(self.imbox_syringe, [xExp, yExp], frameon=False, pad=0.1)
            axes.add_artist(ab)
        
            self.tooltipData_addon[(xExp, yExp, dx, dy)]='Date of Exposure'
        
        # draw onset image
        if onsetDate:
            xOnset =  xmap[onsetDate] + 0.25
            if xOnset == xExp:
                xOnset += dx
            ylim = axes.get_ylim()
            yOnset = ylim[1]*0.92
            if self.reports[self.current_report]['DatesConfidence']==0:
                ab2 = AnnotationBbox(self.imbox_sick, [xOnset, yOnset], frameon=True, pad=0.1)
            else:
                ab2 = AnnotationBbox(self.imbox_sick, [xOnset, yOnset], frameon=False, pad=0.1)
            axes.add_artist(ab2)       
            
            self.tooltipData_addon[(xOnset, yOnset, dx, dy)]='Date of Onset'

    def feature_axis_process(self, selectedFeatures):   
        
        features = self.reports[self.current_report]['Features']

        occupancy = {}
        for feat in features:
            if not feat.getType() in selectedFeatures or not feat.hasStartTime():
                continue
            
            yi = selectedFeatures.index(feat.getType()) # + 1
            xi = feat.getStartTime()
            
            plotType = self.comboPlotContent.currentText()
            
            numrows = 1
            if plotType=="Multi-line Text" or plotType=="Split Feature Text":
                singles = re.split(', | and ', feat.getString())
                numrows = len(singles)
        
            if (xi,yi) in occupancy:
                occupancy[(xi,yi)] += numrows
            else:
                occupancy[(xi,yi)] = numrows
        
        maxCount = range(len(selectedFeatures))
        for loc in occupancy:
            if occupancy[loc] > maxCount[loc[1]]:
                maxCount[loc[1]] = occupancy[loc]
                
        if maxCount:
            maxCount[0] += 1 # make more room for the bottom feature
            
        yticks = [0]
        for n in maxCount:
            yticks.append(yticks[-1] + n)
        
        yticklabels = ['']
        for feat in selectedFeatures:
            featname = dictFeatureAbr[feat]
            if featname=='':
                featname = dictFeatureNamesInv[feat]
            
            tokens = featname.split()
            if len(tokens)>1 and tokens[0]!='Selected':
                featname = tokens[0]+'...'
                
            yticklabels.append(featname)
        
        ylim = [0, yticks[-1] * 1.2]
        if ylim[1]==0:
            ylim[1]=1
        
        self.feature_ticks = yticks        
        return (yticks, yticklabels, ylim)       

    def time_axis_process(self, featSet):        
        features = self.reports[self.current_report]['Features']
        expDate = self.reports[self.current_report]['Exposure Date']
        onsetDate = self.reports[self.current_report]['Onset Date']

        tStart = [feat[3] for feat in features if feat[0] in featSet and feat[3]]
        tEnd = [feat[4] for feat in features if feat[0] in featSet and feat[4]]
         
        ts = tStart + tEnd
         
        ti = list(set(ts))
        if expDate and not expDate in ti:
            ti = [expDate] + ti
        if onsetDate and not onsetDate in ti:
            ti = [onsetDate] + ti
        ti.sort()
        
        dt = 3600*24
        xi = [(t-expDate).total_seconds()/dt for t in ti]
        
        num = len(ti)
        # create ticklabels
        if self.comboAxis.currentText()=='Date':
            sameyear = True
            for i in range(1,num):
                if ti[i].year!=ti[i-1].year:
                    sameyear = False
                    break
            if sameyear:
                samemonth = True
                for i in range(1,num):
                    if ti[i].month!=ti[i-1].month:
                        samemonth = False
                        break        
            if sameyear: 
                if samemonth:
                    labelAll = datetime_strftime(ti[0],'m') #ti[0].strftime('%b, %Y')
                    labels = [datetime_strftime(t,'d', True) for t in ti]
                else:
                    labelAll = datetime_strftime(ti[0],'y') #ti[0].strftime('%Y')
                    labels = [datetime_strftime(t,'m/d') for t in ti]
            else:
                labelAll = ''
                labels = [datetime_strftime(t) for t in ti]
        else:
            labelsNeg = ['-day '+str(int(round(-x))) for x in xi if x<0]
            labelsPos = ['day '+str(int(round(x))) for x in xi if x>0]
            labels = labelsNeg + ['Exposure'] + labelsPos
            labelAll = 'Day'
        
        xi =[x - xi[0] for x in xi]
        
        coord_mapping = {}
        if not self.checkCompressAxis.isChecked():
            for i in range(num):
                coord_mapping[ti[i]] = xi[i]
            ticks = xi
            ticklabels = labels
        else:
            # assume the minimum delta is 1 (day)
            interval_allowed = 2    
            coord_mapping[ti[0]] = xi[0]
            ticks = [xi[0]]
            curpt = xi[0]
            ticklabels = [labels[0]]
            for i in range(1,num):
                if xi[i] - xi[i-1] < interval_allowed:
                    coord_mapping[ti[i]] = coord_mapping[ti[i-1]]+xi[i]-xi[i-1]
                    ticks.append(coord_mapping[ti[i]])
                    ticklabels.append(labels[i])
                elif xi[i] - xi[i-1] == interval_allowed:
                    ticks.append(coord_mapping[ti[i-1]] + 1)
                    ticklabels.append(r'${\longrightarrow}$')
                    coord_mapping[ti[i]] = coord_mapping[ti[i-1]]+xi[i]-xi[i-1]
                    ticks.append(coord_mapping[ti[i]])
                    ticklabels.append(labels[i])
                else:
                    ticks.append(coord_mapping[ti[i-1]] + 1)
                    #ticklabels.append('...')
                    #ticklabels.append('${\displaystyle \mathbf{\sim}}$')
                    ticklabels.append(r'${\longrightarrow}$')
                    coord_mapping[ti[i]] = coord_mapping[ti[i-1]] + 2
                    ticks.append(coord_mapping[ti[i]])
                    ticklabels.append(labels[i])
        
        ticks = ticks + [ticks[-1]+1]
        ticklabels = ticklabels + [labelAll] 
#         ticks = [t+0.5 for t in ticks]

        self.timeline = ti
        self.time_coord_map = coord_mapping
        self.time_ticks = ticks 
        xlim = self.set_time_range(ti, ticks, coord_mapping)
        
        return (coord_mapping, ticks, ticklabels, xlim)         
    
    def time_axis_process_2layer_label(self, featSet):        
        
        features = self.reports[self.current_report]['Features']
        expDate = self.reports[self.current_report]['Exposure Date']
        onsetDate = self.reports[self.current_report]['Onset Date']

        tStart = [feat.getStartTime() for feat in features if feat.getType() in featSet and feat.hasStartTime()]
        tEnd = [feat.getEndTime() for feat in features if feat.getType() in featSet and feat.hasEndTime()]
         
        ts = tStart + tEnd
        
        if not ts or not expDate:
            return (None, None, None, None)
         
        ti = list(set(ts))
        if expDate and not expDate in ti:
            ti = [expDate] + ti
        if onsetDate and not onsetDate in ti:
            ti = [onsetDate] + ti
        ti.sort()
        
        dt = 3600*24
        xi = [(t-expDate).total_seconds()/dt for t in ti]
        
#         if expDate:
#             x0 = int((expDate-t0).total_seconds()/dt)+1 
#             xi = [x-x0 for x in xi]
        
        num = len(ti)
        sameyear = True
        for i in range(1,num):
            if ti[i].year!=ti[i-1].year:
                sameyear = False
                break
        if sameyear:
            samemonth = True
            for i in range(1,num):
                if ti[i].month!=ti[i-1].month:
                    samemonth = False
                    break        
        if sameyear: 
            if samemonth:
                labelAllDate = datetime_strftime(ti[0],'m') #ti[0].strftime('%b, %Y')
                labelsDate = [datetime_strftime(t,'d', True) for t in ti]
            else:
                labelAllDate = datetime_strftime(ti[0],'y') #ti[0].strftime('%Y')
                labelsDate = [datetime_strftime(t,'m/d') for t in ti]
        else:
            labelAllDate = ''
            labelsDate = [datetime_strftime(t) for t in ti]
            
        labelsNeg = ['-day '+str(int(round(-x))) for x in xi if x<0]
        labelsPos = ['day '+str(int(round(x))) for x in xi if x>0]
        labelsDay = labelsNeg + ['Exposure (day 0)'] + labelsPos
        #labelAllDay = 'Day'
        labelAllDay = ''
        
        if self.comboAxis.currentText()=='Date':
            labels = [labelsDate[i]+'\n'+labelsDay[i] for i in range(len(labelsDate))]
            labelAll = labelAllDate + '\n' + labelAllDay
        else:
            labels = [labelsDay[i]+'\n'+labelsDate[i] for i in range(len(labelsDate))]
            labelAll = labelAllDay + '\n' + labelAllDate
            
        
        xi =[x - xi[0] for x in xi]
        
        coord_mapping = {}
        if not self.checkCompressAxis.isChecked():
            for i in range(num):
                coord_mapping[ti[i]] = xi[i]
            ticks = xi
            ticklabels = labels
        else:
            # assume the minimum delta is 1 (day)
            interval_allowed = 2    
            coord_mapping[ti[0]] = xi[0]
            ticks = [xi[0]]
            curpt = xi[0]
            ticklabels = [labels[0]]
            for i in range(1,num):
                if xi[i] - xi[i-1] < interval_allowed:
                    coord_mapping[ti[i]] = coord_mapping[ti[i-1]]+xi[i]-xi[i-1]
                    ticks.append(coord_mapping[ti[i]])
                    ticklabels.append(labels[i])
                elif xi[i] - xi[i-1] == interval_allowed:
                    ticks.append(coord_mapping[ti[i-1]] + 1)
                    ticklabels.append(r'${\longrightarrow}$')
                    coord_mapping[ti[i]] = coord_mapping[ti[i-1]]+xi[i]-xi[i-1]
                    ticks.append(coord_mapping[ti[i]])
                    ticklabels.append(labels[i])
                else:
                    ticks.append(coord_mapping[ti[i-1]] + 1)
                    ticklabels.append(r'${\longrightarrow}$')
                    coord_mapping[ti[i]] = coord_mapping[ti[i-1]] + 2
                    ticks.append(coord_mapping[ti[i]])
                    ticklabels.append(labels[i])
        
        ticks = ticks + [ticks[-1]+1]
        ticklabels = ticklabels + [labelAll] 

        self.timeline = ti
        self.time_coord_map = coord_mapping
        self.time_ticks = ticks 
        xlim = self.set_time_range(ti, ticks, coord_mapping)
        
        ticks = [t+0.5 for t in ticks]
        ticks[-1] -= 0.5
        return (coord_mapping, ticks, ticklabels, xlim)       
    
    def set_time_range(self, ti, ticks, coord_mapping):        
        
        expDate = self.reports[self.current_report]['Exposure Date']
        secDay = datetime.timedelta(days=1).total_seconds()             

        if not self.is_time_range_applied:
            tFrom = ti[0]
            tTo = ti[-1]
            xlim = [ticks[0],ticks[-1]]
        else:
            if self.comboAxis.currentText()=='Date':
                tFrom = self.textRangeFrom.dateTime().toPython()
                tTo = self.textRangeTo.dateTime().toPython()
            else:            
                dayFrom = self.spinDayFrom.value()
                dayTo = self.spinDayTo.value()
                tFrom = expDate + datetime.timedelta(days=dayFrom)
                tTo = expDate + datetime.timedelta(days=dayTo)
            
            if tFrom > tTo:
                QMessageBox.critical(QMessageBox(), "VaeTM", "Time Range Invalid!")
            
            if not tFrom in coord_mapping:
                tafter = [t for t in coord_mapping if t>=tFrom]
                tFrom = min(tafter)
             
            if not tTo in coord_mapping:
                tbefore = [t for t in coord_mapping if t<=tTo]
                tTo = max(tbefore)
    
            tickFrom = coord_mapping[tFrom]     
            tickTo = coord_mapping[tTo]                   
            tickTo = ticks[ticks.index(tickTo)+1]     
            xlim = [tickFrom, tickTo]
             
        self.time_range = (tFrom, tTo)
        self.update_time_range_widget()
        return xlim
    
    def get_time_unit_days(self, strUnit):
        #strUnit = self.comboAxisUnit.currentText()
        if strUnit=='Day':
            timeunit = 1
        elif strUnit=='Week':
            timeunit = 7.
        elif strUnit=='Month':
            timeunit = 30.
        elif strUnit=='Year':
            timeunit = 365.
        
        return timeunit
    
    def time_axis_process_unit(self, featSet):        
        
        features = self.reports[self.current_report]['Features']
        expDate = self.reports[self.current_report]['Exposure Date']
        onsetDate = self.reports[self.current_report]['Onset Date']
         
        tStart = [feat[3] for feat in features if feat[0] in featSet and feat[3]]
        tEnd = [feat[4] for feat in features if feat[0] in featSet and feat[4]]
         
        ts = tStart + tEnd
         
        ti = list(set(ts))
        if expDate and not expDate in ti:
            ti = [expDate] + ti
        if onsetDate and not onsetDate in ti:
            ti = [onsetDate] + ti
        ti.sort()
        
        # Find minimal time step, and use it for  
        minDelta = datetime.timedelta(days=1)             
        #=======================================================================
        # if len(ti)>1:
        #     minDelta = ti[1] - ti[0]
        #     for i in range(2, len(ti)):
        #         if ti[i]-ti[i-1]<minDelta:
        #             minDelta = ti[i]-ti[i-1]
        # # set minimum time interval as one day
        # if minDelta < datetime.timedelta(days=1):
        #     minDelta = datetime.timedelta(days=1)
        #=======================================================================
        
        dt = minDelta.total_seconds()
        xi = [int((t-expDate).total_seconds()/dt) for t in ti]
        
        num = len(ti)
        # create ticklabels
        if self.comboAxis.currentText()=='Date':
            sameyear = True
            for i in range(1,num):
                if ti[i].year!=ti[i-1].year:
                    sameyear = False
                    break
            if sameyear:
                samemonth = True
                for i in range(1,num):
                    if ti[i].month!=ti[i-1].month:
                        samemonth = False
                        break        
   
            if sameyear: 
                if samemonth:
                    labelAll = datetime_strftime(ti[0],'m') #ti[0].strftime('%b, %Y')
                    labels = [datetime_strftime(t,'d', True) for t in ti]
                else:
                    labelAll = datetime_strftime(ti[0],'y') #ti[0].strftime('%Y')
                    labels = [datetime_strftime(t,'m/d') for t in ti]
            else:
                labelAll = ''
                labels = [datetime_strftime(t) for t in ti]    
        else:
            labelsNeg = ['-day '+str(-x) for x in xi if x<0]
            labelsPos = ['day '+str(x) for x in xi if x>0]
            labels = labelsNeg + ['Vax'] + labelsPos
            labelAll = 'Day'
        
        xi =[x - xi[0] for x in xi]
        
        coord_mapping = {}
        if not self.checkCompressAxis.isChecked():
            for i in range(num):
                coord_mapping[ti[i]] = xi[i]
            ticks = xi
            ticklabels = labels
        else:
            # assume the minimum delta is 1 (day)
            interval_allowed = 2    
            coord_mapping[ti[0]] = xi[0]
            ticks = [xi[0]]
            curpt = xi[0]
            ticklabels = [labels[0]]
            for i in range(1,num):
                if xi[i] - xi[i-1] <= interval_allowed:
                    coord_mapping[ti[i]] = coord_mapping[ti[i-1]]+xi[i]-xi[i-1]
                    ticks.append(coord_mapping[ti[i]])
                    ticklabels.append(labels[i])
                else:
                    ticks.append(coord_mapping[ti[i-1]] + 1)
                    ticklabels.append(r'${\longrightarrow}$')
                    coord_mapping[ti[i]] = coord_mapping[ti[i-1]] + 2
                    ticks.append(coord_mapping[ti[i]])
                    ticklabels.append(labels[i])
        
        ticks = ticks + [ticks[-1]+1]
        ticklabels = ticklabels + [labelAll] 

        self.time_coord_map = coord_mapping
        self.time_ticks = ticks 
        xlim = self.set_time_range(ti, ticks, coord_mapping)
        
        return (coord_mapping, ticks, ticklabels, xlim)      

    def set_time_range_unit(self, ti, ticks, coord_mapping, timeunit):        
#         expDate = self.reports[self.current_report]['Exposure Date']
#         secDay = datetime.timedelta(days=1).total_seconds()             

        if not self.is_time_range_applied:
            tFrom = ti[0]
            tTo = ti[-1]
            xlim = [ticks[0], ticks[-1]]
        else:
            if self.comboAxis.currentText()=='Date':
                tFrom = self.textRangeFrom.dateTime().toPython()
                tTo = self.textRangeTo.dateTime().toPython()
            else:            
                tFrom = timeunit * self.spinDayFrom.value()
                tTo = timeunit * self.spinDayTo.value()
            
            if tFrom > tTo:
                QMessageBox.critical(QMessageBox(), "VaeTM", "Time Range Invalid!")
            
            if not tFrom in coord_mapping:
                tafter = [t for t in coord_mapping if t>=tFrom]
                tFrom = min(tafter)
            
            if not tTo in coord_mapping:
                tbefore = [t for t in coord_mapping if t<=tTo]
                tTo = max(tbefore)
    
            tickFrom = coord_mapping[tFrom]     
            tickTo = coord_mapping[tTo]                            
            tickTo = tickTo + 1                        
            xlim = [tickFrom, tickTo]
             
        self.time_range = (tFrom, tTo)
        self.update_time_range_widget_unit(timeunit)
        return xlim
    
                
    def set_current_report(self, current_report):
        self.current_report = current_report
      
        if  current_report < 0 or current_report >= len(self.reports):
            self.fig.clf()
            self.canvas.draw()
            self.set_feature_checkboxes([])
            return
        
        # Only features with temporal datetime can be plotted. These features are save in a dictionary, 
        # dictionary value indicates if the feature is selected or not. The dictionary  is saved 
        # in a report field. When the report is currently visible, previously selected features will be plotted. 
        if 'SelectedFeatures' in self.reports[current_report]:
            featDict = self.reports[current_report]['SelectedFeatures']
        else:
            # Find features with valid temporal information
            #featTlinks = self.reports[current_report]['TLinks']
            features = self.reports[current_report]['Features']
            sFeat = []
            for i, feat in enumerate(features):
                if feat.hasStartTime():
                    sFeat.append(feat.getType())
            featSetStr = list(set(sFeat))
            featDict = {}
            for feat in featSetStr:
                #if feat!='TIME_TO_ONSET':
                if feat in dictFeatureNames.values():
                    featDict[feat] = True
            self.reports[current_report]['SelectedFeatures'] = featDict
            
        self.set_feature_checkboxes(featDict)
        
        if self.comboAxis.currentText()=='Date':
            self.is_time_range_applied = False
        else:
            self.spinDayFrom.setValue(0)
            self.spinDayTo.setValue(self.defaut_day_range)       
            self.is_time_range_applied = True
        
        self.plot()
    
    def set_feature_checkboxes(self, featDict):
        
        feats = [(feat, self.allFeatures.index(feat)) for feat in featDict if feat in dictFeatureNames.values()]
        feats.sort(key = lambda f:f[1])
        
        if self.featureGroup.layout().count() > 0:
            preAggregateState = self.checkAggregated.checkState()
        else:
            preAggregateState = None
            
        self.clearLayout(self.featureGroup.layout()) 
        
        isAllChecked = True
        for feat in feats:
            if dictFeatureAbr[feat[0]]!='':
                featname =  dictFeatureNamesInv[feat[0]] + ' ('+dictFeatureAbr[feat[0]] +')'
            else:
                featname =  dictFeatureNamesInv[feat[0]]
            checkBox = QCheckBox(featname)
            if featDict[feat[0]]:
                checkBox.setChecked(True)
            else:
                isAllChecked = False
            self.featureGroup.layout().addWidget(checkBox)
    
        self.checkAll = QCheckBox("All")
        if isAllChecked:
            self.checkAll.setChecked(True)
        self.featureGroup.layout().addWidget(self.checkAll)
        
        self.checkAggregated = QCheckBox("Aggregate")
        if preAggregateState:
            self.checkAggregated.setCheckState(preAggregateState)
        self.featureGroup.layout().addWidget(self.checkAggregated)
        if self.comboPlotContent.currentText()=='Line Plot':
            self.checkAggregated.setEnabled(True)
        else:
            self.checkAggregated.setEnabled(False)
            
        # use 'clicked' signal instead of 'state_changed'. otherwise, "All" checkbox will 
        # intrigue all other checkboxes' signals 
        self.checkAll.clicked.connect(self.checkbox_all_clicked)
        self.checkAggregated.clicked.connect(self.plot)
        for i in range(self.featureGroup.layout().count()-2): 
            self.featureGroup.layout().itemAt(i).widget().clicked.connect(self.checkbox_clicked)
            
    def checkbox_all_clicked(self):
        if self.checkAll.isChecked():
            for i in range(self.featureGroup.layout().count()-2): 
                self.featureGroup.layout().itemAt(i).widget().setChecked(True)
                text = self.featureGroup.layout().itemAt(i).widget().text()
                loc = text.find('(')
                if loc>=0:
                    text = text[:loc-1]
                self.reports[self.current_report]['SelectedFeatures'][dictFeatureNames[text]] = True
        else:
            for i in range(self.featureGroup.layout().count()-2): 
                self.featureGroup.layout().itemAt(i).widget().setChecked(False)
                text = self.featureGroup.layout().itemAt(i).widget().text()
                loc = text.find('(')
                if loc>=0:
                    text = text[:loc-1]
                self.reports[self.current_report]['SelectedFeatures'][dictFeatureNames[text]] = False
        
        self.time_range = None
        self.plot()
        
    def checkbox_clicked(self):
        #selectedReports = self.mainWindow.selectedReportIndices
        isAllChecked = True
        for i in range(self.featureGroup.layout().count()-2): 
            text = self.featureGroup.layout().itemAt(i).widget().text()
            state = self.featureGroup.layout().itemAt(i).widget().checkState()
            #self.reports[selectedReports[self.current_report]]['SelectedFeatures'][feat] = state       
            loc = text.find('(')
            if loc>=0:
                text = text[:loc-1]
            self.reports[self.current_report]['SelectedFeatures'][dictFeatureNames[text]] = state            
            if not state:
                isAllChecked = False
        
        if isAllChecked:
            self.checkAll.setChecked(True)
        else:
            self.checkAll.setChecked(False)
        
        self.time_range = None
        self.plot()

    # Wrap the string in multiple lines for given length and rows. 
    # If the string is beyond give rows, the rest will be chopped and replaced with '...'
    def wrap_string(self, s, length, rows):
        tokens = s.split(' ')
        
        r = 0
        margin = 3
        out = tokens[0]
        cur = len(out)
        for t in tokens[1:]:
            if r >= rows:
                out = out[:-3]+'...'
                break
            
            if cur+len(t) <= length:
                if cur==0: # first word in this line, skip the space
                    out += t
                else:
                    out += ' ' +t
                cur += len(t)
            # only less then margin letters left, keep it in this line
            elif cur+len(t)-length <= margin: 
                out += ' ' + t + '\n'
                cur = 0
                r += 1
            # only less then margin letters kept in this line, move the whole word to the next line
            elif length-cur <= margin:
                out += '\n' + t
                r += 1
                cur = len(t)
            else:
                if r < rows: # break this word by '-'
                    out += ' ' + t[:length-cur] + '-\n' + t[length-cur:]
                else: # limit reached, replace this word by '...', and break
                    out += ' ' + t[:length-cur]
                    out = out[:-3]+'...'
                    break                
                cur = length-cur
                r += 1
        
        # remove the last '\n' if existing
        if out[-1:]=='\n':
            out = out[:-1]
            
        return out
     
    # clear all widgets in a layout. 
    def clearLayout(self, layout):
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clearLayout(item.layout())
    
    def chop_string(self, s, lenPoint):
        lenPoint = lenPoint*1.1
        
        if self.textFontManager.measure('...') > lenPoint:
            return '...'
        
        if self.textFontManager.measure(s)>lenPoint:
            s = s[:-2]+'...'
            
        while self.textFontManager.measure(s)>lenPoint:
            s = s[0:-4]+'...'
            
        return s

class ReportGroupAnalysisPlot(QFrame):
    def __init__(self, reports = [], mainWin=None):
        super(ReportGroupAnalysisPlot, self).__init__(mainWin)
        self.reports = reports
        self.mainWindow = mainWin
        
        self.plot_flag = False

        self.plotFrame = QFrame()
        
        self.optionFrame = QGroupBox()
        self.optionFrame.setLayout(QVBoxLayout())
        self.optionFrame.setTitle('Setting Panel')
        self.optionFrame.setToolTip('Setting Panel (Ctrl+H to hide)')
        
        #######################################################
        ##### Feature checkboxes
        self.featureGroup = QGroupBox()
        self.featureGroup.setLayout(QVBoxLayout())
        self.featureGroup.setTitle("Feature Types")
        self.featureGroup.setToolTip('Select features to plot')
        
        self.strFeatures = ["DIAGNOSIS", "CAUSE_OF_DEATH", "SECOND_LEVEL_DIAGNOSIS", "SYMPTOM", 
                       "RULE_OUT", "MEDICAL_HISTORY", "FAMILY_HISTORY", "DRUG", "VACCINE"]

        for feat in self.strFeatures:
            if dictFeatureAbr[feat]!='':
                featname =  dictFeatureNamesInv[feat] + ' ('+dictFeatureAbr[feat] +')'
            else:
                featname =  dictFeatureNamesInv[feat]
            checkBox = QCheckBox(featname)
            checkBox.clicked.connect(self.checkbox_clicked)
            self.featureGroup.layout().addWidget(checkBox)
        
        self.checkAll = QCheckBox("All Feature Types")
        self.checkAll.clicked.connect(self.checkbox_all_clicked)
        self.featureGroup.layout().addWidget(self.checkAll)
            
        self.checkAggregated = QCheckBox("Aggregate")
        self.checkAggregated.clicked.connect(self.plot)
        self.featureGroup.layout().addWidget(self.checkAggregated)
        self.set_feature_checkboxes()
        
        ##############################################
        typeFrame = QFrame()
        typeFrame.setLayout(QHBoxLayout())
        self.comboPlotContent = QComboBox()
        self.comboPlotContent.addItems([ "Line plot (Report counts vs. time/age)",
                                        "Line plot (Feature counts vs. time/age)", "Lasagna plot(Feature counts per case vs. time/age)"])
        self.comboPlotContent.setToolTip('Select plot type')
        self.comboPlotContent.setCurrentIndex(0)
        self.comboPlotContent.currentIndexChanged.connect(self.plot)
        
        typeFrame.layout().addWidget(QLabel('Plot Type:'))
        typeFrame.layout().addWidget(self.comboPlotContent)
        typeFrame.layout().setStretch(0, 1)
        typeFrame.layout().setStretch(1, 10)
        
        #### Time axis control #######################
        self.timeGroup = QGroupBox()
        self.timeGroup.setLayout(QGridLayout())
        self.timeGroup.setTitle("Time Axis (Feature Occurrence)")
        self.timeGroup.setToolTip("Set time axis options")
        
        self.comboAxis = QComboBox()
        self.comboAxis.addItems(['From Exposure', 'Date of Occurrence', 'Age at Occurrence'])
        self.comboAxis.setToolTip('Select time axis type')
        self.comboAxis.currentIndexChanged.connect(self.on_timeaxis_changed)
        self.comboAxis.setCurrentIndex(0)   
        
        self.checkCompressAxis = QCheckBox('Compressed')
        self.checkCompressAxis.setToolTip('Compress time axis by removing large intervals')
        self.checkCompressAxis.setChecked(True)
        self.checkCompressAxis.clicked.connect(self.plot)
        self.textRangeFrom = QDateEdit()
        self.textRangeFrom.setCalendarPopup(True)
        self.textRangeFrom.setDisplayFormat('MM/dd/yyyy')
        #self.textRangeFrom.setFixedWidth(65)
        self.textRangeTo = QDateEdit()
        self.textRangeTo.setCalendarPopup(True)
        self.textRangeTo.setDisplayFormat('MM/dd/yyyy')
        
        self.spinDayFrom = QSpinBox()
        self.spinDayFrom.setPrefix('Day ')
        self.spinDayFrom.setMinimum(-36000)
        self.spinDayFrom.setMaximum(36000)
        self.spinDayTo = QSpinBox()
        self.spinDayTo.setPrefix('Day ')
        self.spinDayTo.setMinimum(-36000)
        self.spinDayTo.setMaximum(36000)
        
        #### Set initial value for time range widgets
        self.spinDayFrom.setValue(0)
        self.spinDayTo.setValue(28)        
        self.time_range_vax = [0, 28, None, None] # (current range and full range)
        self.time_range_date = None
        self.time_range_age = None
    
        self.stackedFrom = QStackedWidget()
        self.stackedFrom.addWidget(self.spinDayFrom)
        self.stackedFrom.addWidget(self.textRangeFrom)
        self.stackedFrom.setCurrentIndex(0)
        
        self.stackedTo = QStackedWidget()
        self.stackedTo.addWidget(self.spinDayTo)
        self.stackedTo.addWidget(self.textRangeTo)
        self.stackedTo.setCurrentIndex(0)    
        self.btnRestoreRange = QPushButton('Full Range')
        self.btnRestoreRange.setToolTip('Restore time axis to full range')
        self.btnApplyRange = QPushButton('Apply')
        self.btnApplyRange.setToolTip('Apply time range to time axis')
        self.btnApplyRange.clicked.connect(self.apply_time_range)
        self.btnRestoreRange.clicked.connect(self.on_restore_time_range_clicked)
        self.comboAxisUnit = QComboBox()
        self.comboAxisUnit.addItems(['Day', 'Week', 'Month', 'Year'])
        self.comboAxisUnit.setToolTip('Select time axis unit')
        self.comboAxisUnit.setCurrentIndex(0)
        self.comboAxisUnit.currentIndexChanged.connect(self.onTimeUnitChanged)

        self.timeGroup.layout().addWidget(QLabel('Axis:'), 0, 0)
        self.timeGroup.layout().addWidget(self.comboAxis, 0, 1)
        self.timeGroup.layout().addWidget(QLabel('in'), 0, 2)
        self.timeGroup.layout().addWidget(self.comboAxisUnit, 0, 3)
        self.timeGroup.layout().addWidget(self.checkCompressAxis, 0, 4)
        self.timeGroup.layout().addWidget(QLabel('From:'), 1, 0)
        self.timeGroup.layout().addWidget(QLabel('To:'), 2, 0)
        self.timeGroup.layout().addWidget(self.stackedFrom, 1, 1, 1, 3)
        self.timeGroup.layout().addWidget(self.stackedTo, 2, 1, 1, 3)
        self.timeGroup.layout().addWidget(self.btnRestoreRange, 1, 4)
        self.timeGroup.layout().addWidget(self.btnApplyRange, 2, 4)
        self.timeGroup.layout().setColumnStretch(0,4)
        self.timeGroup.layout().setColumnStretch(1,40)
        self.timeGroup.layout().setColumnStretch(2,1)
        self.timeGroup.layout().setColumnStretch(3,4)
        self.timeGroup.layout().setColumnStretch(4,4)
        
        ####################################################
        self.optionFrame.layout().addWidget(self.featureGroup)
        self.optionFrame.layout().addWidget(typeFrame)
        self.optionFrame.layout().addWidget(self.timeGroup)
        self.optionFrame.layout().setStretch(0, 10)
        self.optionFrame.layout().setStretch(1, 1)
        
        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self.plotFrame)
        self.layout().addWidget(self.optionFrame)
        self.layout().setStretch(0, 80)
        self.layout().setStretch(1, 1)      
        self.layout().setStretch(1, 5)        
        
        # Initialize plot area
        self.dpi = 72          
        self.fontsize = 12
        self.x_offset = 0.05
        self.y_offset = 0.2
        self.textfontsize = 12
        self.linewidth = 4
        self.textFontManager = tkFont.Font(root=tk.Tk(), family='sans-serif', size=self.textfontsize)
        self.pickRadius = (.5, .5)
        
        self.fig = Figure(dpi=self.dpi, facecolor='w', tight_layout=True)
        #self.fig = Figure(facecolor='w', tight_layout=True)
        self.canvas = FigureCanvas(self.fig)   
        self.timeline = None
        self.feature_count_range_for_line_plot = 0
        
        layout=QVBoxLayout()
        self.plotFrame.setLayout(layout)
        layout.addWidget(self.canvas)
        
        im_syringe = read_png("./syringe1.png")
        self.imbox_syringe = OffsetImage(im_syringe, zoom=0.2)
        im_sick = read_png("./sick.png")
        self.imbox_sick = OffsetImage(im_sick, zoom=0.125)
        #self.plot_temporal()
        
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_motion)
        #self.canvas.mpl_connect('scroll_event', self.zoom_fun)
        self.canvas.mpl_connect('resize_event', self.on_resize)
    
    def on_timeaxis_changed(self):
        if 'Age' in self.comboAxis.currentText():
            self.comboAxisUnit.setCurrentIndex(3)
        else:
            self.comboAxisUnit.setCurrentIndex(0)
        self.plot()        
        
    def on_resize(self, event):
        self.plot()        
        # because tooltip data is based on axes information, which is not totally created yet in the first call
        # after resizing, thus call second time to adjust tooltip data to be more accurate         
        #self.plot() 
    
    def zoom_fun(self, event):
        # get the current x and y limits
        base_scale = 1.5
        ax = self.fig.axes[0]
        cur_xlim = ax.get_xlim()
        cur_ylim = ax.get_ylim()
        cur_xrange = (cur_xlim[1] - cur_xlim[0])*.5
        cur_yrange = (cur_ylim[1] - cur_ylim[0])*.5
        xdata = event.xdata # get event x location
        ydata = event.ydata # get event y location
        if event.button == 'up':
            # deal with zoom in
            scale_factor = 1/base_scale
        elif event.button == 'down':
            # deal with zoom out
            scale_factor = base_scale
        else:
            # deal with something that should never happen
            scale_factor = 1
            print event.button
        # set new limits
        ax.set_xlim([xdata - cur_xrange*scale_factor,
                     xdata + cur_xrange*scale_factor])
        ax.set_ylim([ydata - cur_yrange*scale_factor,
                     ydata + cur_yrange*scale_factor])
        #ax.grid(True)
        self.canvas.draw()
        
    def on_mouse_motion(self, event):
        
        if not event.xdata or not event.ydata:
            self.canvas.setToolTip(None)
            return
        
        self.canvas.setToolTip(None)

        (rx, ry) = self.pickRadius
        dmin = 1e10
        minloc = None
        for loc in self.tooltipData:
            if abs(event.xdata-loc[0])<=rx and abs(event.ydata-loc[1])<=ry:
                d = (event.xdata-loc[0])*(event.xdata-loc[0]) + (event.ydata-loc[1])*(event.ydata-loc[1])
                if d < dmin:
                    dmin = d
                    minloc = loc
        if minloc:
            tooltip =  self.tooltipData[minloc]
            self.canvas.setToolTip(tooltip)
            return
            
        self.canvas.setToolTip(None)
        
    def apply_time_range(self):
        self.plot()
        
    def on_restore_time_range_clicked(self):
        
        axisType = self.comboAxis.currentText()
        if axisType=='Age at Occurrence':
            self.time_range_age = None
        elif axisType=='Date of Occurrence':
            self.time_range_date = None
        else:
            self.time_range_vax = None

        self.plot()
        return
    
    def update_time_range_widget(self, timeUnit=None):
        
        if not timeUnit:
            timeUnit = self.get_time_unit_days(self.comboAxisUnit.currentText())
            
        axisType = self.comboAxis.currentText()
        if axisType == 'Date of Occurrence':
            self.stackedFrom.setCurrentIndex(1)
            self.stackedTo.setCurrentIndex(1)

            self.textRangeFrom.setDate(self.time_range_date[0])
            self.textRangeTo.setDate(self.time_range_date[1])
                
            if self.time_range_date[0]==self.timeline[0] and  self.time_range_date[1]==self.timeline[-1]:
                self.btnRestoreRange.setDisabled(True)
            else:
                self.btnRestoreRange.setDisabled(False)
            
        else: #if self.comboAxis.currentText()=='From Exposure':
            self.stackedFrom.setCurrentIndex(0)
            self.stackedTo.setCurrentIndex(0)
            if axisType=='Age at Occurrence':
                time_range = self.time_range_age
            else: # axisType=='From Exposure':
                time_range = self.time_range_vax
                
            if time_range and not isinstance(time_range[0], datetime.datetime):
                tFrom = int(time_range[0]/timeUnit)
                tTo = int(math.ceil(time_range[1]/timeUnit))
            
                self.spinDayFrom.setValue(tFrom)
                self.spinDayTo.setValue(tTo)
                
            if time_range and time_range[0]==self.timeline[0] and  time_range[1]==self.timeline[-1]:
                self.btnRestoreRange.setDisabled(True)
            else:
                self.btnRestoreRange.setDisabled(False)
        
    def onTimeUnitChanged(self):
        strUnit = self.comboAxisUnit.currentText()
        self.spinDayFrom.setPrefix(strUnit + ' ')
        self.spinDayTo.setPrefix(strUnit + ' ')
        
        self.update_time_range_widget()
        
        self.plot()
            
    def plot(self):  
        self.tooltipData_addon = []
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))

        index = self.comboPlotContent.currentIndex()
        if index == 2: #"Lasagna Plot":
            if self.mainWindow.sysPreferences.toSortLasagna():
                self.plot_lasagna_in_range_only()
            else:
                self.plot_lasagna_unsorted()
        elif index == 1:
            self.plot_linecurve_in_range_only()
        else:
            self.plot_linecurve_report_count()
                
        QApplication.restoreOverrideCursor()       
        
    
    def plot_lasagna_unsorted(self):
        self.fig.clf()
        axes = self.fig.add_subplot(111)

        strTimeUnit = self.comboAxisUnit.currentText()        
        axisType = self.comboAxis.currentText()
        
        featLists = []
        plotNames = []
        if not self.checkAggregated.isChecked():
            for i in range(self.featureGroup.layout().count()-2): 
                if self.featureGroup.layout().itemAt(i).widget().checkState():
                    text = self.featureGroup.layout().itemAt(i).widget().text()
                    loc = text.find('(')
                    if loc>=0:
                        text = text[:loc-1]
                    strFeat = dictFeatureNames[text]
                    featLists.append([strFeat])
            featLists.sort(key=lambda x:self.strFeatures.index(x[0]), reverse=True)
            for feat in featLists:
                featname = dictFeatureAbr[feat[0]]
                if featname=='':
                    featname = dictFeatureNamesInv[feat[0]]
                plotNames.append(featname)
        else:
            featList = []
            for i in range(self.featureGroup.layout().count()-2): 
                if self.featureGroup.layout().itemAt(i).widget().checkState():
                    featList.append(dictFeatureNames[self.featureGroup.layout().itemAt(i).widget().text()])
            featLists.append(featList)
            plotNames.append('Selected Feature Types')
        
        ts = []
        allPlots = []
        allTooltips = []
        ti_plots = []
        featList = []
        for featList in featLists:
            (curves, tooltips, tsi) = self.get_multi_report_curves(featList, axisType, True)
            if not curves: 
                continue
            
            allPlots.append(curves)
            allTooltips.append(tooltips)
            ti_plots.append(tsi)
            ts += tsi
            
        ####################################################################
        ## create time axis
        #################################################################
        if len(ts)==0:
            self.canvas.draw()
            return
        
        ti = list(set(ts))
        ti.sort()
        self.timeline = ti
         
        (xmap, ticks, ticklabels, xlim)=self.create_coord_mapping(ti, axisType, strTimeUnit)

        ###################
        ## process xlabel and xticklabels  
        if xlim[0]==xlim[1]:
            xlim[1] = xlim[0]+1
        
        if axisType=='Age at Occurrence':
            axes.set_xlabel('Age at Occurrence (' + strTimeUnit + ')')
        elif axisType=='From Exposure':
            axes.set_xlabel('From Exposure (' + strTimeUnit + ')')
            pos0 = ticks.index(int(math.floor(xmap[0])))
            ticklabels[pos0]='Exposure'
        elif axisType=='Date of Occurrence':
            axes.set_xlabel('Date of Occurrence (' + strTimeUnit + ')')
            ids = [i for i, xt in enumerate(ticklabels) if xt[0]!='$']
            sameyear = True
            samemonth = True
            for i in range(1, len(ids)):
                if ticklabels[ids[i]][-2:]!=ticklabels[ids[i-1]][-2:]:
                    sameyear = False
                if ticklabels[ids[i]][-5:-3]!=ticklabels[ids[i-1]][-5:-3]:
                    samemonth = False
                if not sameyear and not samemonth:
                    break
            labelAll = ''
            if sameyear and strTimeUnit!='Week':
                for i in range(1, len(ids)):
                    ticklabels[ids[i]] = ticklabels[ids[i]][:-3]
                labelAll = ticklabels[0][-2:]
            if samemonth and strTimeUnit!='Week':
                for i in range(1, len(ids)):
                    ticklabels[ids[i]] = ticklabels[ids[i]][:-3]
                labelAll += ticklabels[0][-2:]
            if labelAll!='' and not xlim[1] in ticks:
                ticks.append(xlim[1])                
                ticklabels.append(labelAll)
         
        ###### Plot ############################################
        
        self.tooltipData = {}
        self.lasagna_regions = []
        matCount = []
        maxCountAllowed = 255 # Below use ascii char to sort the rows
        x0 = min(ticks)
        leng = max(ticks) - x0 + 1
        yticklabels = []
        yticks = []
        separate_pos = []
        for plotid, allCurves in enumerate(allPlots):
            tooltipData = {}
            mat = []
            
            ypos0 = len(matCount)
            separate_pos.append(ypos0 - 0.5)
            tooltips = allTooltips[plotid]
            for i, curve in enumerate(allCurves):
                row = [0] * leng
                ti = curve[0]
                yi = curve[1]
                #legend = curve[2]
                xi = [xmap[t] for t in ti]
            
                for j, x in enumerate(xi):
                    pos = int(x)-x0                    
                    row[pos] += yi[j]
                    row[pos] = min(row[pos], maxCountAllowed)
                    if (i, ti[j]) in tooltips:
                        if not (pos,i) in tooltipData:
                            tooltipData[(pos, i)] = tooltips[(i, ti[j])]
                        else:
                            #tooltipData[(pos, i)] += tooltips[(i, ti[j])]                        
                            tooltipData[(pos, i)] = self.combine_tooltips(tooltipData[(pos, i)], tooltips[(i, ti[j])])

                mat.append(row)
            
            matCount += mat
            for (pos, i) in tooltipData:
                self.tooltipData[pos, ypos0+i] = tooltipData[(pos,i)]
            
            yticks.append((ypos0+len(matCount))/2.-0.5)
            pName = plotNames[plotid]
            tokens = pName.split()
            if len(tokens)>1 and tokens[0]!='Selected':
                pName = tokens[0]+'...'

            ylbl = pName + '(' + str(len(mat)) + ')'
            yticklabels.append(ylbl)
        
            self.lasagna_regions.append((len(matCount), pName))
        
        maxncolor = 8
        ncol = max([max(r) for r in matCount])+1
        if ncol > maxncolor:
            (matCount, cbticks, cbticklabels) = self.rearrange_color_bins(matCount, maxncolor)
            ncol = len(cbticks)
        else:
            cticks = range(ncol)
            cbticklabels = [str(t) for t in cticks]
            intv = (ncol-1.)/ncol # segment interval
            cbticks = [(t + 0.5)*intv for t in cticks]

        cmap = matplotlib.cm.get_cmap(self.mainWindow.sysPreferences.getColorScheme(), ncol)
        im = axes.imshow(matCount, cmap=cmap, origin = 'lower', interpolation='none', aspect='auto')
        for i in range(1, len(separate_pos)):
            ysep = separate_pos[i]
            axes.plot(xlim, [ysep, ysep])
        
        cbar = self.fig.colorbar(im, drawedges=True)
        cbar.set_ticks(cbticks)
        cbar.set_ticklabels(cbticklabels)
        cbar.set_label('Split Feature Text Count', rotation=270, labelpad = 12)
        
        axes.set_yticks(yticks)
        if len(yticklabels)==1:
            axes.set_yticklabels(yticklabels, rotation = 90)
        else:
            axes.set_yticklabels(yticklabels, rotation = 80)
        ylim = [-0.5, len(matCount)-0.5]
        
        ticks = [t-x0 for t in ticks]
        xlim = [xlim[0] - x0, xlim[1] - x0]
        
        (ticks, ticklabels) = self.adjust_xtick_labels(ticks, ticklabels, xlim)
        axes.set_xticks(ticks)
        axes.set_xticklabels(ticklabels, size=self.fontsize)
        axes.set_ylim(ylim)
        axes.set_xlim(xlim)
        
        num = len(self.mainWindow.selectedReportIndices)
        axes.set_title('Total ' + str(num) + ' cases')
        self.canvas.draw()
        
    def plot_lasagna_in_range_only(self):
        self.fig.clf()
        axes = self.fig.add_subplot(111)

        strTimeUnit = self.comboAxisUnit.currentText()        
        axisType = self.comboAxis.currentText()
        
        featLists = []
        plotNames = []
        if not self.checkAggregated.isChecked():
            for i in range(self.featureGroup.layout().count()-2): 
                if self.featureGroup.layout().itemAt(i).widget().checkState():
                    text = self.featureGroup.layout().itemAt(i).widget().text()
                    loc = text.find('(')
                    if loc>=0:
                        text = text[:loc-1]
                
                    strFeat = dictFeatureNames[text]
                    featLists.append([strFeat])
            featLists.sort(key=lambda x:self.strFeatures.index(x[0]), reverse=True)
            for feat in featLists:
                featname = dictFeatureAbr[feat[0]]
                if featname=='':
                    featname = dictFeatureNamesInv[feat[0]]
                plotNames.append(featname)
        else:
            featList = []
            for i in range(self.featureGroup.layout().count()-2): 
                if self.featureGroup.layout().itemAt(i).widget().checkState():
                    text = self.featureGroup.layout().itemAt(i).widget().text()
                    loc = text.find('(')
                    if loc>=0:
                        text = text[:loc-1]
                    featList.append(dictFeatureNames[text])
            featLists.append(featList)
            plotNames.append('Selected Feature Types')
        
        ts = []
        allPlots = []
        allTooltips = []
        ti_plots = []
        featList = []
        for featList in featLists:
            (curves, tooltips, tsi) = self.get_multi_report_curves(featList, axisType)
            if not curves: 
                continue
            
            allPlots.append(curves)
            allTooltips.append(tooltips)
            ti_plots.append(tsi)
            ts += tsi
            
        ####################################################################
        ## create time axis
        #################################################################
        if len(ts)==0:
            self.canvas.draw()
            return
        
        ti = list(set(ts))
        ti.sort()
        
        self.timeline = ti
#         
        (xmap, ticks, ticklabels, xlim)=self.create_coord_mapping(ti, axisType, strTimeUnit)

        ###################
        ## process xlabel and xticklabels  
        if xlim[0]==xlim[1]:
            xlim[1] = xlim[0]+1
        if axisType=='Age at Occurrence':
            axes.set_xlabel('Age at Occurrence (' + strTimeUnit + ')')
        elif axisType=='From Exposure':
            axes.set_xlabel('From Exposure (' + strTimeUnit + ')')
            pos0 = ticks.index(int(math.floor(xmap[0])))
            ticklabels[pos0]='Exposure'
        elif axisType=='Date of Occurrence':
            axes.set_xlabel('Date of Occurrence (' + strTimeUnit + ')')
            ids = [i for i, xt in enumerate(ticklabels) if xt[0]!='$']
            sameyear = True
            samemonth = True
            for i in range(1, len(ids)):
                if ticklabels[ids[i]][-2:]!=ticklabels[ids[i-1]][-2:]:
                    sameyear = False
                if ticklabels[ids[i]][-5:-3]!=ticklabels[ids[i-1]][-5:-3]:
                    samemonth = False
                if not sameyear and not samemonth:
                    break
            labelAll = ''
            if sameyear and strTimeUnit!='Week':
                for i in range(1, len(ids)):
                    ticklabels[ids[i]] = ticklabels[ids[i]][:-3]
                labelAll = ticklabels[0][-2:]
            if samemonth and strTimeUnit!='Week':
                for i in range(1, len(ids)):
                    ticklabels[ids[i]] = ticklabels[ids[i]][:-3]
                labelAll += ticklabels[0][-2:]
            if labelAll!='' and not xlim[1] in ticks:
                ticks.append(xlim[1])                
                ticklabels.append(labelAll)
         
        ###### Plot ############################################
        
        self.tooltipData = {}
        self.lasagna_regions = []
        matCount = []
        maxCountAllowed = 255 # Below use ascii char to sort the rows
        x0 = min(ticks)
        
        leng = max(ticks) - x0 + 1
        yticklabels = []
        yticks = []
        separate_pos = []
        for plotid, allCurves in enumerate(allPlots):
            tooltipData = {}
            mat = []
            
            ypos0 = len(matCount)
            separate_pos.append(ypos0 - 0.5)
            tooltips = allTooltips[plotid]
            icount = 0
            for i, curve in enumerate(allCurves):
                row = [0] * leng
                ti = curve[0]
                yi = curve[1]
                
                xi = [xmap[t] for t in ti]
                
                # if all points are out of xlim, skip this row
                xr = [xi[k] for k in range(len(xi)) if yi[k]>0]
                xx = [xri for xri in xr if xri>= xlim[0] and xri<=xlim[1]]
                if not xx:
                    continue
                
                for j, x in enumerate(xi):
                    pos = int(x)-x0                    
                    row[pos] += yi[j]
                    row[pos] = min(row[pos], maxCountAllowed)
                    if (i, ti[j]) in tooltips:
                        if not (pos,icount) in tooltipData:
                            tooltipData[(pos, icount)] = tooltips[(i, ti[j])]
                        else:
                            #tooltipData[(pos, i)] += tooltips[(i, ti[j])]                        
                            tooltipData[(pos, icount)] = self.combine_tooltips(tooltipData[(pos, icount)], tooltips[(i, ti[j])])

                icount += 1
                mat.append(row)
            
            ### reorder matrix by converting each row into a string
            rowStrCode = []
            for row in mat:
                s= ''.join([chr(n) for n in row])
                rowStrCode.append(s)
            pointers = [i[0] for i in sorted(enumerate(mat), key=lambda x:x[1])]
            invPointers = [i[0] for i in sorted(enumerate(pointers), key=lambda x:x[1])] 
          
            matNew = []
            for idx in pointers:
                matNew.append(mat[idx]) 
            newTipData = {}
            for (pos, i) in tooltipData:
                self.tooltipData[pos, ypos0+invPointers[i]] = tooltipData[(pos,i)]
            
            matCount += matNew
            
            yticks.append((ypos0+len(matCount))/2.-0.5)
            pName = plotNames[plotid]
            tokens = pName.split()
            if len(tokens)>1 and tokens[0]!='Selected':
                pName = tokens[0]+'...'
            ylbl = pName + '(' + str(len(matNew)) + ')'
            yticklabels.append(ylbl)
        
            self.lasagna_regions.append((len(matCount), pName))
        
        maxncolor = 8
        ncol = max([max(r) for r in matCount])+1
        if ncol > maxncolor:
            (matCount, cbticks, cbticklabels) = self.rearrange_color_bins(matCount, maxncolor)
            ncol = len(cbticks)
        else:
            cticks = range(ncol)
            cbticklabels = [str(t) for t in cticks]
            intv = (ncol-1.)/ncol # segment interval
            cbticks = [(t + 0.5)*intv for t in cticks]

        cmap = matplotlib.cm.get_cmap(self.mainWindow.sysPreferences.getColorScheme(), ncol)
        im = axes.imshow(matCount, cmap=cmap, origin = 'lower', interpolation='none', aspect='auto')
        for i in range(1, len(separate_pos)):
            ysep = separate_pos[i]
            axes.plot(xlim, [ysep, ysep])
        
        cbar = self.fig.colorbar(im, drawedges=True)
        cbar.set_ticks(cbticks)
        cbar.set_ticklabels(cbticklabels)
        cbar.set_label('Split Feature Text Count', rotation=270, labelpad = 12)
        
        axes.set_yticks(yticks)
        if len(yticklabels)==1:
            axes.set_yticklabels(yticklabels, rotation = 90)
        else:
            axes.set_yticklabels(yticklabels, rotation = 80)
        ylim = [-0.5, len(matCount)-0.5]
        
        ticks = [t-x0 for t in ticks]
        xlim = [xlim[0] - x0, xlim[1] - x0]
        
        (ticks, ticklabels) = self.adjust_xtick_labels(ticks, ticklabels, xlim)
        axes.set_xticks(ticks)
        axes.set_xticklabels(ticklabels, size=self.fontsize)
        axes.set_ylim(ylim)
        axes.set_xlim(xlim)
        
        num = len(self.mainWindow.selectedReportIndices)
        axes.set_title('Total ' + str(num) + ' cases')
        self.canvas.draw()
        
    def plot_linecurve_in_range_only(self):
                
        self.fig.clf()
        axes = self.fig.add_subplot(111)

        strTimeUnit = self.comboAxisUnit.currentText()        
        axisType = self.comboAxis.currentText()
        
        featLists = []
        plotNames = []
        if not self.checkAggregated.isChecked():
            for i in range(self.featureGroup.layout().count()-2): 
                if self.featureGroup.layout().itemAt(i).widget().checkState():
                    text = self.featureGroup.layout().itemAt(i).widget().text()                    
                    loc = text.find('(')
                    if loc>=0:
                        text = text[:loc-1]
                    strFeat = dictFeatureNames[text]
                    featLists.append([strFeat])
            featLists.sort(key=lambda x:self.strFeatures.index(x[0]), reverse=True)
            for feat in featLists:
                featname = dictFeatureAbr[feat[0]]
                if featname=='':
                    featname = dictFeatureNamesInv[feat[0]]
                plotNames.append(featname)
        else:
            featList = []
            for i in range(self.featureGroup.layout().count()-2): 
                if self.featureGroup.layout().itemAt(i).widget().checkState():
                    text = self.featureGroup.layout().itemAt(i).widget().text()              
                    loc = text.find('(')
                    if loc>=0:
                        text = text[:loc-1]
                    featList.append(dictFeatureNames[text])
            featLists.append(featList)
            plotNames.append('Selected Feature Types')
        
        ts = []
        allPlots = []
        allTooltips = []
        ti_plots = []
        featList = []
        for featList in featLists:
            (curves, tooltips, tsi) = self.get_multi_report_curves(featList, axisType)
            if not curves: 
                continue
            
            allPlots.append(curves)
            allTooltips.append(tooltips)
            ti_plots.append(tsi)
            ts += tsi
            
        ####################################################################
        ## create time axis
        #################################################################
        if len(ts)==0:
            self.canvas.draw()
            return
        
        ti = list(set(ts))
        ti.sort()
        
        self.timeline = ti
#         
        (xmap, ticks, ticklabels, xlim)=self.create_coord_mapping(ti, axisType, strTimeUnit)

        ###################
        ## process xlabel and xticklabels  
        if xlim[0]==xlim[1]:
            xlim[1] = xlim[0]+1
        #axes.set_xlim(xlim)
        if axisType=='Age at Occurrence':
            axes.set_xlabel('Age at Occurrence (' + strTimeUnit + ')')
        elif axisType=='From Exposure':
            axes.set_xlabel('From Exposure (' + strTimeUnit + ')')
            #pos0 = ticks.index(xmap[0])
            pos0 = ticks.index(int(math.floor(xmap[0])))
            ticklabels[pos0]='Exposure'
            #ticklabels[0]='Vax'
        elif axisType=='Date of Occurrence':
            axes.set_xlabel('Date of Occurrence (' + strTimeUnit + ')')
            ids = [i for i, xt in enumerate(ticklabels) if xt[0]!='$']
            sameyear = True
            samemonth = True
            for i in range(1, len(ids)):
                if ticklabels[ids[i]][-2:]!=ticklabels[ids[i-1]][-2:]:
                    sameyear = False
                if ticklabels[ids[i]][-5:-3]!=ticklabels[ids[i-1]][-5:-3]:
                    samemonth = False
                if not sameyear and not samemonth:
                    break
            labelAll = ''
            if sameyear and strTimeUnit!='Week':
                for i in range(1, len(ids)):
                    ticklabels[ids[i]] = ticklabels[ids[i]][:-3]
                labelAll = ticklabels[0][-2:]
            if samemonth and strTimeUnit!='Week':
                for i in range(1, len(ids)):
                    ticklabels[ids[i]] = ticklabels[ids[i]][:-3]
                labelAll += ticklabels[0][-2:]
            if labelAll!='' and not xlim[1] in ticks:
                ticks.append(xlim[1])                
                ticklabels.append(labelAll)
                
        ###### Plot ############################################
        
        self.tooltipData = {}
        self.lasagna_regions = []
        matCount = []
        allCounts = []
        maxCountAllowed = 255 # Below use ascii char to sort the rows
        x0 = min(ticks)
        
        leng = max(ticks) - x0 + 1
        curveNames = []
        yticks = []
        separate_pos = []
        ypos0 = 0
        for plotid, allCurves in enumerate(allPlots):
            tooltipData = {}
            mat = []
            
            tooltips = allTooltips[plotid]
            icount = 0
            for i, curve in enumerate(allCurves):
                row = [0] * leng
                ti = curve[0]
                yi = curve[1]
                
                xi = [xmap[t] for t in ti]
                
                # if all points are out of xlim, skip this row
                xr = [xi[k] for k in range(len(xi)) if yi[k]>0]
                xx = [xri for xri in xr if xri>= xlim[0] and xri<=xlim[1]]
                if not xx:
                    continue
                
                for j, x in enumerate(xi):
                    pos = int(x)-x0                    
                    row[pos] += yi[j]
                    row[pos] = min(row[pos], maxCountAllowed)
                    if (i, ti[j]) in tooltips:
                        if not (pos,icount) in tooltipData:
                            tooltipData[(pos, icount)] = tooltips[(i, ti[j])]
                        else:
                            #tooltipData[(pos, i)] += tooltips[(i, ti[j])]                        
                            tooltipData[(pos, icount)] = self.combine_tooltips(tooltipData[(pos, icount)], tooltips[(i, ti[j])])

                icount += 1
                mat.append(row)
            
            y = [ypos0]*leng
            for j in range(leng):
                tooltip = ''
                for i, row in enumerate(mat):
                    y[j] += row[j]
                    if (j, i) in tooltipData:
                        tooltip = self.combine_tooltips(tooltip, tooltipData[(j, i)])
                nc = y[j] - ypos0
                if tooltip != '':
                    self.tooltipData[(j, y[j])] = '<b>Count = ' + str(nc) + '</b><br>' + tooltip
            
            ypos0 = max(y) + 1
            separate_pos.append(ypos0)
            
            curveNames.append(plotNames[plotid] + ' (' + str(len(mat)) + ' cases)')

            allCounts.append(y)
        
        for y in allCounts:
            axes.plot(y, 's-')
            
        ### create yticks and yticklabels
        # compute proper tick interval
        maxYTicks = 20
        maxY = separate_pos[-1]
        yintervalset = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000]
        yd = int(float(maxY)/maxYTicks)
        yinterval = 10000
        for itv in yintervalset:
            if itv >= yd:
                yinterval = itv
                break
        
        ycur = 0
        yticks = [0]
        yticklabels = ['0']
        for i in range(len(separate_pos)):
            ysep = separate_pos[i]
            while ysep > yticks[-1] + yinterval:
                yticks.append(yticks[-1] + yinterval)
                ycur += yinterval
                yticklabels.append(str(ycur))

            # skip the last region
            if i == len(separate_pos)-1:
                break
            
            yticks.append(ysep)
            ycur = 0
            yticklabels.append(str(ycur))
            axes.plot(xlim, [ysep, ysep])
        
        if self.checkAggregated.isChecked() and not self.mainWindow.sysPreferences.toAdjustYScaleAggregated():
            if maxY > self.feature_count_range_for_line_plot:
                self.feature_count_range_for_line_plot = maxY
                self.aggregated_yticks = yticks
                self.aggregated_yticklabels = yticklabels
            ylim = [0, self.feature_count_range_for_line_plot]
            yticks = self.aggregated_yticks
            yticklabels = self.aggregated_yticklabels
            separate_pos[0] = ylim[1]
        else:
            ylim = [0, maxY]
            
        axes.set_ylim(ylim)
        axes.set_yticks(yticks)
        axes.set_yticklabels(yticklabels)
                
        ticks = [t-x0 for t in ticks]
        xlim = [xlim[0] - x0, xlim[1] - x0]
        
        (ticks, ticklabels) = self.adjust_xtick_labels(ticks, ticklabels, xlim)
        axes.set_xticks(ticks)
        axes.set_xticklabels(ticklabels, size=self.fontsize)
        
        axes.set_xlim(xlim)
        
        coordData = axes.transData.inverted().transform([(0,0), (self.textfontsize/2, self.textfontsize/2)])
        yfontcoordsize = coordData[1][1]-coordData[0][1]
        xpadcoordsize = coordData[1][0]-coordData[0][0]
        for i in range(len(separate_pos)):
            ysep = separate_pos[i]
            axes.text(xlim[1]-xpadcoordsize, ysep-yfontcoordsize, curveNames[i], size=self.textfontsize, va='top', ha='right', bbox=dict(fc=[1, 1, 1]))
        
        num = len(self.mainWindow.selectedReportIndices)
        axes.set_title('Total ' + str(num) + ' cases')
        #axes.grid(True)
        self.canvas.draw()
        
    def plot_linecurve_report_count(self):
                
        self.fig.clf()
        axes = self.fig.add_subplot(111)

        strTimeUnit = self.comboAxisUnit.currentText()        
        axisType = self.comboAxis.currentText()
        
        featLists = []
        plotNames = []
        if not self.checkAggregated.isChecked():
            for i in range(self.featureGroup.layout().count()-2): 
                if self.featureGroup.layout().itemAt(i).widget().checkState():
                    text = self.featureGroup.layout().itemAt(i).widget().text()                    
                    loc = text.find('(')
                    if loc>=0:
                        text = text[:loc-1]
                    strFeat = dictFeatureNames[text]
                    featLists.append([strFeat])
            featLists.sort(key=lambda x:self.strFeatures.index(x[0]), reverse=True)
            for feat in featLists:
                featname = dictFeatureAbr[feat[0]]
                if featname=='':
                    featname = dictFeatureNamesInv[feat[0]]
                plotNames.append(featname)
        else:
            featList = []
            for i in range(self.featureGroup.layout().count()-2): 
                if self.featureGroup.layout().itemAt(i).widget().checkState():
                    text = self.featureGroup.layout().itemAt(i).widget().text()              
                    loc = text.find('(')
                    if loc>=0:
                        text = text[:loc-1]
                    featList.append(dictFeatureNames[text])
            featLists.append(featList)
            plotNames.append('Selected Feature Types')
        
        ts = []
        allPlots = []
        allTooltips = []
        ti_plots = []
        featList = []
        for featList in featLists:
            (curves, tooltips, tsi) = self.get_report_count_curves(featList, axisType)
            if not curves: 
                continue
            
            allPlots.append(curves)
            allTooltips.append(tooltips)
            ti_plots.append(tsi)
            ts += tsi
            
        ####################################################################
        ## create time axis
        #################################################################
        if len(ts)==0:
            self.canvas.draw()
            return
        
        ti = list(set(ts))
        ti.sort()
        
        self.timeline = ti
#         
        (xmap, ticks, ticklabels, xlim)=self.create_coord_mapping(ti, axisType, strTimeUnit)

        ###################
        ## process xlabel and xticklabels  
        if xlim[0]==xlim[1]:
            xlim[1] = xlim[0]+1
        if axisType=='Age at Occurrence':
            axes.set_xlabel('Age at Occurrence (' + strTimeUnit + ')')
        elif axisType=='From Exposure':
            axes.set_xlabel('From Exposure (' + strTimeUnit + ')')
            pos0 = ticks.index(int(math.floor(xmap[0])))
            ticklabels[pos0]='Exposure'
        elif axisType=='Date of Occurrence':
            axes.set_xlabel('Date of Occurrence (' + strTimeUnit + ')')
            ids = [i for i, xt in enumerate(ticklabels) if xt[0]!='$']
            sameyear = True
            samemonth = True
            for i in range(1, len(ids)):
                if ticklabels[ids[i]][-2:]!=ticklabels[ids[i-1]][-2:]:
                    sameyear = False
                if ticklabels[ids[i]][-5:-3]!=ticklabels[ids[i-1]][-5:-3]:
                    samemonth = False
                if not sameyear and not samemonth:
                    break
            labelAll = ''
            if sameyear and strTimeUnit!='Week':
                for i in range(1, len(ids)):
                    ticklabels[ids[i]] = ticklabels[ids[i]][:-3]
                labelAll = ticklabels[0][-2:]
            if samemonth and strTimeUnit!='Week':
                for i in range(1, len(ids)):
                    ticklabels[ids[i]] = ticklabels[ids[i]][:-3]
                labelAll += ticklabels[0][-2:]
            if labelAll!='' and not xlim[1] in ticks:
                ticks.append(xlim[1])                
                ticklabels.append(labelAll)
                
        ###### Plot ############################################
        
        self.tooltipData = {}
        self.lasagna_regions = []
        matCount = []
        allCounts = []
        maxCountAllowed = 255 # Below use ascii char to sort the rows
        x0 = min(ticks)
        
        leng = max(ticks) - x0 + 1
        curveNames = []
        yticks = []
        separate_pos = []
        ypos0 = 0
        for plotid, allCurves in enumerate(allPlots):
            tooltipData = {}
            mat = []

            tooltips = allTooltips[plotid]
            icount = 0
            for i, curve in enumerate(allCurves):
                row = [0] * leng
                ti = curve[0]
                yi = curve[1]
                
                xi = [xmap[t] for t in ti]
                
                # if all points are out of xlim, skip this row
                xr = [xi[k] for k in range(len(xi)) if yi[k]>0]
                xx = [xri for xri in xr if xri>= xlim[0] and xri<=xlim[1]]
                if not xx:
                    continue
                
                for j, x in enumerate(xi):
                    pos = int(x)-x0                    
                    row[pos] += yi[j]
                    row[pos] = min(row[pos], maxCountAllowed)
                    if (i, ti[j]) in tooltips:
                        if not (pos,icount) in tooltipData:
                            tooltipData[(pos, icount)] = tooltips[(i, ti[j])]
                        else:
                            #tooltipData[(pos, i)] += tooltips[(i, ti[j])]                        
                            tooltipData[(pos, icount)] = self.combine_tooltips(tooltipData[(pos, icount)], tooltips[(i, ti[j])])

                icount += 1
                mat.append(row)
            
            y = [ypos0]*leng
            for j in range(leng):
                tooltip = ''
                for i, row in enumerate(mat):
                    y[j] += row[j]
                    if (j, i) in tooltipData:
                        tooltip = self.combine_tooltips(tooltip, tooltipData[(j, i)])
                nc = y[j] - ypos0
                if tooltip != '':
                    self.tooltipData[(j, y[j])] = '<b>Count = ' + str(nc) + '</b><br>' + tooltip
            
            ypos0 = max(y) + 1
            separate_pos.append(ypos0)
            
            curveNames.append(plotNames[plotid] + ' (' + str(len(mat)) + ' cases)')

            allCounts.append(y)
        
        for y in allCounts:
            axes.plot(y, 's-')
            
        ### create yticks and yticklabels
        # compute proper tick interval
        maxYTicks = 20
        maxY = separate_pos[-1]
        yintervalset = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000]
        yd = int(float(maxY)/maxYTicks)
        yinterval = 10000
        for itv in yintervalset:
            if itv >= yd:
                yinterval = itv
                break
        
        ycur = 0
        yticks = [0]
        yticklabels = ['0']
        for i in range(len(separate_pos)):
            ysep = separate_pos[i]
            while ysep > yticks[-1] + yinterval:
                yticks.append(yticks[-1] + yinterval)
                ycur += yinterval
                yticklabels.append(str(ycur))

            # skip the last region
            if i == len(separate_pos)-1:
                break
            
            yticks.append(ysep)
            ycur = 0
            yticklabels.append(str(ycur))
            axes.plot(xlim, [ysep, ysep])
        
        if self.checkAggregated.isChecked() and not self.mainWindow.sysPreferences.toAdjustYScaleAggregated():
            if maxY > self.feature_count_range_for_line_plot:
                self.feature_count_range_for_line_plot = maxY
                self.aggregated_yticks = yticks
                self.aggregated_yticklabels = yticklabels
            ylim = [0, self.feature_count_range_for_line_plot]
            yticks = self.aggregated_yticks
            yticklabels = self.aggregated_yticklabels
            separate_pos[0] = ylim[1]
        else:
            ylim = [0, maxY]
            
        axes.set_ylim(ylim)
        axes.set_yticks(yticks)
        axes.set_yticklabels(yticklabels)
                
        ticks = [t-x0 for t in ticks]
        xlim = [xlim[0] - x0, xlim[1] - x0]
        
        (ticks, ticklabels) = self.adjust_xtick_labels(ticks, ticklabels, xlim)
        axes.set_xticks(ticks)
        axes.set_xticklabels(ticklabels, size=self.fontsize)
        
        axes.set_xlim(xlim)
        
        coordData = axes.transData.inverted().transform([(0,0), (self.textfontsize/2, self.textfontsize/2)])
        yfontcoordsize = coordData[1][1]-coordData[0][1]
        xpadcoordsize = coordData[1][0]-coordData[0][0]
        for i in range(len(separate_pos)):
            ysep = separate_pos[i]
            axes.text(xlim[1]-xpadcoordsize, ysep-yfontcoordsize, curveNames[i], size=self.textfontsize, va='top', ha='right', bbox=dict(fc=[1, 1, 1]))
        
        num = len(self.mainWindow.selectedReportIndices)
        axes.set_title('Total ' + str(num) + ' cases')
        #axes.grid(True)
        self.canvas.draw()
        
    def adjust_xtick_labels(self, ticks0, ticklabels0, xlim):
        len_allowed = 80
        xxticks = zip(ticks0, ticklabels0)
        if xlim[0] in ticks0:
            i0 = ticks0.index(xlim[0])
        else:
            i0=0
        if xlim[1] in ticks0:
            i1 = ticks0.index(xlim[1])
        else:
            i1 = len(ticks0)-1
        
        xxticks = [t for (i, t) in enumerate(xxticks) if i in range(i0, i1+1)]
        labels = [t[1] for t in xxticks]
        for i in range(len(labels)):
            if labels[i][0]=='$':
                labels[i]='-->'
        s = ''.join(labels)
        if len(s)<len_allowed:
            return (ticks0, ticklabels0)
        
        xxticks = [t for t in xxticks if t[1][0]!='$']
        labels = [t[1] for t in xxticks]
        s = ''.join(labels)
        if len(s)<len_allowed:
            ticks = [t[0] for t in xxticks]
            return (ticks, labels)
        
        ratio = 1.0*len(s)/len_allowed
        num = int(1.0*len(labels)*len_allowed/len(s))
        outticks = []
        for i in range(num):
            pos = int(round(i*ratio))
            outticks.append(xxticks[pos])
        
        labels = [t[1] for t in outticks]
        ticks = [t[0] for t in outticks]
        return (ticks, labels)
    
    # To arragne color distribution to avoid the case where a high count unncessarily broadens
    # the range of colors, which reduces the color difference between classes. 
    def rearrange_color_bins(self, matCount, maxncolor=10):
        
        nmax = max([max(r) for r in matCount])
        ncol = nmax + 1
        if ncol > maxncolor:
            hist = [0] * ncol
            for row in matCount:
                for x in row:
                    hist[x] += 1
            total = sum(hist[1:])
            perbin = int(total/maxncolor)
            
            # Recalculate average number in bins after removing those with big numbers. 
            # For example, a histogram like [24914, 104, 44, 17, 8, 1, 1, 0, 0, 1], the bin of 104
            # can take away most of counts, which leaves more color number for the rest, and thus
            # no need to combine bins of 17 and 8. 
            lowbins = [x for x in hist[1:] if x < perbin]
            nlow = maxncolor-nmax+len(lowbins)
            nlow = max(1, nlow)
            perbin = int(sum(lowbins)/nlow)
            perbin = max(1, perbin)
            
            bins = [(0, 0)]
            ncur = 0
            taken = 0
            for i in range(1, ncol):
                n = hist[i]
                if n >=perbin:
                    if i-1 >= taken+1:
                        cnt = sum(hist[taken+1:i])
                        # combine previous remained with this bin if it's less than 5% of this bin
                        if cnt/n > 0.05: 
                            bins.append((taken+1, i-1))
                            taken = i-1
                    bins.append((taken+1, i))
                    taken = i
                    ncur = 0
                    continue
                
                ncur += n
                if ncur >= perbin:
                    bins.append((taken+1, i))
                    taken = i
                    ncur = 0
            if taken < nmax:
                bins.append((taken+1, nmax))
        
        mapping = [0] * ncol
        for i, xbin in enumerate(bins):
            for j in range(xbin[0], xbin[1]+1):
                mapping[j] = i
        
        matNew = []
        for row in matCount:
            newrow = [mapping[x] for x in row]
            matNew.append(newrow)
            
        nbins = len(bins)
        cticks = range(nbins)
        cbticklabels = []
        for i, xbin in enumerate(bins):
            if xbin[1]==xbin[0]:
                s = str(xbin[0])
            elif xbin[1]-xbin[0]==1:
                s = str(xbin[0]) + ', ' + str(xbin[1]) 
            else:
                s = str(xbin[0]) + '~' + str(xbin[1]) 
            cbticklabels.append(s)

        intv = (nbins-1.)/nbins # segment interval
        cbticks = [(t + 0.5)*intv for t in cticks]
        
        return (matNew, cbticks, cbticklabels)
        
    def combine_tooltips(self, tip, newtip):
        p1 = tip.find('<b>')
        p2 = tip.find('</b>')
        title1 = tip[p1+3:p2]
        
        p1 = newtip.find('<b>')
        p2 = newtip.find('</b>')
        title2 = newtip[p1+3:p2]
        
        if title2==title1:
            tooltip = tip + newtip[p2+4:]
        else:
            tooltip = tip + newtip
            
        return tooltip
        
    def get_multi_report_curves(self, featList, axisType, flag_unsort = False):

        ##########################################
        ### Create all curves
        ##########################################
        allCurves=[]
        tooltips = {}
        reports = [self.reports[index] for index in self.mainWindow.selectedReportIndices]
        for report in reversed(reports):
            features = report['Features']
            #features = [feat for feat in features if feat[0] in featList and feat[0] in featList]
            features = [feat for feat in features if feat.getType() in featList]
            expDate = report['Exposure Date']
            if not expDate:
                continue
            
            if axisType == 'Age at Occurrence':
                if report['Age'].lower()=='unknown' or report['Age'].lower()=='':
                    if flag_unsort:
                        allCurves.append(([0],[0], ''))
                    continue
                else:
                    ageDays = int(float(report['Age'])*365)
#             
            dicts = {}
            for feature in features:
                 
                if feature.hasStartTime():
                    singles = re.split(', | and ', feature.getString())
                    singles = [feature.getType()+': '+s for s in singles]
                     
                    if axisType == 'Date of Occurrence':
                        tt = feature.getStartTime()
                    elif axisType == 'From Exposure':
                        tt = (feature.getStartTime()-expDate).days
                    elif axisType == 'Age at Occurrence':
                        tt = (feature.getStartTime()-expDate).days + ageDays
                        if tt < 0:
                            continue
                    if not tt in dicts:
                        dicts[tt]= singles
                    else:
                        dicts[tt] += singles
         
            if axisType!='Date of Occurrence' and not 0 in dicts:
                dicts[0] = []
             
            time_severity = [(k, dicts[k]) for k in dicts]
            time_severity.sort(key=lambda ts:ts[0])
            ti = [severity[0] for severity in time_severity]
            yi = [len(severity[1]) for severity in time_severity]
            si = [severity[1] for severity in time_severity]
             
            if not yi or max(yi)==0:
                if flag_unsort:
                    allCurves.append(([0],[0], ''))
                continue
            
            curveid = len(allCurves)
            legend = '#' + report['Report ID']
            for i, t in enumerate(ti):    
                if si[i]==[]:
                    continue
                 
                tooltip = '<b> '+ legend +' </b>'    
                tooltip += '<ul>'
                for s in si[i]:
                    tooltip += '<li> ' + s
             
                tooltip += '</ul>'
                 
                if (curveid, t) in tooltips:
                    tooltips[(curveid, t)] = self.combine_tooltips(tooltips[(curveid, t)], tooltip)
                    
                else:
                    tooltips[(curveid, t)] = tooltip
                    
             
            allCurves.append((ti,yi, legend))
             
        legends = ()
        for curve in allCurves:
            legends = legends + (curve[2],)
             
        ####################################################################
        ## create time axis
        #################################################################
        ts=[]
        for curve in allCurves:
            ts+=curve[0]
        # if there is not curve at all 
        if len(ts)==0:
            self.canvas.draw()
            return (None, None, None)
        
        ti = list(set(ts))
        if axisType != 'Date of Occurrence' and not 0 in ti:
            negt = [t for t in ti if t<0]
            ti.insert(len(negt), 0)
                
        ti.sort()
        
        return (allCurves, tooltips, ti)
        
    def get_report_count_curves(self, featList, axisType, flag_unsort = False):

        ##########################################
        ### Create all curves
        ##########################################
        allCurves=[]
        tooltips = {}
        reports = [self.reports[index] for index in self.mainWindow.selectedReportIndices]
        for report in reversed(reports):
            features = report['Features']
            #features = [feat for feat in features if feat[0] in featList and feat[0] in featList]
            features = [feat for feat in features if feat.getType() in featList]
            expDate = report['Exposure Date']
            if not expDate:
                continue
            
            if axisType == 'Age at Occurrence':
                if report['Age'].lower()=='unknown' or report['Age'].lower()=='':
                    if flag_unsort:
                        allCurves.append(([0],[0], ''))
                    continue
                else:
                    ageDays = int(float(report['Age'])*365)
             
            dicts = {}
            for feature in features:
                 
                if feature.hasStartTime():                     
                    if axisType == 'Date of Occurrence':
                        tt = feature.getStartTime()
                    elif axisType == 'From Exposure':
                        tt = (feature.getStartTime()-expDate).days
                    elif axisType == 'Age at Occurrence':
                        tt = (feature.getStartTime()-expDate).days + ageDays
                        if tt < 0:
                            continue
                        
                    if not tt in dicts:
                        dicts[tt]= [report['Report ID']]
                    else:
                        if not report['Report ID'] in dicts[tt]:
                            dicts[tt].append(report['Report ID'])
         
            if axisType!='Date of Occurrence' and not 0 in dicts:
                dicts[0] = []
             
            time_severity = [(k, dicts[k]) for k in dicts]
            time_severity.sort(key=lambda ts:ts[0])
            ti = [severity[0] for severity in time_severity]
            yi = [len(severity[1]) for severity in time_severity]
            si = [severity[1] for severity in time_severity]
             
            if not yi or max(yi)==0:
                if flag_unsort:
                    allCurves.append(([0],[0], ''))
                continue
            
            curveid = len(allCurves)
            legend = '#' + report['Report ID']
            for i, t in enumerate(ti):    
                if si[i]==[]:
                    continue
                 
                tooltip = '<b> '+ legend +' </b><br>'    
                 
                if (curveid, t) in tooltips:
                    tooltips[(curveid, t)] = self.combine_tooltips(tooltips[(curveid, t)], tooltip)
                else:
                    tooltips[(curveid, t)] = tooltip
             
            allCurves.append((ti,yi, legend))
             
        legends = ()
        for curve in allCurves:
            legends = legends + (curve[2],)
             
        ####################################################################
        ## create time axis
        #################################################################
        ts=[]
        for curve in allCurves:
            ts+=curve[0]
        if len(ts)==0:
            self.canvas.draw()
            return (None, None, None)
        
        ti = list(set(ts))
        if axisType != 'Date of Occurrence' and not 0 in ti:
            negt = [t for t in ti if t<0]
            ti.insert(len(negt), 0)
                
        ti.sort()
        
        return (allCurves, tooltips, ti)
        
    
    def get_multi_report_curves_on_terms(self, plotName, axisType):
         
        filename = 'vomiting blood.txt'
        try:
            with open(filename, 'rb') as csvfile:
                reader = csv.reader(csvfile)
                terms = [row[0] for row in reader]
        except Exception as e:
            QMessageBox.critical(None, "ETHER", str(e))
                 
        featureDict = {'Number of Symptoms':["SYMPTOM"],
                       'Number of Diagnoses':["DIAGNOSIS", "SECOND_LEVEL_DIAGNOSIS", "CAUSE_OF_DEATH"],
                       'Number of Vaccines':["VACCINE"],
                       'Number of Drugs':["DRUG"]}
              
        featList=[]
        if plotName in featureDict:
            featList = featureDict[plotName]
        else:
            for i in range(self.featureGroup.layout().count()-1): 
                if self.featureGroup.layout().itemAt(i).widget().checkState():
                    featList.append(self.featureGroup.layout().itemAt(i).widget().text())

        ##########################################
        ### Create all curves
        ##########################################
        allCurves=[]
        tooltips = {}
        reports = [self.reports[index] for index in self.mainWindow.selectedReportIndices]
        for report in reports:
            features = report['Features']
            features = [feat for feat in features if feat[0] in featList]
            
            expDate = report['Exposure Date']
            
            if axisType == 'Age at Occurrence':
                if report['Age'].lower()=='unknown' or report['Age'].lower()=='':
                    continue
                else:
                    ageDays = int(float(report['Age'])*365)
#             
            dicts = {}
            for feature in features:
                 
                if feature[3]:
                    singles = re.split(', | and |&', feature[1])
                    singles = [s for s in singles if s in terms]
                    if not singles:
                        continue
                    
                    singles = [feature[0]+': '+s for s in singles]
                    
                    if axisType == 'Date of Occurrence':
                        tt = feature[3]
                    elif axisType == 'From Exposure':
                        tt = (feature[3]-expDate).days
                        if tt < 0:
                            continue
                    elif axisType == 'Age at Occurrence':
                        tt = (feature[3]-expDate).days + ageDays
                         
                    if not tt in dicts:
                        dicts[tt]= singles
                    else:
                        dicts[tt] += singles
         
            if axisType!='Date of Occurrence' and not 0 in dicts:
                dicts[0] = []
             
            time_severity = [(k, dicts[k]) for k in dicts]
            time_severity.sort(key=lambda ts:ts[0])
            ti = [severity[0] for severity in time_severity]
            yi = [len(severity[1]) for severity in time_severity]
            si = [severity[1] for severity in time_severity]
             
            if not yi or max(yi)==0:
                continue
            
            curveid = len(allCurves)
            legend = '#' + report['Report ID']
            for i, t in enumerate(ti):    
                if si[i]==[]:
                    continue
                 
                tooltip = '<b> '+ legend +' </b>'    
                tooltip += '<ul>'
                for s in si[i]:
                    tooltip += '<li> ' + s
             
                tooltip += '</ul>'
                 
                if (curveid, t) in tooltips:
                    tooltips[(curveid, t)] = self.combine_tooltips(tooltips[(curveid, t)], tooltip)
                else:
                    tooltips[(curveid, t)] = tooltip
             
            allCurves.append((ti,yi, legend))
             
        legends = ()
        for curve in allCurves:
            legends = legends + (curve[2],)
             
        ####################################################################
        ## create time axis
        #################################################################
        ts=[]
        for curve in allCurves:
            ts+=curve[0]
        if len(ts)==0:
            self.canvas.draw()
            return (None, None, None)
        
        ti = list(set(ts))
        ti.sort()
        
        return (allCurves, tooltips, ti)    
    
    def create_coord_mapping(self, ti, axisType, strTimeUnit):
        ####################################################################
        ## create time axis
        #################################################################
        timeUnit = self.get_time_unit_days(strTimeUnit)
        num = len(ti)
        if axisType == 'Date of Occurrence':
            if strTimeUnit == 'Day' or strTimeUnit =='Week':
                t0 = ti[0]
                tni = [(t-t0).days/timeUnit for t in ti]                
            elif strTimeUnit == 'Month':
                days =[31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
                tni = [ti[0].month + (ti[0].day-1.)/days[ti[0].month-1]]
                year0 = ti[0].year
                for i in range(1, num):
                    tni.append((ti[i].year-year0)*12 + ti[i].month + (ti[i].day-1.)/days[ti[i].month-1])                    
            elif strTimeUnit == 'Year':
                tni = []
                for i in range(0, num):
                    days = (ti[i]-datetime.datetime(ti[i].year, 1, 1)).days
                    tni.append(ti[i].year + days/365.)
            t0 = int(tni[0])
            tni = [t-t0 for t in tni]
        else:
            tni = [t/timeUnit for t in ti] # normalized ti 
        
        coord_mapping = {}
        if not self.checkCompressAxis.isChecked():
            ticks = []
            ticklabels = []
            for i in range(num):
                coord_mapping[ti[i]] = tni[i]
                fl = int(math.floor(tni[i]))
                if not ticks or fl!=ticks[-1]:
                    ticks.append(fl)
                    if axisType=='Date of Occurrence': # and trTimeUnit!='Week':  
                        ticklabels.append(datetime_strftime(ti[i], strTimeUnit))   
                    else:
                        ticklabels.append(str(fl))

        else:
            # assume the minimum delta is 1 (day)
            interval_allowed = 2    

            if axisType == 'Date of Occurrence':
                coord_mapping[ti[0]] = 0
                ticks = [0]
                ticklabels = [datetime_strftime(ti[0], strTimeUnit)]
            else:
                tn0 = int(math.floor(tni[0]))
                ticks = [0]
                ticklabels = [str(tn0)]
                if tn0 == tni[0]:
                    coord_mapping[ti[0]] = 0
                else:
                    coord_mapping[ti[0]-(tni[0]-tn0)*timeUnit] = 0
                    coord_mapping[ti[0]] = tni[0]-tn0
                    
            for i in range(1,num):
                if int(tni[i]) - int(tni[i-1]) <= interval_allowed:
                    coord_mapping[ti[i]] = coord_mapping[ti[i-1]] + tni[i] - tni[i-1]
                    
                    if int(math.floor(coord_mapping[ti[i]])) != ticks[-1]:
                        ticks.append(int(math.floor(coord_mapping[ti[i]])))
                        
                        if axisType == 'Date of Occurrence':
                            ticklabels.append(datetime_strftime(ti[i], strTimeUnit))
                        else:
                            ticklabels.append(str(int(math.floor(tni[i]))))
                else:
                    ticks.append(ticks[-1] + 1)
                    ticklabels.append(r'${\rightarrow}$')
                    coord_mapping[ti[i]] = ticks[-1] + 1 + tni[i]-int(math.floor(tni[i]))
                    ticks.append(int(math.floor(coord_mapping[ti[i]])))
                    
                    if axisType == 'Date of Occurrence':
                        ticklabels.append(datetime_strftime(ti[i], strTimeUnit))
                    else:
                        ticklabels.append(str(int(math.floor(tni[i]))))
        
        ticks.append(ticks[-1] + 1)
        ticklabels.append(' ')
        
        xlim = self.get_time_range_unit(ti, ticks, coord_mapping, timeUnit)
        
        return (coord_mapping, ticks, ticklabels, xlim)
        
    def get_time_unit_days(self, strUnit):
        timeunit = None
        if strUnit=='Day':
            timeunit = 1
        elif strUnit=='Week':
            timeunit = 7.
        elif strUnit=='Month':
            timeunit = 30.
        elif strUnit=='Year':
            timeunit = 365.
        
        return timeunit
    
    def get_time_range_unit(self, ti, ticks, coord_mapping, timeunit):   
        
        axisType = self.comboAxis.currentText()
                
        if (axisType == 'From Exposure' and not self.time_range_vax) or \
            (axisType == 'Date of Occurrence' and not self.time_range_date) or \
            (axisType == 'Age at Occurrence' and not self.time_range_age):
            tFrom = ti[0]
            tTo = ti[-1]
            xlim = [ticks[0], ticks[-1]]
                
        else:
            if axisType == 'Date of Occurrence':
                tFrom = self.textRangeFrom.dateTime().toPython()
                tTo = self.textRangeTo.dateTime().toPython()
            else:            
                tFrom = timeunit * self.spinDayFrom.value()
                tTo = timeunit * self.spinDayTo.value()
            
            if tFrom > tTo:
                QMessageBox.critical(QMessageBox(), "VaeTM", "Time Range Invalid!")
            
            if not tFrom in coord_mapping:
                tafter = [t for t in coord_mapping if t>=tFrom]
                tFrom = min(tafter)
            
            if not tTo in coord_mapping:
                tbefore = [t for t in coord_mapping if t<=tTo]
                tTo = max(tbefore)
    
            tickFrom = coord_mapping[tFrom]     
            tickTo = coord_mapping[tTo]  
            
            # range should always be integers since this is for image plot
            tickFrom = int(tickFrom)
            tickTo = int(math.ceil(tickTo))                          
            #tickTo = tickTo + 1                        
            xlim = [tickFrom, tickTo]
        
        if axisType == 'Date of Occurrence':
            self.time_range_date = (tFrom, tTo)
        elif axisType == 'Age at Occurrence':
            self.time_range_age = (tFrom, tTo)
        else:
            self.time_range_vax = (tFrom, tTo)
        
        self.update_time_range_widget(timeunit)

        return xlim
    
    # Have to keep this function so that the main window can loop over all tabs
    def set_current_report(self, current_report, tabindex):
        return
        
    def set_feature_checkboxes(self):
        defaultFeats = ["DIAGNOSIS", "SECOND_LEVEL_DIAGNOSIS", "SYMPTOM"]
        featDict = {}            
        reports = [self.reports[index] for index in self.mainWindow.selectedReportIndices]
        for features in [report['Features'] for report in reports]:
            for feat in features:
                featDict[feat.getType()] = True

        for i in range(len(dictFeatureNames)): 
            check = self.featureGroup.layout().itemAt(i).widget()
            featname =check.text()
            loc = featname.find('(')
            if loc>=0:
                featname = featname[:loc-1]
                
            feat = dictFeatureNames[featname]
            if feat in featDict:
                check.setEnabled(True)
                if feat in defaultFeats:
                    check.setChecked(True)
                else:
                    check.setChecked(False)
            else:
                self.featureGroup.layout().itemAt(i).widget().setEnabled(False)
                 
    def checkbox_all_clicked(self):
        
        if self.checkAll.isChecked():
            for i in range(self.featureGroup.layout().count()-2): 
                if self.featureGroup.layout().itemAt(i).widget().isEnabled():
                    self.featureGroup.layout().itemAt(i).widget().setChecked(True)
        else:
            for i in range(self.featureGroup.layout().count()-2): 
                self.featureGroup.layout().itemAt(i).widget().setChecked(False)
        
        self.plot()
        
    def checkbox_clicked(self):
        isAllChecked = True
        for i in range(self.featureGroup.layout().count()-2): 
            state = self.featureGroup.layout().itemAt(i).widget().checkState()
            if self.featureGroup.layout().itemAt(i).widget().isEnabled() and not state:
                isAllChecked = False
        
        if isAllChecked:
            self.checkAll.setChecked(True)
        else:
            self.checkAll.setChecked(False)
        
        self.plot()
     
    # clear all widgets in a layout. 
    def clearLayout(self, layout):
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clearLayout(item.layout())
                    
class ReportTemporal(QFrame):
    def __init__(self, reports = [], parent=None):
        super(ReportTemporal, self).__init__(parent)
        
        self.reports = reports
        self.mainWindow = parent
        self.setLayout(QVBoxLayout())
        
        self.text = ReportText(reports, self, True)
        self.temporalPlot = ReportTemporalPlot(reports, self.mainWindow, self)
        
        self.layout().addWidget(self.temporalPlot)
        
        self.layout().addWidget(self.text)
        
        self.layout().setStretch(0, 4)
        self.layout().setStretch(1, 1)
        
        if self.mainWindow.sysPreferences.toHideNarrative():
            self.text.hide()
        else:
            self.text.show()
        
    def set_current_report(self, current_report):
        self.text.set_current_report(current_report)
        self.temporalPlot.set_current_report(current_report)
        self.current_report = current_report
        
        doc = self.text.report_text.document()
        plain_text = doc.toPlainText()
        sentences = util.sentence_tokenize(plain_text)
        self.sent_locs = []
        for sent in sentences:            
            start_char_sent = plain_text.find(sent)
            end_char_sent = start_char_sent + len(sent)
            self.sent_locs.append((start_char_sent, end_char_sent))
            
    def highlight_sentence_timexes(self, sentNum, featString=None):
        if sentNum >= 0:
            doc = self.text.report_text.document()
            plain_text = doc.toPlainText()
            sent = plain_text[self.sent_locs[sentNum][0]:self.sent_locs[sentNum][1]]
            (istart, iend) = util.find_sub_text_range(sent, featString) 
            pstart = self.sent_locs[sentNum][0] + istart
            pend = self.sent_locs[sentNum][0] + iend
            
            self.text.highlight_feature_text(pstart, pend)
        else:
            self.text.highlight_feature_text(0, 0)

    def update_layout(self):
        if self.mainWindow.sysPreferences.toHideNarrative():
            self.text.hide()
        else:
            self.text.show()
        
        if self.mainWindow.sysPreferences.toHideSettings():
            self.temporalPlot.optionFrame.hide()
        else:
            self.temporalPlot.optionFrame.show()

        self.temporalPlot.plot()
                                
class ReviewTab(QWidget):
    def __init__(self, reports, central_widget, parent=None):
        super(ReviewTab, self).__init__(parent)
        
        self.reports = reports
        self.setLayout(QVBoxLayout())
        
        #structured information widget
        self.structured = Structured(self.reports, self)
        #report review information widget
        self.central = central_widget
        
        #lay out widgets
        self.layout().addWidget(self.structured, 1)
        self.layout().addWidget(self.central, 50)
    
    def set_current_report(self, current_report, tabindex=0):
        self.structured.set_current_report(current_report)
        self.central.set_current_report(current_report)

class DBHandler():
    def __init__(self, db):
        self.vaersdb = db
        
    def updateSummarizations(self, reportid, summarizations):
        self.vaersdb.deleteReportSummarizations(reportid)
        for elem in summarizations:
            row = elem.summarizationDBRecord()
            record = (reportid,) + row 
            self.vaersdb.updateSummarization(record)
        self.vaersdb.conn.commit()
        

class OutLog:
    def __init__(self, edit, out=None, color=None):
        """(edit, out=None, color=None) -> can write stdout, stderr to a
        QTextEdit.
        edit = QTextEdit
        out = alternate stream ( can be the original sys.stdout )
        color = alternate color (i.e. color stderr a different color)
        """
        self.edit = edit
        self.out = out
        self.color = color

    def write(self, m):
        if self.color:
            tc = self.edit.textColor()
            self.edit.setTextColor(self.color)

        self.edit.moveCursor(QTextCursor.End)
        self.edit.insertPlainText( m )

        if self.color:
            self.edit.setTextColor(tc)

        if self.out:
            self.out.write(m)
        
class MainWindow(QMainWindow):
    def __init__(self, reportFile = None, parent = None):
        super(MainWindow, self).__init__(parent)

        self.sysPreferences = SystemPreferences(self)
        self.showMaximized()

        #read config file
        configfile = 'config.py'
        try:
            with open(configfile, 'r') as f:
                self.config = ast.literal_eval(f.read())
        except Exception as e:
            QMessageBox.critical(None, "ETHER", str(e))
            sys.exit(app.quit())

        #connect to database
        self.vaersdb = dbstore(self.config['localpath'] + 'etherlocal.db', "", self.config['localpath'])
        self.dbHandler = DBHandler(self.vaersdb)

        #get the userid
        self.username = getpass.getuser().lower()
          
        self.num_tabs = 5      
        
        self.file_load_reports = QAction("Load cases (reports)...", self)
        self.file_load_reports.setShortcut("Ctrl+L")
        self.file_load_reports.setStatusTip("Load report file")
        self.file_load_reports.triggered.connect(self.load_reports)
        self.file_load_reports.setDisabled(True)
        
        self.file_load_reports_faers = QAction("Load FAERS BizObj file...", self)
        self.file_load_reports_faers.setShortcut("Ctrl+F")
        self.file_load_reports_faers.setStatusTip("Load FAERS BizObj file")
        self.file_load_reports_faers.triggered.connect(self.load_reports_faers)
        self.loading_faers_file = False
        
        self.extractor = None
        self.lexicon = None
        
        if reportFile == 'idsdebug.csv':
            self.in_debug_mode = True
        else:
            self.in_debug_mode = False
        
        self.reportType = 'vaers'
        if not reportFile:
            reportFile = self.config['localpath']+'reports.txt'

        report_form_data = self.read_data_file_universal(reportFile)
        self.reports = self.read_reports_form_data(report_form_data)
        
        if not self.reports:
            sys.exit(app.quit())
            
        if len(self.reports[0]['Report ID'].split('-')[0]) > 6:
            self.reportType = 'faers'
            
        self.selectedReportIndices = range(len(self.reports))
#         if not self.reports:
#             sys.exit(app.quit())
        self.file_load_reports.setDisabled(False)
        
        self.current_report = 0
        self.current_report_global_index = 0

        self.timer = time.time()
        self.reports.sort(key=lambda report: report['Report ID'])
        self.reports.sort(key=lambda report: len(report['Diagnosis']) > 0, reverse=True)
        self.selectedReportIndices = range(len(self.reports)) # this array will be updated in LimitedFeatures Tab
        
        #setup window and create widgets
        self.setWindowTitle(reportFile + " - ETHER: Event-based Text-mining of Health Electronic Records")

        self.mainTabWidget = QTabWidget(self)
        self.setCentralWidget(self.mainTabWidget)
        
        self.centralWidget().addTab(ReviewTab(self.reports, ReportLimitedFeatures(self.reports,self), self.centralWidget()), "Summarized Cases")
        self.centralWidget().addTab(ReviewTab(self.reports, ReportTextAndFeatures(self.reports, self), self.centralWidget()), "Case Narrative && Features")
        self.centralWidget().addTab(ReviewTab(self.reports, ReportTemporal(self.reports, self), self.centralWidget()), "Case Features over Time")   
        self.centralWidget().addTab(ReviewTab(self.reports, AnnotationTab(self.reports, self), self.centralWidget()), "Annotation")   
        
        self.centralWidget().setTabsClosable(True)
        ##: Hide close button for existing tabs
        for i in range(self.centralWidget().count()):
            self.centralWidget().tabBar().tabButton(i, QTabBar.RightSide).resize(0, 0)
            
        self.centralWidget().tabCloseRequested.connect(self.delete_tab)
        
        # connect tab changed signal
        self.centralWidget().currentChanged.connect(self.save_timer_comment)
        self.current_tabindex = 0
               
        #create actions
        self.next_action = QAction("Next Case", self)
        self.next_action.setShortcut(QKeySequence.Forward)   
        self.next_action.setStatusTip("Select next event")
        self.next_action.triggered.connect(self.next_report)
        
        self.previous_action = QAction("Previous Case", self)
        self.previous_action.setShortcut(QKeySequence.Back)
        self.previous_action.setStatusTip("Select previous event")
        self.previous_action.triggered.connect(self.previous_report)  
                
        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.setStatusTip("Exit application")
        self.exit_action.triggered.connect(self.close)
        
        self.research_mode_action = QAction("Enable research mode", self)
#         self.research_mode_action.setShortcut("Ctrl+R")
        self.research_mode_action.setStatusTip("Enable research mode")
        self.research_mode_action.setCheckable(True)
        self.research_mode_action.setChecked(True)
        self.research_mode_action.toggled.connect(self.research_toggle)
        self.research_mode_enabled = True
       
        self.mouse_mode_action = QAction("Enable mouse selection", self)
#         self.mouse_mode_action.setShortcut("Ctrl+M")
        self.mouse_mode_action.setStatusTip("Enable mouse selection for Limited Feature table")
        self.mouse_mode_action.setCheckable(True)
        self.mouse_mode_action.setChecked(True)
        self.mouse_mode_action.toggled.connect(self.mouse_toggle)            
        
        self.save_features_action = QAction("Extracted Information...", self)
        self.save_features_action.setStatusTip("Save all extracted features to a CSV file")
        self.save_features_action.triggered.connect(self.save_full_features)
        
        self.save_limited_action = QAction("Summarized Cases Tab...", self)
        #self.save_limited_action.setShortcut("Ctrl+L")
        self.save_limited_action.setStatusTip("Save summarized cases to a CSV file")
        self.save_limited_action.triggered.connect(self.save_summarized_cases)
        
        self.save_ether_summary_action = QAction("Product Info && Case Summaries...", self)
        #self.save_ether_summary_action.setShortcut("Ctrl+H")
        self.save_ether_summary_action.setStatusTip("Save Product Info & Case Summaries to a CSV file")
        self.save_ether_summary_action.triggered.connect(self.save_ether_summary)
        
        self.save_annotations_action = QAction("Annotations", self)
        self.save_annotations_action.setStatusTip("Export annotations")
        self.save_annotations_action.setShortcut("Ctrl+N")
        self.save_annotations_action.triggered.connect(self.save_annotations)        
        
        self.save_ether_annotations_action = QAction("ETHER Annotations", self)
        self.save_ether_annotations_action.setStatusTip("Export ETHER annotations")
        self.save_ether_annotations_action.setShortcut("Ctrl+M")
        self.save_ether_annotations_action.triggered.connect(self.save_ether_annotations)        
        
        self.save_report_dataset_action = QAction("Save cases (reports)...", self)
        self.save_report_dataset_action.setShortcut("Ctrl+R")
        self.save_report_dataset_action.setStatusTip("Save reports file")
        self.save_report_dataset_action.triggered.connect(self.save_reports_csv)
        
        self.data_all_action = QAction("All data", self)
        self.data_all_action.setShortcut("Ctrl+A")
        self.data_all_action.setCheckable(True)
        self.data_all_action.setChecked(True)
        self.data_all_action.triggered.connect(self.data_all)
        
        self.data_filter_action = QAction("Filter Builder...", self)
        self.data_filter_action.setShortcut("Ctrl+F")
        self.data_filter_action.triggered.connect(self.data_filtering)
        self.data_filter_panacea = QAction("Find Duplicate Cases...", self)
        self.data_filter_panacea.triggered.connect(self.find_duplicate_cases)
        self.menu_separator = QAction(self)
        self.menu_separator.setSeparator(True)
        self.menu_separator1 = QAction(self)
        self.menu_separator1.setSeparator(True)
        self.menu_separator2 = QAction(self)
        self.menu_separator2.setSeparator(True)
        
        self.option_preferences_action = QAction("Preferences", self)
        self.option_preferences_action.setStatusTip("Open Preferences dialog")
        self.option_preferences_action.triggered.connect(self.open_preferences_dialog)
        
        self.option_setting_colorscheme_action = QAction("Color Scheme", self)
        self.option_setting_colorscheme_action.setStatusTip("Select coloring scheme for Lasagna plot")
        self.option_setting_colorscheme_action.triggered.connect(self.select_color_scheme)
        
        self.option_remove_irrelavant_DB_action = QAction("Remove irrelevant reports from DB", self)
#         self.option_remove_irrelavant_DB_action.triggered.connect(self.remove_irrelavant_reports)
        
        #setup timer display
        self.pauseButton = QPushButton("Pause", self)
        self.timerLabel = QLabel("", self)        
        #self.pauseButton.clicked.connect(self.pause_timer)
        
        #start timer
        self.update = QTimer()
        #self.update.timeout.connect(self.update_timer)
        self.update.start(100)

        self.set_current_report(0) 

        #add toolbar
        self.nav_toolbar = self.addToolBar("Navigation")
        self.nav_toolbar.addAction(self.previous_action)
        self.nav_toolbar.addAction(self.next_action)
        self.nav_toolbar.addSeparator()
        self.pause_action = self.nav_toolbar.addWidget(self.pauseButton)
        
        #add menus
        self.file_menu = self.menuBar().addMenu("File")
        self.file_menu.addAction(self.file_load_reports)      
        
        self.file_menu.addAction(self.save_report_dataset_action)
         
        self.export_menu = self.file_menu.addMenu("Export")
        self.export_menu.addAction(self.save_ether_summary_action)
        self.export_menu.addAction(self.save_limited_action)
        self.export_menu.addAction(self.save_features_action)
        self.export_menu.addAction(self.save_annotations_action)
        self.export_menu.addAction(self.save_ether_annotations_action)
        
        self.data_load_database_action = QAction("Retrieve Reviewed Reports...", self)
        self.data_load_database_action.setShortcut("Ctrl+D")
#         self.data_load_database_action.triggered.connect(self.load_local_database)
        self.data_load_database_action.triggered.connect(lambda: self.load_reports(True))
        self.file_menu.addAction(self.data_load_database_action)           
                
        self.file_menu.addAction(self.menu_separator)     
        self.file_menu.addAction(self.option_preferences_action)
        
        self.file_menu.addAction(self.menu_separator2)                
        self.file_menu.addAction(self.exit_action)
        
        self.data_menu = self.menuBar().addMenu("Data")
        self.data_menu.addAction(self.data_all_action)
        self.filter_menu = self.data_menu.addMenu("Filter")
        self.filter_menu.addAction(self.data_filter_action)
        self.data_menu.addAction(self.data_filter_panacea)
#         self.filter_menu.addAction(self.menu_separator)      
#         self.filter_current_menu = self.filter_menu.addMenu("Current Filters")  
        self.filter_recent_menu = self.filter_menu.addMenu("Recent Filters")          
        
        self.shortcut_ctrl_T = QShortcut(QKeySequence("Ctrl+T"), self)
        self.shortcut_ctrl_T.activated.connect(self.sysPreferences.toggleHideNarrative)
        self.shortcut_ctrl_H = QShortcut(QKeySequence("Ctrl+H"), self)
        self.shortcut_ctrl_H.activated.connect(self.sysPreferences.toggleHideSettings)
        self.shortcut_ctrl_H = QShortcut(QKeySequence("Ctrl+W"), self)
        self.shortcut_ctrl_H.activated.connect(self.save_time_plot)
        
        self.help_menu = self.menuBar().addMenu("Help")
        self.help_documentation_action = QAction("Documentation", self)
        self.help_documentation_action.triggered.connect(self.open_help_documentation)
        self.help_menu.addAction(self.help_documentation_action)
        self.help_about_action = QAction("About", self)
        self.help_about_action.triggered.connect(self.open_help_about_dialog)
        self.help_menu.addAction(self.help_about_action)
        
        
        #self.research_mode_action.trigger()
        self.research_mode_action.setChecked(False)
        
        self.lexiconDict = None
        self.lexicon_tagger = None
        self.filters_current = []
        self.filters_recent = []
        self.filters_current_actions = []
        self.filters_recent_actions = []
        self.filters_maxcount = 5
        
        for i in range(self.filters_maxcount):
#             self.filters_current_actions.append(QAction(self))
#             self.filters_current_actions[i].setVisible(False)
#             self.filter_current_menu.addAction(self.filters_current_actions[i])
            self.filters_recent_actions.append(QAction(self))
            self.filters_recent_actions[i].setVisible(False)
            self.filters_recent_actions[i].triggered.connect(self.on_menu_recent_filters_clicked)
            self.filter_recent_menu.addAction(self.filters_recent_actions[i])
#         self.filters_current_actions[0].setDisabled(True)
#         self.filters_current_actions[0].setText('Empty')
#         self.filters_current_actions[0].setVisible(True)
        self.filters_recent_actions[0].setDisabled(True)
        self.filters_recent_actions[0].setText('Empty')
        self.filters_recent_actions[0].setVisible(True)
        
        #add status bar
        self.statusBar().showMessage("Ready")
 
    def event(self, event):
        if event.type() == QEvent.Polish:
            #setup stuff that must wait for everything to be constructed
            logging.debug('polish event')
            pass
        return super(MainWindow, self).event(event)

    def research_toggle(self, checked):
        logging.debug('research mode toggled, currently: {0}'.format(checked))

        if self.research_mode_enabled:
            #switch to review mode
            self.save_timer_comment(self.current_tabindex)
            self.update.stop()
        else:
            #switch to research mode
            self.timer = time.time()
            self.update.start(100)
            #self.update_timer()
        self.research_mode_enabled = checked

        #hide pause button
        self.pause_action.setVisible(checked)
        
        #hide comment/review fields in review mode
        for i in range(self.centralWidget().count()):
            #hide MedDRA line in the header
            self.centralWidget().widget(i).structured.meddra_label.setVisible(not checked)
                    
    def mouse_toggle(self, checked):
        logging.debug('mouse select mode toggled, currently: {0}'.format(checked))
                      
        limited_feature_table = self.centralWidget().widget(0).central.feature_table
        limited_feature_table.mouse_enabled = checked

    def update_timer(self):
        tabTime = float(self.reports[self.current_report]['Timer'][self.centralWidget().currentIndex()])
        timerDisplay = str(datetime.timedelta(seconds = int(time.time() - self.timer + tabTime)))
        self.pauseButton.setText(timerDisplay)

    def pause_timer(self):
        if self.update.isActive():
            logging.debug('pausing timer')
            self.update.stop()        
            self.pauseButton.setStyleSheet("QPushButton {color: #ff0000;}")
            self.pause = time.time()
        else:
            logging.debug('unpausing timer')
            self.timer += time.time() - self.pause
            self.update.start(100)            
            self.pauseButton.setStyleSheet("QPushButton {color: #000000;}")
    
    def save_timer_comment(self, tabindex):
        self.current_tabindex = tabindex   
        
    def faers_report_csv_reader(self, reports_data): 
        report_form_data = None
        for row in reports_data:
            if 'Case #' in row[0]:
                report_form_data = self.faers_quick_query_csv_reader(reports_data)
                break
            elif "Case Id" in row[0:2]:
                if 'QQNarrative1' in row:
                    report_form_data = self.faers_dasr_csv_reader(reports_data)
                else:
                    report_form_data = self.faers_dasr_v2_csv_reader(reports_data)
                break
                
        if not report_form_data: 
            QMessageBox.critical(None, "ETHER", "The data file is not in the right format as a FAERS BO file!")
            return None
        
        for report in report_form_data:
            report['Received Date'] = parse(report['Received Date']).isoformat().split('T')[0]
            
        return report_form_data

    
    def faers_dasr_csv_reader(self, reports_data): 
        fieldnames = ['Report ID','Age','Date of Exposure','Date of Onset','Vaccines','Vaccine Names','MedDRA','Gender','Free Text', 'Lab Text', 
                      'Location', 'Received Date', 'Died', 'History', 'Indication', 'Primary Suspect']
        dictMatchStrings = {'Report ID': ['Case Id'], 'Age':['Age Years'], 
                            'Vaccines':['Suspect Drugs List'],'Vaccine Names':['Suspect Drugs List'],
                            'Free Text':['QQNarrative1', 'QQNarrative2'], 'MedDRA':['Pt List'], 'Gender':['Gender'],
                            'Date of Exposure':[], 'Date of Onset':[], 'Lab Text':[], 'Location':['Reporter Country'], 
                            'Received Date':['FDA Recd Date'], 'Died':['Died Flag'], 'History':['Medical History Comments'],
                            'Indication':['Indication Primary Suspect'], 'Primary Suspect':['Primary Suspect']}

        reLotNum = re.compile('Product 1?[0-9] +Lot #')
        seriousFields = ['Outcome Lf Threat Flag', 'Outcome Hospitalization', 'Outcome Intrvtn', 'Disab Flag','Congen Flag']
        
        row0 = -1
        for i, row in enumerate(reports_data):
            if "Case Id" in row[1]:
                row0 = i
                break
            
        if row0 == -1: 
            QMessageBox.critical(None, "ETHER", "The data file is not in the right format as a FAERS BO file!")
            return None
            
        headers = reports_data[row0]
        dictFieldColumnIndex = {}
        for fld in fieldnames:
            strings = dictMatchStrings[fld]

            ids = [ind for s in strings for (ind, strcol) in enumerate(headers) if s==strcol]
            if fld=='Age':
                ids = [ids[0]]
            dictFieldColumnIndex[fld] = ids
                
        diedCol = [i for (i, s) in enumerate(headers) if s=='All Outcomes'][0]
        
        reports_data = reports_data[row0+1:]
        report_form_data = []
        report_id_list=[]
        for row in reports_data:    
            if not [c for c in row if c!='']:
                continue 
            report = {}
            for fld in fieldnames: 
                if dictFieldColumnIndex[fld]:
                    ##: It could be mulitple columns, e.g., Narrative I and Narrative II. They need to be merged
                    report[fld] = ' '.join([row[idx].strip() for idx in dictFieldColumnIndex[fld]])
                    
                    # special processing
                    if fld in ['MedDRA', 'Vaccines', 'Vsaccine Names']:
                        report[fld] = re.sub(',|:', ';', report[fld])                           
                    if fld=='Gender' and report[fld]=='NULL':
                        report[fld]='UNKNOWN'                  
                else:
                    report[fld] = ''
            
            diedStrs = row[diedCol].split(',')
            if 'DE' in diedStrs:
                report['Died'] = True
                diedStrs.remove('DE')
            else:
                report['Died'] = False
            
            if len(diedStrs)>0:
                report['Serious'] = True
            else:
                report['Serious'] = False
            
            if report['Report ID'] in report_id_list:
                continue
            
            report_form_data.append(report)
            report_id_list.append(report['Report ID'])
        
        return report_form_data
    
    ##: DASR report in its 2nd format
    def faers_dasr_v2_csv_reader(self, reports_data): 
        fieldnames = ['Report ID','Age','Date of Exposure','Date of Onset','Vaccines','Vaccine Names','MedDRA','Gender','Free Text', 'Lab Text', 
                      'Location', 'Received Date', 'Died', 'History', 'Indication', 'Primary Suspect']
        dictMatchStrings = {'Report ID': ['Case Id'], 'Age':['Age Years'], 
                            'Vaccines':['Suspect Drugs List'],'Vaccine Names':['Suspect Drugs List'],
                            'Free Text':[], 'MedDRA':['Pt List'], 'Gender':['Gender'],
                            'Date of Exposure':[], 'Date of Onset':[], 'Lab Text':[], 'Location':['Reporter Country'], 
                            'Received Date':['Initial Mfr Recvd Date'], 'Died':['Died Flag'], 'History':['Medical History Comments'],
                            'Indication':['Indication Primary Suspect'], 'Primary Suspect':['Primary Suspect']}

        reLotNum = re.compile('Product1?[0-9] +Lot Number')
        seriousFields = ['Outcome Lf Threat Flag', 'Outcome Hospitalization', 'Outcome Intrvtn', 'Disab Flag','Congen Flag']
        
        row0 = -1
        for i, row in enumerate(reports_data):
            if "Case Id" in row:
                row0 = i
                break            
        if row0 == -1: 
            QMessageBox.critical(None, "ETHER", "The data file is not in the right format as a FAERS BO file!")
            return None
            
        headers = reports_data[row0]
        dictFieldColumnIndex = {}
        for fld in fieldnames:
            strings = dictMatchStrings[fld]

            ids = [ind for s in strings for (ind, strcol) in enumerate(headers) if s==strcol]
            if fld=='Age' or fld=='Location':
                ids = [ids[0]]
            dictFieldColumnIndex[fld] = ids
                
        dictFieldColumnIndex['Free Text'] = [ind for s in strings for (ind, strcol) in enumerate(headers) if 'Narrative' in strcol]
        
        lotColumns = [i for (i, s) in enumerate(headers) if reLotNum.match(s)]
            
        diedCol = [i for (i, s) in enumerate(headers) if s=='All Outcomes'][0]
        
        reports_data = reports_data[row0+1:]
        report_form_data = []
        report_id_list=[]
        for row in reports_data:    
            if not [c for c in row if c!='']:
                continue 
            report = {}
            for fld in fieldnames: 
                if dictFieldColumnIndex[fld]:
                    ##: It could be mulitple columns, e.g., Narrative I and Narrative II. They need to be merged
                    report[fld] = ''.join([row[idx].strip() for idx in dictFieldColumnIndex[fld]])
                    
                    # special processing
                    if fld in ['MedDRA', 'Vaccines', 'Vsaccine Names']:
                        report[fld] = re.sub(',|:', ';', report[fld])                           
                    if fld=='Gender' and report[fld]=='NULL':
                        report[fld]='UNKNOWN'                  
                else:
                    report[fld] = ''
            
            diedStrs = row[diedCol].split(',')
            if 'DE' in diedStrs:
                report['Died'] = True
                diedStrs.remove('DE')
            else:
                report['Died'] = False
            
            if len(diedStrs)>0:
                report['Serious'] = True
            else:
                report['Serious'] = False
            
            if lotColumns: 
                report['Lot Number'] = '; '.join([row[i] for i in lotColumns if row[i]!='' and row[i].lower()!='unknown'])
            else:
                report['Lot Number'] = ''
            
            if report['Indication']!='':
                report['Indication'] = ';'.join(set(report['Indication'].split(';')))
                
            if report['Report ID'] in report_id_list:
                rpt = [r for r in report_form_data if r['Report ID']==report['Report ID']][0]
                if report['Lot Number']!='':
                    if rpt['Lot Number']=='':
                        rpt['Lot Number'] = report['Lot Number']
                    else:
                        rpt['Lot Number'] += ';' + report['Lot Number']
                continue
            else:
                report_id_list.append(report['Report ID'])   
                report_form_data.append(report)
        
        return report_form_data
    
    def faers_quick_query_csv_reader(self, reports_data): 
        fieldnames = ['Report ID','Age','Date of Exposure','Date of Onset','Vaccines','Vaccine Names','MedDRA','Gender','Free Text', 'Lab Text', 
                      'Location', 'Received Date', 'Died', 'History', 'Indication']
        dictMatchStrings = {'Report ID': ['Case #'], 'Age':['Age in Years'], 
                            'Vaccines':['Suspect Products'],'Vaccine Names':['Suspect Products'],
                            'Free Text':['Narrative'], 'MedDRA':['PTs', 'Pt List'], 'Gender':['Gender'],
                            'Date of Exposure':[], 'Date of Onset':[], 'Lab Text':[], 'Location':['Country'], 
                            'Received Date':['Initial FDA received Date'], 'Died':['Died Flag'], 'History':['Medical History Comments'],
                            'Indication':['Indication Primary Suspect', 'Product 1 Indication']}

        reLotNum = re.compile('Product 1?[0-9] +Lot #')
        seriousFields = ['Outcome Lf Threat Flag', 'Outcome Hospitalization', 'Outcome Intrvtn', 'Disab Flag','Congen Flag']
        
        row0 = -1
        for i, row in enumerate(reports_data):
            if 'Case #' in row[0] or "Case Id" in row[1]:
                row0 = i
                break
            
        if row0 == -1: 
            QMessageBox.critical(None, "ETHER", "The data file is not in the right format as a FAERS BO file!")
            return None
            
        headers = reports_data[row0]
        dictFieldColumnIndex = {}
        for fld in fieldnames:
            strings = dictMatchStrings[fld]
            ids = [ind for s in strings for (ind, strcol) in enumerate(headers) if s in strcol]
            
            dictFieldColumnIndex[fld] = ids
                
        lotColumns = [i for (i, s) in enumerate(headers) if reLotNum.match(s)]
        
        reports_data = reports_data[row0+1:]
        report_form_data = []
        for row in reports_data:    
            if not [c for c in row if c!='']:
                continue 
            report = {}
            for fld in fieldnames: 
                if dictFieldColumnIndex[fld]:
                    ##: It could be mulitple columns, e.g., Narrative I and Narrative II. They need to be merged
                    report[fld] = ' '.join([row[idx].strip() for idx in dictFieldColumnIndex[fld]])
                    
                    # special processing
                    if fld in ['MedDRA', 'Vaccines', 'Vsaccine Names']:
                        report[fld] = re.sub(',|:', ';', report[fld])   
                else:
                    report[fld] = ''
            
            if lotColumns: 
                report['Lot Number'] = '; '.join([row[i] for i in lotColumns if row[i]!=''])
            else:
                report['Lot Number'] = ''
                
            report['Serious'] = False
            seriousColumns = [i for (i, s) in enumerate(headers) if s in seriousFields]
            for i in seriousColumns:
                if row[i]=='Y':
                    report['Serious'] = True
                    break
            
            report_form_data.append(report)
        
        return report_form_data
    
    def load_reports_faers(self):
        self.loading_faers_file = True
        self.load_reports()
        self.loading_faers_file = False
        
    def read_saved_report_csv(self, reports_data): 
         
        fieldnames = ['Report ID','Age','Date of Exposure','Date of Onset','Vaccines','Vaccine Names','MedDRA','Gender', 'Lab Text', 'Received Date', 'Lot Number', 'Free Text']
        if not reports_data[0][0][0].isdigit():
            reports_data = reports_data[1:]
        
        if len(reports_data[0][0].split('-')[0]) > 6:
            isFAERS = True
        else:
            isFAERS = False
            
        report_form_data = []
        for row in reports_data:           
            if len(row)==9:
                row.append(row[8])
            row[5]=row[5].rstrip()
            row[6]=row[6].rstrip()
            row[5] = re.sub('\n', ', ', row[5])
            row[6] = re.sub('\n', '; ', row[6])
            
            if isFAERS:
                row[2] = ''
                row[3] = ''
            report = dict(zip(fieldnames, row))
            report_form_data.append(report)
        
        return report_form_data
    
    def vaers_report_csv_reader(self, reports_data): 
        
        reports_data = reports_data[1:]
        #fieldnames = ['Report ID','Age','Date of Exposure','Date of Onset','Vaccines','Vaccine Names','MedDRA','Gender','Free Text', 'Lab Text']
        fieldnames = ['Report ID','Age','Date of Exposure','Date of Onset','Vaccines','Vaccine Names','MedDRA','Gender', 'Lab Text','Free Text']
        if len(reports_data[0][0]) > 6:
            isFAERS = True
        else:
            isFAERS = False
            
        report_form_data = []
        for row in reports_data:           
            if len(row)==9:
                row.append(row[8])
            row[5]=row[5].rstrip()
            row[6]=row[6].rstrip()
            row[5] = re.sub('\n', ', ', row[5])
            row[6] = re.sub('\n', '; ', row[6])
            
            if isFAERS:
                row[2] = ''
                row[3] = ''
            report = dict(zip(fieldnames, row))
            report_form_data.append(report)
        
        return report_form_data
    
    def xml_files_reader(self, reader): 
        sections = ['Boxed Warning', 'Warnings and Precautions', 'Adverse Reactions', 'Use in Specific Populations']
        
        numreports= len(reader)
        progress = QProgressDialog("Processing XML file and translate AE terms to MedDRA terms from {0} reports.".format(numreports), "Cancel", 0, numreports - 1)
        progress.setWindowTitle("ETHER")
        progressbar = QProgressBar(progress)
        progressbar.setVisible(1)
        progress.setBar(progressbar)
        progress.setWindowModality(Qt.WindowModal)
        progress.setRange(0, numreports)
        progress.setValue(0)
        
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))

        report_form_data = []
        for idx, line in enumerate(reader):
#             tree = ET.parse('.\\xml\\'+line)
            line = line.strip('\n')
            filename = '.\\xml\\'+line
            (fulltext, textSectionLabel) = util.XMLUtil.find_section_text_by_titles(filename, sections)
            if not fulltext:
                continue
            report = {}
            report['Report ID'] = line
            report['Free Text'] = fulltext
            
            report['PTsXML'] = []
            
            allPTs = []
            for (section, subsection, table, PTs) in report['PTsXML']:
                allPTs +=[pt[1] for pt in PTs]
            allPTs = list(set(allPTs))
            report['MedDRA']= '; '.join(allPTs)
            report_form_data.append(report)
            
            progress.setValue(idx)
            if progress.wasCanceled():
                QApplication.restoreOverrideCursor()       
                return None          
            
        QApplication.restoreOverrideCursor()       
        filename = QFileDialog.getSaveFileName(self, "Save MedDRA terms from XML files", "./meddra_xml.csv", "CSV (*.csv)")[0]
        if filename:
            util.ReportGenerator.save_xml_reports_csv(report_form_data, filename)        
        
        return report_form_data
        
    def vaers_report_txt_reader(self, reader): 
        #fieldnames = ['Report ID','Age','Date of Exposure','Date of Onset','Vaccines','Vaccine Names','MedDRA','Gender','Free Text', 'Lab Text']
        fieldnames = ['Report ID','Age','Date of Exposure','Date of Onset','Vaccines','Vaccine Names','MedDRA','Gender', 'Lab Text','Free Text']
        report_form_data = []
        if len(reader[0][0]) > 6:
            isFAERS = True
        else:
            isFAERS = False
        
        for line in reader:
            #drop initial '"' and trailing '"\n'. split on '" ,  "'
            fields = re.split('", "|","', line[1:-2])
            if isFAERS:
                fields[2] = ''
                fields[3] = ''
            report = dict(zip(fieldnames, fields))
            
            report_form_data.append(report)
            
        return report_form_data
    
    def vaers_report_txt_reader_new(self, reader): 
        #fieldnames = ['Report ID','Age','Date of Exposure','Date of Onset','Vaccines','Vaccine Names','MedDRA','Gender','Free Text', 'Lab Text']
        fieldnames = ['Report ID','Age','Date of Exposure','Date of Onset','Vaccines','Vaccine Names','MedDRA','Gender', 'Lab Text','Received Date', 'Lot Number', 'Free Text']
        report_form_data = []
        if len(reader[0][0].split('-')[0]) > 6:
            isFAERS = True
        else:
            isFAERS = False
        
        reportIDs = []
        for line in reader:
            #drop initial '"' and trailing '"\n'. split on '" ,  "'
            fields = re.split('", "|","', line[1:-2])
            if isFAERS:
                fields[2] = ''
                fields[3] = ''
            if fields[10]=='NULL':
                fields[10]=''
                
            report = dict(zip(fieldnames, fields))
            
            if report['Report ID'] in reportIDs:
                rpt = [r for r in report_form_data if r['Report ID']==report['Report ID']][0]
                if report['Lot Number']!='':
                    if rpt['Lot Number']=='':
                        rpt['Lot Number'] = report['Lot Number']
                    else:
                        rpt['Lot Number'] += '; ' + report['Lot Number']
                continue
            else:
                reportIDs.append(report['Report ID'])          
                
            #yield report
            report_form_data.append(report)
            
        return report_form_data
    
    def read_data_file_universal(self, filename):      
        try:
            with open(filename, 'r') as f:
#            with codecs.open(filename, 'r', encoding='utf-8-sig') as f:
                if filename[-3:]=='csv':
                    reader = csv.reader(f)
                    raw_data = [row for row in reader]
                    header = raw_data[0]
                    ncol = len(header)
                    if ncol<=2:
                        report_form_data = self.read_report_ids(raw_data)
                    elif ncol==12:
                        report_form_data = self.read_saved_report_csv(raw_data)
                    elif ncol<12:
                        report_form_data = self.vaers_report_csv_reader(raw_data)
                    else:
                        report_form_data = self.faers_report_csv_reader(raw_data)
                else:
                    raw_data = f.readlines()
                    raw_data = [r for r in raw_data if r!=''] ##: remove empty line
                    
                    line0 = raw_data[0]
                    ncol = len(re.split('", "|","', line0))
                    if ncol==1 and 'xml' in line0.lower():
                        report_form_data = self.xml_files_reader(raw_data)
                    elif ncol>2:
                        report_form_data = self.vaers_report_txt_reader_new(raw_data)
                    else:
                        id_data = [line.strip() for line in raw_data]
                        report_form_data = self.read_report_ids(id_data)
                        
        except Exception as e:
            QMessageBox.critical(None, "ETHER", str(e) + "\nData file not valid!")
            return None
                
        ##: Complement empty fields
        fieldnames = ['Report ID','Age','Date of Exposure','Date of Onset','Vaccines','Vaccine Names','MedDRA','Gender','Free Text', 'Lab Text', 
                      'Serious', 'Died', 'Location', 'History', 'Received Date', 'Lot Number', 'Indication', 'Primary Suspect', 
                      'Birth Date', 'First Name', 'Middle Initial', 'Last Name', 'Patient ID', 'MFR Control Number']
                
        if report_form_data:
            for fld in fieldnames:
                if not fld in report_form_data[0].keys():
                    default = ''
                    if fld=='Gender':
                        default = 'UNKNOWN'
                    elif fld=='Died' or fld=='Serious':
                        default = False
                        
                    for report in report_form_data:
                        report[fld] = default
            
            for report in report_form_data:
                report['Free Text'] = util.remove_nonascii(report['Free Text'])

        return report_form_data
    
    def read_data_file_universal_noXML(self, filename):      
        try:
            with open(filename, 'r') as f:
#            with codecs.open(filename, 'r', encoding='utf-8-sig') as f:
                if filename[-3:]=='csv':
                    reader = csv.reader(f)
                    raw_data = [row for row in reader]
                    header = raw_data[0]
                    ncol = len(header)
                    if ncol<=2:
                        #report_form_data = [row[0] for row in raw_data]
                        report_form_data = self.read_report_ids(raw_data)
                    elif ncol==12:
                        report_form_data = self.read_saved_report_csv(raw_data)
                    elif ncol<12:
                        report_form_data = self.vaers_report_csv_reader(raw_data)
                    else:
                        report_form_data = self.faers_report_csv_reader(raw_data)
                else:
#                    reports_string = f.read()
                    raw_data = f.readlines()
                    raw_data = [r for r in raw_data if r!=''] ##: remove empty line
                    #raw_data = StringIO.StringIO(reports_string)
                    
                    line0 = raw_data[0]
                    ncol = len(re.split('", "|","', line0))
                    if ncol>2:
                        report_form_data = self.vaers_report_txt_reader_new(raw_data)
                    else:
                        id_data = [line.strip() for line in raw_data]
                        report_form_data = self.read_report_ids(id_data)
                        
        except Exception as e:
            QMessageBox.critical(None, "ETHER", str(e) + "\nData file not valid!")
            return None
                
        ##: Complement empty fields
        fieldnames = ['Report ID','Age','Date of Exposure','Date of Onset','Vaccines','Vaccine Names','MedDRA','Gender','Free Text', 'Lab Text', 
                      'Serious', 'Died', 'Location', 'History', 'Received Date', 'Lot Number', 'Indication', 'Primary Suspect']
#                 self.c.execute("create table ETHER_REPORT_FORM (VAERS_ID text, AGE text, DATE_EXPOSURE text, DATE_ONSET text, VACCINES text, VACCINE_NAMES text, \
#                 MEDDRA text, GENDER text, FREE_TEXT text, LAB_TEXT text, SERIOUS boolean, DIED boolean, LOCATION text, HISTORY text, DATE_RECEIVED text, \
#                 LOT_NUMBER text, INDICATION text, PRIMARY_SUSPECT text)")
                
        if report_form_data:
            for fld in fieldnames:
                if not fld in report_form_data[0].keys():
                    default = ''
                    if fld=='Gender':
                        default = 'UNKNOWN'
                    elif fld=='Died' or fld=='Serious':
                        default = False
                        
                    for report in report_form_data:
                        report[fld] = default
                        
        return report_form_data
    
    def read_in_patient_txt(self, reports):
        filename = 'C:\\VAERS_Network_Analysis\\data\\patient.txt'
        try:
            with open(filename, 'r') as f:
#            with codecs.open(filename, 'r', encoding='utf-8-sig') as f:
                raw_data = f.readlines()
                for line in raw_data:
                    if line=='': continue
                    cols = re.split('", "|","', line[1:-2])
                    
                    report = None
                    for r in reports:
                        if r['Report ID'] == cols[0]:
                            report = r
                            break
                    
                    ##: couldn't find corresponding report, this means the patient.txt doesn't match reports.txt. stop reading patient.txt.
                    if not report:
                        return reports
                    
                    if report:
                        if cols[1]=='Yes':
                            report['Serious'] = True
                        else:
                            report['Serious'] = False
                        if cols[2]=='Yes':
                            report['Died'] = True
                        else:
                            report['Died'] = False
                        report['Location'] = cols[3]
                        report['History'] = cols[7]
                        
        except Exception as e:
            #QMessageBox.critical(None, "ETHER", str(e) + "\nPatient.txt file not valid!")
            print str(e) + "\nPatient.txt file not valid!"
            return reports
        
        return reports
    
    def read_report_ids(self, raw_data):
        report_data = []
        for row in raw_data[1:]:     
            report = {}
            if isinstance(row,list):
                report['Report ID'] = row[0]
            else:
                report['Report ID'] = row
            
            report_data.append(report)
        
        return report_data

    def read_reports_form_data(self, report_form_data):
        if report_form_data:
            numreports = len(report_form_data)
        else:
            return

        #display a progress window
        progress = QProgressDialog("Extracting features from {0} reports.".format(numreports), "Cancel", 0, numreports - 1)
        
        progress.setWindowTitle("ETHER")
        progressbar = QProgressBar(progress)
        progressbar.setVisible(1)
        progress.setBar(progressbar)
        progress.setWindowModality(Qt.WindowModal)
        progress.setRange(0, numreports)
        progress.setValue(0)
        
        #self.use_DB = True
        self.overwrite_DB = self.sysPreferences.toOverwriteDB()
        reports = []
        self.preStrExpDate = None
        for idx, report in enumerate(report_form_data):
#             print idx
            try:
                # check if the report is in the database
                if  not self.overwrite_DB and self.vaersdb.checkid(report['Report ID']):
                    #report = self.retrieve_report_from_DB(report['Report ID'], report)
                    report = self.retrieve_report_vaers_formdata_from_DB(report['Report ID'], report)
                    
                    if self.in_debug_mode:
                        report = self.processing_report_text(report)
                        
                    if self.has_report_text_mined(report['Report ID']):
                        report = self.retrieve_report_TM_from_DB(report['Report ID'], report)
                    else:
                        report = self.processing_report_text(report)
                        
                    #report = self.retrieve_report_from_DB(report['Report ID'])
                    #report['Lab Data'] = ''
                                       
                    if self.vaersdb.checktimers(report['Report ID'], self.username):
                        timers_comments = list(self.vaersdb.retrievetimers(report['Report ID'], self.username)[0])
                        report['Timer'] = timers_comments[2:7]
#                         report['Comment'] = timers_comments[7:12]
                    else:
                        report['Timer'] = [0] * self.num_tabs
#                         report['Comment'] = [''] * self.num_tabs
                else:
                    report = self.processing_report_text(report)
                    
            except sqlite3.OperationalError as strerror:
                logging.warning("Database error. " + str(strerror))          
                choice = QMessageBox.question(None, "ETHER", "Database error. " + str(strerror) 
                                              +". Case # " + report['Report ID'] + '!', \
                                              QMessageBox.Ignore, QMessageBox.Abort)
                if choice == QMessageBox.Ignore:
                    continue
                else:
                    return None     
#             except Exception as e:
#                 choice = QMessageBox.question(None, "ETHER", str(e)+"\nCouldn't process report #"+ \
#                                               str(idx) + ' (Case ID = ' + report['Report ID'] \
#                                               +'). Please check the input file or send the report ID to the developer.', \
#                                               QMessageBox.Ignore, QMessageBox.Abort)
#                 if choice == QMessageBox.Ignore:
#                     continue
#                 else:
#                     return False
   
            #parse features into report dictionary fields    
            if report['Features']:
                report['Diagnosis'] = ';'.join(set([f.getString() for f in report['Features'] if f.getType() in set(['DIAGNOSIS', 'CAUSE_OF_DEATH', 'SECOND_LEVEL_DIAGNOSIS'])]))
                report['Alternative Explanation'] = ';'.join([f.getString() for f in report['Features'] if f.getType() in set(['DRUG', 'MEDICAL_HISTORY', 'FAMILY_HISTORY'])])
                report['Time to Onset'] = ';'.join([f.getString() for f in report['Features'] if f.getType() == 'TIME_TO_ONSET'])
            else:
                report['Diagnosis'] = ''
                report['Alternative Explanation'] = ''
                report['Time to Onset'] = ''
                              
            reports.append(report)
            progress.setValue(idx)
            if progress.wasCanceled():
                #sys.exit()  
                return None          

        self.vaersdb.create_index()
        return reports
    
    def processing_report_text(self, report):
        
        if not self.extractor:
            #read lexicon file
            try:
                with open('lexicon.txt', 'r') as f:
                    lexicon = ast.literal_eval(f.read())
                with open('lexicon2nd.txt', 'r') as f:
                    lexicon2 = ast.literal_eval(f.read())    
                with open('lexicon3rd.txt', 'r') as f:
                    lexicon3 = ast.literal_eval(f.read())    
            except Exception as e:
                QMessageBox.critical(None, "ETHER", str(e))
                sys.exit(app.quit())
            #self.lexicon = lexicon2 + lexicon
            self.lexicon = lexicon3 + lexicon + lexicon2
            
            self.extractor = textan.FeatureExtractor(self.config, self.lexicon)
         
        if len(report['Report ID'].split('-')[0])<=6:
            self.reportType = 'vaers'
        else:
            self.reportType = 'faers'
        
        documentFeature= self.extractor.extract_features_temporal(
                            report['Free Text'], report['Date of Exposure'], report['Date of Onset'], report['Received Date'], self.reportType)
        self.preStrExpDate = report['Date of Exposure']
                    
        if not documentFeature:
            report['PreferredTerms'] = ''
            report['Features'] = []
            report['Exposure Date'] = None
            report['Onset Date'] = None
            report['CalculatedOnsetTime'] = None
            report['DatesConfidence'] = None                    
            report['Timexes'] = []
            report['Lab Data'] = ''
            report['Comment'] = ''
            report['Class'] = 0
            report['DxLevel'] = ''
            report['Review'] = ''
            report['Action'] = 0
            report['Mark'] = False
            report['Annotations'] = []
            report['Summarizations'] = []
            report['TimeAnnotations'] = []
            return report
                
        featuresTM = documentFeature.getFeatureArray()
        features = [FeatureStruct(feat) for feat in featuresTM]
        
        report['PreferredTerms'] = ''
        
        report['Features'] = features
                        
        report['Exposure Date'] = documentFeature.getExposeDate()
        report['Onset Date'] = documentFeature.getOnsetDate()
        report['CalculatedOnsetTime'] = documentFeature.getCalculatedOnsetTimeHours()
        #report['IsDatesInput'] = documentFeature.isDatesInput(
        report['DatesConfidence'] = documentFeature.getConfidenceLevel()
                    
        report['Date of Exposure'] = documentFeature.getInputExpDate()
        report['Date of Onset'] = documentFeature.getInputOnsetDate()
        report['Received Date'] = documentFeature.getReceivedDate()
        
        report['Review'] = util.ReportUtil.getReportSummary(report, self.reportType, self.sysPreferences.toCodeSummary())
        report['Action'] = -1
        report['Mark'] = False
        
        report['Comment'] = ''
        (report['Class'], report['DxLevel']) = ('', 0)
                    
        report['Timexes'] = documentFeature.getTimexes()
        
        report['Annotations'] = []
        report['TimeAnnotations'] = []
        report['Summarizations'] = []
        
        report['Lab Data'] = ''
        
        if self.overwrite_DB and self.vaersdb.checkid(report['Report ID']):
            self.vaersdb.deleteReport(report['Report ID'])

        self.commit_to_DB(report, documentFeature)
 
        report['Timer'] = [0] * self.num_tabs
        
        return report
        
    def processing_report_text_featnosplit(self, report):
        
        if not self.extractor:
            #read lexicon file
            try:
                with open('lexicon.txt', 'r') as f:
                    lexicon = ast.literal_eval(f.read())
                with open('lexicon2nd.txt', 'r') as f:
                    lexicon2 = ast.literal_eval(f.read())    
            except Exception as e:
                QMessageBox.critical(None, "ETHER", str(e))
                sys.exit(app.quit())
            #self.lexicon = lexicon2 + lexicon
            self.lexicon = lexicon + lexicon2
            
            self.extractor = textan.FeatureExtractor(self.config, self.lexicon)
        
        if len(report['Report ID'].split('-')[0])<=6:
            self.reportType = 'vaers'
        else:
            self.reportType = 'faers'
        
        if report['Report ID']=='425983':
            ddd=1
        documentFeature= self.extractor.extract_features_temporal(
                            report['Free Text'], report['Date of Exposure'], report['Date of Onset'], report['Received Date'], self.reportType)
        self.preStrExpDate = report['Date of Exposure']
                    
        if not documentFeature:
            report['PreferredTerms'] = ''
            report['Features'] = []
            report['Exposure Date'] = None
            report['Onset Date'] = None
            report['CalculatedOnsetTime'] = None
            report['DatesConfidence'] = None                    
            report['Timexes'] = []
            report['Lab Data'] = ''
            report['Comment'] = ''
            report['Class'] = 0
            report['DxLevel'] = ''
            report['Review'] = ''
            report['Action'] = 0
#             report['Received Date'] = ''
#             report['Lot Number'] = ''
            return report
                
#        features= documentFeature.getMedicalFeaturesTM()
        featuresTM = documentFeature.getFeatureArray()
        features = [FeatureStruct(feat) for feat in featuresTM]
        
        report['PreferredTerms'] = ''
        report['Features'] = features
                        
        report['Exposure Date'] = documentFeature.getExposeDate()
        report['Onset Date'] = documentFeature.getOnsetDate()
        report['CalculatedOnsetTime'] = documentFeature.getCalculatedOnsetTimeHours()
        #report['IsDatesInput'] = documentFeature.isDatesInput(
        report['DatesConfidence'] = documentFeature.getConfidenceLevel()
                    
        report['Date of Exposure'] = documentFeature.getInputExpDate()
        report['Date of Onset'] = documentFeature.getInputOnsetDate()
        report['Received Date'] = documentFeature.getReceivedDate()
        
        report['Review'] = ''
        report['Action'] = -1
        
        report['Comment'] = ''

        (report['Class'], report['DxLevel']) = ('', 0)
                    
#         if not report['Exposure Date']:
#             print 'Exposure Date of report#' + report['Report ID'] + 'is None!'
                    
        report['Timexes'] = documentFeature.getTimexes()
        
        report['Lab Data'] = ''
        
        if self.overwrite_DB and self.vaersdb.checkid(report['Report ID']):
            self.vaersdb.deleteReport(report['Report ID'])
                        #print 'delete report' + report['Report ID']

        self.commit_to_DB(report, documentFeature)

        report['Timer'] = [0] * self.num_tabs
        report['Comment'] = [''] * self.num_tabs
        
        return report
    
    def retrieve_report_vaers_formdata_from_DB(self, reportid, report = None):
        report = {}
        report['Report ID'] = reportid
        form_data = self.vaersdb.retrieveReportForm(reportid)
        (report['Age'], report['Date of Exposure'], report['Date of Onset'], report['Vaccines'], 
                    report['Vaccine Names'], report['MedDRA'], report['Gender'], report['Free Text'], report['Lab Text'], 
                    report['Serious'], report['Died'], report['Location'], report['History'], report['Received Date'], 
                    report['Lot Number'], report['Indication'], report['Primary Suspect'],
                    report['Birth Date'], report['First Name'], report['Middle Initial'], report['Last Name'], 
                    report['Patient ID'], report['MFR Control Number']
                    ) = form_data  
                                                   
        return report
    
    def retrieve_report_TM_from_DB(self, reportid, report = None):
                                                              
        features = self.vaersdb.retrieveFeatures(report['Report ID'])    
        
        featureComments = self.vaersdb.retrieveFeatureComments(report['Report ID'])
        comments = ['']*len(features)   
        matches = [0]*len(features)   
        for comment in featureComments:
            comments[comment[0]] = comment[1]
            matches[comment[0]] = comment[2]
                
        confidence = 1 ##: feature confidence has not been handled, and not in the database
        featuresTM = []
        for feat in features:
            ft = FeatureStruct((feat[0], feat[1], feat[2],  feat[5],  feat[6], feat[3], feat[4], confidence, feat[7], feat[8], comments[feat[8]], matches[feat[8]], feat[9]))
            featuresTM.append(ft)
        report['Features'] = featuresTM
        
        reportFeature = self.vaersdb.retrieveReportFeature(report['Report ID'])
        if reportFeature[0]!='':
            report['Exposure Date'] = parse(reportFeature[0])
        else:
            report['Exposure Date'] = None       
        if reportFeature[1]!='':
            report['Onset Date'] = parse(reportFeature[1])
        else:
            report['Onset Date'] = None
        report['CalculatedOnsetTime'] = reportFeature[2]
        report['DatesConfidence'] = reportFeature[3]
        
        report['PreferredTerms'] = reportFeature[4]
        report['Comment'] = reportFeature[5]  ##: This is the SUMMARY column in database table, due to historical reason. 
        if '<html>' in report['Comment']:
            report['Comment'] = ''          ##: Clean up historical summary from this field
        report['Review'] = reportFeature[6]
        report['Action'] = reportFeature[7]
        report['Class'] = reportFeature[8]
        report['DxLevel'] = reportFeature[9]
        report['Mark'] = reportFeature[10]
        
#         report['Summary'] = reportFeature[6]
        report['Lab Data'] = []
        
        report['Annotations'] = [FeatureAnnotation(annt) for annt in self.vaersdb.retrieveAnnotations(report['Report ID'])]
        
        summarizations = self.vaersdb.retrieveSummarizations(report['Report ID'])
        elements = []
        for elem in summarizations:
            record = elem + (-1, '')
            elements.append(SummaryElement(record))
        report['Summarizations'] = elements

        report['TimeAnnotations'] = [TimeAnnotation(annt) for annt in self.vaersdb.retrieveTimeAnnotations(report['Report ID'])]
        
        timexes = self.vaersdb.retrieveTimexes(report['Report ID'])
        timexList = [(s, pos, pos+len(s), dt) for s, pos, dt in timexes]
        report['Timexes'] = timexList
   
        return report
    
    def updateReportReview(self, reportid, review, action, comment):
        self.vaersdb.updateReportReview(reportid, review, action, comment)
        self.vaersdb.conn.commit()
        
    def updateFeatureComment(self, reportid, comments):
        for featureid, comment, matchid in comments:
            self.vaersdb.updateFeatureComment(reportid, featureid, comment, matchid)
        self.vaersdb.conn.commit()
        
    def updateFeatureAnnotation(self, reportid, annotations):
        self.vaersdb.deleteReportAnnotations(reportid)
        for annt in annotations:
            (antid, featText, featType, errorType, comment, startPos, endPos, pt, featID, timeID, timeRel) = annt.getDBRecord()
            self.vaersdb.updateAnnotation((reportid, antid, featText, featType, errorType, comment, startPos, endPos, pt, featID, timeID, timeRel))
        self.vaersdb.conn.commit()

    def updateTimeAnnotation(self, reportid, annotations):
        self.vaersdb.deleteReportTimeAnnotations(reportid)
        for annt in annotations:
            (antid, timeText, startPos, endPos, timeType, timeVal, confidence, comment, timeID, timeRel) = annt.getRecord()
            self.vaersdb.updateTimeAnnotation(reportid, antid, timeText, timeType, timeVal, startPos, endPos, confidence, comment, timeID, timeRel)
        self.vaersdb.conn.commit()
        
    def has_report_text_mined(self, reportid):
        return self.vaersdb.hasTextMined(reportid)
        
    def commit_to_DB(self, report, documentFeature):
        report_form_data = (report['Report ID'], report['Age'], report['Date of Exposure'], report['Date of Onset'], report['Vaccines'], 
                            report['Vaccine Names'], report['MedDRA'], report['Gender'], report['Free Text'], report['Lab Text'], 
                            report['Serious'], report['Died'], report['Location'], report['History'], report['Received Date'], 
                            report['Lot Number'], report['Indication'], report['Primary Suspect'],
                            report['Birth Date'], report['First Name'], report['Middle Initial'], report['Last Name'], 
                            report['Patient ID'], report['MFR Control Number'])
        self.vaersdb.insertReportForm(report_form_data)
        
        if report['Exposure Date']:
            strExpDateEst = report['Exposure Date'].isoformat().split('T')[0]
        else:
            strExpDateEst = ''
        if report['Onset Date']:
            strOnsetDateEst = report['Onset Date'].isoformat().split('T')[0]
        else:
            strOnsetDateEst = ''
        document_feature = (report['Report ID'], strExpDateEst, strOnsetDateEst, report['CalculatedOnsetTime'], report['DatesConfidence'], 
                            report['PreferredTerms'], report['Comment'], report['Review'], report['Action'], report['Class'], report['DxLevel'], report['Mark'])
        self.vaersdb.insertReportFeature(document_feature)
                    
        featList = []
        for feat in report['Features']:
            featrow = feat.getDBFeatureTableRow()
            featList.append(featrow)
                
        self.vaersdb.insertFeatures(report['Report ID'], featList)
        
        labList = []
        for name, val, unit, specimen, strRange, evaluation, strTest in report['Lab Data']:
            labList.append((name, val, unit, specimen, evaluation, strTest, '')) # the last '' is comment
        self.vaersdb.insertLabTests(report['Report ID'], labList)

        timexList = documentFeature.getTimexesDB()
        self.vaersdb.insertTimexes(report['Report ID'], timexList)
                    
        self.vaersdb.conn.commit()
                    
    def parse_time_string(self, time_string, preStrExpDate = None):        
        if time_string == '' and preStrExpDate:
            return preStrExpDate
     
        try:
            dt = parse(time_string)
        except:
            return preStrExpDate
        
        return dt
        
    def save_full_features(self):
        filename = QFileDialog.getSaveFileName(self, "Save extracted features", "./Extracted Information.csv", "CSV (*.csv *.txt)")[0]
        if filename:
            reports = [self.reports[i] for i in self.selectedReportIndices]
            util.ReportGenerator.save_features(reports, filename)
            
    def save_reports_txt(self):
        filename = QFileDialog.getSaveFileName(self, "Save ETHER summaries", "./reports.txt", "TXT (*.txt)")[0]
        if filename:
            reports = [self.reports[i] for i in self.selectedReportIndices]
            util.ReportGenerator.save_reports_txt(reports, filename)
    
    def save_reports_csv(self):
        filename = QFileDialog.getSaveFileName(self, "Save reports in a .csv file", "./reports.csv", "CSV (*.csv)")[0]
        if filename:
            reports = [self.reports[i] for i in self.selectedReportIndices]
            util.ReportGenerator.save_reports_csv(reports, filename)
                        
    def save_ether_summary(self):
        filename = QFileDialog.getSaveFileName(self, "Save ETHER summaries", "./Product Info & Case Summaries.csv", "CSV (*.csv *.txt)")[0]
        if filename:
            reports = [self.reports[i] for i in self.selectedReportIndices]
            util.ReportGenerator.save_ether_summary(reports, filename)
            
    def save_summarized_cases(self):
        filename = QFileDialog.getSaveFileName(self, "Save summarized cases", "./Summarized Cases Tab.csv", "CSV (*.csv *.txt)")[0]
        if filename:
            reports = [self.reports[i] for i in self.selectedReportIndices]
            util.ReportGenerator.save_summarized_cases(reports, filename)

    def save_annotations(self):
        
        path = os.path.dirname('./eval/uima/annotation/')
        if not os.path.exists(path):
            os.makedirs(path)
        else:
            filelist = [ f for f in os.listdir(path)]
            for f in filelist:
                os.remove(path + '/' + f)
    
        path = os.path.dirname('./eval/i2b2/annotation/')
        if not os.path.exists(path):
            os.makedirs(path)
        else:
            filelist = [ f for f in os.listdir(path)]
            for f in filelist:
                os.remove(path + '/' + f)
                
        reports = [self.reports[i] for i in self.selectedReportIndices]
        for report in reports:
            print report['Report ID']
            self.save_report_annotations(report)
        
        QMessageBox.information(None, "Annotations", "Annotations of " + str(len(reports)) + " reports have been saved in ./eval folder", \
                                              QMessageBox.Ok)
        
    def save_report_annotations(self, report):
        featureAnnotations = report['Annotations']
        timeAnnotations = report['TimeAnnotations']
        
        featList = [(feat.getID(), feat.getType(), feat.getStartPos(), feat.getEndPos(), feat.getText(), feat.getTimeID(), feat.getTimeRelation()) for feat in featureAnnotations]
        timexList = [(t.getID(), t.getType(), t.getStartPos(), t.getEndPos(), t.getDate(), t.getString(), t.getTimeID(), t.getTimeRelation()) for t in timeAnnotations]
        
        tree = util.XMLUtil.create_annotation_tree_uima(featList, timexList, report['Free Text'])
        outputFileName = './eval/uima/annotation/' + report['Report ID']+'.xml'
        tree.write(outputFileName, pretty_print=True, xml_declaration=True, encoding="utf-8")
        
        tree = util.XMLUtil.create_annotation_tree_i2b2(featList, timexList, report['Free Text'])
        outputFileName = './eval/i2b2/annotation/' + report['Report ID']+'.xml'
        tree.write(outputFileName, pretty_print=True, xml_declaration=True, encoding="utf-8")
       
    
    def save_ether_annotations(self):
        
        path = os.path.dirname('./eval/uima/ETHER/')
        if not os.path.exists(path):
            os.makedirs(path)
        else:
            filelist = [ f for f in os.listdir(path)]
            for f in filelist:
                os.remove(path + '/' + f)
    
        path = os.path.dirname('./eval/i2b2/ETHER/')
        if not os.path.exists(path):
            os.makedirs(path)
        else:
            filelist = [ f for f in os.listdir(path)]
            for f in filelist:
                os.remove(path + '/' + f)
                
        reports = [self.reports[i] for i in self.selectedReportIndices]
        for report in reports:
#             if report['Report ID']!='258529-1': continue
            self.save_report_ETHER_annotations(report)
        
        QMessageBox.information(None, "Annotations", "Annotations of " + str(len(reports)) + " reports have been saved in ./eval folder", \
                                              QMessageBox.Ok)
            
    def get_report_timexes(self, report):
        text = report['Free Text']
        timexes = report['Timexes']        

        rel_signals = ['before','after','prior','later','earlier','post','ago','next', 'following', 'until']    
        
        timexList = []
        for i, t in enumerate(timexes):
            timeString, posStart, posEnd, dtime = t
            previous3Words, next2Words = util.find_neighboring_words(text, posStart, posEnd, 3, 2)
            ttype = timexan.getTimexType(t[0],  previous3Words, next2Words)
            
            if ttype =='Relative':
                if next2Words and (next2Words[0] in rel_signals or next2Words[0].split('-')[0] in rel_signals):
                    timeString += ' ' + next2Words[0]
                elif previous3Words and previous3Words[-1] in rel_signals:
                    timeString = previous3Words[-1] + ' ' + timeString 
                    posStart = posStart - len(previous3Words[-1]) -1
                    
            dt = None
            if dtime!= '':
#                 dt = timexan.parse_single_raw_time(t[0])
                dt = self.parse_time_string(dtime)
            
            timex = timexan.Timex3(posStart, posStart + len(timeString), ttype, dt, timeString, 1)
            timex.setID(i)
            
            timexList.append(timex)
        
        return timexList
    
    def save_report_ETHER_annotations(self, report):
            
        featureStructs = report['Features']
        features = []
        for ft in featureStructs:
            feat = textan.Feature((ft.getType(), ft.getString(), -1, [], ft.getStartPos(), ft.getEndPos()))
            feat.setID(ft.getFeatureID())        
            features.append(feat)
        features.sort(key=lambda x:x.getStartPos())
        
        timexes = self.get_report_timexes(report)
        
        if not self.extractor:
            self.extractor = textan.FeatureExtractor()
        
        print report['Report ID']
        docFeature = self.extractor.extract_feature_time_associations(features, timexes, report['Free Text'])    
            
        tree = util.XMLUtil.create_ether_annotation_tree_i2b2(docFeature, report['Free Text'])
        outputFileName = './eval/i2b2/ETHER/' + report['Report ID']+'.xml'
        tree.write(outputFileName, pretty_print=True, xml_declaration=True, encoding="utf-8")
        
        tree = util.XMLUtil.create_ether_annotation_tree_uima(docFeature, report['Free Text'])
        outputFileName = './eval/uima/ETHER/' + report['Report ID']+'.xml'
        tree.write(outputFileName, pretty_print=True, xml_declaration=True, encoding="utf-8")
    
    def save_time_plot(self):
        report = self.reports[self.selectedReportIndices[self.current_report]]
        fname = 'timeplot_' + report['Report ID']
        
        if not os.path.exists('./reports'):
            os.makedirs('./reports')
    
        filename = QFileDialog.getSaveFileName(self, "Report Generation", "./reports/" + fname + ".pdf", "PDF (*.pdf)")[0]
        
        if not filename: return
        
        tab_temporal = self.get_mainWindow_tab('Case Features over Time')
        if tab_temporal:
            tab_temporal.central.temporalPlot.fig.savefig(filename, format='pdf') # "Temporal" Tab

    def update_temporal_setting(self):
        tab_temporal = self.get_mainWindow_tab('Case Features over Time')
        if tab_temporal:
            tab_temporal.central.update_layout() 
            
    def data_all(self):
        del self.filters_current[:]        
        self.update_filter_menu()            
        
        self.selectedReportIndices = range(len(self.reports))
        self.update_selected_reports()
        
    def on_menu_recent_filters_clicked(self):
        curAction = self.sender()
        strQuery = curAction.text()
        
        self.data_filtering(strQuery)
                
    def on_menu_recent_filters_clicked_apply(self):
        curAction = self.sender()
        strQuery = curAction.text()
        
        if not 'SMQ' in strQuery: # is a SMQ query
            criteria = FilterDialog.parseQueryString(strQuery)
            if criteria:
                self.apply_filter_criteria(criteria, strQuery)
        
                # keep new filter in the beginging of the list
                if strQuery in self.filters_current:
                    self.filters_current.remove(strQuery)
                self.filters_current.insert(0, strQuery)
                if strQuery in self.filters_recent:
                    self.filters_recent.remove(strQuery)
                self.filters_recent.insert(0, strQuery)
                self.update_filter_menu()
        
    def apply_filter_criteria(self, criteria, strQuery):
       
        if not criteria:
            return        
        
        results = set(self.selectedReportIndices)
        for (op, field, string, tFrom, tTo, axis) in criteria:
            indices = []
            for index in self.selectedReportIndices:
                report = self.reports[index]
                features = report['Features']
                expDate = report['Exposure Date']
                if axis=='Age':
                    if report['Age'].lower()=='unknown' or report['Age'].lower()=='':
                        ageDays = None
                    else:
                        ageDays = int(float(report['Age'])*365)
                    
                feats=[]
                for feat in features:
                    if feat.getType()!=field and field!='ALL': continue

                    if string!='Any' and string!='' and not re.findall('(^|\W)('+string+')($|\W)', feat.getString(), re.I):
                        continue
                    
                    ### test From condition
                    if tFrom!=None:
                        if not feat.getStartTime(): 
                            condFrom = False
                            continue
                            
                        if axis == 'Date':
                            tF = tFrom
                        elif axis == 'Vax':
                            tF = datetime.timedelta(days=tFrom) + expDate
                        elif axis == 'Age':
                            if ageDays:
                                tF = datetime.timedelta(days=tFrom*365-ageDays) + expDate
                            else: # make tF an impossible condition
                                tF = datetime.datetime(4000,1,1)
                         
                        if feat.getStartTime() >= tF:
                            condFrom = True
                        else:
                            condFrom = False
                    else:
                        condFrom = True
                    if not condFrom: 
                        continue
                    
                    ### test To condition
                    if tTo!=None:
                        if not feat.getEndTime(): 
                            condTo = False
                            continue
                            
                        if axis == 'Date':
                            tT = tTo
                        elif axis == 'Vax':
                            tT = datetime.timedelta(days=tTo) + expDate
                        elif axis == 'Age':
                            if ageDays:
                                #tT = datetime.timedelta(days = tTo-ageDays) + expDate
                                tT = datetime.timedelta(days = tTo*365-ageDays) + expDate
                            else: # make tT an impossible condition
                                tT = datetime.datetime(1000,1,1)
                         
                        if feat.getEndTime() <= tT:
                            condTo = True
                        else:
                            condTo = False
                    else:
                        condTo = True
                    if not condTo: 
                        continue
                                
                    feats.append(feat)                            

                if feats:
                    indices.append(index)
                    
            if op=='AND':
                results = results.intersection(set(indices))
            elif op=='OR':
                results = results.union(set(indices))
            else:
                results = results.difference(set(indices))
      
        lst = list(results)
        lst.sort()
        self.selectedReportIndices = lst
        
        # keep new filter in the beginning of the list
        if strQuery in self.filters_current:
            self.filters_current.remove(strQuery)
        self.filters_current.insert(0, strQuery)
        if strQuery in self.filters_recent:
            self.filters_recent.remove(strQuery)
        self.filters_recent.insert(0, strQuery)
        self.update_filter_menu()
            
        self.update_selected_reports()
        
        if len(lst) < len(self.reports):        
            self.data_all_action.setChecked(False)
        
    def open_preferences_dialog(self):
        toSortLasagna = self.sysPreferences.toSortLasagna()
        toAdjustYScale = self.sysPreferences.toAdjustYScaleAggregated()
        
        fontsize = self.sysPreferences.getFontSize()
        
        dialogConfig = PreferenceDialog(self.sysPreferences, self)
        dialogConfig.exec_()        
        
        if self.sysPreferences.getFontSize() != fontsize:
            tab_temporal = self.get_mainWindow_tab('Case Features over Time')
            if tab_temporal:
                tab_temporal.central.temporalPlot.fontsize = self.sysPreferences.getFontSize()
                tab_temporal.central.temporalPlot.textfontsize = self.sysPreferences.getFontSize()
                tab_temporal.central.temporalPlot.plot()
            
        if self.sysPreferences.toSortLasagna() != toSortLasagna or self.sysPreferences.toAdjustYScaleAggregated() != toAdjustYScale:            
            # update group plot if exists
            groupplot = self.get_mainWindow_tab('Group Plot')
            if groupplot:
                groupplot.plot()
 
    def data_filtering(self, strQuery=None):
        if not self.lexicon:
            try:
                with open('lexicon.txt', 'r') as f:
                    self.lexicon = ast.literal_eval(f.read())    
            except Exception as e:
                QMessageBox.critical(None, "ETHER", str(e))
                return
        if not self.lexicon_tagger:
            self.lexicon_tagger = textan.FastTagger(self.lexicon)
        
        strFeatures = ["DIAGNOSIS", "CAUSE_OF_DEATH", "SECOND_LEVEL_DIAGNOSIS", "SYMPTOM", 
                       "RULE_OUT", "MEDICAL_HISTORY", "FAMILY_HISTORY", "DRUG", "VACCINE"]
        
        lexiconRange = ['death', 'dignosis', 'vaccination', 'acronym', 
                         'anatomy', 'symptom', 'injection', 'vaccine', 'deathIndicator', 'drug', 
                         'diagnosis', 'medicalHistory', 'history', 'medication', 'Family', 'Allergy', 'Food', 'FamilyHistory']
        
        lexiconDict = {}
        for f in strFeatures:
            lexiconDict[f.lower()] = []
            
        reports = [self.reports[index] for index in self.selectedReportIndices]
        dateFrom = datetime.datetime(3000,1,1)
        dateTo = datetime.datetime(1000,1,1)
        for features in [report['Features'] for report in reports]:
            for feat in features:
                if not feat.getType() in strFeatures:
                    continue
                
                s = feat.getString()
                words = re.split(' |, ', s)
                words = [w.lower() for w in words]
                tags = self.lexicon_tagger.tag(words)
                for tag in tags:
                    if tag[1].lower() in lexiconRange:
                        lexiconDict[feat.getType().lower()].append(tag[0].lower())                
                
                if feat.hasStartTime() and feat.getStartTime() < dateFrom:
                    dateFrom = feat.getStartTime()
                if feat.hasEndTime() and feat.getEndTime() > dateTo:
                    dateTo = feat.getEndTime()
                     
        for key in lexiconDict:
            lexiconDict[key] = list(set(lexiconDict[key])) #.sort()
            lexiconDict[key].sort()
        
        filterDialog = FilterDialog(lexiconDict, (dateFrom, dateTo), strQuery)
        filterDialog.exec_()
        criteria = filterDialog.getCriteria()
        strQuery = filterDialog.getQueryString()
        
        if criteria:
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            try:
                self.apply_filter_criteria(criteria, strQuery)
            except:
                QApplication.restoreOverrideCursor()
                return
            QApplication.restoreOverrideCursor()
            
            # update group plot if exists
            groupplot = self.get_mainWindow_tab('Group Plot')
            if groupplot:
                groupplot.plot()
            
    def update_filter_menu(self):
        # display all recent filters on the menu and hide the rest menu items
        nn = min(self.filters_maxcount, len(self.filters_recent))
        for i in range(nn):
            self.filters_recent_actions[i].setText(self.filters_recent[i])
            self.filters_recent_actions[i].setVisible(True)
            if i==0 and not self.filters_recent_actions[i].isEnabled():
                self.filters_recent_actions[0].setEnabled(True)
        for i in range(nn,self.filters_maxcount):
            self.filters_recent_actions[i].setVisible(False)
        if nn==0:
            self.filters_recent_actions[0].setDisabled(True)
            self.filters_recent_actions[0].setText('Empty')
            self.filters_recent_actions[0].setVisible(True)
    
    def select_color_scheme(self):
        cmaps = [('Sequential',     ['binary', 'Blues', 'BuGn', 'BuPu', 'gist_yarg',
                             'GnBu', 'Greens', 'Greys', 'Oranges', 'OrRd',
                             'PuBu', 'PuBuGn', 'PuRd', 'Purples', 'RdPu',
                             'Reds', 'YlGn', 'YlGnBu', 'YlOrBr', 'YlOrRd']),
         ('Sequential (2)', ['afmhot', 'autumn', 'bone', 'cool', 'copper',
                             'gist_gray', 'gist_heat', 'gray', 'hot', 'pink',
                             'spring', 'summer', 'winter']),
         ('Diverging',      ['BrBG', 'bwr', 'coolwarm', 'PiYG', 'PRGn', 'PuOr',
                             'RdBu', 'RdGy', 'RdYlBu', 'RdYlGn', 'seismic']),
         ('Qualitative',    ['Accent', 'Dark2', 'hsv', 'Paired', 'Pastel1',
                             'Pastel2', 'Set1', 'Set2', 'Set3', 'spectral']),
         ('Miscellaneous',  ['gist_earth', 'gist_ncar', 'gist_rainbow',
                             'gist_stern', 'jet', 'brg', 'CMRmap', 'cubehelix',
                             'gnuplot', 'gnuplot2', 'ocean', 'rainbow',
                             'terrain', 'flag', 'prism'])]
        
        colors = cmaps[0][1] + cmaps[4][1] + cmaps[1][1] + cmaps[2][1] + cmaps[3][1]
        
        (color, ok) = QInputDialog.getItem(self, self.tr("Choose Coloring Scheme"),
                                     self.tr("Color Scheme for Lasagna Plot:"), colors)
        if color and ok:
            self.sysPreferences.setColorScheme(color)
            grouptab = self.get_mainWindow_tab('Group Plot')
            if grouptab:
                grouptab.plot()
    
    def find_duplicate_cases(self):        #filename = 'C:\\VAERS_Text_Mining\\EtherBO.csv'
        filename = '.\\ForFindingReportDuplication.txt'
        reports = [self.reports[i] for i in self.selectedReportIndices]
        util.ReportGenerator.save_report_id(reports, filename)
        duplication_finder = '.\\lib\\DuplicateSearch.jar'
        
        reportTypes = ['VAERS', 'FAERS']
        dlg = RadioDialog(reportTypes, 'Report Type: ', 'Find Duplication')
        dlg.exec_()
        choice = dlg.getChoice()
        if choice < 0:
            return
        
        QMessageBox.information(None, "ETHER",  'Duplication results are generated in "Duplicate Detection Output.csv".', \
                                              QMessageBox.Ok)
        
#         QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        rptType = reportTypes[choice]
        t = FindDuplication(filename, rptType)
        t.start()
        t.join()
#         QApplication.restoreOverrideCursor()    
                
    def open_help_documentation(self):
        subprocess.Popen("hh.exe .\\ETHER.chm")
        
    def open_help_about_dialog(self):
        QMessageBox.information(None, "About", """Event-based Text-mining of Health Electronic Records (ETHER)\n\nFood and Drug Administration\nCenter for Biologics Evaluation and Reserach\nOffice of Biostatistics and Epidemiology""", \
                                              QMessageBox.Ok)
        
    def remove_irrelavant_reports(self):
        choice = QMessageBox.question(None, "ETHER", "Remove irrelavant reports from DB. This cannot be undone! Continue?", \
                                              QMessageBox.Cancel, QMessageBox.Ok)
        if choice == QMessageBox.Cancel:
            return
    
        allReportIDs = self.vaersdb.retriveReportID()
        reportIDs = [self.reports[idx]['Report ID'] for idx in self.selectedReportIndices]
        reportsToDelete = [rptId[0] for rptId in allReportIDs if not rptId[0] in reportIDs]
        for rptID in reportsToDelete:
            self.vaersdb.deleteReport(rptID)

        self.vaersdb.conn.commit()
        QMessageBox.information(None, "ETHER", 'Irrelavant reports removed!')
        
    def load_local_database(self):
        dbfilename = QFileDialog.getOpenFileName(self, "Load local Database file", './etherlocal.db', "Database File (*.db)")[0]        
        if not dbfilename: return        
        
        self.vaersdb.close()
        self.vaersdb = dbstore(dbfilename, "", '')

        ids = self.vaersdb.retriveReportID()
        
        report_data = []
        for rid in ids:     
            report = {}
            report['Report ID'] = rid
            report_data.append(report)
        
        return report_data
    
    def load_etherlocal_db(self):
        ids = self.vaersdb.retriveReportID()
        
        report_data = []
        for rid in ids:     
            report = {}
            report['Report ID'] = rid
            report_data.append(report)
        
        return report_data
    
    def load_reports(self, loadDB=False):        
        if loadDB:        
            dlg = FilterLocalDBDialog()     
            dlg.exec_()
            (dbfilename, sqlStr) = dlg.getDBSQL()
            if not dbfilename:
                return
            try:
                vaersdb = dbstore(dbfilename, "", '')
            except sqlite3.OperationalError as strerror:
                QMessageBox.critical(QMessageBox(), "ETHER",  "Database error. " + str(strerror))
                return
         
            self.vaersdb.close()
            self.vaersdb = vaersdb
 
            ids = self.vaersdb.retriveReportID(sqlStr)
            report_form_data = []
            for row in ids:
                report = {}
                report['Report ID'] = row[0]
                report_form_data.append(report)
            reportsfilename = dbfilename
        
        else:
            reportsfilename = QFileDialog.getOpenFileName(self, "Load report file", './', "Report File (*.txt *.csv)")[0]        
            if not reportsfilename: return        
            self.file_load_reports.setDisabled(True)
            report_form_data = self.read_data_file_universal(reportsfilename)   
            
            loc = reportsfilename.rfind('/')
            if loc>=0:
                reportsfilename = reportsfilename[loc+1:]
        
        reports = self.read_reports_form_data(report_form_data)

        if not reports:
            QMessageBox.critical(None, "ETHER", "No reports found!")
            self.file_load_reports.setDisabled(False)
            return
        
        self.setWindowTitle(reportsfilename + " - ETHER: Event-based Text-mining of Health Electronic Records")
        
        self.reports = reports
        
        self.timer = time.time()
        self.reports.sort(key=lambda report: report['Report ID'])
        self.reports.sort(key=lambda report: len(report['Diagnosis']) > 0, reverse=True)
        self.selectedReportIndices = range(len(self.reports)) # this array will be updated in LimitedFeaturesTab
        
        self.current_tabindex = 0
        
        ids = range(self.centralWidget().count())
        ids.reverse()
        for i in ids:
            tab = self.centralWidget().widget(i)
            self.centralWidget().removeTab(i)
            tab.deleteLater()
            
        # Force garbage collection 
        gc.collect()
        
        #self.research_mode_action.setChecked(True)
        self.centralWidget().addTab(ReviewTab(self.reports, ReportLimitedFeatures(self.reports,self), self.centralWidget()), "Summarized Cases")
#         self.centralWidget().addTab(ReviewTab(self.reports, ReportText(self.reports, self), self.centralWidget()), "Text")
#         self.centralWidget().addTab(ReviewTab(self.reports, ReportFeatures(self.reports, self), self.centralWidget()), "Features")
        self.centralWidget().addTab(ReviewTab(self.reports, ReportTextAndFeatures(self.reports, self), self.centralWidget()), "Case Narrative && Features")
        self.centralWidget().addTab(ReviewTab(self.reports, ReportTemporal(self.reports, self), self.centralWidget()), "Case Features over Time")   
        self.centralWidget().addTab(ReviewTab(self.reports, AnnotationTab(self.reports, self), self.centralWidget()), "Annotation")   
        #self.centralWidget().addTab(ReviewTab(self.reports, ReportReview(self.reports, self), self.centralWidget()), "Review")   
        
        #self.centralWidget().setTabEnabled(3, False)
#         self.centralWidget().setTabEnabled(4, False)
        
        self.centralWidget().setTabsClosable(True)
        for i in range(self.centralWidget().count()):
            self.centralWidget().tabBar().tabButton(i, QTabBar.RightSide).resize(0, 0)

# #         self.research_mode_action.setChecked(False)
        self.research_toggle(False)
        self.current_report = 0
        self.current_report_global_index = 0
        self.set_current_report(0) 

        self.file_load_reports.setDisabled(False)
        
        # reset the current and recent menus
        for i in reversed(range(self.filters_maxcount)):
            self.filter_recent_menu.removeAction(self.filters_recent_actions[i])
        self.filters_current = []
        self.filters_recent = []
        self.filters_current_actions = []
        self.filters_recent_actions = []
        for i in range(self.filters_maxcount):
            self.filters_recent_actions.append(QAction(self))
            self.filters_recent_actions[i].setVisible(False)
            self.filters_recent_actions[i].triggered.connect(self.on_menu_recent_filters_clicked)
            self.filter_recent_menu.addAction(self.filters_recent_actions[i])

        self.filters_recent_actions[0].setDisabled(True)
        self.filters_recent_actions[0].setText('Empty')
        self.filters_recent_actions[0].setVisible(True)
#         
    def delete_tab(self,index):
        tab = self.centralWidget().widget(index)
        self.centralWidget().removeTab(index)
        tab.deleteLater()
            
    def get_mainWindow_tab(self, tab_title):
        for i in xrange(self.centralWidget().count()):
            if tab_title in self.centralWidget().tabText(i):
                return self.centralWidget().widget(i)
        return None
    
    def get_mainWindow_tab_index(self, tab_title):
        for i in xrange(self.centralWidget().count()):
            if tab_title in self.centralWidget().tabText(i):
                return i
        return None
    
    def update_selected_reports(self):
        self.centralWidget().widget(0).central.update_report_list() # "Limited Features" Tab
        #self.centralWidget().widget(4).central.temporalPlot.plot() # "Temporal" Tab
        tab_temporal = self.get_mainWindow_tab('Case Features over Time')
        if tab_temporal:
            tab_temporal.central.temporalPlot.plot() # "Temporal" Tab
            
        groupplot = self.get_mainWindow_tab('Group Plot')
        if groupplot:
            groupplot.plot()
        
        self.current_report = 0
        self.set_current_report(self.current_report)
        if len(self.selectedReportIndices)==len(self.reports):
            self.data_all_action.setChecked(True)
        else:
            self.data_all_action.setChecked(False)
                            
    def closeEvent(self, event):
        self.on_current_report_changed()
        
        tab_summary = self.get_mainWindow_tab("Summarized Cases").central
        if tab_summary:
            tab_summary.save_report_marks()
            for report in self.reports:
                self.vaersdb.updateReportMark(report['Report ID'], report['Mark'])
            self.vaersdb.conn.commit()

    def next_report(self):
        if self.current_report < 0 or self.current_report > (len(self.selectedReportIndices)-1):
            logging.warning('next_report: current report index outside of allowable range [0, numreports-1]')
            self.current_report = 0
        elif self.current_report == (len(self.selectedReportIndices) - 1):
            report_index = 0
        else:
            report_index = self.current_report + 1
        
        logging.debug('next button pushed, next report is {0}'.format(report_index))
        
        self.set_current_report(report_index)                    
        
    def previous_report(self):
        if self.current_report < 0 or self.current_report > (len(self.selectedReportIndices)-1):
            logging.warning('previous_report: current report index outside of allowable range [0, numreports-1]')
            self.current_report = 0
        elif self.current_report == 0:
            report_index = len(self.selectedReportIndices) - 1
        else:
            report_index = self.current_report - 1
            
        logging.debug('previous button pushed, previous report is {0}'.format(report_index))
 
        self.set_current_report(report_index)
 
    # Note the set_current_report() here use selected index, while globla index is used in set_current_report() for tabs. 
    def set_current_report(self, report_index):
        #switch to the new report
        pre_report = self.current_report
        self.current_report = report_index
        if report_index < len(self.selectedReportIndices):
            current_report_global_index = self.selectedReportIndices[report_index]
        else:
            current_report_global_index = -1
            
        if current_report_global_index != self.current_report_global_index:
            self.to_continue_change_current_report = True
            self.on_current_report_changed()
            if not self.to_continue_change_current_report:
                self.current_report = pre_report
                return
            
        for i in xrange(self.centralWidget().count()):
            self.centralWidget().widget(i).set_current_report(current_report_global_index, i)
            
        self.current_report_global_index = current_report_global_index
        
    def on_current_report_changed(self):
        tab_feature = self.get_mainWindow_tab("Case Narrative && Features")
        if tab_feature:
            tab_feature.central.current_report_changed()
            
        tab_annotation = self.get_mainWindow_tab("Annotation")
        if tab_annotation:
            tab_annotation.central.current_report_changed()

class FindDuplication(Thread):
    def __init__(self, inputFileName, reportType):        
        Thread.__init__(self)
        self.inputFileName = inputFileName
        self.reportType = reportType
        
    def run(self):
        duplication_finder = '.\\lib\\DuplicateSearch.jar'
        
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        subprocess.Popen(["java", '-jar', '-Xmx1024m', '-Dsun.java2d.noddraw=true', duplication_finder, 
                          self.reportType, self.inputFileName, './etherlocal.db'])
        
        outfile = "./Duplicate Detection Output.csv"        
        tInput = os.path.getmtime(self.inputFileName)
        max_wait_sec = 300
        waited = 0
        while waited < max_wait_sec:
            if os.path.exists(outfile):
                tOutput = os.path.getmtime(outfile)
                if tOutput >= tInput:
                    os.startfile(os.path.abspath(outfile))
                    break
            time.sleep(1)
            waited += 1
            
        QApplication.restoreOverrideCursor()    

#         progress = QProgressDialog("Searching for duplications...", "Cancel", 0, max_wait_sec)
#         progress.setWindowTitle("ETHER")
#         progressbar = QProgressBar(progress)
#         progressbar.setVisible(1)
#         progress.setBar(progressbar)
#         progress.setWindowModality(Qt.WindowModal)
#         progress.setRange(0, max_wait_sec)
#         progress.setValue(0)
#             
#         waited = 0
#         while waited < max_wait_sec:
#             if os.path.exists(outfile):
#                 tOutput = os.path.getmtime(outfile)
#                 if tOutput >= tInput:
#                     os.startfile(os.path.abspath(outfile))
#                     progress.setValue(max_wait_sec)
#                     break
#             time.sleep(1)
#             waited += 1
#             progress.setValue(waited)
#             if progress.wasCanceled():
#                 return None     
                 
if __name__ == "__main__":
    logging.basicConfig(level=logging.WARN)
    
    # start gui
    app = QApplication(sys.argv)
#     
#     splash_pix = QPixmap('splash.jpg')
#     splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
#     splash.setMask(splash_pix.mask())
#     splash.show()
#     app.processEvents()

    # Simulate something that takes time
#     time.sleep(1)
   
    main_window = MainWindow()
    
    #cProfile.run('MainWindow()')
    main_window.show()
       
#     splash.finish(main_window)
    sys.exit(app.exec_())
    

