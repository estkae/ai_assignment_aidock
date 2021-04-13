import logging
import os
import re
import string
import sys
import numpy as np
import pandas as pd
import spacy
from spacy.lang.en.stop_words import STOP_WORDS
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.preprocessing.text import Tokenizer
from config import DATA_FILE, DIGIT_RX, SYMBOL_RX, DOT_RX, LOG_FILE, TEST_SIZE
from utils import save_data_to_pkl, stratified_split_data, profile

# python3 -m spacy download en_core_web_sm
nlp = spacy.load('en_core_web_sm')
nlp.Defaults.stop_words |= {" f ", " s ", " etc"}
stop_words = set([w.lower() for w in list(STOP_WORDS)])

# # log-file will be created in the main dir
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


# @profile
def from_list_to_str(series):
    """Function to transform series of list(str) to series of string
    param: series:list(str)
    return: new series: str
    """
    return ' '.join([words for words in series])


# @profile
def replace_numbers_str(series):
    """
    Replace numbers expression (11 ; 11,00;  1111.99; 23-th 25-,1/2,¼) with tag ' zNUM ',
    . and : replace with ' zDOT '
    :param series: pandas series of text strings
    :return: series with replaced numbers
    """
    try:
        new_series1 = re.sub(DIGIT_RX, " zNUM ", series[0].decode('utf-8'))
    except AttributeError:
        new_series1 = re.sub(DIGIT_RX, " zNUM ", series)
    new_series2 = re.sub(SYMBOL_RX, ' ', new_series1)
    new_series = re.sub(DOT_RX, " zDOT ", new_series2)
    return new_series


# @profile
def lemmatiz(series):
    """
    Transform all words to lemma, add tag  -PRON-
    param: series:str
    return: series:str
    """
    new_series = ' '.join([word.lemma_ for word in nlp(series)])

    return new_series


# @profile
def verb_count(series):
    """
    To count how many verbs contains the sentence
    :param series:str
    :return series:int count of verbs in each sentence
    """
    count = len([token for token in nlp(series) if token.pos_ == 'VERB'])
    return count


# @profile
def have_pron(series):
    """
    Give the answer is there a pron in the paragraph
    param:series:str
    return: int 1 or 0
    """
    answer = 0
    if series.__contains__('-PRON-'):
        answer = 1
    return answer


# @profile
def remove_punctuation(series):
    """
    Remove punctuation from each word, make every word to lower case
    params: series of strings
    return transformed series
    """
    table = str.maketrans('', '', string.punctuation)
    tokens_punct = series.translate(table).lower()
    tokens_spaces = ' '.join([token.strip() for token in tokens_punct.split() if token != ' '])
    return tokens_spaces


# @profile
def remove_stop_words(series):
    """
    Remove stopwords in the series:str and makes words lower case
    param:series:str
    return: new_series:str
    """
    new_series = ' '.join([word for word in series.split() if word not in stop_words])
    return new_series


# @profile
def count_paragraph_sentences(series):
    """
    Count number of sentences in the paragraph
    :param series: pandas series of text strings
    :return: int count of sentences in the string (if no dots -> count = 1)
    """
    sent_count = series.count('zdot')
    if sent_count == 0:
        sent_count = 1
    return sent_count


# @profile
def num_count(series):
    """
    Count number of sentences in the paragraph
    :param series: pandas series of text strings
    :return: int count of sentences in the string
    """
    return series.count('znum')


# @profile
def count_words(series):
    """
    Count words in each string (paragraph)
    without dots and numbers
    params: series of strings
    returns: new series:int
    """
    clean_sent_len = len([word for word in series.split()])
    return clean_sent_len


# @profile
def load_data_transform_to_set(filename):
    """
    Read from pkl file,transform from dict(str:list(str),str:str)
    a normal dataset with labels, without nans and duplicates
    :param filename: string path to pkl file with saved json data
    :return: pandas DataFrame, columns=[paragraphs:str, labels:int]
                                (1 and 0 - recipe and instructions)
    """
    # load data
    if type(filename) == str:
        df = pd.DataFrame(pd.read_pickle(filename))
        # transform recipe to array
        recipe_col = df["Recipe"].apply(from_list_to_str).to_numpy()
    else:
        df = pd.DataFrame([filename])  # here we got a list(dict())
        recipe_col = df["Recipe"].to_numpy()

    recipe = recipe_col.reshape(-1, 1)

    # and give a label 1
    recipe = np.hstack((recipe, np.ones(len(recipe), int).reshape(-1, 1)))
    logging.info(f'Recipe transformed to array and have a label 1 with shape {recipe.shape}')

    # transform instructions to array and give a label 0
    instr_col = df["INSTRUCTIONS"].str.split('\n\n').to_numpy()
    # if instr_col != 0:
    instr = np.concatenate(instr_col).reshape(-1, 1)
    instr = np.hstack((instr, np.zeros(len(instr), int).reshape(-1, 1)))
    logging.info(f'INSTRUCTIONS transformed to array and have a label 0 with shape {instr.shape}')

    # forming a full data array with labels
    data = np.concatenate((instr, recipe), axis=0)
    logging.info('Shape  of all paragraphs data matrix ' + str(data.shape))

    # remove duplicates
    unique = np.unique(data.astype(str), axis=0)
    logging.info(f'Shape without duplicates {unique.shape}')

    # #remove empty string rows(from table)
    unique = np.delete(unique.astype(str), np.where(unique == ''), axis=0)
    logging.info(f'Shape without empty string rows {unique.shape}')

    return pd.DataFrame(unique, columns=['paragraph', 'label'])


