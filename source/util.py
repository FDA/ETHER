#!/usr/bin python
# -*- coding: utf-8 -*-

"""This module provides a number of utility functions and classes:

    class ReportUtil – report related functions provide capabilities such as creating report summary, calculate onset time
    
    class ReportClassifier – perform report classification
    
    class ReportGenerator – provides functions to export ETHER results into a series of format
    
    class XMLUtil – class provides capability to handle XML files

"""
#
# Wei Wang, Engility, wei.wang@engility.com
#

'''
Created on Oct 28, 2014

@author: WEI.WANG1
'''
import re, nltk, csv
import xml.etree.cElementTree as ETree
import timexan, textan
from lxml import etree as ET
from lxml.etree import CDATA

dictFeatureNamesInv = {"SYMPTOM":"Symptom", "VACCINE":"Vaccine", "DIAGNOSIS": "Primary Diagnosis", 
                "SECOND_LEVEL_DIAGNOSIS":"Second Level Diagnosis", "CAUSE_OF_DEATH":"Cause of Death", 
                "DRUG":"Drug", "FAMILY_HISTORY":"Family History", 'TIME_TO_ONSET':'Time to Onset',
                "MEDICAL_HISTORY":"Medical History", "RULE_OUT":"Rule out", "LOT":'Lot Number'}

class ReportUtil:
    """report related functions provide capabilities such as creating report summary, calculate onset time"""
    
    @staticmethod
    def consolidate_reports(reports, medDRA = False):
        newfeatures = []
        for report in reports:            
            for feat in report['Features']:
                if not feat.hasStartTime(): continue     
                tStart = feat.getStartDate()
                tEnd = feat.getEndDate()
                    
                for nft in newfeatures:
                    if nft.getStartDate==tStart and nft.getEndDate==tEnd:
                        (commonstr, fstr1, featLeft) = ReportUtil.get_merged_feature(nft.getCleanString(), feat.getCleanString())
                        if featLeft:
                            newfeat = feat.copy()
                            newfeat.setString(featLeft)
                            newfeatures.append(newfeat)
                            continue
                            
                    newfeat = feat.copy()
                    newfeatures.append(newfeat)
        
        consolidatedReport = {}
        consolidatedReport['Features'] = newfeatures
        
        return consolidatedReport

    @staticmethod
    def get_report_type(report):
        if len(report['Report ID'].split('-')[0])<=6:
            reportType = 'vaers'
        else:
            reportType = 'faers'
        return reportType
    
    @staticmethod
    def get_merged_feature(self, str1, str2):
        
        set1 = set(str1.split(', '))
        set2 = set(str2.split(', '))
        inst = set1.intersection(set2)
        if not inst:
            return ('', str1, str2)
        
        st1 = set1 - inst
        st2 = set2 - inst
        
        s1 = ', '.join(st1)
        s2 = ', '.join(st2)
        sinst = ', '.join(inst)
        
        return (sinst, s1, s2)
    
    @staticmethod
    def get_report_onset_time(report):
        
        totalHours = report['CalculatedOnsetTime']
        if totalHours >= 0:
            
            (days, hours) = divmod(totalHours, 24)
            
            days0 = days
            (years, days) = divmod(days, 365)
            (months, days) = divmod(days, 30)
            #(weeks, days) = divmod(days, 7)
            
            s = ''
            if years>1:
                s += str(years) + ' years ' 
            elif years==1:
                s += 'one year ' 
                    
            if months>1:
                s += str(months) + ' months '
            elif months==1:
                s += 'one month '
            
            if days > 1:
                s += str(days) + ' days'
            elif days==1:
                s += ' one day'
            elif years==0 and months==0 and hours==0:
                s += 'the same day'
            
            if hours > 1:
                s += str(hours) + ' hours'
            elif hours==1:
                s += ' one hour'
                
            if hours != 0:
                dec = round(hours/24)
                strSort = str(days0).zfill(5) + '.' + str(dec)
            else:
                strSort = str(days0).zfill(5)
            if report['DatesConfidence']<1:
                s += '*'
        else:
            strSort = 'UNKNOWN'
            s = 'UNKNOWN'
        
        s = s.strip()
        
        return (strSort, s)
    
    @staticmethod
    def getReportSummary_old(report):
        s = ''
        if report['Age']:
            s += 'A ' + report['Age'] + ' years old'
        
        sex = report['Gender'].lower()
        if sex:
            if sex[0]=='f':
                s += ' female'
            elif sex[0] == 'm':
                s += ' male'

        features = report['Features']
        mhx = '; '.join([feat.getString() for feat in features if feat.getType()=='MEDICAL_HISTORY'])
        if mhx:
            s += ' <html><b>with medical history of</b></html> <html><i>' + mhx + '</i></html>' 
        
        fhx = '; '.join([feat.getString() for feat in features if feat.getType()=='FAMILY_HISTORY'])
        if fhx:
            if mhx:
                s += ' and <html><b>family history of</b></html> <html><i>' + fhx + '</i></html>' 
            else:
                s += ' <html><b>with family history of</b></html> <html><i>' + fhx + '</i></html>' 
                
        diagnosis = '; '.join([feat.getString() for feat in features if feat.getType()=='DIAGNOSIS' or feat.getType()=='SECOND_LEVEL_DIAGNOSIS'])
        if diagnosis:
            s += ' <html><b>who presents with</b></html> <html><i>' + diagnosis + '</i></html>'
        
        (strOnsetSort, strOnsetDisp) = ReportUtil.get_report_onset_time(report)
        if strOnsetDisp!='UNKNOWN':
            strOnsetDisp = strOnsetDisp.strip('*') 
            s += ' <html><b>on</b></html> <html><i>'+ strOnsetDisp + '</i></html>' 
            
        if report['Vaccines']:
            s += ' <html><b>after exposure to</b></html> ' + report['Vaccines']
        
        s += '.'
        return s

    ##: Create a summary string for the list of features
    ##: 1. Split all feature text by ", "
    ##: 2. Remove duplicates and re-join them
    @staticmethod
    def getSummaryString(featureStrList):
        dxFeatSet = []
        for fs in featureStrList:
