#!/usr/bin python
# -*- coding: utf-8 -*-

import sqlite3, os, sys, pyodbc, string
from PySide.QtCore import *
from PySide.QtGui import *

import json
    
class dbstore:

    def __init__(self, dbname, database, localpath):
        self.schema = ""
        
        if dbname == "oracle":
            try:                
                # pyodbc connection
                driver = "DRIVER={Microsoft ODBC for Oracle};"
                #driver = "DRIVER={Oracle in Ora10g};" #Oracle driver, doesn't work
                cred = "UID=VAERS_TM;PWD=May08_2012;" # credentials for test, preprod, and prod
                #cred = "UID=Var2$admin;PWD=vaers_var2;" # credentials for dev
                self.conn = pyodbc.connect(driver + database + cred)
                self.schema = "VAR2$ADMIN."
                self.c = self.conn.cursor()
            except:
                # cannot connect
                msgBox = QMessageBox(QMessageBox.Critical, "VaeTM", "Cannot connect to the remote database.")
                msgBox.setInformativeText("Do you want to store the extracted features in a local database?")
                msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
                msgBox.setDefaultButton(QMessageBox.Ok)
                ret = msgBox.exec_()
                if ret == QMessageBox.Cancel:
                    sys.exit()
                else:
                    dbname = localpath + 'vaersfeatures.db'
        
        if dbname != "oracle":
            # sqlite connection            
            if os.path.isfile(dbname):                
                self.conn = sqlite3.connect(dbname)
                self.conn.text_factory = str
                self.c = self.conn.cursor()
                self.db_version_validation()
            else:
                self.conn = sqlite3.connect(dbname)
                self.conn.text_factory = str
                self.c = self.conn.cursor()
                self.create_tables()
    
    def close(self):
        self.conn.close()
        
    def db_version_validation(self):
        self.c.execute("PRAGMA table_info(ETHER_REPORT_FORM);")
        tbinfo = self.c.fetchall()
        cols = [c[1] for c in tbinfo]
        if not 'INDICATION' in cols:
            self.c.execute("alter table ETHER_REPORT_FORM add column INDICATION text")
        if not 'PRIMARY_SUSPECT' in cols:
            self.c.execute("alter table ETHER_REPORT_FORM add column PRIMARY_SUSPECT text")                        
        
        self.c.execute("PRAGMA table_info(ETHER_REPORT_EXTRACTED);")
        tbinfo = self.c.fetchall()
        cols = [c[1] for c in tbinfo]
        if not 'MARK' in cols:
            self.c.execute("alter table ETHER_REPORT_EXTRACTED add column MARK boolean")
            
        self.c.execute("PRAGMA table_info(ETHER_ANNOTATIONS);")
        tbinfo = self.c.fetchall()
        cols = [c[1] for c in tbinfo]
        if not 'START_POS' in cols:
            self.c.execute("alter table ETHER_ANNOTATIONS add column START_POS integer")
            self.c.execute("alter table ETHER_ANNOTATIONS add column END_POS integer")
            
        if not 'FEATURE_ID' in cols:
            self.c.execute("alter table ETHER_ANNOTATIONS add column PREFER_TERM text")      
            self.c.execute("alter table ETHER_ANNOTATIONS add column FEATURE_ID integer")
            self.c.execute("alter table ETHER_ANNOTATIONS add column TIME_ID integer")
            self.c.execute("alter table ETHER_ANNOTATIONS add column TIME_REL text")           
        
        self.c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ETHER_ANNOTATIONS'")
        if not self.c.fetchall():
            self.c.execute("create table ETHER_ANNOTATIONS(VAERS_ID text, ANNOTATION_ID integer, FEATURE_TEXT text, FEATURE_TYPE integer, ERROR_TYPE integer, COMMENT text)")
        
        typeIdx = cols.index('FEATURE_TYPE')
        if tbinfo[typeIdx][2]=='integer':
            self.modify_feature_annnotation_column_type()
            
        self.c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ETHER_TIME_ANNOTATIONS'")
        if not self.c.fetchall():
            self.c.execute("create table ETHER_TIME_ANNOTATIONS(VAERS_ID text, ANNOTATION_ID integer, STRING text, DATETIME text, TIME_TYPE integer, START_POS integer, CONFIDENCE_LEVEL integer, COMMENT text)")

        self.c.execute("PRAGMA table_info(ETHER_TIME_ANNOTATIONS);")
        tbinfo = self.c.fetchall()
        cols = [c[1] for c in tbinfo]
        if not 'TIME_ID' in cols:
            self.c.execute("alter table ETHER_TIME_ANNOTATIONS add column TIME_ID integer default '' ")
            self.c.execute("alter table ETHER_TIME_ANNOTATIONS add column TIME_REL text default '' ")
            
        typeIdx = cols.index('TIME_TYPE')
        if tbinfo[typeIdx][2]=='integer':
            self.modify_time_annnotation_column_type()
        
        self.c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ETHER_SUMMARIZATIONS'")
        if not self.c.fetchall():
            self.c.execute("create table ETHER_SUMMARIZATIONS (VAERS_ID text, ELEMENT_ID integer, ELEMENT_TEXT text, ELEMENT_TYPE integer, ERROR_TYPE integer, COMMENT text, START_POS integer, END_POS integer, PREFER_TERM text, FEATURE_ID integer, START_DATE text, END_DATE text)")

        self.c.execute("PRAGMA table_info(ETHER_SUMMARIZATIONS);")
        tbinfo = self.c.fetchall()
        cols = [c[1] for c in tbinfo]
        if not 'START_DATE' in cols:
            self.c.execute("alter table ETHER_SUMMARIZATIONS add column START_DATE text")
            self.c.execute("alter table ETHER_SUMMARIZATIONS add column END_DATE text")
    
    def modify_time_annnotation_column_type(self):
        
        filename = 'preferences.json'
        try:
            with open(filename, 'r') as json_data:
                config = json.load(json_data)
        except Exception as e:
            QMessageBox.critical(None, "ETHER", str(e)+"\nCoundn't find preferences.json! Default parameters will be used.")
            return
        
        self.annotationSettings = config['annotations']
        self.annotationClass = [''] + self.annotationSettings['Time']
        
        self.c.execute("create table IF NOT EXISTS ETHER_TIME_ANNOTATIONS_temp (VAERS_ID text, ANNOTATION_ID integer, STRING text, DATETIME text, TIME_TYPE text, START_POS integer, END_POS integer, CONFIDENCE_LEVEL integer, COMMENT text, TIME_ID integer, TIME_REL text)")
        self.c.execute("select * from ETHER_TIME_ANNOTATIONS")       
        tpyeIdx = 4
        data = self.c.fetchall()
        for row in data:
            record = [c for c in row]
            if record[tpyeIdx] >= len(self.annotationClass):
                record[tpyeIdx] = 0
            record[tpyeIdx] = self.annotationClass[record[tpyeIdx]]
            self.c.execute("insert into {}ETHER_TIME_ANNOTATIONS_temp values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)".format(self.schema), record)

        self.c.execute("DROP TABLE IF EXISTS ETHER_TIME_ANNOTATIONS")
        self.c.execute("ALTER TABLE ETHER_TIME_ANNOTATIONS_temp RENAME TO ETHER_TIME_ANNOTATIONS")
        self.conn.commit()   
    
    def modify_feature_annnotation_column_type(self):
        
        filename = 'preferences.json'
        try:
            with open(filename, 'r') as json_data:
                config = json.load(json_data)
        except Exception as e:
            QMessageBox.critical(None, "ETHER", str(e)+"\nCoundn't find preferences.json! Default parameters will be used.")
            return
        
        self.annotationSettings = config['annotations']
        self.annotationClass = [''] + self.annotationSettings['Feature']
        
        self.c.execute("create table IF NOT EXISTS ETHER_ANNOTATIONS_temp (VAERS_ID text, ANNOTATION_ID integer, FEATURE_TEXT text, FEATURE_TYPE text, ERROR_TYPE integer, COMMENT text, START_POS integer, END_POS integer, PREFER_TERM text,  FEATURE_ID integer, TIME_ID integer, TIME_REL text)")
        self.c.execute("select * from ETHER_ANNOTATIONS")       
        tpyeIdx = 3
        data = self.c.fetchall()
        for row in data:
