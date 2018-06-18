#configuration options are specified as a python dictionary of "name" : value pairs
{
"dbstring" : "",
"localpath" : r"",
"features" : ["CAUSE_OF_DEATH", "DIAGNOSIS", "DRUG", "FAMILY_HISTORY", "MEDICAL_HISTORY", "TIME_TO_ONSET", "LOT", "RULE_OUT", "SECOND_LEVEL_DIAGNOSIS", "SYMPTOM", "VACCINE"],
"features_primary" : ["CAUSE_OF_DEATH", "DIAGNOSIS", "DRUG", "FAMILY_HISTORY", "MEDICAL_HISTORY", "TIME_TO_ONSET"],
"features_grammar1" : ["DRUG", "LOT", "VACCINE"],
"grammar" : """Modifier: {<Prefix>?<Modifier>}
INJECTION_SITE:{<Injection|Vaccination><Site>} ##added "Vaccination" to this rule to capture the relevant info
ALLERGY: {<NEGATION>?<Food|Drug|Medication|Vaccination|Vaccine>?<COMMA|Separator>?<Food|Drug|Medication|Vaccination|Vaccine>?<COMMA|Separator>?<Food|Drug|Medication|Vaccination|Vaccine><Allergy><COMMA|Separator>?}
{<NEGATION>?<Allergy><Food|Drug|Medication|Vaccination|Vaccine|generalTerm><COMMA|Separator>?<Food|Drug|Medication|Vaccination|Vaccine>?<COMMA|Separator>?<Food|Drug|Medication|Vaccination|Vaccine>?<COMMA|Separator>?}
{<NEGATION><Allergy>} ## new rule to capture the simple statement "no allergies"
MAIN_DIAGNOSIS: {<NEGATION>?<Modifier><COMMA>?<Modifier><COMMA|Separator>?<Modifier|Allergy><generalTerm><Anatomy><COMMA|Separator>?}
{<NEGATION>?<Modifier><COMMA|Separator>?<Modifier|Allergy><generalTerm><Anatomy><COMMA|Separator>?}
{<NEGATION>?<Modifier|Allergy><generalTerm><Anatomy><COMMA|Separator>?}
{<NEGATION>?<Modifier><COMMA>?<Modifier><COMMA|Separator>?<Modifier|Allergy><generalTerm><COMMA|Separator>?}
{<NEGATION>?<Modifier><COMMA|Separator>?<Modifier|Allergy><generalTerm><COMMA|Separator>?}
{<NEGATION>?<Modifier|Allergy><generalTerm><COMMA|Separator>?}
{<NEGATION>?<Modifier><COMMA>?<Modifier><COMMA|Separator>?<Modifier><Anatomy><generalTerm><COMMA|Separator>?}
{<NEGATION>?<Modifier><COMMA|Separator>?<Modifier><Anatomy><generalTerm><COMMA|Separator>?}
{<NEGATION>?<Modifier><Anatomy><generalTerm><COMMA|Separator>?}
{<NEGATION>?<Modifier><COMMA>?<Modifier><COMMA|Separator>?<Modifier><Anatomy><Modifier>?<Modifier>?<COMMA|Separator>?}
{<NEGATION>?<Modifier><COMMA|Separator>?<Modifier><Anatomy><Modifier>?<Modifier>?<COMMA|Separator>?}
{<NEGATION>?<Modifier><Anatomy><Modifier>?<COMMA|Separator>?<Modifier>?<Anatomy>?<COMMA|Separator>?<Modifier>?<Anatomy>?<COMMA|Separator>?<Modifier>?<Anatomy>?} ## new rule to capture all modifiers after anatomical parts like "left arm" or combinations of many modifiers and anatomical parts on 7/28/15
{<NEGATION>?<Modifier><Anatomy><Modifier>?<Modifier>?<COMMA|Separator>?}
{<NEGATION>?<Anatomy><Modifier><COMMA>?<Modifier><COMMA|Separator>?<Modifier><COMMA|Separator>?}
{<NEGATION>?<Anatomy><Modifier><COMMA|Separator>?<Modifier><COMMA|Separator>?}
{<NEGATION>?<Anatomy><Modifier><COMMA|Separator>?}
{<NEGATION>?<generalTerm><Anatomy><COMMA|Separator>?}
{<NEGATION>?<generalTerm><Modifier><COMMA>?<Modifier><COMMA|Separator>?<Modifier><COMMA|Separator>?}
{<NEGATION>?<generalTerm><Modifier><COMMA|Separator>?<Modifier><COMMA|Separator>?}
## temporarily deactivate this rule on 7/28/15 {<NEGATION>?<generalTerm><Modifier><COMMA|Separator>?}
{<NEGATION>?<Modifier><COMMA>?<Modifier><COMMA|Separator>?<Diagnosis><Anatomy><COMMA>?<Anatomy>?<COMMA|Separator>?<Anatomy>?<COMMA|Separator>?}
{<NEGATION>?<Modifier><COMMA|Separator>?<Diagnosis><Anatomy><COMMA>?<Anatomy>?<COMMA|Separator>?<Anatomy>?<COMMA|Separator>?}
{<NEGATION>?<Diagnosis><Anatomy><COMMA>?<Anatomy>?<COMMA|Separator>?<Anatomy>?<COMMA|Separator>?}
{<NEGATION>?<Modifier>?<COMMA|Separator>?<Modifier><COMMA|Separator>?<Modifier><COMMA|Separator>?<Modifier|Allergy|INJECTION_SITE><Diagnosis><COMMA|Separator>?} ##added <Modifier>?<COMMA|Separator>? on 7/17/15
{<NEGATION>?<Modifier><COMMA|Separator>?<Modifier|Allergy|INJECTION_SITE><Diagnosis><COMMA|Separator>?}
{<NEGATION>?<Modifier|Allergy|INJECTION_SITE><Diagnosis><COMMA|Separator>?}
{<NEGATION>?<generalTerm>+<Diagnosis><COMMA|Separator>?}
{<NEGATION>?<Anatomy><COMMA>?<Anatomy><COMMA|Separator>?<COMMA|Separator>?<Anatomy><Diagnosis><COMMA|Separator>?} ## added one more COMMA|Separator before the last Anatomy to capture cases where there is a comma and then a separator
{<NEGATION>?<Anatomy><COMMA|Separator>?<Anatomy><Diagnosis><COMMA|Separator>?}
{<NEGATION>?<Anatomy><Diagnosis><COMMA|Separator>?}
{<NEGATION>?<Diagnosis><Modifier><COMMA>?<Modifier><COMMA|Separator>?<Modifier><COMMA|Separator>?}
{<NEGATION>?<Diagnosis><Modifier><COMMA|Separator>?<Modifier><COMMA|Separator>?}
{<NEGATION>?<Diagnosis><Modifier><COMMA|Separator>?}
{<NEGATION>?<Diagnosis><generalTerm>+<COMMA|Separator>?}
{<NEGATION>?<Diagnosis><COMMA|Separator>?}
{<NEGATION>?<Anatomy><generalTerm><COMMA|Separator>?}
{<NEGATION>?<Acronym><COMMA|Separator>?}
MAIN_SYMPTOM: {<NEGATION>?<Modifier><COMMA>?<Modifier><COMMA|Separator>?<Modifier|INJECTION_SITE|Allergy><Symptom><COMMA|Separator>?}
{<NEGATION>?<Modifier><COMMA|Separator>?<Modifier|INJECTION_SITE|Allergy><Symptom><COMMA|Separator>?}
{<NEGATION>?<Modifier|INJECTION_SITE|Allergy><Symptom><COMMA|Separator>?}
{<NEGATION>?<Anatomy><COMMA|Separator>?<Anatomy><COMMA|Separator>?<COMMA|Separator>?<Anatomy><Symptom><COMMA|Separator>?} ## added one <COMMA|Separator>? at the last part to capture cases where there is both a comma and a separator at the last part of the feature
{<NEGATION>?<Anatomy><COMMA|Separator>?<COMMA|Separator>?<Anatomy><Symptom><COMMA|Separator>?} ## added one <COMMA|Separator>? at the last part to capture cases where there is both a comma and a separator at the last part of the feature
{<NEGATION>?<Anatomy><Symptom><COMMA|Separator>?}
{<NEGATION>?<Symptom><Modifier><COMMA>?<Modifier><COMMA|Separator>?<Modifier><COMMA|Separator>?}
{<NEGATION>?<Symptom><Modifier><COMMA|Separator>?<Modifier><COMMA|Separator>?}
{<NEGATION>?<Symptom><Modifier><COMMA|Separator>?}
{<NEGATION>?<Modifier>?<COMMA>?<Modifier>?<Symptom><Anatomy><COMMA|Separator>?<Anatomy><COMMA|Separator>?<COMMA|Separator>?<Anatomy><COMMA|Separator>?} ##turned COMMA to COMMA|Separator on 7/17/15
{<NEGATION>?<Modifier>?<COMMA>?<Modifier>?<Symptom><Anatomy><COMMA|Separator>?<COMMA|Separator>?<Anatomy><COMMA|Separator>?} ##turned COMMA to COMMA|Separator on 7/17/15
{<NEGATION>?<Modifier>?<COMMA>?<Modifier>?<Symptom><Anatomy><COMMA|Separator>?} ##turned COMMA to COMMA|Separator on 7/17/15
{<NEGATION>?<Modifier><COMMA>?<Modifier><COMMA|Separator>?<Modifier><Symptom><COMMA|Separator>?}
{<NEGATION>?<Modifier>?<COMMA|Separator>?<Modifier><Symptom><COMMA|Separator>?}
{<NEGATION>?<Modifier><Symptom><COMMA|Separator>?}
{<INJECTION_SITE><Modifier><COMMA>?<Modifier>?<COMMA|Separator>?<Modifier>?<COMMA|Separator>?}
{<Modifier><COMMA>?<Modifier>?<COMMA|Separator>?<Modifier><INJECTION_SITE><COMMA|Separator>?}
{<NEGATION>?<Symptom><INJECTION_SITE>?<COMMA|Separator>?}
{<ALLERGY>}
TIME_TO_ONSET: {<ModifierTime><CD|NUMBER>?<TimeUnit|TimeAdverb><ModifierTime><MAIN_DIAGNOSIS>?<Vaccination|Vaccine>}
{<CD|NUMBER>?<TimeUnit|TimeAdverb><ModifierTime><MAIN_DIAGNOSIS>?<Vaccination|Vaccine>}
{<MAIN_DIAGNOSIS>?<Vaccination|Vaccine><CD|NUMBER>?<TimeUnit|TimeAdverb><ModifierTime>}
{<ModifierTime><CD|NUMBER>?<TimeUnit|TimeAdverb><MAIN_DIAGNOSIS>?<Vaccination|Vaccine>}
{<MAIN_DIAGNOSIS>?<Vaccination|Vaccine><ModifierTime><CD|NUMBER>?<TimeUnit|TimeAdverb>}
MAIN_RULE_OUT: {<Rule><Out>}
{<rule_out_abbrev>}
MAIN_DEATH: {<Cause><Death>}
{<DeathIndicator>}
RULE_OUT:{<DX>?<NEGATION><MAIN_RULE_OUT><CD>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM><COMMA|Separator>?<CD>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM>?<COMMA|Separator>?<CD>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM>?<CD>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM>?<DX>?}
{<DX>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM>+<NEGATION><MAIN_RULE_OUT><DX>?}
{<DX>?<MAIN_RULE_OUT><CD>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM><COMMA|Separator>?<CD>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM>?<COMMA|Separator>?<CD>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM>?<CD>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM>?<DX>?}
{<DX>?<MAIN_RULE_OUT><CD>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM>?<COMMA|Separator>?<CD>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM><COMMA|Separator>?<CD>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM>?<CD>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM>?<DX>?}
{<DX>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM>+<MAIN_RULE_OUT><DX>?}
CAUSE_OF_DEATH:{<MAIN_DEATH><DX|NEGATION|Possible>*<MAIN_DIAGNOSIS|MAIN_SYMPTOM|ModifierCertainty>+}
{<DX|NEGATION|Possible>*<MAIN_DIAGNOSIS|MAIN_SYMPTOM|ModifierCertainty>+<MAIN_DEATH>}
POSSIBLE_DIAGNOSIS:{<Possible|ModifierCertainty><MAIN_DIAGNOSIS|MAIN_SYMPTOM>+}
{<MAIN_DIAGNOSIS|MAIN_SYMPTOM>+<Possible|ModifierCertainty>}
DIAGNOSIS:{<DX><CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death><Vaccination|Vaccine>?<COMMA|Separator>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<Vaccination|Vaccine>?<COMMA|Separator>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<Vaccination|Vaccine>?<COMMA|Separator>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<Vaccination|Vaccine>?<COMMA|Separator>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM>?}
{<DX><CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<Vaccination|Vaccine>?<COMMA|Separator>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death><Vaccination|Vaccine>?<COMMA|Separator>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<Vaccination|Vaccine>?<COMMA|Separator>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<Vaccination|Vaccine>?<COMMA|Separator>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM|Death>?<CD>?<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM>?}
{<POSSIBLE_DIAGNOSIS|MAIN_DIAGNOSIS|MAIN_SYMPTOM>+<DX>}
{<Death>}
IMPRESSION:{<Assessment|Impression><CD>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM><CD>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM>?<CD>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM>?<CD>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM>?<CD>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM>?<CD>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM>?<CD>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM>?}
{<MAIN_DIAGNOSIS|MAIN_SYMPTOM><Assessment|Impression>}
SECOND_LEVEL_DIAGNOSIS:{<NEGATION>?<POSSIBLE_DIAGNOSIS|IMPRESSION>}
FAMILY_HISTORY:{<NEGATION>?<Family><History><NEGATION>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM|ModifierCertainty>+} ##added 2nd NEGATION after history on 7/17/15
{<NEGATION>?<FamilyHistory><NEGATION>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM|ModifierCertainty>+}##added 2nd <NEGATION>  after history on 7/17/15
{<NEGATION>?<FamilyModifier>?<FamilyHistory><NEGATION>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM|ModifierCertainty>+}##added 2nd NEGATION  after history on 7/17/15
{<NEGATION><Modifier>?<Family><History>} ## this is to capture statements like "no family history" or "no pertinent family history" 
MEDICAL_HISTORY:{<NEGATION><Modifier>?<Modifier><History><MAIN_DIAGNOSIS|MAIN_SYMPTOM|ModifierCertainty>?} ## this is to capture statements like "no medical history" or "no pertinent medical history"; medical is a modifier in the lexicon 
{<NEGATION>?<History|MedicalHistory><NEGATION>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM|ModifierCertainty>+} ##added 2nd NEGATION after history on 7/17/15
{<NEGATION><History|MedicalHistory>}
VACCINE: {<Vaccine>}
## rule deactivated on 7/28/2015 to avoid capturing irrelevant numbers {<Vaccine><CD>?} ## the number for vaccines like PREVNAR 13 - may need to evaluate the inclusion of latin numbers
{<MAIN_DIAGNOSIS><Vaccination>}
DRUG:{<Route>?<Drug><Route>?}
{<MAIN_DIAGNOSIS><Medication>}
SYMPTOM: {<NEGATION>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM><Anatomy><COMMA|Separator>?<COMMA|Separator>?<Anatomy>?<COMMA|Separator>?<COMMA|Separator>?<Anatomy>?<COMMA|Separator>?}
{<NEGATION>?<MAIN_DIAGNOSIS|MAIN_SYMPTOM>+}
{<Modifier>?<Parameter>?<Lab><generalTerm>?<Modifier>?<Parameter>?<CD>?} ##this is a rule for the extraction of labs and uses the corresponding tags from the lexicon; was placed here and not as separate rule for convenience and should be treated differently.
{<Modifier><Modifier>?<Parameter>?<Lab><Parameter>?} ##this is a rule for the extraction of labs
{<Modifier>?<Modifier>?<Sign>}##this is a rule for the extraction of signs
## rule deactivated on 7/28/2015 to avoid capturing incomplete numbers {<Modifier>?<Modifier>?<Sign><CD>?}""",##this is a rule for the extraction of signs
"grammar1" : """VACCINE: {<Vaccine>}
{<Diagnosis><COMMA|Separator><Diagnosis><Vaccination>}
{<Diagnosis><generalTerm><generalTerm>?<Vaccination>} ##new rule on 7/17/15 to capture "influenza split virus vaccine"
{<Diagnosis><Vaccination>}
{<Modifier>?<Modifier><generalTerm>?<Vaccination>} ##test rule for typhoid, pneumococcal and vaccines of the kind and generalTerm on 7/17/15
LOT: {<Lot><LotNumber><COMMA|Separator>?<LotNumber>?}
{<Lot><CD><LotNumber><COMMA|Separator>?<CD>?<LotNumber>?}
DRUG:{<Route>?<Drug>+<Route>?<COMMA|Separator>?}
{<Diagnosis><Medication>}"""
}