#            dxFeatSet += fs.split(', ')
            if fs:
                dxFeatSet += re.split(', | and ', fs)
        s = ', '.join(set(dxFeatSet))
        s.strip(', ')
        return s
    
    @staticmethod
    def get_feature_original_time(feature, report):
        text = report['Free Text']
        sentences = sentence_tokenize(text)
        sentNum = feature.getSentNum()
        timexList = timexan.annotateTimexes(sentences[sentNum])
        while not timexList and sentNum>0:
            sentNum -= 1
            timexList = timexan.annotateTimexes(sentences[sentNum])
        
        fTime = feature.getStartTime()
        candidates = []
        for t in timexList:
            if t.getDateTime() and t.getDateTime()==fTime:
                if t.getDateCompleteness()==3:  ##: Found exact match
                    return None
                else:
                    candidates.append(t)
        
        tmax = None
        maxCompleteness = 0
        for t in candidates:
            if t.getDateCompleteness() > maxCompleteness:
                tmax = t
        
        if tmax:
            return tmax.getString()
    
    ##: Create a summary string for features with their start time
    @staticmethod
    def get_feature_summary_string_time(featureList, report, expDate = None, coding = False):
        ##: remove duplicate features
        uniq_diags = []
        for feat in featureList:
            if not coding or feat.getMedDRA()=='':
                ft = (feat.getCleanString(), feat.getStartTime(), feat.getEndTime())
            else:
                ft = (feat.getMedDRA(), feat.getStartTime(), feat.getEndTime())
                    
            if ft in uniq_diags:
                featureList.remove(feat)
            else:
                uniq_diags.append(ft)
        
        ##: Remove features that are contained in others
        features = []
        for i in xrange(len(featureList)):
            curFeat = featureList[i]
            others = featureList[:i]+featureList[i+1:]
            containers = [ft for ft in others if (curFeat.getCleanString() in ft.getCleanString()) 
                          and (not curFeat.getStartTime() or (curFeat.getStartTime()==ft.getStartTime() and curFeat.getEndTime()==ft.getEndTime()))]
            if not containers:  ##: if current feature is contained in another feature, skip it
                if curFeat.getStartTime() and curFeat.getStartTime().day==1:
                    timeOriginalStr = ReportUtil.get_feature_original_time(curFeat, report)
                else:
                    timeOriginalStr = None
                    
                if not coding or curFeat.getMedDRA()=='':
                    features.append((curFeat.getCleanString(), curFeat.getStartTime(), curFeat.getEndTime(), timeOriginalStr))       
                else:
                    features.append((curFeat.getMedDRA(), curFeat.getStartTime(), curFeat.getEndTime(), timeOriginalStr))                         
            
        segments = []
        segments_notime = []
        used = []
        ##: Group features with the same time
        for i, fi in enumerate(features):
            if i in used: continue
            fts = [fi[0]]
            used.append(i)
            for j, fj in enumerate(features):
                if j<i or j in used:
                    continue
                if fj[1]==fi[1] and fj[2]==fi[2]:
                    fts.append(fj[0])
                    used.append(j)
            seg = ' <html><i>' + ', '.join(fts) + '</i></html>'
            if fi[1] and not expDate:
                if fi[3]:
                    seg += ' on ' + fi[3]
                elif fi[1]==fi[2]:
                    seg += ' on ' + fi[1].isoformat().split('T')[0]
                else:  
                    seg += ' from ' + fi[1].isoformat().split('T')[0] + ' to ' + fi[2].isoformat().split('T')[0] 
                segments.append(seg)
            elif fi[1] and expDate:
                if fi[3]:
                    seg += ' on ' + fi[3]
                elif fi[1] > expDate:  
                    seg += ' ' + timexan.beautifyTimeInterval(fi[1]-expDate) + ' later'
                elif fi[1] < expDate:
                    seg += ' ' + timexan.beautifyTimeInterval(expDate-fi[1]) + ' earlier'
                else:
                    seg += ' on the same day'
                segments.append(seg)
            else:
                segments_notime.append(seg)
        segments += segments_notime 
        
        if not segments:
            ss = ''
        elif len(segments)==1:
            ss = segments[0]
        else:
            ss = ', '.join(segments[:-1]) + ', and ' + segments[-1]
        
        return ss
            
    
    ##: createReportSummaryTemplate1
    ##: A xx years old male/female with medical history of Medical History and family history of Family History who presents with 
    ##: Primary Diagnosis/Second Level Diagnosis after Onset Time after exposure to Vaccine and was treated with medications of Drugs 
    @staticmethod
    def createReportSummaryTemplate1(report, reportType):
        s = ''
        if report['Age']:
            s += 'A ' + report['Age'] + ' years old'
        
        sex = report['Gender'].lower()
        if sex:
            if sex[0]=='f':
                s += ' female'
            elif sex[0] == 'm':
                s += ' male'

        features = report['Features']
        mhx = '; '.join([feat.getCleanString() for feat in features if feat.getType()=='MEDICAL_HISTORY'])
        if mhx:
            s += ' <html><b>with medical history of</b></html> <html><i>' + mhx + '</i></html>' 
        
        fhx = '; '.join([feat.getCleanString() for feat in features if feat.getType()=='FAMILY_HISTORY'])
        if fhx:
            if mhx:
                s += ' and <html><b>family history of</b></html> <html><i>' + fhx + '</i></html>' 
            else:
                s += ' <html><b>with family history of</b></html> <html><i>' + fhx + '</i></html>' 
        
        dxFeatureStrs = [feat.getCleanString() for feat in features if feat.getType()=='DIAGNOSIS' or feat.getType()=='SECOND_LEVEL_DIAGNOSIS']
        diagnosis = ReportUtil.getSummaryString(dxFeatureStrs)
        #diagnosis = '; '.join([feat.getString() for feat in features if feat.getType()=='DIAGNOSIS' or feat.getType()=='SECOND_LEVEL_DIAGNOSIS'])
        if diagnosis:
            s += ' <html><b>who presents with</b></html> <html><i>' + diagnosis + '</i></html>'
        
        onsetFeatures = [feat.getCleanString() for feat in features if feat.getType()=='TIME_TO_ONSET']
        if reportType=='vaers' and onsetFeatures:
            strOnsetDisp = onsetFeatures[0]
        else:
            (strOnsetSort, strOnsetDisp) = ReportUtil.get_report_onset_time(report)
        
        if strOnsetDisp!='UNKNOWN':
            strOnsetDisp = strOnsetDisp.strip('*') 
            s += ' <html><b>on</b></html> <html><i>'+ strOnsetDisp + '</i></html>' 
            
        if report['Vaccines']:
            s += ' <html><b>after exposure to</b></html> ' + report['Vaccines']
            #s += ' <html><b>after exposure</b></html> to <html><i>' + report['Vaccines'] + '</i></html>'
                
        dxFeatureStrs = [feat.getCleanString() for feat in features if feat.getType()=='DRUG']
        drugs = ReportUtil.getSummaryString(dxFeatureStrs)
        if reportType =='vaers' and drugs:
            s += ' <html><b>and was treated with medications of </b></html> <html><i>' + drugs + '</i></html>' 
        
        s += '.'
        return s

    ##: createReportSummaryTemplate2
    ##: 1st sentence: age, sex, past history, indication for drug of interest, drug of interest
    ##: Next sentences: dates with the primary, cause of death or secondary diagnosis (this is the part we will need to improve in parallel with the improvements in the TM code).
    @staticmethod
    def getReportSummaryTemplate2(report, reportType):
        s = 'A'
        if report['Age']:
            s += ' ' + report['Age'] + ' years old'
        
        sex = report['Gender'].lower()
        if sex:
            if sex[0]=='f':
                s += ' female'
            elif sex[0] == 'm':
                s += ' male'
            else:
                s += ' patient'
        else:
            s += ' patient'

        features = report['Features']
        mhx = '; '.join([feat.getCleanString() for feat in features if feat.getType()=='MEDICAL_HISTORY'])
        if mhx:
            s += ' <html><b>with medical history of</b></html> <html><i>' + mhx + '</i></html>' 
        
        fhx = '; '.join([feat.getCleanString() for feat in features if feat.getType()=='FAMILY_HISTORY'])
        if fhx:
            if mhx:
                s += ' and <html><b>family history of</b></html> <html><i>' + fhx + '</i></html>' 
            else:
                s += ' <html><b>with family history of</b></html> <html><i>' + fhx + '</i></html>' 
        
        reportType = ReportUtil.get_report_type(report)
        ##: Find indication of drugs/vaccines
        if reportType=='vaers':
            indications = set([vac.strip('(),') for vac in report['Vaccine Names'].lower().split()])
        else:            
            indications = set(report['Primary Suspect'].lower().split())
        
        ##: Find drug of interest
        ss = '.'
        if indications:
            ss = ' <html><b>was treated with</b></html> '
            featIndicated = [feat for feat in features if feat.getType() in ['VACCINE', 'DRUG'] and set(feat.getCleanString().lower().split()).intersection(indications)]
            strFeats = ReportUtil.get_feature_summary_string_time(featIndicated, report)
            if strFeats:
                ss += strFeats
                
            if ReportUtil.get_report_type(report)=='faers':
                if not strFeats:
                    ss += report['Primary Suspect'].lower()
                    
                indication = report['Indication']
                if indication:
                    strIndication = '<html><b> for </b></html>' + indication.lower()
                    ss += strIndication
            else:
                if not strFeats:
                    ss += report['Vaccine Names'].lower()
                
            ss += '.'

        s += ss
        
        ##: Find diagnosis of interest
        diagFeatures = [feat for feat in features if feat.getType() in ['DIAGNOSIS', 'SECOND_LEVEL_DIAGNOSIS', 'CAUSE_OF_DEATH']]
        ss = '.'
        if diagFeatures:
            strDiags = ReportUtil.get_feature_summary_string_time(diagFeatures, report)
            if strDiags:
                ss = ' The patient <html><b>was diagnosed with</b></html> ' + strDiags + '.'
        s += ss 
             
        return s
    
    ##: createReportSummaryTemplate
    ##: 1st sentence: age, sex, past history, indication for drug of interest, drug of interest
    ##: Next sentences: dates with the primary, cause of death or secondary diagnosis (this is the part we will need to improve in parallel with the improvements in the TM code).
    @staticmethod
    def getReportSummary(report, reportType, coding = False, features = None, posOutcomes = []):
        s = 'A'
        if report['Age']:
            s += ' ' + report['Age'] + ' year-old'
            
        sex = report['Gender'].lower()
        if sex:
            if sex[0]=='f':
                s += ' female'
            elif sex[0] == 'm':
                s += ' male'
            elif s=='A':
                s = 'An individual'
            else:
                s += ' individual'
        elif s=='A':
            s = 'An individual'
        else:
            s += ' individual'
        
        if not features:
            features = report['Features']
        
        reportType = ReportUtil.get_report_type(report)
        ##: Find indication of drugs/vaccines
        if reportType=='vaers':
            indications = set([vac.strip('(),') for vac in report['Vaccine Names'].lower().split()])
        else:            
            indications = set(report['Primary Suspect'].lower().split())
        
        ##: Find drug of interest
        ss = '.'
        expDate = report['Exposure Date']
        if not expDate:
            expDate = timexan.parse_time_string(report['Date of Exposure'])
        
        if indications:
            featIndicated = [feat for feat in features if feat.getType() in ['VACCINE', 'DRUG'] and set(feat.getCleanString().lower().split()).intersection(indications)]
            if not coding:
                strFeats = ReportUtil.getSummaryString([feat.getString() for feat in featIndicated])  
            else: 
                pts = [feat.getMedDRA() if feat.getMedDRA()!='' else feat.getString() for feat in featIndicated]
                strFeats = ReportUtil.getSummaryString(pts)  
            
            
            if not strFeats:
                if ReportUtil.get_report_type(report)=='faers':
                    strFeats = report['Primary Suspect']
                else:
                    strFeats = report['Vaccine Names']    
                 
            if strFeats:
                ss = ' <html><b>received </b></html>'
                ss += strFeats
                
                if expDate:
                    ss += ' on ' + expDate.isoformat().split('T')[0] + '.'
#                     ss += ' on ' + report['Date of Exposure'] + '.'
                else:
                    ss += ' on an unknown date.'         
                
        s += ss
        
        ##: Find diagnosis/symptom to display
        ##: 1. Find DIAGNOSIS
        ##: 2. If not, find SECOND_LEVEL_DIAGNOSIS
        ##: 3. If not, find SYMPTOM
        ##: 4. Always show CAUSE_OF_DEATH
        diagFeatures = [feat for feat in features if feat.getType()=='DIAGNOSIS']
        
        if not diagFeatures:
            diagFeatures = [feat for feat in features if feat.getType()=='SECOND_LEVEL_DIAGNOSIS']
            
        if not diagFeatures:
            diagFeatures = [feat for feat in features if feat.getType()=='SYMPTOM']            

        if diagFeatures:
            ss = ' This individual '
            if sex:
                if sex[0]=='f':
                    ss = ' She '
                elif sex[0] == 'm':
                    ss = ' He '            
            strDiags = ReportUtil.get_feature_summary_string_time(diagFeatures, report, expDate, coding)
            if strDiags:
                ss += '<html><b>experienced</b></html> ' + strDiags + '.'
        s += ss         
        
        cod = [feat for feat in features if feat.getType()=='CAUSE_OF_DEATH']
        if cod:
            if coding:
                strCods = [feat.getMedDRA() if feat.getMedDRA()!='' else feat.getString() for feat in cod]
            else:
                strCods = [feat.getString() for feat in cod]
                
            strCods = remove_duplicates_from_list(strCods)
            ss2 = ' <html><i>' + ', '.join(strCods) + '</i></html>'
            s += ' The <html><b>cause of death</b></html> is ' + ss2 + '.'
            
        s = s.strip()
        
        if len(posOutcomes) > 0:
            text = report['Free Text']
            terms = []
            termsLowercase = []
            for posStart, posEnd in posOutcomes:
                t = text[posStart:posEnd+1].lower()
                if not t.lower() in termsLowercase:
                    terms.append(t)
                    termsLowercase.append(t.lower())
            
            s += ' <html><b>This report has associated outcome(s) of interest</b></html>: ' + ', '.join(terms) +'.'