#             record = [c for c in row]
#             record[tpyeIdx] = self.annotationClass[record[tpyeIdx]]
            self.c.execute("insert into {}ETHER_ANNOTATIONS_temp values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)".format(self.schema), row)

        self.c.execute("DROP TABLE IF EXISTS ETHER_ANNOTATIONS")
        self.c.execute("ALTER TABLE ETHER_ANNOTATIONS_temp RENAME TO ETHER_ANNOTATIONS")
        self.conn.commit()   
        
    def create_tables(self):
#         self.c.execute("create table ETHER_REPORT_FORM (VAERS_ID text, AGE text, DATE_EXPOSURE text, DATE_ONSET text, VACCINES text, VACCINE_NAMES text, \
#                 MEDDRA text, GENDER text, FREE_TEXT text, LAB_TEXT text, SERIOUS boolean, DIED boolean, LOCATION text, HISTORY text, DATE_RECEIVED text, \
#                 LOT_NUMBER text, INDICATION text, PRIMARY_SUSPECT text)")
        self.c.execute("create table ETHER_REPORT_FORM (VAERS_ID text, AGE text, DATE_EXPOSURE text, DATE_ONSET text, VACCINES text, VACCINE_NAMES text, \
                MEDDRA text, GENDER text, FREE_TEXT text, LAB_TEXT text, SERIOUS boolean, DIED boolean, LOCATION text, HISTORY text, DATE_RECEIVED text, \
                LOT_NUMBER text, INDICATION text, PRIMARY_SUSPECT text, \
                BIRTH_DATE text, FIRST_NAME text, MIDDLE_INITIAL text, LAST_NAME text, PATIENT_ID text, MFR_CONTROL_NUMBER text)")
        self.c.execute("create table ETHER_REPORT_EXTRACTED (VAERS_ID text, TIME_EXPOSURE text, TIME_ONSET text, ONSET_HOURS integer, CONFIDENCE_LEVEL integer, \
                PREFER_TERM text, SUMMARY text, REVIEW text, ACTION integer, CLASS boolean, DXLEVEL integer, MARK boolean)")
        #self.c.execute("create table ETHER_REPORT_EXTRACTED (VAERS_ID text, TIME_EXPOSURE text, TIME_ONSET text, ONSET_HOURS integer, CONFIDENCE_LEVEL integer, PREFER_TERM text, SUMMARY text, CLASS text)")
        #self.c.execute("create table ETHER_FEATURES (VAERS_ID text, FEATURE_ID integer, FEATURE_TYPE text, FEATURE_TEXT text, SENTENCE_NUMBER integer, FEATURE_TEMP_START text, FEATURE_TEMP_END text, PREFER_TERM text)")
        self.c.execute("create table ETHER_FEATURES (VAERS_ID text, FEATURE_ID integer, FEATURE_TYPE text, FEATURE_TEXT text, SENTENCE_NUMBER integer, START_POS integer, END_POS integer, FEATURE_TEMP_START text, FEATURE_TEMP_END text, PREFER_TERM text, CLEAN_TEXT text)")
        self.c.execute("create table ETHER_FEATURES_RESEARCH (VAERS_ID text, FEATURE_ID integer, COMMENT text, MATCH integer)")
        self.c.execute("create table ETHER_TIMEXES (VAERS_ID text, STRING text, DATETIME text, START_POS integer, CONFIDENCE_LEVEL integer)")
        self.c.execute("create table ETHER_RESEARCH (VAERS_ID text, USER_ID text, TIMER1 integer, TIMER2 integer, TIMER3 integer, TIMER4 integer, TIMER5 integer, COMMENT1 text, COMMENT2 text, COMMENT3 text, COMMENT4 text, COMMENT5 text)")
        self.c.execute("create table ETHER_LABTESTS (VAERS_ID text, NAME text, VALUE text, UNIT text, SAMPLE text, EVALUATION text, TESTSTRING text, COMMENT text)")
        self.c.execute("create table ETHER_ANNOTATIONS (VAERS_ID text, ANNOTATION_ID integer, FEATURE_TEXT text, FEATURE_TYPE text, ERROR_TYPE integer, COMMENT text, START_POS integer, END_POS integer, PREFER_TERM text,  FEATURE_ID integer, TIME_ID integer, TIME_REL text)")
        self.c.execute("create table ETHER_TIME_ANNOTATIONS (VAERS_ID text, ANNOTATION_ID integer, STRING text, DATETIME text, TIME_TYPE text, START_POS integer, END_POS integer, CONFIDENCE_LEVEL integer, COMMENT text, TIME_ID integer, TIME_REL text)")
        self.c.execute("create table ETHER_SUMMARIZATIONS (VAERS_ID text, ELEMENT_ID integer, ELEMENT_TEXT text, ELEMENT_TYPE integer, ERROR_TYPE integer, COMMENT text, START_POS integer, END_POS integer, PREFER_TERM text, FEATURE_ID integer, START_DATE text, END_DATE text)")
