import spacy
from spacy.pipeline import EntityRuler
def setup_entity_ruler():
    nlp = spacy.load("en_core_web_lg")
    ruler = EntityRuler(nlp, overwrite_ents=True)
    patterns = [
    {"label": "PERSON", "pattern": [
        {"TEXT": {"REGEX": "^(Dr|Mr|Mrs|Ms|Prof)\.?"}, "OP": "?"},  # Optional title
        {"IS_ALPHA": True, "IS_TITLE": True},  # First name
        {"IS_ALPHA": True, "IS_TITLE": True, "OP": "?"}  # Optional last name
    ]},
    # GOVERNMENT IDENTIFIERS
    {"label": "US_SSN", "pattern": [{"TEXT": {"REGEX": "^(\d{3}-?\d{2}-?\d{4}|XXX-XX-XXXX)$"}}]},
    {"label": "PASSPORT_NUMBER", "pattern": [{"TEXT": {"REGEX": "[A-Z0-9<]{6,20}"}}]},
    {"label": "DRIVER_LICENSE", "pattern": [{"TEXT": {"REGEX": "DL-\d{9}"}}]},
    {"label": "TAX_ID", "pattern": [{"TEXT": {"REGEX": "EIN-\d{6}"}}]},
    {"label": "NHS", "pattern": [{"TEXT": {"REGEX": "NHS\d{6}"}}]},
    {"label": "CITIZEN_ID", "pattern": [{"TEXT": {"REGEX": "CIT-[A-Z]{2}-\d{6}"}}]},
    {"label": "BUSINESS_REG", "pattern": [{"TEXT": {"REGEX": "BRN-\d{9}"}}]},
    {"label": "IDENTITY_CARD", "pattern": [{"TEXT": {"REGEX": "IC-\d{9}"}}]},
    {"label": "RESIDENCE_PERMIT", "pattern": [{"TEXT": {"REGEX": "RP-[A-Z]{2}-\d{6}"}}]},
    # Personal information
    {"label": "EMAIL_ADDRESS", "pattern": [{"TEXT": {"REGEX": "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"}}]},
    {"label": "PHONE_NUMBER", "pattern": [{"TEXT": {"REGEX": "(\+?\d{1,3}[\s-]?)?(\(?\d{1,3}\)?[\s-]?)(\d{3}[\s-]\d{4})"}}]},
    # Financial information
    {"label": "CREDIT_CARD", "pattern": [{"TEXT": {"REGEX": "^(?:4[0-9]{12}(?:[0-9]{3})?|[25][1-7][0-9]{14}|6(?:011|5[0-9][0-9])[0-9]{12}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|(?:2131|1800|35\d{3})\d{11})$"}}]},
    # LEGAL
    {"label": "DOCUMENT_TYPE", "pattern": [{"TEXT": {"REGEX": "(Regulatory Compliance|Contract|Intellectual Property|Data Privacy Policy|Corporate Governance|Litigation Record|Compliance Training|KYC Data|Risk Assessment|Whistleblower Report|Government Filing|Policy Document)"}}]},
    {"label": "STATUS", "pattern": [{"TEXT": {"REGEX": "(Approved|Active|Granted|Under Review|Finalized|Ongoing|Completed|In Progress|Submitted)"}}]},
    # IP
    {"label": "PATENT_ID", "pattern": [{"TEXT": {"REGEX": "P\d{3}"}}]},
    {"label": "INVENTOR", "pattern": [{"TEXT": {"REGEX": "Inventor: (.+?)\|"}}]},
    {"label": "TITLE", "pattern": [{"TEXT": {"REGEX": "Title: (.+?)\|"}}]},
    {"label": "FILING_DATE", "pattern": [{"TEXT": {"REGEX": "Filing Date: (\d{4}-\d{2}-\d{2})"}}]},
    {"label": "GRANT_DATE", "pattern": [{"TEXT": {"REGEX": "Grant Date: (\d{4}-\d{2}-\d{2})"}}]},
    {"label": "ABSTRACT_PATTERN", "pattern": [{"TEXT": {"REGEX": "Abstract: (.+?)\|"}}]},
    {"label": "COPYRIGHT_ID_PATTERN", "pattern": [{"TEXT": {"REGEX": "C\d{3}"}}]},
    {"label": "CREATOR_PATTERN", "pattern": [{"TEXT": {"REGEX": "Creator: (.+?)\|"}}]},
    {"label": "REGISTRATION_DATE_PATTERN", "pattern": [{"TEXT": {"REGEX": "Registration Date: (\d{4}-\d{2}-\d{2})"}}]},
    {"label": "EXPIRY_DATE_PATTERN", "pattern": [{"TEXT": {"REGEX": "Expiry Date: (\d{4}-\d{2}-\d{2})"}}]},
    {"label": "DESCRIPTION_PATTERN", "pattern": [{"TEXT": {"REGEX": "Description: (.+?)\|"}}]},
    {"label": "TRADEMARK_ID_PATTERN", "pattern": [{"TEXT": {"REGEX": "T\d{3}"}}]},
    {"label": "OWNER_PATTERN", "pattern": [{"TEXT": {"REGEX": "Owner: (.+?)\|"}}]},
    {"label": "BRAND_PATTERN", "pattern": [{"TEXT": {"REGEX": "Brand: (.+?)\|"}}]},
    {"label": "RENEWAL_DATE_PATTERN", "pattern": [{"TEXT": {"REGEX": "Renewal Date: (\d{4}-\d{2}-\d{2})"}}]},
]
    ruler.add_patterns(patterns)
    ruler.to_disk("./entity_ruler_patterns.json")
if __name__ == "__main__":
    setup_entity_ruler()