@profile
def preprocess_clean_data(df, name_to_save):
    """
    The function replace numbers with the tag, lemmatize, counts prons,
    counts dots, counts numbers and removes stopwords
    saves as pkl file
    :param name_to_save: str
    :param  df: ndArray
    :return data:pandas df, path_to_data:str
    """

    # transform to pandas -> easy to clean
    data = pd.DataFrame(df, columns=['paragraph', 'label'])
    data['replaced_num'] = data.paragraph.apply(replace_numbers_str)
    logging.info('Numbers are replaced by tag')

    # this one takes an eternity (lemmatiz)
    data['lemmatiz'] = data.replaced_num.apply(lemmatiz)
    logging.info('Lemmatization is done')

    data['verb_count'] = data.lemmatiz.apply(verb_count)
    logging.info('column verb_count created')

    data['contains_pron'] = data.lemmatiz.apply(have_pron)
    logging.info('column contains_pron created')

    data['tokens_punct'] = data.lemmatiz.apply(remove_punctuation)
    logging.info('column tokens_punct created')

    data['remove_stop_words'] = data.tokens_punct.apply(remove_stop_words)
    logging.info('column remove_stop_words is created')

    data['sent_count'] = data.remove_stop_words.apply(count_paragraph_sentences)
    logging.info('column sent_count is created')

    data['num_count'] = data.remove_stop_words.apply(num_count)
    logging.info('column num_count is created')

    data['clean_paragraph_len'] = data.remove_stop_words.apply(count_words)
    logging.info('column clean_paragraph_len is created')

    data['label'] = data.label.apply(int)  # this line (convert list --> int)

    data_clean = data[
        ['paragraph', 'remove_stop_words', 'sent_count', 'num_count', 'clean_paragraph_len', 'verb_count',
         'contains_pron', 'label']]
    path_to_data = save_data_to_pkl(data_clean, f'new_{name_to_save}_data_clean.pkl')

    logging.info(f'Clean data is in {path_to_data}')
    logging.info(
        f'The proportion of target variable\n{round(data_clean.label.value_counts() / len(data_clean) * 100, 2)}')
    return path_to_data


@profile
def sent2vec(texts, max_sequence_length, vocab_size):
    """
    Create a union train set vocabulary and turn text in set
    into  padded sequences (word --> num )
    :param vocab_size: int lemmas count
    :param max_sequence_length: int max count words in series sentences
    :param texts: series of prepared strings
    :return ndArray with transformed series of text to int
            with 0-padding up to max_sequence_length
    """
    tokenizer = Tokenizer(num_words=vocab_size)
    tokenizer.fit_on_texts(texts)

    # Turn text into  padded sequences (word --> num )
    text_sequences = tokenizer.texts_to_sequences(texts)
    return pad_sequences(text_sequences, maxlen=max_sequence_length, padding="post", value=0)


@profile
def tfidf(texts, vocab_size):
    """ Create a union train set vocabulary and turn text in set
    into  padded sequences (word --> num )
    :param texts: series of prepared strings
    :param vocab_size: int count of unique words in text series
    :return ndArray with transformed series of text to arrays of float Tf-IdF coefficients"""

    tokenizer = Tokenizer(num_words=vocab_size)
    tokenizer.fit_on_texts(texts)

    # Turn text into  padded sequences (word --> num )
    text_sequences = tokenizer.texts_to_sequences(texts)
    # print ('hallo')
    # #text_sequences_fit = tokenizer.fit_on_sequences(text_sequences)
    # print (len (text_sequences))
    mode = 'tfidf'
    # mode = 'binary'
    return tokenizer.sequences_to_matrix(text_sequences, mode=mode)


@profile
def main_preprocess(filename=DATA_FILE):
    """
    Function load the data after scrapping from pkl file
    transform to data set with column 'paragraph' and 'label',
    split stratified on label  and preprocess separately train and test sets
    add new columns with additional features and save to 2 pkl files in ../data folder
    :param filename : str / default config.DATA_FILE
    :return void
    """
    # load data
    filename = os.getcwd() + '/data/' + filename  # ../data/recipes.pkl'
    logging.info(f'Data set is loading from {filename}')
    df = load_data_transform_to_set(filename)  # pd.DataFrame(unique,columns=['paragraph', 'label'])

    text = pd.DataFrame(df['paragraph'])
    label = pd.DataFrame(df['label']).astype(int)

    # data stratified split test_size = 0.2 default it is in config
    train_dataset, test_dataset = stratified_split_data(text, label, TEST_SIZE)  # data/train_data_clean.pkl

    # preprocessing + feature engineering for train and test sets
    preprocess_clean_data(train_dataset.as_numpy_iterator(), 'train')
    preprocess_clean_data(test_dataset.as_numpy_iterator(), 'test')
    logging.info('If you want to continue run model_train.py\nYour data is in the ../data folder')
    sys.exit('If you want to continue run model_train.py')


if __name__ == '__main__':
    main_preprocess()