#         self.c.execute("create table ETHER_ANNOTATIONS (VAERS_ID text, ANNOTATION_ID integer, FEATURE_TEXT text, FEATURE_TYPE integer, ERROR_TYPE integer, COMMENT text, START_POS integer, END_POS integer, PREFER_TERM text,  FEATURE_ID integer, TIME_ID integer, TIME_REL text)")
#         self.c.execute("create table ETHER_TIME_ANNOTATIONS (VAERS_ID text, ANNOTATION_ID integer, STRING text, DATETIME text, TIME_TYPE integer, START_POS integer, END_POS integer, CONFIDENCE_LEVEL integer, COMMENT text, TIME_ID integer, TIME_REL text)")
#         self.c.execute("create table ETHER_SUMMARIZATIONS (VAERS_ID text, ELEMENT_ID integer, ELEMENT_TEXT text, ELEMENT_TYPE integer, ERROR_TYPE integer, COMMENT text, START_POS integer, END_POS integer, PREFER_TERM text, FEATURE_ID integer, START_DATE text, END_DATE text)")

    def create_index(self):
        self.c.execute("CREATE INDEX IF NOT EXISTS index_reportid_form ON ETHER_REPORT_FORM (VAERS_ID)")
        self.c.execute("CREATE INDEX IF NOT EXISTS index_reportid_reprot ON ETHER_REPORT_EXTRACTED (VAERS_ID)")
        self.c.execute("CREATE INDEX IF NOT EXISTS index_reportid_feature ON ETHER_FEATURES (VAERS_ID)")
        self.c.execute("CREATE INDEX IF NOT EXISTS index_reportid_feature_research ON ETHER_FEATURES_RESEARCH (VAERS_ID)")
        self.c.execute("CREATE INDEX IF NOT EXISTS index_reportid_timex ON ETHER_TIMEXES (VAERS_ID)")
        self.c.execute("CREATE INDEX IF NOT EXISTS index_reportid_labtest ON ETHER_LABTESTS (VAERS_ID)")
        self.c.execute("CREATE INDEX IF NOT EXISTS index_reportid_report_extracted ON ETHER_REPORT_EXTRACTED (VAERS_ID)")
        self.c.execute("CREATE INDEX IF NOT EXISTS index_reportid_annotation ON ETHER_ANNOTATIONS (VAERS_ID)")
        self.c.execute("CREATE INDEX IF NOT EXISTS index_reportid_time_annotation ON ETHER_TIME_ANNOTATIONS (VAERS_ID)")
        self.c.execute("CREATE INDEX IF NOT EXISTS index_reportid_summarization ON ETHER_SUMMARIZATIONS (VAERS_ID)")

