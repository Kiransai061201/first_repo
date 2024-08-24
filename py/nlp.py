import PyPDF2
import nltk
import spacy
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from heapq import nlargest

# Download stopwords if not already downloaded
nltk.download('punkt')
nltk.download('stopwords')

# Load English tokenizer, tagger, parser, NER, and word vectors
nlp = spacy.load('en_core_web_sm')

def extract_text_from_pdf(pdf_path):
    pdf_file = open(pdf_path, 'rb')
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    num_pages = len(pdf_reader.pages)
    text = ''
    for page_num in range(num_pages):
        page = pdf_reader.pages[page_num]
        text += page.extract_text()
    pdf_file.close()
    return text

def preprocess_text(text):
    # Tokenize the text into sentences
    sentences = sent_tokenize(text)
    # Tokenize the text into words and remove stopwords
    words = word_tokenize(text)
    stop_words = set(stopwords.words('english'))
    words = [word.lower() for word in words if word.isalnum() and word.lower() not in stop_words]
    return sentences, words

def score_sentences(sentences, words):
    word_frequencies = nltk.FreqDist(words)
    # Calculate the importance of each sentence
    sentence_scores = {}
    for sentence in sentences:
        for word in word_tokenize(sentence.lower()):
            if word in word_frequencies:
                if sentence not in sentence_scores:
                    sentence_scores[sentence] = word_frequencies[word]
                else:
                    sentence_scores[sentence] += word_frequencies[word]
    return sentence_scores

def get_important_sentences(sentence_scores, num_sentences=10):
    # Get the top 'num_sentences' sentences with the highest scores
    important_sentences = nlargest(num_sentences, sentence_scores, key=sentence_scores.get)
    return important_sentences

def main(pdf_path, num_sentences=10):
    text = extract_text_from_pdf(pdf_path)
    sentences, words = preprocess_text(text)
    sentence_scores = score_sentences(sentences, words)
    important_sentences = get_important_sentences(sentence_scores, num_sentences)
    return important_sentences

if __name__ == "__main__":
    from google.colab import files
    uploaded = files.upload()
    pdf_path = next(iter(uploaded))  # Get the uploaded file name
    num_sentences = 10  # Number of important sentences you want to extract
    important_sentences = main(pdf_path, num_sentences)
    for idx, sentence in enumerate(important_sentences, 1):
        print(f"{idx}: {sentence}")