#             s += '<html><br><html>This report has associated <html><b>outcome of interest</b><html>: ' + '; '.join(terms) +'.'
        
        return s
    
class ReportClassifier:
    """Perform report classification. Developed by Taxiarchis Botsis."""
    
    def __init__(self):  
        self.lexicon=[(r'non$','NEGATION'), (r'no$','NEGATION'), (r'hour$','TIME'),(r'minute.*$','TIME'), (r'hr$','TIME'), (r'hrs$','TIME'), (r'day$','TIME'), (r'min$','TIME'), 
             (r'wheez.*$','majorRESP'), (r'bronchospasm.*$','majorRESP'),(r'stridor.*$','majorRESP'), (r'distress.*$','majorRESP'), (r'swell.*$','swelRESP'), 
             (r'swollen$','swelRESP'), (r'edema$','swelRESP'), (r'neck$','ANATOMY'), (r'lip.*$','ANATOMY'), (r'tongue$','ANATOMY'), (r'uvula.*$','ANATOMY'), 
             (r'larynx$','ANATOMY'), (r'throat$','throatANATOMY'), (r'hands$','handANATOMY'),(r'hand$','handANATOMY'),(r'abdomen$','abdomenANATOMY'), 
             (r'body$','bodyANATOMY'), (r'fac.*$','faceANATOMY'), (r'eye.*$','eyeANATOMY'), (r'voice.*$','minorRESP'),(r'dyspn.*$','minorRESP'), (r'swall.*$','minorRESP'), 
             (r'sob$','minorRESP'), (r'breath.*$','breathRESP'), (r'sneez.*$', 'minorRESP'), (r'rhinor.*$', 'minorRESP'), (r'tight.*$', 'closureRESP'), (r'clos.*$', 'closureRESP'), 
             (r'constrict.*$', 'closureRESP'), (r'scratch.*$', 'closureRESP'), (r'sore.*$', 'closureRESP'), (r'dry.*$', 'closureRESP'), (r'funny$', 'closureRESP'), 
             (r'hoarse.*$', 'closureRESP'), (r'anaphyl.*$','OBSERV'), (r'.*phylaxis$','OBSERV'), (r'hive.*$','majorDERM'),(r'erythem.*$','majorDERM'),(r'angioedema$','majorDERM'), 
             (r'itch.*$','ITCHY'), (r'general.*$','GENERALIZED'), (r'urticari.*$','minorDERM'), (r'prurit.*$','minorDERM'),(r'rash$','rashDERM'), (r'diffuse$','diffuseDERM'), 
             (r'hypoten.*$','majorCDV'),(r'diarr.*$','minorGI'),(r'nause.*$','minorGI'),(r'vomit.*$','minorGI'), (r'epinephrine$','drug'), (r'epipen$','drug'), (r'epi$','drug'), 
             (r'.*','unimportant'), (r'one$','NUMBER'),(r'two$','NUMBER'),(r'three$','NUMBER'),(r'four$','NUMBER'),(r'five$','NUMBER'),(r'six$','NUMBER'),(r'seven$','NUMBER'),
             (r'eight$','NUMBER'),(r'nine$','NUMBER'), (r'ten$','NUMBER') , (r'^-?[0-9]+(.[0-9]+)?$','CD')]

        self.regexp_tagger=nltk.RegexpTagger(self.lexicon)

        grammar = r""" non: {<unimportant|CD|NUMBER|TIME>}
                            observation: {<OBSERV>}
                            DRUG:{<drug>}
                            MRESP:{<majorRESP>}
                            {<ANATOMY|throatANATOMY>+?<non>*<swelRESP>}
                            {<swelRESP><non>*<ANATOMY|throatANATOMY>+?}
                            mRESP: {<minorRESP>}
                            {<breathRESP>}
                            {<throatANATOMY><non>*<closureRESP|ITCHY>+?}
                            {<closureRESP|ITCHY>+?<non>*<throatANATOMY>}
                            MDERM: {<majorDERM>}
                            {<minorDERM|majorDERM|diffuseDERM|ITCHY>+?<non>*<rashDERM>+?}
                            {<rashDERM><non>*<minorDERM|majorDERM|diffuseDERM|ITCHY>+?}
                            {<swelRESP><non>*<faceANATOMY|eyeANATOMY|bodyANATOMY|abdomenANATOMY|handANATOMY>+?}
                            {<faceANATOMY|eyeANATOMY|bodyANATOMY|abdomenANATOMY|handANATOMY>+?<non>*<swelRESP>}
                            {<GENERALIZED><minorDERM>}
                            {<ITCHY>}
                            mDERM: {<minorDERM>}
                            MCDV: {<majorCDV>}
                            GI: {<minorGI>}
                            exclude:{<NEGATION><MRESP|mRESP|MDERM|mDERM|MCDV|GI>}
                            {<ANATOMY>}
                            {<throatANATOMY>}
                            {<non>}
                            {<swelRESP>}
                            {<closureRESP>}
                            {<diffuseDERM>}
                            {<rashDERM>}
                            {<GENERALIZED>}
                            {<faceANATOMY>}
                            {<bodyANATOMY>}
                            {<abdomenANATOMY>}
                            {<handANATOMY>}
                            {<eyeANATOMY>}
                            pattern1:{<MCDV><exclude>*<MDERM>}
                            {<MCDV><exclude>*<MRESP>}
                            {<MCDV><exclude>*<DRUG>}
                            {<MDERM><exclude>*<MCDV>}
                            {<MDERM><exclude>*<MRESP>}
                            {<MDERM><exclude>*<DRUG>}
                            {<MRESP><exclude>*<MCDV>}
                            {<MRESP><exclude>*<MDERM>}
                            {<MRESP><exclude>*<DRUG>}
                            {<DRUG><exclude>*<MCDV>}
                            {<DRUG><exclude>*<MRESP>}
                            {<DRUG><exclude>*<MDERM>}
                            pattern2:{<MCDV><exclude>*<mDERM>}
                            {<MCDV><exclude>*<mRESP>}
                            {<MCDV><exclude>*<GI>}
                            {<MRESP><exclude>*<mDERM>}
                            {<MRESP><exclude>*<GI>}
                            {<MDERM><exclude>*<mRESP>}
                            {<MDERM><exclude>*<GI>}
                            {<DRUG><exclude>*<mDERM>}
                            {<DRUG><exclude>*<mRESP>}
                            {<DRUG><exclude>*<GI>}
                            {<mDERM><exclude>*<MCDV>}
                            {<mDERM><exclude>*<MRESP>}
                            {<mDERM><exclude>*<DRUG>}
                            {<mRESP><exclude>*<MCDV>}
                            {<mRESP><exclude>*<MDERM>}
                            {<mRESP><exclude>*<DRUG>}
                            {<GI><exclude>*<MCDV>}
                            {<GI><exclude>*<MRESP>}
                            {<GI><exclude>*<MDERM>}
                            {<GI><exclude>*<DRUG>}
                            pattern3:{<mDERM><exclude>*<mRESP><exclude>*<GI>}
                            {<mDERM><exclude>*<GI><exclude>*<mRESP>}
                            {<mRESP><exclude>*<GI><exclude>*<mDERM>}
                            {<mRESP><exclude>*<mDERM><exclude>*<GI>}
                            {<GI><exclude>*<mRESP><exclude>*<mDERM>}"""


        self.cp=nltk.RegexpParser(grammar)

    def getClassification(self, reportText):
        cls = self.ie_process(reportText) 
        level = 0
        return (cls, level)
        
    def ie_process(self, document):    
        punctuations = ['."',"```","`","+","*","^","%","@","&","<",">","'","-",',', '.', '!', '?', ';', ':', '"', '/', ')','(']
        allw=self.regexp_tagger.tag([w.lower() for w in document if w.lower() not in punctuations]) 
        tree=self.cp.parse(allw)
        report=''
        features={}
        for subtree in tree.subtrees():
            if subtree.label()=='pattern1':
                features['pattern1']= (subtree.node=='pattern1')
                report='positive'
            if subtree.label()=='pattern2':
                features['pattern2']= (subtree.node=='pattern2')
                report='positive'
            if subtree.label()=='pattern3':
                features['pattern3']= (subtree.node=='pattern3')
                report='positive'
            if subtree.label()=='observation':
                features['observation']= (subtree.node=='observation')
                report='positive'
        return report
    