#     def retrieveDates(self, reportid):  "    
#         self.c.execute("select TIME_EXPOSURE, TIME_ONSET from {}VAERS_TM_REPORT_INFO where VAERS_ID = ?".format(self.schema), [reportid])
#         return self.c.fetchall()
        
#     def saveEstimatedDates(self, reportid, expDate, onsetDate):
#         self.c.execute(("insert into {}VAERS_TM_REPORT_INFO values (?, ?, ?)").format(self.schema), (reportid, expDate, onsetDate))
#         
#     def insert(self, reportid, featurelist):
#         for ftype, feature, sentnumber, tempmodifier in featurelist:
#             self.c.execute("insert into {}VAERS_TM_EXTRACTED values (?, ?, ?, ?, ?)".format(self.schema), (reportid, ftype, feature, sentnumber, tempmodifier))
    def insertReportFeature(self, report_feature):        
        self.c.execute("insert into {}ETHER_REPORT_EXTRACTED values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)".format(self.schema), report_feature)
        #self.c.execute("insert into {}ETHER_REPORT_EXTRACTED values (?, ?, ?, ?, ?, ?)".format(self.schema), report_feature)

    def insertReportForm(self, report_form):        
        self.c.execute("insert into {}ETHER_REPORT_FORM values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)".format(self.schema), report_form)
