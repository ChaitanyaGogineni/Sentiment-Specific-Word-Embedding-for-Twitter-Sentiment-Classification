import json
import os
import re
import string
import sys
import time
from os import listdir
from string import digits

from tweepy import OAuthHandler
from tweepy import Stream
from tweepy.streaming import StreamListener

import Configure_TweepyParameters


# load doc into memory
def load_doc(filename):
    # open the file as read only
    file = open(filename, 'r', encoding="utf-8")
    # read all text
    text = file.read()
    # close the file
    file.close()
    return text


class MyListener(StreamListener):
    """Custom StreamListener for streaming data."""

    def __init__(self, data_dir, sentiment, number_of_training_tweets, number_of_test_tweets):
        self.number_of_training_tweets = number_of_training_tweets
        self.number_of_test_tweets = number_of_test_tweets
        self.data_dir = data_dir
        self.test_data_file_index = 0;
        self.train_data_file_index = fetch_init_counter(data_dir)
        self.sentiment = sentiment
        self.trainingstweet_filename = "%s/tweet_" + sentiment + "_%s.txt"
        self.testtweet_filename = "%s/testtweet_" + sentiment + "_%s.txt"
        self.collected_tweets = fetch_all_existing_tweets(data_dir)

        self.current_filename = self.trainingstweet_filename % (data_dir, str(self.train_data_file_index))

    # Called when new data is received by the twitter stream
    def on_data(self, data):
        # Increment the file index for the trainings data by one, has to happen before the check for the case you
        # execute the script on existing test data
        self.train_data_file_index += 1
        # Should the data be seen as trainings data?
        if self.train_data_file_index <= self.number_of_training_tweets:
            # Update the filename
            self.current_filename = self.trainingstweet_filename % (self.data_dir, str(self.train_data_file_index))
            try:
                self.collected_tweets = write_tweet_to_file(self.current_filename, data, self.collected_tweets)
                return True
            except (IOError, ValueError) as e:
                print("Error on_data: %s" % str(e))
                self.train_data_file_index -= 1

                # Remove the file because an error occured
                if isinstance(e, IOError):
                    os.remove(self.current_filename)
                    time.sleep(5)
            return True
        # If not should the data be seen as test data?
        elif self.test_data_file_index < self.number_of_test_tweets:
            # Increment the file index for the test data by one
            self.test_data_file_index += 1
            # Update the filename
            self.current_filename = self.testtweet_filename % (self.data_dir, str(self.test_data_file_index))

            try:
                # Try to write the data to a file
                self.collected_tweets = write_tweet_to_file(self.current_filename, data, self.collected_tweets)
                return True
            except (IOError, ValueError) as e:
                print("Error on_data: %s" % str(e))
                self.test_data_file_index -= 1

                # Remove the file because an error occured
                if isinstance(e, IOError):
                    os.remove(self.current_filename)
                    time.sleep(5)
            return True
        # If not we already got all our tweets and exit the program
        else:
            sys.exit("All files successfully collected")

    def on_error(self, status):
        print(status)
        return True


# This is where the magic happens, checks the tweet for constraints,
# cleans and formats it and writes it to file afterwards
def write_tweet_to_file(filename, data, collected_tweets):
    min_word_count = 3
    try:
        with open(filename, 'a', encoding="utf-8") as f:
            # Get Tweet Text
            tweet_text = get_tweet_text(data)
            print ("Original text is: " + tweet_text)
            # Format the Tweet text
            formatted_data = clean_tweet(tweet_text)
            print ("formatted data is: " + formatted_data)
            # If the tweet is not already contained in the collected data-set and is not empty
            if no_duplicate(collected_tweets, formatted_data) and not tweet_text.isspace():
                # If the tweet contains the minimum amount of words
                if len(formatted_data.split()) >= min_word_count:
                    # Write the formatted tweet to file
                    f.write(formatted_data)
                    print(filename, ":", formatted_data)
                else:
                    raise ValueError("Tweet contains only " + str(len(formatted_data.split())) + " words")
            else:
                raise ValueError("Tweet already exists or is empty.")
    except BaseException:
        raise

    return formatted_data


def fetch_init_counter(data_dir):
    # Initial Index counter
    heighest_index = 0
    # Iterate through all existing filenames and get the highest index
    for filename in listdir(data_dir):
        # Get index of filename
        file_index = int(filename.split('_')[2].split('.')[0])
        # Check if the file_index is heigher than the current heighest index
        if file_index > heighest_index:
            heighest_index = file_index

    # Return the heighest found index
    return heighest_index