class ReportGenerator:
    """This class provides functions to export ETHER results into a series of format."""
    
    @staticmethod
    def save_report_summary(reports, filename):
        try:
            with open(filename, 'wb') as f:
                featurewriter = csv.writer(f, dialect='excel', delimiter=',')
                featurewriter.writerow(['Report ID', 'Age', 'Gender', 'Primary Diagnosis', 'Time to Onset', 'Secondary Diagnosis/Symptoms', 'Classification'])
                        
                for report in reports:
                    (strOnsetSort, strOnsetDisp) = ReportUtil.get_report_onset_time(report)
                    features = report['Features']
                        
                    diagnosis = ReportUtil.getSummaryString([feat.getCleanString() for feat in features if feat.getType()=='DIAGNOSIS' or feat.getType()=='CAUSE_OF_DEATH'])
                    diagnosis2nd = ReportUtil.getSummaryString([feat.getCleanString() for feat in features if feat.getType()=='SECOND_LEVEL_DIAGNOSIS' or feat.getType()=='SYMPTOM'])
                    featurewriter.writerow([report['Report ID'], report['Age'], report['Gender'], diagnosis, strOnsetDisp, diagnosis2nd, report['CLASS']])
        except Exception as e:
            print(str(e))
            
    @staticmethod
    def save_reports_txt(reports, filename):
        try:
            with open(filename, 'w') as f:
                for report in reports:
                    row = [report['Report ID'], report['Age'], report['Date of Exposure'], report['Date of Onset'], report['Vaccines'], report['Vaccine Names'], report['MedDRA'], 
                           report['Gender'], report['Lab Text'], report['Received Date'], report['Lot Number'], report['Free Text']]
                    
                    s = '", "'.join(row)
                    s = '"' + s + '"\n'
                    f.write(s)
        except Exception as e:
            print(str(e)) 
        
    @staticmethod
    def save_reports_csv(reports, filename):
        try:
            with open(filename, 'wb') as f:
                featurewriter = csv.writer(f, dialect='excel', delimiter=',')                        
                for report in reports:
                    row = [report['Report ID'], report['Age'], report['Date of Exposure'], report['Date of Onset'], report['Vaccines'], report['Vaccine Names'], report['MedDRA'], 
                           report['Gender'], report['Lab Text'], report['Received Date'], report['Lot Number'], report['Free Text']]
                    featurewriter.writerow(row)
        except Exception as e:
            print(str(e))      
    
    @staticmethod
    def save_xml_reports_csv(reports, filename):
        if filename:
            try:
                with open(filename, 'wb') as f:
                    featurewriter = csv.writer(f, dialect='excel', delimiter=',')
                    featurewriter.writerow(['File name', 'AE Term', 'MedDRA PT', 'Text', 'Sentence', 'Section', 'Subsection', 'Table', 'Boxed Warning', 'Comment'])
                    for report in reports:
                        fname = report['Report ID']
                        ptAll = report['PTsXML']
                        for (section, subsection, table, PTs) in  ptAll:
                            if subsection=='None':
                                subsection = ''
                            if table=='None':
                                table = ''
                            if section.startswith('BOXED'):
                                warning = 'Y'
                                section = ''
                                subsection = ''
                            else:
                                warning = ''

                            for pt in PTs:
                                ftStr = pt[0].encode('ascii', 'ignore').decode('ascii')
                                ftTxt = pt[2].encode('ascii', 'ignore').decode('ascii')
                                ftSent = pt[3].encode('ascii', 'ignore').decode('ascii')
                                row = [fname, ftStr, pt[1], ftTxt, ftSent, section, subsection, table, warning, '']                                
                                row = [unicode(s).encode("utf-8") for s in row]
                                featurewriter.writerow(row)

            except Exception as e:
                print(str(e))
                
    @staticmethod
    def save_report_id(reports, filename):
        try:
            with open(filename, 'w') as f:
                for report in reports[:-1]:
                    f.write(report['Report ID']+'\n')
                f.write(reports[-1]['Report ID'])
        except Exception as e:
            print(str(e))   
            
    @staticmethod
    def save_ether_summary(reports, filename):
        try:
            with open(filename, 'wb') as f:
                featurewriter = csv.writer(f, dialect='excel', delimiter=',')
                featurewriter.writerow(['Case ID', 'Product', 'Lot Number', 'Summary'])
                        
                for report in reports:
                    if report['Review']!='':
                        s = report['Review']
                    else:
                        s = clean_html_tags(report['Summary'])
                        
                    featurewriter.writerow([report['Report ID'], report['Vaccines'], report['Lot Number'], s])
                    
        except Exception as e:
            print(str(e))

    @staticmethod
    def save_summarized_cases(reports, filename):
        if filename:
            try:
                with open(filename, 'wb') as f:
                    featurewriter = csv.writer(f, dialect='excel', delimiter=',')
                    featurewriter.writerow(['Flag', 'Case ID', 'Age', 'Sex', 'Products',  'Calculated Onset', 'Diagnosis', 'Secondary Diagnosis', 'Medical History', 'Concomitant Medications'])

                    for report in reports:
                        (strOnsetSort, strOnsetDisp) = ReportUtil.get_report_onset_time(report)
                        features = report['Features']
                        diagnosis = ReportUtil.getSummaryString([feat.getCleanString() for feat in features if feat.getType()=='DIAGNOSIS' or feat.getType()=='CAUSE_OF_DEATH'])
                        diagnosis2nd = ReportUtil.getSummaryString([feat.getCleanString() for feat in features if feat.getType()=='SECOND_LEVEL_DIAGNOSIS'])
            
                        mhx = '; '.join([feat.getString() for feat in features if feat.getType()=='MEDICAL_HISTORY'])
                        medications = '; '.join(set([feat.getString() for feat in features if feat.getType()=='DRUG']))
                        
                        if report['Mark']:
                            revisit = 'Y'
                        else:
                            revisit = 'N'
                        row = [revisit, report['Report ID'], report['Age'], report['Gender'], report['Vaccines'], strOnsetDisp, diagnosis, diagnosis2nd, mhx, medications]
                        featurewriter.writerow(row)
                        
            except Exception as e:
                print(str(e))
    
    @staticmethod
    def save_features_split(reports, filename):
        if filename:
            try:
                with open(filename, 'wb') as f:
                    featurewriter = csv.writer(f, dialect='excel', delimiter=',')
                    featurewriter.writerow(['Report ID', 'Type', 'Text', 'MedDRA', 'Date', 'Negation'])
                    for r in reports:
                        for feature in  r['Features']:
                            strRows = feature.getFeatureDescription_split()
                            for row in strRows:
                                featurewriter.writerow([r['Report ID']] + row)
            except Exception as e:
                print(str(e))
                
    @staticmethod
    def save_features(reports, filename):
        if filename:
            try:
                with open(filename, 'wb') as f:
                    featurewriter = csv.writer(f, dialect='excel', delimiter=',')
                    featurewriter.writerow(['Report ID', 'Type', 'Text', 'Date'])
                    for r in reports:
                        for feature in  r['Features']:
                            strFeat = feature.getFeatureDescription()
                            featurewriter.writerow([r['Report ID']] + strFeat)
            except Exception as e:
                print(str(e))
                
    @staticmethod
    def save_timexes(reports, filename):
        if filename:
            try:
                with open(filename, 'wb') as f:
                    featurewriter = csv.writer(f, dialect='excel', delimiter=',')
                    featurewriter.writerow(['Report ID', 'Text', 'Type', 'Location'])
                    for r in reports:
                        rptid = r['Report ID']
                        for t in  r['TimexDisplay']:
                            strRow = [rptid, t.getString(), t.getType(), str(t.getStartPos())]
                            featurewriter.writerow(strRow)
            except Exception as e:
                print(str(e))
                
    @staticmethod
    def save_time_annotations(reports, filename):
        strTimeTypes = ['', 'Date', 'Relative', 'Duration', 'Weekday', 'Frequency', 'Age', 'Time']
        if filename:
            try:
                with open(filename, 'wb') as f:
                    featurewriter = csv.writer(f, dialect='excel', delimiter=',')
                    featurewriter.writerow(['Report ID', 'Text', 'Type', 'Location', 'Comment'])
                    for r in reports:
                        if not r['TimeAnnotations']: continue
                        
                        rptid = r['Report ID']
                        for annt in  r['TimeAnnotations']:
                            strRow = [rptid, annt[1], strTimeTypes[annt[2]], str(annt[4]), annt[6]]
                            featurewriter.writerow(strRow)
            except Exception as e:
                print(str(e))
                
class XMLUtil:
    """This class provides capability to handle XML files."""
    
    ##: Reference: "Structured Product Labeling (SPL) Implementation Guide with Validation Procedures," FDA
    sectionCode = {'Boxed Warning':'34066-1', 'Recent Major Changes':'43683-2', 'Indications and Usage':'34067-9', 
                   'Dosage and Administration':'34068-7', 'Dosage Forms and Strengths':'43678-2', 'Contraindications':'34070-3',
                   'Warnings and Precautions':'43685-7', 'Adverse Reactions':'34084-4', 'Drug Interactions':'34073-7',
                   'Use in Specific Populations':'43684-0', 'Microbiology':'49489-8'}
    
    @staticmethod
    def find_element_text(textList, element, subsection):
        if element.tag=='{urn:hl7-org:v3}excerpt' and element[0].tag=='{urn:hl7-org:v3}highlight':
            return textList
    
        curText=''
        if element.text and re.findall('\S', element.text):
            curText += element.text
        if element.tail and re.findall('\S', element.tail):
            curText += element.tail
        curText.replace('\n', '')
        if curText:
            textList.append((curText, subsection, None))
        
        if not list(element): 
            return textList
    
        for child in element:
            if child.tag=='{urn:hl7-org:v3}table':
                t = ' '.join(child.itertext())
                t.replace('\n', '')
                textList.append((t, subsection, child))
                continue
        
            if child.tag=='{urn:hl7-org:v3}section':
                if subsection is None:
                    subsection = child
            XMLUtil.find_element_text(textList, child, subsection)
    
        return textList
    
    @staticmethod
    def get_child_text_by_tag(element, childTag):
        tag = '{urn:hl7-org:v3}' + childTag
        for child in element:
            if child.tag==tag:
                if child.text:
                    return ''.join(child.itertext())
                else:
                    return 'None'
        return 'None'
    
    @staticmethod
    def get_full_text(sectionTripleList):
        full = '\n\n'.join(['\n'.join([t[0] for t in textTripleList]) for (sec, textTripleList) in sectionTripleList])
        return full
            
    @staticmethod
    def find_section_only_text_by_titles(xmlfilename, titles):
        try:
            tree = ETree.parse(xmlfilename)
        except Exception as e:
#             QMessageBox.critical(None, "ETHER", str(e))
            print(str(e))
            return (None, None)
        
        codes = [XMLUtil.sectionCode[sect] for sect in titles]
        root = tree.getroot()
            
        prefix = 'urn:hl7-org:v3'
        namespace = {'ns':prefix}
        ns = '{' + prefix + '}'
        
        sectionTextList = []
        for section in root.findall('.//ns:component/ns:section/ns:code/..', namespace):
            title = None
            for child in section:
                #print child.tag, child.text
                if child.tag==ns+'code' and child.get('code') in codes:
                    title =  XMLUtil.get_child_text_by_tag(section,'title')
                    title = re.sub('\n+', '', title)
                    title = title.strip()
                    
                    if child.get('code')=='34066-1':
                        if title.lower().startswith('warning'):
                            title = 'BOXED ' + title
                        else:
                            title = 'BOXED WARNING' + title                    
                    break
            
            text = ' '.join([x for x in child.itertext()])
            
            sectionTextList.append((title,text))
            
        return sectionTextList
    
    @staticmethod
    def find_section_text_by_titles(xmlfilename, titles):
        try:
            tree = ETree.parse(xmlfilename)
        except Exception as e:
            print(str(e))
            return (None, None)
        
        codes = [XMLUtil.sectionCode[sect] for sect in titles]
        root = tree.getroot()
            
        prefix = 'urn:hl7-org:v3'
        namespace = {'ns':prefix}
        ns = '{' + prefix + '}'
        
        sectionTextList = []
        for section in root.findall('.//ns:component/ns:section/ns:code/..', namespace):
            title = None
            for child in section:
                #print child.tag, child.text
                if child.tag==ns+'code' and child.get('code') in codes:
                    title =  XMLUtil.get_child_text_by_tag(section,'title')
                    title = re.sub('\n+', '', title)
                    title = title.strip()
                    
                    if child.get('code')=='34066-1':
                        if title.lower().startswith('warning'):
                            title = 'BOXED ' + title
                        else:
                            title = 'BOXED WARNING' + title                    
                    break
            
            if not title: continue
            tripleList = []
            tripleList = XMLUtil.find_element_text(tripleList, section, None)
            tripleList = [t for t in tripleList if t[0] and re.findall('\S', t[0])]
            for i, t in enumerate(tripleList):
                tt = re.sub('(\n[ \t\r\v\f]*)+', '\n', t[0])
                tripleList[i]=(tt, t[1], t[2])
        
            if not tripleList: continue
        
            cleanTextList = []
            preElement = tripleList[0]
            curText = preElement[0]
            for elem in tripleList[1:]:
                if elem[1]==preElement[1] and elem[2]==preElement[2]:
                    curText += '\n'+ elem[0]
                    continue
                cleanTextList.append((curText, preElement[1], preElement[2]))
                preElement = elem
                curText = elem[0]
            cleanTextList.append((curText, preElement[1], preElement[2]))
            
            textLabelList = []
            for t in cleanTextList:
                subsectionTitle = 'None'
                if t[1] is not None:
                    subsectionTitle =  XMLUtil.get_child_text_by_tag(t[1],'title')
                tableCaption = 'None'
                if t[2] is not None:
                    tableCaption =  XMLUtil.get_child_text_by_tag(t[2],'caption')
                textLabelList.append((t[0], subsectionTitle, tableCaption))
            
            sectionTextList.append((title, textLabelList))
        
        fullText = XMLUtil.get_full_text(sectionTextList)
        return (fullText, sectionTextList)
                        
    @staticmethod
    def find_section_text_by_titletext(xmlfilename, titles):
        try:
            tree = ETree.parse(xmlfilename)
        except Exception as e:
            print str(e)
            return (None, None)
        
        codes = [XMLUtil.sectionCode[sect] for sect in titles]
        root = tree.getroot()
            
        prefix = 'urn:hl7-org:v3'
        namespace = {'ns':prefix}
        ns = '{' + prefix + '}'
        
        sectionTextList = []
        for section in root.findall('.//ns:component/ns:section/ns:title/..', namespace):
            title = None
            for child in section:
                #print child.tag, child.text
                if child.tag==ns+'title' and child.text and [t for t in titles if t.lower() in child.text.lower()]:
                    title = child.text
                    break
            
            if not title: continue
            tripleList = []
            tripleList = XMLUtil.find_element_text(tripleList, section, None)
            tripleList = [t for t in tripleList if t[0] and re.findall('\S', t[0])]
            for i, t in enumerate(tripleList):
                tt = re.sub('(\n[ \t\r\v\f]*)+', '\n', t[0])
                tripleList[i]=(tt, t[1], t[2])
        
            if not tripleList: continue
        
            cleanTextList = []
            preElement = tripleList[0]
            curText = preElement[0]
            for elem in tripleList[1:]:
                if elem[1]==preElement[1] and elem[2]==preElement[2]:
                    curText += '\n'+ elem[0]
                    continue
                cleanTextList.append((curText, preElement[1], preElement[2]))
                preElement = elem
                curText = elem[0]
            cleanTextList.append((curText, preElement[1], preElement[2]))
            
            textLabelList = []
            for t in cleanTextList:
                subsectionTitle = 'None'
                if t[1] is not None:
                    subsectionTitle =  XMLUtil.get_child_text_by_tag(t[1],'title')
                tableCaption = 'None'
                if t[2] is not None:
                    tableCaption =  XMLUtil.get_child_text_by_tag(t[2],'caption')
                textLabelList.append((t[0], subsectionTitle, tableCaption))
            
            sectionTextList.append((title, textLabelList))
        
        fullText = XMLUtil.get_full_text(sectionTextList)
        return (fullText, sectionTextList)
    
    @staticmethod
    def create_annotation_tree_uima(featList, timexList, doctext):
        
        dictFeatureAbr = {"SYMPTOM":"SYM", "VACCINE":"VAX", "DIAGNOSIS": "pDx", 
                "SECOND_LEVEL_DIAGNOSIS":"sDx", "CAUSE_OF_DEATH":"CoD", 
                "DRUG":'Tx', "FAMILY_HISTORY":"FHx", 'TIME_TO_ONSET':'',
                "MEDICAL_HISTORY":"MHx", "RULE_OUT":"R/O", "LOT":''}
        
        dictFeature2Names = dict((v,k) for k, v in dictFeatureAbr.iteritems())
        dictTime2Names = {'AGE':'Age', 'WEEKDAY':'Weekday', 'REL':'Relative', 'DUR':'Duration', 
                'FRQ':'Frequency', 'OTHER':'Other', 'DATE':'Date'}

        TCAS_NS  = "http:///uima/tcas.ecore"
        XMI_NS   =  "http://www.omg.org/XMI"
        CAS_NS  = "http:///uima/cas.ecore"
        VAERS_NS = "http:///gov/hhs/fda/srs/annotation/vaers.ecore"
        NS_MAP = {"tcas":TCAS_NS, "xmi": XMI_NS, "cas":CAS_NS, "vaers":VAERS_NS}

        root = ET.Element(ET.QName(XMI_NS, 'XMI'), {ET.QName(XMI_NS, 'version'):'2.0'}, nsmap=NS_MAP)
        
        sofaID = '6'
        elemCas = ET.SubElement(root, ET.QName(CAS_NS, 'NULL'), {ET.QName(XMI_NS, 'id'):'0'})
        elemtCas = ET.SubElement(root, ET.QName(TCAS_NS, 'DocumentAnnotation'), 
                                 {ET.QName(XMI_NS, 'id'):'1', "sofa":sofaID, "begin":'0', "end":str(len(doctext)), "language":"en"})
        
        elemtSofa = ET.SubElement(root, ET.QName(CAS_NS, 'Sofa'), 
                                 {ET.QName(XMI_NS, 'id'):sofaID, "sofaNum":'1', "sofaID":"_InitialView", "mimeType":'text', "sofaString":doctext})
    
        ##: Export Feature Annotations
        eids = set([])
        for eid, ftype, startPos, endPos, ftext, tid, rel in featList:
            if eid in eids:  ##: There are duplicated features with different associated time. They should be in temporal relation section.
                continue
            else:
                eids.add(eid)
                
            if ftype in dictFeature2Names:
                ftype = dictFeature2Names[ftype]
            elem = ET.SubElement(root, ET.QName(XMI_NS, 'VaersFeature'), 
                        {"type":ftype, ET.QName(XMI_NS, 'id'):'E'+str(eid), "sofa":sofaID, "begin":str(startPos), "end":str(endPos), "text":ftext})        
        
        ##: Export Timex Annotations
        dictTimexID2Text = {}
        timeRefs = []
        for tid, ftype, startPos, endPos, sdate, ftext, refID, refRel in timexList:
            if ftype in dictTime2Names:
                ftype = dictTime2Names[ftype]
            if sdate=='':
                elem = ET.SubElement(root, ET.QName(XMI_NS, 'TemporalFeature'), 
                                 {"type":ftype, ET.QName(XMI_NS, 'id'):'T'+str(tid), "sofa":sofaID, "begin":str(startPos), "end":str(endPos), "text":ftext})
            else:
                elem = ET.SubElement(root, ET.QName(XMI_NS, 'TemporalFeature'), 
                                 {"type":ftype, ET.QName(XMI_NS, 'id'):'T'+str(tid), "sofa":sofaID, "begin":str(startPos), "end":str(endPos), "text":ftext, "date":sdate})
            dictTimexID2Text[tid] = ftext
            if refID:
                timeRefs.append((tid, ftext, refID, refRel))

        ##: Export Feature-Time Associations
        tlid = 0
        for eid, ftype, startPos, endPos, ftext, tid, rel in featList:
            if tid:
                if not tid in dictTimexID2Text:  ##: Annnotator's error, assign an nonexisting time to a feature
                    continue
                elem = ET.SubElement(root, ET.QName(XMI_NS, 'TemporalRelation'), 
                        {ET.QName(XMI_NS, 'id'):'TL'+str(tlid), "sofa":sofaID, "coreID":'E'+str(eid), "refID":'T'+str(tid), "coreText":ftext, "refText":dictTimexID2Text[tid], "type":rel})
                
            tlid += 1
        
        for tid, ftext, refID, refRel in timeRefs:            
            elem = ET.SubElement(root, ET.QName(XMI_NS, 'TemporalRelation'), 
                        {ET.QName(XMI_NS, 'id'):'TL'+str(tlid), "sofa":sofaID, "coreID":'T'+str(tid), "refID":'T'+str(refID), "coreText":ftext, "refText":dictTimexID2Text[refID], "type":refRel})
            tlid += 1
    
        tree = ET.ElementTree(root)
        return tree
    
    @staticmethod
    def create_annotation_tree_i2b2(featList, timexList, doctext):

        dictFeatureAbr = {"SYMPTOM":"SYM", "VACCINE":"VAX", "DIAGNOSIS": "pDx", 
                "SECOND_LEVEL_DIAGNOSIS":"sDx", "CAUSE_OF_DEATH":"CoD", 
                "DRUG":'Tx', "FAMILY_HISTORY":"FHx", 'TIME_TO_ONSET':'',
                "MEDICAL_HISTORY":"MHx", "RULE_OUT":"R/O", "LOT":''}
        dictAbr2Fetures = dict((v,k) for k, v in dictFeatureAbr.iteritems())
        
        root = ET.Element("ClinicalNarrativeTemporalAnnotation")
        
        elemText = ET.SubElement(root, "Text")
        elemText.text = CDATA(doctext)
        elemTags = ET.SubElement(root, "TAGS")
        
        ##: Export Feature Annotations
        for eid, ftype, startPos, endPos, ftext, tid, rel in featList:
            if ftype in dictAbr2Fetures:
                ftype = dictAbr2Fetures[ftype]
            elem = ET.SubElement(elemTags, "EVENT", 
                        {"type":ftype, 'id':'E'+str(eid), "start":str(startPos), "end":str(endPos), "text":ftext, "modality":"None", "polarity":"None"})        
        
        ##: Export Timex Annotations
        dictTimexID2Text = {}
        timeRefs = []
        for tid, ftype, startPos, endPos, sdate, ftext, refID, refRel in timexList:
            elem = ET.SubElement(elemTags, "TIMEX3", 
                                 {"type":ftype, 'id':'T'+str(tid), "start":str(startPos), "end":str(endPos), "text":ftext, "val":sdate,"mod":"None"})
            dictTimexID2Text[tid] = ftext
            if refID:
                timeRefs.append((tid, ftext, refID, refRel))

        ##: Export Feature-Time Associations
        tlid = 0
        for eid, ftype, startPos, endPos, ftext, tid, rel in featList:
            if not tid: continue
            if not tid in dictTimexID2Text:  ##: Annnotator's error, assign an nonexisting time to a feature
                    continue
                
            if rel=='':
                rel='OVERLAP'
            elem = ET.SubElement(elemTags, "TLINK", 
                        {'id':'TL'+str(tlid), "fromID":'E'+str(eid), "toID":'T'+str(tid), "fromText":ftext, "toText":dictTimexID2Text[tid], "type":rel})
            tlid += 1
        
        for tid, ftext, refID, refRel in timeRefs:            
            elem = ET.SubElement(elemTags,"TLINK", 
                        {'id':'TL'+str(tlid), "fromID":'T'+str(tid), "toID":'T'+str(refID), "fromText":ftext, "toText":dictTimexID2Text[refID], "type":refRel})
            tlid += 1
    
        tree = ET.ElementTree(root)
        return tree
    
    @staticmethod
    def create_ether_annotation_tree_i2b2(docFeature, doctext):

        root = ET.Element("ClinicalNarrativeTemporalAnnotation")
        
        elemText = ET.SubElement(root, "TEXT")
        elemText.text = CDATA(doctext)
        elemTags = ET.SubElement(root, "TAGS")
        ##: Export Feature Annotations        
        features = docFeature.featureList
        featList = [(feat.getID(), feat.getType(), feat.getStartPos(), feat.getEndPos(), feat.getString()) for feat in features]        
        for eid, ftype, startPos, endPos, ftext in featList:
            elem = ET.SubElement(elemTags, "EVENT", 
                        {"type":ftype, 'id':'E'+str(eid), "start":str(startPos), "end":str(endPos), "text":ftext, "modality":"None", "polarity":"None"})        

        ##: Export Timex Annotations
        timexList = docFeature.timexList
        dictTimexID2Text = {}
        for t in timexList:
            dt = t.getDateTime()
            if dt:
                sdt = dt.isoformat().split('T')[0]
            else:
                sdt = 'None'
            elem = ET.SubElement(elemTags, "TIMEX3", 
                                 {"type":t.getType(), 'id':'T'+str(t.getID()), "start":str(t.getStartPos()), "end":str(t.getEndPos()), 
                                  "text":t.getString(), "val":sdt,"mod":"None"})
            dictTimexID2Text[t.getID()] = t.getString()         
        
        tlid = 0
        for i, feat in enumerate(features):
            tlink = feat.getTlink()
            if not tlink: 
                continue
            timexes = tlink.getTimexes()
            if not timexes: 
                continue
            
            fid = feat.getID()
            if not timexes[0] in timexList:
                continue
            tid = timexes[0].getID()
            
            startPos = feat.getStartPos()
            endPos = feat.getEndPos()
            ftext = feat.getString()
            
            if len(timexes)==1:
                elem = ET.SubElement(elemTags, "TLINK", 
                        {'id':'TL'+str(tlid), "fromID":'E'+str(fid), "toID":'T'+str(tid), "fromText":ftext, "toText":dictTimexID2Text[tid], "type":"OVERLAP"})
                tlid += 1
            elif len(timexes)>1:
                timex_rel = 'AFTER'
                elem = ET.SubElement(elemTags, "TLINK", 
                        {'id':'TL'+str(tlid), "fromID":'E'+str(fid), "toID":'T'+str(tid), "fromText":ftext, "toText":dictTimexID2Text[tid], "type":timex_rel})
                tlid += 1
                
                tid = timexes[1].getID()
                if tid not in dictTimexID2Text: 
                    continue  ##: Come back to check report 678807-1
            
                timex_rel = 'BEFORE'                        
                elem = ET.SubElement(elemTags, "TLINK", 
                        {'id':'TL'+str(tlid), "fromID":'E'+str(fid), "toID":'T'+str(tid), "fromText":ftext, "toText":dictTimexID2Text[tid], "type":timex_rel})
                tlid += 1
                             
        tree = ET.ElementTree(root)
    
        return tree


    @staticmethod
    def create_ether_annotation_tree_uima(docFeature, doctext):

        dictFeature2Names = {"SYMPTOM":"Symptom", "VACCINE":"Vaccine", "DIAGNOSIS": "PrimaryDiagnosis", 
                "SECOND_LEVEL_DIAGNOSIS":"SecondLevelDiagnosis", "CAUSE_OF_DEATH":"CategoryCauseOfDeath", 
                "DRUG":"Drug", "FAMILY_HISTORY":"CategoryFamilyHistory", 
                "MEDICAL_HISTORY":"CategoryMedicalHistory", "RULE_OUT":"RuleOut"}

        TCAS_NS  = "http:///uima/tcas.ecore"
        XMI_NS   =  "http://www.omg.org/XMI"
        CAS_NS  = "http:///uima/cas.ecore"
        VAERS_NS = "http:///gov/hhs/fda/srs/annotation/vaers.ecore"
        NS_MAP = {"tcas":TCAS_NS, "xmi": XMI_NS, "cas":CAS_NS, "vaers":VAERS_NS}

        root = ET.Element(ET.QName(XMI_NS, 'XMI'), {ET.QName(XMI_NS, 'version'):'2.0'}, nsmap=NS_MAP)
        
        sofaID = '6'
        elemCas = ET.SubElement(root, ET.QName(CAS_NS, 'NULL'), {ET.QName(XMI_NS, 'id'):'0'})
        elemtCas = ET.SubElement(root, ET.QName(TCAS_NS, 'DocumentAnnotation'), 
                                 {ET.QName(XMI_NS, 'id'):'1', "sofa":sofaID, "begin":'0', "end":str(len(doctext)), "language":"en"})
        
        elemtSofa = ET.SubElement(root, ET.QName(CAS_NS, 'Sofa'), 
                                 {ET.QName(XMI_NS, 'id'):sofaID, "sofaNum":'1', "sofaID":"_InitialView", "mimeType":'text', "sofaString":doctext})
    
        ##: Export Feature Annotations        
        features = docFeature.featureList
        featList = [(feat.getID(), feat.getType(), feat.getStartPos(), feat.getEndPos(), feat.getString()) for feat in features]        
        for eid, ftype, startPos, endPos, ftext in featList:
            elem = ET.SubElement(root, ET.QName(XMI_NS, 'VaersFeature'), 
                        {"type":ftype, ET.QName(XMI_NS, 'id'):'E'+str(eid), "sofa":sofaID, "begin":str(startPos), "end":str(endPos), "text":ftext})        
        
        ##: Export Timex Annotations
        timexList = docFeature.timexList
        dictTimexID2Text = {}
        for t in timexList:
            dt = t.getDateTime()
            if dt:
                sdt = dt.isoformat().split('T')[0]
            else:
                sdt = ''
            elem = ET.SubElement(root, ET.QName(XMI_NS, 'TemporalFeature'), 
                    {"type":t.getType(), ET.QName(XMI_NS, 'id'):'T'+str(t.getID()), "sofa":sofaID, "begin":str(t.getStartPos()), "end":str(t.getEndPos()), 
                     "text":t.getString(), "date":sdt})            
            dictTimexID2Text[t.getID()] = t.getString()         
        
        tlid = 0
        for i, feat in enumerate(features):
            tlink = feat.getTlink()
            if not tlink: 
                continue
            timexes = tlink.getTimexes()
            if not timexes: 
                continue
            
            fid = feat.getID()
            if not timexes[0] in timexList:
                continue
            tid = timexes[0].getID()
            startPos = feat.getStartPos()
            endPos = feat.getEndPos()
            ftext = feat.getString()
            
            if len(timexes)==1:
                elem = ET.SubElement(root, ET.QName(XMI_NS, 'TemporalRelation'), 
                        {ET.QName(XMI_NS, 'id'):'TL'+str(tlid), "sofa":sofaID, "coreID":'E'+str(fid), "refID":'T'+str(tid), 
                            "coreText":ftext, "refText":dictTimexID2Text[tid], "type":"OVERLAP"})            
                tlid += 1
            elif len(timexes)>1:
                timex_rel = 'AFTER'                
                elem = ET.SubElement(root, ET.QName(XMI_NS, 'TemporalRelation'), 
                        {ET.QName(XMI_NS, 'id'):'TL'+str(tlid), "sofa":sofaID, "coreID":'E'+str(fid), "refID":'T'+str(tid), 
                            "coreText":ftext, "refText":dictTimexID2Text[tid], "type":timex_rel})      
                tlid += 1
                
                tid = timexes[1].getID()
                if tid not in dictTimexID2Text: 
                    continue  ##: Come back to check report 678807-1
                
                timex_rel = 'BEFORE'                          
                elem = ET.SubElement(root, ET.QName(XMI_NS, 'TemporalRelation'), 
                        {ET.QName(XMI_NS, 'id'):'TL'+str(tlid), "sofa":sofaID, "coreID":'E'+str(fid), "refID":'T'+str(tid), 
                            "coreText":ftext, "refText":dictTimexID2Text[tid], "type":timex_rel})                   
                tlid += 1
                             
        tree = ET.ElementTree(root)
    
        return tree
    
    @staticmethod
    def load_events(inputFileName):        
        with open(inputFileName, 'r') as f:
            xmlstring= f.read()   
        if not xmlstring:
            return ([], '')
        
        TCAS_NS  = "http:///uima/tcas.ecore"
        XMI_NS   =  "http://www.omg.org/XMI"
        CAS_NS  = "http:///uima/cas.ecore"
        VAERS_NS = "http:///gov/hhs/fda/srs/annotation/vaers.ecore"
        NS_MAP = {"tcas":TCAS_NS, "xmi": XMI_NS, "cas":CAS_NS, "vaers":VAERS_NS}

        root = ET.fromstring(xmlstring)
        
        elemText = root.find('cas:Sofa', namespaces=NS_MAP)
        text = elemText.get('sofaString')
        
        elements = root.findall('xmi:VaersFeature', namespaces=NS_MAP)
        features = []
        for elem in elements:            
            startPos = int(elem.get('begin'))
            endPos = int(elem.get('end'))
            if 'text' in elem.attrib:
                ftext = elem.get('text')
            else:
                ftext = ''
            ftype = elem.get('type')
            fid = elem.get('{' + XMI_NS + '}id')
            feat = (fid, startPos, endPos, ftext, ftype)
            
            features.append(feat)
        
        return (features, text)

    @staticmethod
    def load_times(inputFileName):        
        with open(inputFileName, 'r') as f:
            xmlstring= f.read()   
        if not xmlstring:
            return ([], '')

        dictTime2Name = {'AGE':'Age', 'WEEKDAY':'Weekday', 'REL':'Relative', 'DUR':'Duration', 
                'FRQ':'Frequency', 'OTHER':'', 'DATE':'Date'}
        dictName2Time = dict((v,k) for k, v in dictTime2Name.iteritems())


        TCAS_NS  = "http:///uima/tcas.ecore"
        XMI_NS   =  "http://www.omg.org/XMI"
        CAS_NS  = "http:///uima/cas.ecore"
        VAERS_NS = "http:///gov/hhs/fda/srs/annotation/vaers.ecore"
        NS_MAP = {"tcas":TCAS_NS, "xmi": XMI_NS, "cas":CAS_NS, "vaers":VAERS_NS}

        root = ET.fromstring(xmlstring)
        
        elemText = root.find('cas:Sofa', namespaces=NS_MAP)
        text = elemText.get('sofaString')
        
        elements = root.findall('xmi:TemporalFeature', namespaces=NS_MAP)
        timexes = []
        for elem in elements:
            ttype = elem.get('type')
            
            startPos = int(elem.get('begin'))
            endPos = int(elem.get('end'))
            tid = elem.get('{' + XMI_NS + '}id')

            ttext = elem.get('text')

            if 'date' in elem.keys():
                tdate = elem.get('date')
            else:
                tdate = ''
            timex = (tid, startPos, endPos, ttext, ttype, tdate)
            timexes.append(timex)
        