#         self.c.execute("insert into ETHER_REPORT_FORM (VAERS_ID, AGE, DATE_EXPOSURE, DATE_ONSET, VACCINES, VACCINE_NAMES, \
#                 MEDDRA, GENDER, FREE_TEXT, LAB_TEXT,  DATE_RECEIVED, LOT_NUMBER, INDICATION, PRIMARY_SUSPECT, 
#        BIRTH_DATE, FIRST_NAME, MIDDLE_INITIAL, LAST_NAME, PATIENT_ID, MFR_CONTROL_NUMBER) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)".format(self.schema), report_form)
                
    def insertFeatures(self, reportid, featurelist):
        for ftype, feature, sentnumber, tempstart, tempend, startPos, endPos, pt, fid, cleanString in featurelist:
            self.c.execute("insert into {}ETHER_FEATURES values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)".format(self.schema), 
                           (reportid, fid, ftype, feature, sentnumber, startPos, endPos, tempstart, tempend, pt, cleanString))

    def insertLabTests(self, reportid, tests):        
        for name, value, unit, sample, evaluation, testString, comment in tests:
            self.c.execute("insert into {}ETHER_LABTESTS values (?, ?, ?, ?, ?, ?, ?, ?)".format(self.schema), (reportid, name, value, unit, sample, evaluation, testString, comment))
    
    def updateReportMark(self, reportid, mark):            
        self.c.execute("update ETHER_REPORT_EXTRACTED SET MARK = ? where VAERS_ID = ?".format(self.schema), (mark, reportid))
     
    def updateReportReview(self, reportid, review, action, comment):
        if self.hasTextMined(reportid):
            self.c.execute("update ETHER_REPORT_EXTRACTED SET REVIEW = ?, ACTION = ?, SUMMARY = ? where VAERS_ID = ?".format(self.schema), (review, action, comment, reportid))
        else:            
            self.c.execute("insert into ETHER_REPORT_EXTRACTED (VAERS_ID, REVIEW, ACTION, SUMMARY) values (?, ?, ?, ?)".format(self.schema), (reportid, review, action, comment))
        
    def updateFeatureComment(self, reportid, featureid, comment, match):
        #self.c.execute("select distinct VAERS_ID from {}ETHER_FEATURES_RESEARCH where VAERS_ID = ? and FEATURE_ID = ? and MATCH = ?".format(self.schema), [reportid, featureid, match])
        self.c.execute("select distinct VAERS_ID from {}ETHER_FEATURES_RESEARCH where VAERS_ID = ? and FEATURE_ID = ?".format(self.schema), [reportid, featureid])
        if self.c.fetchone():
            if comment=='' and match==0:
                self.c.execute("delete from {}ETHER_FEATURES_RESEARCH where VAERS_ID = ? and FEATURE_ID = ?".format(self.schema), (reportid, featureid))
            else:
                self.c.execute("update ETHER_FEATURES_RESEARCH SET COMMENT = ?, MATCH = ? where VAERS_ID = ? and FEATURE_ID = ?".format(self.schema), (comment, match, reportid, featureid))
        else:            
            self.c.execute("insert into {}ETHER_FEATURES_RESEARCH values (?, ?, ?, ?)".format(self.schema), (reportid, featureid, comment, match))
    
    def updateAnnotation(self, record):
        """record = (reportid, annoteId, featText, featType, errorType, comment, startPos, endPos, pt, featID, timeID, timeRel)"""
        cond = (record[0], record[1], record[10])
        self.c.execute("select distinct VAERS_ID from {}ETHER_ANNOTATIONS where VAERS_ID = ? and ANNOTATION_ID = ? and TIME_ID = ?".format(self.schema), cond)
        if self.c.fetchone():            
            self.c.execute("update ETHER_ANNOTATIONS SET FEATURE_TEXT = ?, FEATURE_TYPE = ?, ERROR_TYPE = ?, COMMENT = ?, START_POS = ?, END_POS = ?, \
                             PREFER_TERM=?, FEATURE_ID=?, TIME_ID=?, TIME_REL=? where VAERS_ID = ? and ANNOTATION_ID = ?".format(self.schema), record[2:]+record[:2])
        else:            
            self.c.execute("insert into {}ETHER_ANNOTATIONS values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)".format(self.schema), record)
            
    def updateTimeAnnotation(self, reportid, annoteId, timeString, timeType, timeDate, startPos, endPos, confidence, comment, timeRefID, timeRel):
        self.c.execute("select distinct VAERS_ID from {}ETHER_TIME_ANNOTATIONS where VAERS_ID = ? and ANNOTATION_ID = ?".format(self.schema), [reportid, annoteId])
        if self.c.fetchone():            
            self.c.execute("update ETHER_TIME_ANNOTATIONS SET STRING = ?, DATETIME = ?, TIME_TYPE = ?, START_POS = ?, END_POS = ?, CONFIDENCE_LEVEL = ?, COMMENT = ?, TIME_ID = ?, TIME_REL = ? where VAERS_ID = ? and ANNOTATION_ID = ?".format(self.schema), 
                           (timeString, timeDate, timeType, startPos, endPos, confidence, comment, timeRefID, timeRel, reportid, annoteId))
        else:            
            self.c.execute("insert into {}ETHER_TIME_ANNOTATIONS values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)".format(self.schema), (reportid, annoteId, timeString, timeDate, timeType, startPos, endPos, confidence, comment, timeRefID, timeRel))
    
    def updateSummarization(self, record):
        """record = (reportid, elemId, elemText, elemType, errorType, comment, startPos, endPos, pt, featID, timeStart, timeEnd)"""
        self.c.execute("select distinct VAERS_ID from {}ETHER_SUMMARIZATIONS where VAERS_ID = ? and ELEMENT_ID = ?".format(self.schema), record[:2])
        if self.c.fetchone():            
            self.c.execute("update ETHER_SUMMARIZATIONS SET ELEMENT_TEXT = ?, ELEMENT_TYPE = ?, ERROR_TYPE = ?, COMMENT = ?, START_POS = ?, END_POS = ?, \
                             PREFER_TERM=?, FEATURE_ID=?, START_DATE=?, END_DATE=? where VAERS_ID = ? and ELEMENT_ID = ?".format(self.schema), 
                           record[2:]+record[:2])
        else:            
            self.c.execute("insert into {}ETHER_SUMMARIZATIONS values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)".format(self.schema), record)
            
    def insertTimexes(self, reportid, timexlist):        
        for string, sdate, istart, confid in timexlist:
            self.c.execute("insert into {}ETHER_TIMEXES values (?, ?, ?, ?, ?)".format(self.schema), (reportid, string, sdate, istart, confid))    
        