def de_emojify(emojified_tweet):
    cleared_tweet = ""
    for character in emojified_tweet:
        try:
            character.encode("ascii")
            cleared_tweet += character
        except UnicodeEncodeError:
            cleared_tweet += ''
    return cleared_tweet


# Used to clean the tweets
def clean_tweet(tweet):
    # remove http links
    tweet = re.sub(r'http\S+', '', tweet)
    tweet = re.sub(r'\.', ' ', tweet)
    tweet = tweet.lower()
    # rewriting apostrophy words
    tweet = tweet.replace(r"won't", "will not")
    tweet = tweet.replace(r"can't", "can not")
    tweet = tweet.replace(r"n't", " not")
    tweet = tweet.replace(r"'re", " are")
    tweet = tweet.replace(r"'s", " is")
    tweet = tweet.replace(r"'d", " would")
    tweet = tweet.replace(r"'ll", " will")
    tweet = tweet.replace(r"'t", " not")
    tweet = tweet.replace(r"'ve", " have")
    tweet = tweet.replace(r"'m", " am")
    #Remove repeated charcters which occurs more than 3 times consecutively
    tweet = re.sub(r'(.)\1+', r'\1\1', tweet)
    # Remove Emojis etc.
    tweet = de_emojify(tweet)
    # Remove mentions and retweets
    tweet = re.sub(r'@[A-Za-z0-9]+', ' ', tweet)
    # Remove Retweet RT
    tweet = re.sub(r'^[rt]+\s', ' ', tweet)
    # remove cutted words
    tweet = re.sub(r'\w+(...)$', ' ', tweet)
    # remove punctuation from tweet
    #because len(string.punctuation) = 32
    translator = str.maketrans(string.punctuation,' '*32)
    tweet = tweet.translate(translator)
    # remove numbers from the tweet
    remove_digits = str.maketrans('', '', digits)
    tweet = tweet.translate(remove_digits)
    # remove leading whitespaces
    tweet = tweet.lstrip(' ')
    # remove double whitespaces and tabs
    tweet = " ".join(tweet.split())
    return tweet


def get_tweet_text(data):
    json_object = json.loads(data)
    # 'text' of the .json object
    tweet = json_object['text']
    return tweet


def no_duplicate(collected_tweets, tweet):
    for ct in collected_tweets:
        if ct == tweet:
            return False
    return True


def fetch_all_existing_tweets(data_dir):
    all_tweets = []

    for filename in listdir(data_dir):
        if not filename.startswith('tweet'):
            continue
        # create the full path of the file to open
        path = data_dir + '/' + filename
        # load the doc
        tweet_from_file = load_doc(path)

        # put in all_tweets
        all_tweets.append([tweet_from_file])

    return all_tweets


def format_filename(fname):
    """Convert file name into a safe string.
    Arguments:
        fname -- the file name to convert
    Return:
        String -- converted file name
    """
    return ''.join(convert_valid(one_char) for one_char in fname)


def convert_valid(one_char):
    """Convert a character into '_' if invalid.
    Arguments:
        one_char -- the char to convert
    Return:
        Character -- converted char
    """
    valid_chars = "-_.%s%s" % (string.ascii_letters, string.digits)
    if one_char in valid_chars:
        return one_char
    else:
        return '_'


def stream_pos_tweets(auth, number_of_training_tweets, number_of_test_tweets):
    data_dir = "twitterdata/pos"
    pos_query = [":)", ":-)", ": )", "=)", ";)"]
    

    twitter_stream = Stream(auth, MyListener(data_dir, "pos", number_of_training_tweets, number_of_test_tweets))
    twitter_stream.filter(track=pos_query, languages=['en'])


def stream_neg_tweets(auth, number_of_training_tweets, number_of_test_tweets):
    data_dir = "twitterdata/neg"
    neg_query = [":(", ":-(", ": (", "=("]
    
    twitter_stream = Stream(auth, MyListener(data_dir, "neg", number_of_training_tweets, number_of_test_tweets))
    twitter_stream.filter(track=neg_query, languages=['en'])


def setup_authenticator():
    auth = OAuthHandler(Configure_TweepyParameters.consumer_key, Configure_TweepyParameters.consumer_secret)
    auth.set_access_token(Configure_TweepyParameters.access_token, Configure_TweepyParameters.access_token_secret)
    return auth


auth = setup_authenticator()

stream_pos_tweets(auth, 2000, 200)

#stream_neg_tweets(auth, 2000, 200)