#         timexList = timexan.createTimexList(timexes, text)
        
        timexes.sort(key=lambda x:x[1])
        return (timexes, text)
    
    @staticmethod
    def load_tlinks(inputFileName):        
        with open(inputFileName, 'r') as f:
            xmlstring= f.read()   
        if not xmlstring:
            return ([], '')
        
        TCAS_NS  = "http:///uima/tcas.ecore"
        XMI_NS   =  "http://www.omg.org/XMI"
        CAS_NS  = "http:///uima/cas.ecore"
        VAERS_NS = "http:///gov/hhs/fda/srs/annotation/vaers.ecore"
        NS_MAP = {"tcas":TCAS_NS, "xmi": XMI_NS, "cas":CAS_NS, "vaers":VAERS_NS}

        root = ET.fromstring(xmlstring)
        
        elemText = root.find('cas:Sofa', namespaces=NS_MAP)
        text = elemText.get('sofaString')
        
        elements = root.findall('xmi:TemporalRelation', namespaces=NS_MAP)
        tlinks = []
        for elem in elements:
            ftype = elem.get('type')
            if ftype=='':
                ftype = 'OVERLAP'
            tlid = elem.get('{' + XMI_NS + '}id')
            coreText = elem.get('coreText')
            coreID = elem.get('coreID')
            refText = elem.get('refText')
            refID = elem.get('refID')
            coreText = elem.get('coreText')
            
            tlink = (tlid, coreID, coreText, refID, refText, ftype)
            
            tlinks.append(tlink)
        return (tlinks, text)
    