#     def retrieveid(self, reportid):
#         self.c.execute("select FEATURE_TYPE, FEATURE_TEXT, SENTENCE_NUMBER, FEATURE_TEMP_START, FEATURE_TEMP_END from {}VAERS_TM_EXTRACTED where VAERS_ID = ?".format(self.schema), [reportid])
#         return self.c.fetchall()
        
    def checkid(self, reportid):
        #self.c.execute("select distinct VAERS_ID from {}ETHER_REPORT_EXTRACTED where VAERS_ID = ?".format(self.schema), [reportid])
        self.c.execute("select distinct VAERS_ID from {}ETHER_REPORT_FORM where VAERS_ID = ?".format(self.schema), [reportid])
        return self.c.fetchone()
        
    def hasTextMined(self, reportid):
        #self.c.execute("select distinct VAERS_ID from {}ETHER_REPORT_EXTRACTED where VAERS_ID = ?".format(self.schema), [reportid])
        self.c.execute("select distinct VAERS_ID from {}ETHER_REPORT_EXTRACTED where VAERS_ID = ?".format(self.schema), [reportid])
        return self.c.fetchone()
    
    def retriveReportID(self, sql = None):
        strcmd = "select VAERS_ID from ETHER_REPORT_EXTRACTED"
        if sql:
            strcmd += ' where ' + sql
        self.c.execute(strcmd)
