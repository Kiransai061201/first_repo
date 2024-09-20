
import random
import spacy
from spacy.training.example import Example
from spacy.util import minibatch

# Initialize or load an NLP object and get the NER pipeline
nlp = spacy.blank("en")
nlp.add_pipe("ner")

# Initialize the optimizer
optimizer = nlp.begin_training()

# Train the model
for i in range(100):  # Number of epochs
    random.shuffle(TRAIN_DATA)
    losses = {}
    batches = minibatch(TRAIN_DATA, size=8)
    for batch in batches:
        texts, annotations = zip(*batch)
        example = []
        for i in range(len(texts)):
            doc = nlp.make_doc(texts[i])
            example.append(Example.from_dict(doc, annotations[i]))
        nlp.update(
            example,
            drop=0.5,  # Dropout rate
            losses=losses,
        )
    print(losses)
view raw
ner_training.py hosted with ❤ by GitHub
    
    
from spacy.scorer import Scorer

scorer = Scorer()

# Example evaluation data in the same format as training data
EVAL_DATA = TRAIN_DATA = [
    # GPS_COORDINATES
    ("Coordinates: 124.50 N, 68.95 W", {"entities": [(13, 29, "GPS_COORDINATES")]}),
    ("Location: 13.35 S, 57.80 E", {"entities": [(11, 24, "GPS_COORDINATES")]}),
    ("GPS: 24.50 N, 57.80 W", {"entities": [(5, 19, "GPS_COORDINATES")]}),

    # BANK_ACCOUNT
    ("Bank account: 1235-5778-1235-5778", {"entities": [(13, 33, "BANK_ACCOUNT")]}),
    ("Account number: 4332-8776-4332-8776", {"entities": [(16, 36, "BANK_ACCOUNT")]}),
    ("Acct: 1122-2233-3344-4455", {"entities": [(6, 26, "BANK_ACCOUNT")]}),

    # ID
    ("ID: ABC124", {"entities": [(4, 10, "ID")]}),
    ("Personal ID: XYZ790", {"entities": [(12, 18, "ID")]}),
    ("UID: JKL790", {"entities": [(5, 11, "ID")]}),

    # CREDIT_CARD
    ("Credit card: 1235 5779 9102 1122", {"entities": [(13, 33, "CREDIT_CARD")]}),
    ("Card details: 4332 8776 2102 1122", {"entities": [(14, 34, "CREDIT_CARD")]}),
    ("Card: 7891 1235 5679 9013", {"entities": [(6, 26, "CREDIT_CARD")]}),

    # ADDRESS
    ("Address: 124 Pine St.", {"entities": [(9, 22, "ADDRESS")]}),
    ("Home address: 457 Oak St.", {"entities": [(14, 27, "ADDRESS")]}),
    ("Office: 790 Maple St.", {"entities": [(8, 21, "ADDRESS")]}),
]



results = []

for text, annot in EVAL_DATA:
    doc_gold = nlp.make_doc(text)
    example = Example.from_dict(doc_gold, annot)
    doc_pred = nlp(text)
    result = scorer.score([example])
    results.append(result)

result
view raw
ner_evaluation.py hosted with ❤ by GitHub