def isfloat(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

def remove_nonascii(s):
    return ''.join([i if ord(i) < 128 else ' ' for i in s])
    
def find_token_positions(tokens, text):
    """Find the position of tokens in the text."""
    
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
                
        ##: try to find "patients" in "...patient's..." 
        if pos < 0:
            tk = tokens[i][:-1]
            while pos<0 and len(tk)>0:
                pos = text[curpt:].find(tk)
                tk = tk[:-1]
            
        if pos < 0:
            locsTokenStarts[i] = curpt
            curpt += 1
        else:
            locsTokenStarts[i] = pos + curpt
            curpt = locsTokenStarts[i] + len(tokens[i])
             
        if not curpt<lenText+1:
            print 'The current token:"' + tokens[i] + '" is out of position!!!'
#             assert curpt<len(text)+1
    
    return locsTokenStarts

##: Find all the terms (multiple words) in the text
def find_terms_in_text(text, terms):
    punctuations = ['."',"```","`","+","*","^","%","@","<",">","'","-",'!', '?', ';', ':', '"', '/', ')','(','.','?','?','?','|','_','~','#','[',']','{','}','$','?']

    maxWid = max([len(t.split()) for t in terms])
    leadingTerms = [t.split()[0] for t in terms]
#     terms.reverse()
    text = text.lower()
    words = word_tokenize(text)
    locsTokenStarts = find_token_positions(words, text)
    numTerms = len(terms)
    num = len(words)
    locs = []
    i = 0
    while i<num:
        if words[i] in punctuations or words[i] not in leadingTerms:
            i += 1
            continue
            
        r = min(num-i, maxWid)
        ws = ' '.join(words[i:i+r])
        while r>0:
            if ws in terms:
                break
            elif ws[-1]=='s' and ws[:-1] in terms:
                break
            else:
                ws = ws[:-len(words[i+r-1])-1]
                r -= 1
            
        if ws:
            locs.append((i, i+r-1))
            i += r
        else:
            i += 1
    
    termLocs = []
    for loc in locs:
        pstart = locsTokenStarts[loc[0]]
        pend = locsTokenStarts[loc[1]]+len(words[loc[1]])-1
        termLocs.append((pstart, pend))
    
    return termLocs

def tokenize_with_reserved_strings(sentence, reserved):
    """Tokenize the sentence while keeping reserved strings unbroken. 
    Return tokens and indices of reserved strings"""
    
    tokens=[]
    posReserved=[]
    pfrom = 0
    for s in reserved:
        pos = sentence[pfrom:].lower().find(s.lower())
        pend = pos + len(s)-1
        posReserved.append((s, pos+pfrom, pend+pfrom))
        pfrom += pend + 1
        
    posReserved.sort(key=lambda t: t[1])
        
    cur = 0
    num = len(posReserved)
    indices = []
    for i in range(num):
        t = posReserved[i]
        toks = nltk.word_tokenize(sentence[cur:t[1]])
        tokens += toks
        indices.append(len(tokens))
        tokens += [t[0]]
        cur = t[2]+1
        
    tokens+= nltk.word_tokenize(sentence[cur:])
        
    return (tokens, indices)

cleanr =re.compile('<.*?>')
def clean_html_tags(htmltext):
    cleantext = re.sub(cleanr,'', htmltext)
    return cleantext

def remove_duplicates_from_list(lst):
    newlist = []
    for elem in lst:
        if elem not in newlist:
            newlist.append(elem)
    return newlist

def strip_with_position(s0):
    """Strip string and return its position"""
    s = s0.strip(' .?-/,:')
    startPos = 0
    if len(s)!=len(s0):
        sl = s0.lstrip(' .?-/,:')
        startPos = len(s0)-len(sl)
    
    return (s, startPos)

def find_neighboring_words(text, locLeft, locRight, numLeft, numRight):
    """This function finds numleft words to the left of locleft, and numright workds to the right of locright in text."""

    punctuations = ['."',"```","`","+","*","^","%","@","<",">","'","-",'!', '?', ';', ':', '"', '/', ')','(','.','?','?','?','|','_','~','#','[',']','{','}','$','?']
    textLeft = text[:locLeft]
    
    wordsLeft = []
    pos = locLeft - 1
    word = ''
    while pos>=0:
        if text[pos]!=' ':
            word = text[pos] + word
        else:
            if word!='':
                wordsLeft.append(word)
            word = ''
            if len(wordsLeft)==numLeft or text[pos-1]=='.':
                break
        pos -= 1
        
    if word!='':  ##: when the beginning is reached 
        wordsLeft.append(word)
        
    wordsLeft.reverse()
    
    wordsRight = []
    nmax = len(text)
    pos = locRight + 1
    word = ''
    while pos < nmax:
        if text[pos] in punctuations:
            wordsRight.append(word)
            break
        elif text[pos]!=' ': 
            word += text[pos]
        else:
            if word!='':
                wordsRight.append(word)
            word = ''
            if len(wordsRight)==numRight or text[pos-1]=='.':
                break
        pos += 1
        
    return (wordsLeft, wordsRight)

def find_sub_text_range(text, sub):
    """This function find the range of sub in the text. Sub is a token set obtained from the full text. """

    text = text.lower()
#    tokens = text.split()
    tks = nltk.word_tokenize(text)
    tokens=[]
    for t in tks:
        tokens+=re.split('-|/', t)
    n = len(tokens)
    #print tokens
    
    ###: find starting locations of all tokens
    charlocs = [-1] * n
    curpt = 0
    for i in range(n):
        pos = text[curpt:].find(tokens[i])
        charlocs[i] = pos + curpt
        curpt = charlocs[i] + len(tokens[i])
        
        
    s = sub.lower()
    words = re.split(', | ', s)
    ranges = []
    leading_word_indices = [i for i, tk in enumerate(tokens) if tk==words[0]]
    if leading_word_indices:
        for leadingIdx in leading_word_indices:
            end = leadingIdx
            toSkip = False
            for w in words[1:]:
                locs = [i for i, tk in enumerate(tokens[end+1:]) if tk==w]
                if locs:
                    loc = locs[0]
                    end += loc+1
                else:
                    toSkip = True
            if not toSkip:      
                ranges.append((charlocs[leadingIdx], charlocs[end]+len(tokens[end])))
            
    minDist = len(text)
    minRange = (0, len(text))
    for r in ranges:
        if r[1]-r[0] < minDist:
            minRange = r
            minDist = r[1] - r[0]
    
    ##: range is the whole text, this is possibly due to the fact that feature is extracted from the cleaned text,
    ##: e.g., non-ascii characters are removed, as well as certain punctuations such as "'" or "-"
    ##: In this case, the feature word is only required to match the beginning part of tokens. 
    if minRange[0]==0 and minRange[1]==len(text):
        minRange = find_sub_text_range_partial_match(text, sub)
    
    return minRange    

def find_sub_text_range_partial_match(text, sub):
    """When range is the whole text, this is possibly due to the fact that feature is extracted from the cleaned text,
       e.g., non-ascii characters are removed, as well as certain punctuations such as "'" or "-"
       In this case, the feature word is only required to match the beginning part of tokens. """
       
    text = text.lower()
#    tokens = text.split()
    tks = nltk.word_tokenize(text)
    tokens=[]
    for t in tks:
        tokens+=re.split('-|/', t)
    n = len(tokens)
    #print tokens
    
    ###: find starting locations of all tokens
    charlocs = [-1] * n
    curpt = 0
    for i in range(n):
        pos = text[curpt:].find(tokens[i])
        charlocs[i] = pos + curpt
        curpt = charlocs[i] + len(tokens[i])
        
        
    s = sub.lower()
    words = re.split(', | ', s)
    ranges = []
    leading_word_indices = [i for i, tk in enumerate(tokens) if tk[:len(words[0])]==words[0]]
    if leading_word_indices:
        for leadingIdx in leading_word_indices:
            end = leadingIdx
            toSkip = False
            for w in words[1:]:
                locs = [i for i, tk in enumerate(tokens[end+1:]) if tk[:len(w)]==w]
                if locs:
                    loc = locs[0]
                    end += loc+1
                else:
                    toSkip = True
            if not toSkip:      
                ranges.append((charlocs[leadingIdx], charlocs[end]+len(tokens[end])))
            
    minDist = len(text)
    minRange = (0, len(text))
    for r in ranges:
        if r[1]-r[0] < minDist:
            minRange = r
            minDist = r[1] - r[0]
        
    return minRange    

class text2num:
    """Tools for conversion from text to number."""
    
    Small = {
            'half':0.5,
            'zero': 0,
            'a': 1,
            'one': 1,
            'two': 2,
            'three': 3,
            'four': 4,
            'five': 5,
            'six': 6,
            'seven': 7,
            'eight': 8,
            'nine': 9,
            'ten': 10,
            'eleven': 11,
            'twelve': 12,
            'thirteen': 13,
            'fourteen': 14,
            'fifteen': 15,
            'sixteen': 16,
            'seventeen': 17,
            'eighteen': 18,
            'nineteen': 19,
            'twenty': 20,
            'thirty': 30,
            'forty': 40,
            'fifty': 50,
            'sixty': 60,
            'seventy': 70,
            'eighty': 80,
            'ninety': 90
            }

    Magnitude = {
            'thousand':     1000,
            'million':      1000000,
            'billion':      1000000000,
            'trillion':     1000000000000,
            'quadrillion':  1000000000000000,
            'quintillion':  1000000000000000000,
            'sextillion':   1000000000000000000000,
            'septillion':   1000000000000000000000000,
            'octillion':    1000000000000000000000000000,
            'nonillion':    1000000000000000000000000000000,
            'decillion':    1000000000000000000000000000000000,
            }
    
    Vague = {
             'same': 0,
             'couple': 2,
             'several': 3,
             'few': 3,
             'dozen': 12,
             'following': 1,
             'next': 1
             }
    
    initialDates = {
                ('year', 'beginning'):1,
                ('year', 'early'):2,
                ('year', 'middle'):6,
                ('year', 'late'):11,
                ('year', 'end'):12,
                ('month', 'beginning'):1,
                ('month', 'early'):5,
                ('month', 'middle'):15,
                ('month', 'late'):25,
                ('month', 'end'):31
                }
    

    @staticmethod
    def getInitialDate(date, val, preString):
        #tokens = preString.split()
        tokens = nltk.word_tokenize(preString)
        tokens.reverse()
        indicator = None
        for tk in tokens:
            if tk in ['beginning', 'early', 'middle', 'late', 'end']:
                indicator = tk
                break
            
        if not indicator:
            return 1  ##: 1 for either year and month
            
        if date == 'year':
            mon = text2num.initialDates.get(('year', indicator), None)
            if mon:
                return mon
            
        if date=='month':
            d = text2num.initialDates.get(('month', indicator), None)
            daysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            return min(d, daysInMonth[val-1])

            
    @staticmethod
    def convert(s):
        s = s.lower()
        s=s.strip()
        words = re.split(r"[\s-]+", s)
        
        if words[0] in ['next', 'following']: 
            if len(words)==1:
                return 1
            else:
                del words[0]

        n = 0
        g = 0
        
        isNumber = True
        for w in words:
            x = text2num.Small.get(w, None)
            if x is not None:
                g += x
            elif w == "hundred":
                g *= 100
            else:
                x = text2num.Magnitude.get(w, None)
                if x is not None:
                    n += g * x
                    g = 0
                else:
                    isNumber = False
                    break
                
        if isNumber:         
            return n + g
        
        vags = [w for w in words if w in text2num.Vague]
        if vags:
            return text2num.Vague.get(vags[0])
        
        for w in words:
            x = text2num.convertOrdinal(w)
            if x:
                x = x-1 ##: e.g., the second day of Vax, means day plus one
                return x
        
        return None
    
    
    @staticmethod
    def convertOrdinal(s):
        ordinal = {
            'first':1,
            '1st': 1,
            'second': 2,
            '2nd': 2,
            'third': 3,
            '3rd': 3,
            'fourth': 4,
            '4th': 4,
            'fifth': 5,
            '5th': 5,
            'six': 6,
            '6th': 6,
            'seventh': 7,
            '7th': 7,
            'eighth': 8,
            '8th': 8,
            'ninth': 9,
            '9th': 9,
            'tenth': 10,
            '10th': 10
            }
        if s in ordinal:
            return ordinal[s]
        else:
            return None

def sentence_tokenize_nn(text):
    
    shortmonth = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"

    sent_spliter = re.compile('(?<!('+shortmonth+')\.)(?<!\w\.\w.)(?<=\.|\?)\)?"?\s+', re.I)
    
    paragraphs= re.split('\s*(\n\s*\n)\s*', text) ##: break down paragraphs 
        
    sents = []
    for ptext in paragraphs:
        sents += sent_spliter.split(ptext)
    
    sents = [s for s in sents if s]
    sentences = []
    nns = []
    count = 0
    for sent in sents:
        if sent=='\n\n':
            nns.append(count)
        else:
            sentences.append(sent)
            count += 1
    
    return (sentences, nns)

def word_tokenize(text):
    sents = sentence_tokenize(text)
    words = []
    for sent in sents:
        words += nltk.word_tokenize(sent)
    return words
    
##: Sentence splitter. Ref: https://regex101.com/r/nG1gU7/27
def sentence_tokenize(text):
    
    sents = nltk.sent_tokenize(text)
    if sents:
        return sents
    
    shortmonth = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"
    word2 = 'hx|dx|mr'
    others = 'mrs'
    
#     sent_spliter = re.compile('(?<!(hx|dx)\.)(?<!(jan|feb|mar|apr)\.)(?<![a-zA-Z]\.[a-zA-Z].)(?<=\.|\?)\)?"?\s+', re.I)
    ##: (?<!('+shortmonth+')\.) : exclude things like "apr."
    ##: (?<![a-zA-Z]\.[a-zA-Z].) : exclude abbr. like "i.e."  

    sent_spliter = re.compile('(?<!dx\.)(?<!hx\.)(?<!('+shortmonth+')\.)(?<![a-zA-Z]\.[a-zA-Z].)(?<=\.|\?)\s+', re.I)
    dquote_spliter = re.compile('(?<=[\.|\?]")\s+', re.I)
    paragraphs= re.split('(\n\n)', text) ##: break down paragraphs 
    
    sents = []
    for ptext in paragraphs:
        sents += sent_spliter.split(ptext)
       
    #sent_spliter = re.compile('(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s')
        #sent_spliter = re.compile('(?<!('+shortmonth+')\.)(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=[\.|\?|!])"?\s', re.I)

    #sent_spliter = re.compile('(?<![jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec]\.)(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|!)"?\s')
    
    sents = [s for s in sents if s]
    
    sentences = []
    for sent in sents:
        sentences += dquote_spliter.split(sent)
    
    return sentences

        
if __name__ == '__main__':
    
    print 'Program finished!!'

    
    