#         self.c.execute("select VAERS_ID from ETHER_REPORT_FORM")
        return self.c.fetchall()
        
    def retrieveReportForm(self, reportid):
        #self.c.execute("select AGE, DATE_EXPOSURE, DATE_ONSET, VACCINES, VACCINE_NAMES, MEDDRA, GENDER, FREE_TEXT, LAB_TEXT,  DATE_RECEIVED, LOT_NUMBER, INDICATION from {}ETHER_REPORT_FORM where VAERS_ID = ?".format(self.schema), [reportid])
        self.c.execute("select AGE, DATE_EXPOSURE, DATE_ONSET, VACCINES, VACCINE_NAMES, MEDDRA, GENDER, FREE_TEXT, LAB_TEXT, SERIOUS, DIED, LOCATION, HISTORY, DATE_RECEIVED, \
                            LOT_NUMBER, INDICATION, PRIMARY_SUSPECT, BIRTH_DATE, FIRST_NAME, MIDDLE_INITIAL, LAST_NAME, PATIENT_ID, MFR_CONTROL_NUMBER from {}ETHER_REPORT_FORM where VAERS_ID = ?".format(self.schema), [reportid])
        recordlist = self.c.fetchall()
        return recordlist[0]
     
    def retrieveReportFeature(self, reportid):
        self.c.execute("select TIME_EXPOSURE, TIME_ONSET, ONSET_HOURS, CONFIDENCE_LEVEL, PREFER_TERM, SUMMARY, REVIEW, ACTION, CLASS, DXLEVEL, MARK from {}ETHER_REPORT_EXTRACTED where VAERS_ID = ?".format(self.schema), [reportid])
        #return self.c.fetchall()        
        recordlist = self.c.fetchall()
        return recordlist[0]

    def retrieveLabTests(self, reportid):
        self.c.execute("select NAME, VALUE, UNIT, SAMPLE, EVALUATION, TESTSTRING, COMMENT from {}ETHER_LABTESTS where VAERS_ID = ?".format(self.schema), [reportid])
        return self.c.fetchall()
            
    def retrieveTimexes(self, reportid):
        #self.c.execute("select STRING, DATETIME, START_POS, CONFIDENCE_LEVEL from {}ETHER_TIMEXES where VAERS_ID = ?".format(self.schema), [reportid])
        self.c.execute("select STRING, START_POS, DATETIME from {}ETHER_TIMEXES where VAERS_ID = ?".format(self.schema), [reportid])
        return self.c.fetchall()
    
    def retrieveFeatures(self, reportid):
        self.c.execute("select FEATURE_TYPE, FEATURE_TEXT, SENTENCE_NUMBER, START_POS, END_POS, FEATURE_TEMP_START, FEATURE_TEMP_END, PREFER_TERM, FEATURE_ID, CLEAN_TEXT from {}ETHER_FEATURES where VAERS_ID = ?".format(self.schema), [reportid])
        return self.c.fetchall()
    
    def retrieveFeatureComments(self, reportid):
        self.c.execute("select FEATURE_ID, COMMENT, MATCH from {}ETHER_FEATURES_RESEARCH where VAERS_ID = ?".format(self.schema), [reportid])
        return self.c.fetchall()
    
    def retrieveAnnotations(self, reportid):
        self.c.execute("select ANNOTATION_ID, FEATURE_TEXT, FEATURE_TYPE, ERROR_TYPE, COMMENT, START_POS, END_POS, FEATURE_ID, TIME_ID, TIME_REL from {}ETHER_ANNOTATIONS where VAERS_ID = ?".format(self.schema), [reportid])       
        return self.c.fetchall()
    
    def retrieveSummarizations(self, reportid):
        self.c.execute("select ELEMENT_ID, ELEMENT_TEXT, ELEMENT_TYPE, ERROR_TYPE, COMMENT, START_POS, END_POS, PREFER_TERM, FEATURE_ID, START_DATE, END_DATE from {}ETHER_SUMMARIZATIONS where VAERS_ID = ?".format(self.schema), [reportid])       
        return self.c.fetchall()
    
    def retrieveTimeAnnotations(self, reportid):
        self.c.execute("select ANNOTATION_ID, STRING, TIME_TYPE, DATETIME, START_POS, END_POS, CONFIDENCE_LEVEL, COMMENT, TIME_ID, TIME_REL from {}ETHER_TIME_ANNOTATIONS where VAERS_ID = ?".format(self.schema), [reportid])       
        return self.c.fetchall()

    def retrievetimers(self, reportid, userid):
        self.c.execute("select * from {}ETHER_RESEARCH where VAERS_ID = ? AND USER_ID = ?".format(self.schema), [reportid, userid])
        return self.c.fetchall()
        
    def checktimers(self, reportid, userid):
        self.c.execute("select distinct VAERS_ID from {}ETHER_RESEARCH where VAERS_ID = ? AND USER_ID = ?".format(self.schema), [reportid, userid])
        return self.c.fetchone()

    def deleteReport(self, reportid):
        self.c.execute("delete from {}ETHER_REPORT_FORM where VAERS_ID = ?".format(self.schema), [reportid])
        self.c.execute("delete from {}ETHER_REPORT_EXTRACTED where VAERS_ID = ?".format(self.schema), [reportid])
        self.c.execute("delete from {}ETHER_FEATURES where VAERS_ID = ?".format(self.schema), [reportid])
        self.c.execute("delete from {}ETHER_FEATURES_RESEARCH where VAERS_ID = ?".format(self.schema), [reportid])
        self.c.execute("delete from {}ETHER_TIMEXES where VAERS_ID = ?".format(self.schema), [reportid])
        self.c.execute("delete from {}ETHER_LABTESTS where VAERS_ID = ?".format(self.schema), [reportid])
        self.c.execute("delete from {}ETHER_RESEARCH where VAERS_ID = ?".format(self.schema), [reportid])
        self.c.execute("delete from {}ETHER_ANNOTATIONS where VAERS_ID = ?".format(self.schema), [reportid])
        self.c.execute("delete from {}ETHER_TIME_ANNOTATIONS where VAERS_ID = ?".format(self.schema), [reportid])
        self.c.execute("delete from {}ETHER_SUMMARIZATIONS where VAERS_ID = ?".format(self.schema), [reportid])
        
    def deleteReportAnnotations(self, reportid):
        self.c.execute("delete from {}ETHER_ANNOTATIONS where VAERS_ID = ?".format(self.schema), [reportid])
        
    def deleteReportTimeAnnotations(self, reportid):
        self.c.execute("delete from {}ETHER_TIME_ANNOTATIONS where VAERS_ID = ?".format(self.schema), [reportid])
        
    def deleteReportSummarizations(self, reportid):
        self.c.execute("delete from {}ETHER_SUMMARIZATIONS where VAERS_ID = ?".format(self.schema), [reportid])
        
    def savetimers(self, reportid, userid, timers, comments):
        #remove previous timers and comments for this reportid/userid combinations
        self.c.execute("delete from {}ETHER_RESEARCH where VAERS_ID=? AND USER_ID=?".format(self.schema), (reportid, userid))

        #insert the new timers and comments
        for (i, c) in enumerate(comments):
            if isinstance(c, unicode):
                comments[i] = c.encode('ascii', 'ignore')
        self.c.execute(("insert into {}ETHER_RESEARCH values (" + "?, " * 11 + "?)").format(self.schema), [reportid, userid] + timers + comments)

        #commit transaction
        self.conn.commit()   
        
#     def remove_reports_from_db(self, reportsToDelete):
#         for rptId in reportsToDelete:
#             self.deleteReport(rptId)
#         self.conn.commit()   

            
if __name__ == "__main__":
    # connect to the database and create tables if necessary
    #vaersdb = dbstore(r".\vaersfeatures.db")
    #oracledb = dbstore("oracle")
    
#     vaersdb = dbstore(self.config['localpath'] + 'etherlocal.db', "", self.config['localpath'])
    
    vaersdb = dbstore('etherlocal.db', "", '.')
    #vaersdb = dbstore('c:\\vaers_text_mining\\etherlocal.db', "", 'c:\\vaers_text_mining\\')
    vaersdb.c.execute("PRAGMA table_info(ETHER_REPORT_FORM);")
    tbinfo = vaersdb.c.fetchall()
    print tbinfo
#     if tbinfo[-1][1]!='PRIMARY_SUSPECT':
#         vaersdb.convert_db()
#     else:
#         print 'DB is up to date!'
        
    print 'Program ended!'
    