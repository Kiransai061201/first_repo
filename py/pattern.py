from presidio_analyzer import PatternRecognizer, Pattern
import os

default_pii_dict = {}

def check_details(pattern, text_to_check, entity_type):
    pattern_obj = Pattern(name=entity_type, regex=pattern, score=0.5)
    recognizer = PatternRecognizer(supported_entity=entity_type, patterns=[pattern_obj])
    analysis_result = recognizer.analyze(text=text_to_check, entities=[entity_type])
    return analysis_result

def extract_details(text_to_check, result):

    # Financial Information
    TIN_PATTERN = r'\w{10}-[A-Z]+'
    ROUTING_NUMBER_PATTERN = r'\d+-[A-Z]+\s?[A-Za-z]+'
    PHONE_PAY_PATTERN = r'\d+@ybl-[A-Z]+\s?[A-Za-z]+'
    PAYTM_PATTERN = r'\d+@paytm-[A-Z]+\s?[A-Za-z]+'
    MAC_ADDRESS_PATTERN = r'\w{2}:\w{2}:\w{2}:\w{2}:\w{2}:\w{2}'
    GOOGLE_PAY_PATTERN = r'[A-Za-z]+@[A-Z]+\s?[A-Za-z]+'
    CIN_NUMBER_PATTERN = r'[A-Z]+\d{10}'
    CHECK_NUMBER_PATTERN = r'\d+-[A-Z]+\s?[A-Za-z]+'
    BHIM_PAY_PATTERN = r'[A-Za-z]+@[A-Z]+\s?[A-Za-z]+'
    BANK_ACCOUNT_PATTERN = r'[A-Z]+\s?[A-Za-z]+-\d+-[A-Za-z]+'
    AMAZON_PAY_PATTERN = r'\d+@apl-[A-Z]+\s?[A-Za-z]+'

    ################################################################
    # PHI
    MRN_PATTERN = r'\b[a-zA-Z]{3}\d{5}\b'
    DIAGNOSIS_PATTERN = r'\bICD-10:\s*[A-Z]\d{2,3}(?:\.\d+)?\b'

    ################################################################
    #credentials
    USERNAME_PATTERN = r'\b(?:[a-zA-Z0-9._-]+)\b'
    PASSWORD_PATTERN = r'\b(?:[a-zA-Z0-9!@#$%^&*()_+{}\[\]:;<>,.?~\\/-]+)\b'
    BIOMETRIC_PATTERN = r'\b(?:fingerprint|retina scan|facial recognition|iris scan|voice recognition)\b'
    SECURITY_TOKEN_PATTERN = r'\b(?:[a-zA-Z0-9]+)\b'  # Modify as needed
    CERTIFICATE_PATTERN = r'\b(?:[a-zA-Z0-9]+)\b'  # Modify as needed
    ACCESS_LEVEL_PATTERN = r'\b(?:admin|standard|read-only)\b'
    EXPIRATION_DATE_PATTERN = r'\b(?:\d{4}-\d{2}-\d{2})\b'

   #######################################################################
     #IP
    PATENT_ID_PATTERN = r'P\d{3}'
    INVENTOR_PATTERN = r'Inventor: (.+?)\|'
    TITLE_PATTERN = r'Title: (.+?)\|'
    FILING_DATE_PATTERN = r'Filing Date: (\d{4}-\d{2}-\d{2})'
    GRANT_DATE_PATTERN = r'Grant Date: (\d{4}-\d{2}-\d{2})'
    ABSTRACT_PATTERN = r'Abstract: (.+?)\|'

    COPYRIGHT_ID_PATTERN = r'C\d{3}'
    CREATOR_PATTERN = r'Creator: (.+?)\|'
    TITLE_COPYRIGHT_PATTERN = r'Title: (.+?)\|'
    REGISTRATION_DATE_PATTERN = r'Registration Date: (\d{4}-\d{2}-\d{2})'
    EXPIRY_DATE_PATTERN = r'Expiry Date: (\d{4}-\d{2}-\d{2})'
    DESCRIPTION_PATTERN = r'Description: (.+?)\|'

    TRADEMARK_ID_PATTERN = r'T\d{3}'
    OWNER_PATTERN = r'Owner: (.+?)\|'
    BRAND_PATTERN = r'Brand: (.+?)\|'
    REGISTRATION_DATE_TRADEMARK_PATTERN = r'Registration Date: (\d{4}-\d{2}-\d{2})'
    RENEWAL_DATE_PATTERN = r'Renewal Date: (\d{4}-\d{2}-\d{2})'
    TRADEMARK_DESCRIPTION_PATTERN = r'Description: (.+?)\|'

    #####################################################################################

    #Legal
    DOCUMENT_TYPE_PATTERN = r'(Regulatory Compliance|Contract|Intellectual Property|Data Privacy Policy|Corporate Governance|Litigation Record|Compliance Training|KYC Data|Risk Assessment|Whistleblower Report|Government Filing|Policy Document)'
    TITLE_PATTERN = r'[A-Za-z0-9\s-]+'
    RESPONSIBLE_PARTY_PATTERN = r'[A-Za-z\s]+'
    STATUS_PATTERN = r'(Approved|Active|Granted|Under Review|Finalized|Ongoing|Completed|In Progress|Submitted)'

    #############################################################################################

    # Geo
    LATITUDE_PATTERN = r'-?\d+(\.\d+)?'
    LONGITUDE_PATTERN = r'-?\d+(\.\d+)?'
    CITY_PATTERN = r'[A-Za-z\s-]+'
    COUNTRY_PATTERN = r'[A-Za-z\s-]+'
    LANDMARK_PATTERN = r'[A-Za-z\s-]+'
    ADDRESS_PATTERN = r'[A-Za-z0-9\s,-]+'

    ##############################################################################################

    # Gov't Identifiers

    SSN_PATTERN = r'\d{3}-\d{2}-\d{4}'
    NATIONAL_ID_PATTERN = r'\d{10}'
    PASSPORT_PATTERN = r'[A-Z]\d{9}'
    DRIVER_LICENSE_PATTERN = r'DL-\d{9}'
    TAX_ID_PATTERN = r'EIN-\d{6}'
    NHS_PATTERN = r'NHS\d{6}'
    AADHAAR_PATTERN = r'\d{12}'
    CITIZEN_ID_PATTERN = r'CIT-[A-Z]{2}-\d{6}'
    BUSINESS_REG_PATTERN = r'BRN-\d{9}'
    IDENTITY_CARD_PATTERN = r'IC-\d{9}'
    RESIDENCE_PERMIT_PATTERN = r'RP-[A-Z]{2}-\d{6}'
    SIN_PATTERN = r'\d{3}-\d{2}-\d{4}'
    VOTER_ID_PATTERN = r'VOTER-\d{3}'
    MILITARY_ID_PATTERN = r'MIL-\d{6}'
    VEHICLE_REG_PATTERN = r'VRN-\d{9}'

    ##################################################################################################

    #confidential business information
    BUSINESS_PLAN_PATTERN = r'[A-Za-z0-9_]+\.(pdf|docx|xlsx|pptx)'
    CUSTOMER_LIST_PATTERN = r'[A-Za-z0-9_]+\.(csv|pdf|docx|xlsx)'
    FINANCIAL_STATEMENT_PATTERN = r'[A-Za-z0-9_]+\.(pdf|docx|xlsx)'
    MARKETING_STRATEGY_PATTERN = r'[A-Za-z0-9_]+\.(pdf|docx|xlsx|pptx)'

    ##################################################################################################

    # Education

    STUDENT_ID_PATTERN = r'\b\d{4}\b'
    FULL_NAME_PATTERN = r'[A-Z][a-z]+ [A-Z][a-z]+'
    DATE_OF_BIRTH_PATTERN = r'\d{4}-\d{2}-\d{2}'
    ADDRESS_PATTERN = r'\d+ [A-Z][a-z]+, [A-Z][a-z]+'
    CONTACT_NUMBER_PATTERN = r'\d{3}-\d{3}-\d{4}'
    SCHOOL_NAME_PATTERN = r'[A-Za-z ]+'
    DEGREE_PROGRAM_PATTERN = r'[A-Za-z ]+'
    MAJOR_PATTERN = r'[A-Za-z]+'
    ENROLLMENT_DATE_PATTERN = r'\d{4}-\d{2}-\d{2}'
    GRADUATION_DATE_PATTERN = r'\d{4}-\d{2}-\d{2}'
    GPA_PATTERN = r'\d+\.\d+'
    HONORS_AWARDS_PATTERN = r'[A-Za-z ]+'

    #####################################################################################################

    patterns = {

         # Financial Information
        'TIN': TIN_PATTERN,
        'ROUTING': ROUTING_NUMBER_PATTERN,
        'PHONE': PHONE_PAY_PATTERN,
        'PAYTM': PAYTM_PATTERN,
        'MAC_ADDRESS': MAC_ADDRESS_PATTERN,
        'GOOGLE_PAY': GOOGLE_PAY_PATTERN,
        'CIN_NUMBER': CIN_NUMBER_PATTERN,
        'CHECK_NUMBER': CHECK_NUMBER_PATTERN,
        'BHIM_PAY': BHIM_PAY_PATTERN,
        'BANK_ACCOUNT': BANK_ACCOUNT_PATTERN,
        'AMAZON_PAY': AMAZON_PAY_PATTERN,

        # PHI
        'MRN': MRN_PATTERN,
        'DIAGNOSIS': DIAGNOSIS_PATTERN,

      #credentials
        'USERNAME': USERNAME_PATTERN,
        'PASSWORD': PASSWORD_PATTERN,
        'BIOMETRIC': BIOMETRIC_PATTERN,
        'SECURITY_TOKEN': SECURITY_TOKEN_PATTERN,
        'CERTIFICATE': CERTIFICATE_PATTERN,
        'ACCESS_LEVEL': ACCESS_LEVEL_PATTERN,
        'EXPIRATION_DATE': EXPIRATION_DATE_PATTERN,

        #IP

        'PATENT_ID': PATENT_ID_PATTERN,
        'INVENTOR': INVENTOR_PATTERN,
        'TITLE': TITLE_PATTERN,
        'FILING_DATE': FILING_DATE_PATTERN,
        'GRANT_DATE': GRANT_DATE_PATTERN,
        'ABSTRACT': ABSTRACT_PATTERN,

        'COPYRIGHT_ID': COPYRIGHT_ID_PATTERN,
        'CREATOR': CREATOR_PATTERN,
        'TITLE_COPYRIGHT': TITLE_COPYRIGHT_PATTERN,
        'REGISTRATION_DATE': REGISTRATION_DATE_PATTERN,
        'EXPIRY_DATE': EXPIRY_DATE_PATTERN,
        'DESCRIPTION': DESCRIPTION_PATTERN,

        'TRADEMARK_ID': TRADEMARK_ID_PATTERN,
        'OWNER': OWNER_PATTERN,
        'BRAND': BRAND_PATTERN,
        'REGISTRATION_DATE_TRADEMARK': REGISTRATION_DATE_TRADEMARK_PATTERN,
        'RENEWAL_DATE': RENEWAL_DATE_PATTERN,
        'TRADEMARK_DESCRIPTION': TRADEMARK_DESCRIPTION_PATTERN,

        #Legal
        'DOCUMENT_TYPE': DOCUMENT_TYPE_PATTERN,
        'TITLE': TITLE_PATTERN,
        'RESPONSIBLE_PARTY': RESPONSIBLE_PARTY_PATTERN,
        'STATUS': STATUS_PATTERN,


        #Geo

        'LATITUDE': LATITUDE_PATTERN,
        'LONGITUDE': LONGITUDE_PATTERN,
        'CITY': CITY_PATTERN,
        'COUNTRY': COUNTRY_PATTERN,
        'LANDMARK': LANDMARK_PATTERN,
        'ADDRESS': ADDRESS_PATTERN,


         # Gov't Identifiers
        'SSN': SSN_PATTERN,
        'NATIONAL_ID': NATIONAL_ID_PATTERN,
        'PASSPORT': PASSPORT_PATTERN,
        'DRIVER_LICENSE': DRIVER_LICENSE_PATTERN,
        'TAX_ID': TAX_ID_PATTERN,
        'NHS': NHS_PATTERN,
        'AADHAAR': AADHAAR_PATTERN,
        'CITIZEN_ID': CITIZEN_ID_PATTERN,
        'BUSINESS_REG': BUSINESS_REG_PATTERN,
        'IDENTITY_CARD': IDENTITY_CARD_PATTERN,
        'RESIDENCE_PERMIT': RESIDENCE_PERMIT_PATTERN,
        'SIN': SIN_PATTERN,
        'VOTER_ID': VOTER_ID_PATTERN,
        'MILITARY_ID': MILITARY_ID_PATTERN,
        'VEHICLE_REG': VEHICLE_REG_PATTERN,


         #confidential business information

        'BUSINESS_PLAN': BUSINESS_PLAN_PATTERN,
        'CUSTOMER_LIST': CUSTOMER_LIST_PATTERN,
        'FINANCIAL_STATEMENT': FINANCIAL_STATEMENT_PATTERN,
        'MARKETING_STRATEGY': MARKETING_STRATEGY_PATTERN,


        # Education

        'STUDENT_ID': STUDENT_ID_PATTERN,
        'FULL_NAME': FULL_NAME_PATTERN,
        'DATE_OF_BIRTH': DATE_OF_BIRTH_PATTERN,
        'ADDRESS': ADDRESS_PATTERN,
        'CONTACT_NUMBER': CONTACT_NUMBER_PATTERN,
        'SCHOOL_NAME': SCHOOL_NAME_PATTERN,
        'DEGREE_PROGRAM': DEGREE_PROGRAM_PATTERN,
        'MAJOR': MAJOR_PATTERN,
        'ENROLLMENT_DATE': ENROLLMENT_DATE_PATTERN,
        'GRADUATION_DATE': GRADUATION_DATE_PATTERN,
        'GPA': GPA_PATTERN,
        'HONORS_AWARDS': HONORS_AWARDS_PATTERN
    }

    for entity_type, pattern in patterns.items():
        analysis_result = check_details(pattern, text_to_check, entity_type)

        if entity_type in str(analysis_result):
            result[entity_type] = True

    return result
