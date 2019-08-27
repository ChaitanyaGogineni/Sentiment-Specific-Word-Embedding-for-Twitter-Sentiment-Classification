import os
import pickle
from string import punctuation

from keras.models import model_from_json
from keras.preprocessing.sequence import pad_sequences


# load doc into memory
def load_doc(filename):
    # open the file as read only
    file = open(filename, 'r', encoding="utf-8")
    # read all text
    text = file.read()
    # close the file
    file.close()
    return text


def load_review(filepath):
    # fetch directory path
    script_dir = os.path.dirname(__file__)
    # join absolute with relative filepath
    abs_file_path = os.path.join(script_dir, filepath)
    # load file
    review = load_doc(abs_file_path)
    # return the file
    return review


# turn a doc into clean tokens
def clean_sentence(sentence, vocab):
    # lower the sentence
    sentence.lower()
    # split into tokens by white space
    tokens = sentence.split()
    # remove punctuation from each token
    table = str.maketrans('', '', punctuation)
    tokens = [w.translate(table) for w in tokens]
    # filter out tokens not in vocab
    tokens = [w for w in tokens if w in vocab]
    tokens = ' '.join(tokens)

    return tokens


def predict_tweet_sentiment(tweet):
    # load tokenizer
    with open('twitter_tokenizer.pickle', 'rb') as handle:
        tokenizer = pickle.load(handle)

    # load the vocabulary
    vocab_filename = 'vocab.txt'
    vocab = load_doc(vocab_filename)

    # load model
    json_file = open('twitterSentimentClassficationModel.json', 'r')
    loaded_model_json = json_file.read()
    json_file.close()
    model = model_from_json(loaded_model_json)

    # load weights into model
    model.load_weights("twitterSentimentClassficationWeights.h5")

    # Get the input length of the models embedding layer
    max_length = model.layers[0].get_output_at(0).get_shape().as_list()[1]

    # Remove all tokens which are not known to the model
    cleaned_test_sentence = clean_sentence(tweet, vocab)

    # Creates sequences of the trainingsdata
    sequenced_training_sentence = tokenizer.texts_to_sequences([cleaned_test_sentence])

    # Pad the sequences to the input_length of the embedding layer
    paded_training_sentence_sequence = pad_sequences(sequenced_training_sentence, maxlen=max_length)

    # Make a prediction on the testsentence
    prediction = model.predict(paded_training_sentence_sequence)

    # Return the result
    return prediction


def label_for_prediction(prediction):
    if prediction < 0.5:
        return "Negative"
    else:
        return "Positive"


prediction = predict_tweet_sentiment(load_doc("test_tweet.txt"))

print("Sentiment-Prediction: ", label_for_prediction(prediction), " - ", prediction)
