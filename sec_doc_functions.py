# -*- coding: utf-8 -*-
"""
Created on Fri Oct 27 13:01:37 2023

@author: Local User
"""

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.sentiment import SentimentIntensityAnalyzer

nltk.download('punkt')
nltk.download('stopwords')
nltk.download('vader_lexicon')

# summarize the text and assign a positive/negative score with nltk

def summarizer(text):

    # Tokenize sentences
    sentences = sent_tokenize(text)
    
    # Tokenize words and create a frequency distribution
    words = word_tokenize(text)
    stopWords = set(stopwords.words("english"))
    wordsFiltered = [word for word in words if word.lower() not in stopWords]
    freqTable = dict()
    for word in wordsFiltered:
        if word in freqTable:
            freqTable[word] += 1
        else:
            freqTable[word] = 1
    
    # Score sentences based on frequency
    sentenceScores = dict()
    
    for sentence in sentences:
        for word, freq in freqTable.items():
            if word in sentence.lower():
                if sentence in sentenceScores:
                    sentenceScores[sentence] += freq
                else:
                    sentenceScores[sentence] = freq
    
    # Get the summary - for simplicity, let's take the top 2 sentences
    summary_sentences = sorted(sentenceScores, key=sentenceScores.get, reverse=True)#[:2]
    summary = ' '.join(summary_sentences)
    
    # Sentiment Analysis using VADER
    sia = SentimentIntensityAnalyzer()
    sentiment = sia.polarity_scores(text)
    
    sentiment_result = 'neutral'
    if sentiment['compound'] >= 0.05:
        sentiment_result = 'positive'
    elif sentiment['compound'] <= -0.05:
        sentiment_result = 'negative'
    
    sentiment_dict = {"summary": summary, "sentiment": sentiment_result, "score": sentiment['compound']}
    
    return sentiment_dict

import re

def transform_string(s):
    # Regular expression to match the pattern
    match = re.search(r'(\d+)\.0?(\d+):', s)
    if match:
        # Return the string without the 0 prefix
        return "{}-{}".format(match.group(1), match.group(2))
    return None