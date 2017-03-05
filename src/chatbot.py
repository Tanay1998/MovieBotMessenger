#!/usr/bin/env python
# -*- coding: utf-8 -*-

# PA6, CS124, Stanford, Winter 2016
# v.1.0.2
######################################################################
import csv
import math

import numpy as np
import re, collections
from movielens import ratings
from random import randint
from PorterStemmer import PorterStemmer
from random import randrange, sample, getrandbits

"""
The chatbot needs to keep track of which query the user has had, and the sentiment of the user
to dictate whether it should keep filling the frame or move on to the next set of queries.
This is based on the frame dialog model from lecture.
"""
class Frame:
	NO_SENTIMENT = -999 #Sentinel value

	def __init__(self):
		self.reset()

	def reset(self):
		self.movie = None
		self.movieQuery = ""
		self.sentiment = self.NO_SENTIMENT
		self.potentialMovies = dict()
		self.addedCurrentMovie = False

	def __str__ (self):
		ret = "Query: %s" % (self.movieQuery)
		ret += "; Name: %s" % (self.movie if self.movie != None else "NONE")
		ret += "; Sentiment: %s" % (self.sentiment)
		return ret

class Movie: 
	def __init__(self, name = "", year = "", gens = ""):
		self.movieName = name.strip()
		self.titles = [self.movieName]
		self.year = year
		self.genres = set(gens.split("|"))
		self.id = 0

	def printMovie(self):
		return self.titles[0]# + " from " + self.year

	def recoPrintMovie(self):
		if len(self.year) == 4:
			return "%s (%s)" % (self.titles[0], self.year)
		return printMovie()

	def __str__ (self):
		return "%s (%s)" % (self.movieName, str(self.year))

"""
Used for the chatbot to remember between queries where
it is in the process of movie recommendation.
"""
class ChatbotStateClassEnum:
	def __init__(self):
		self.ASK_MOVIE_INFO = 0 #Last message was asking for more information about the movie
		self.ASK_MOVIE_FROM_CHOICE = 1 #Last message was a list of movie choices
		self.RECOMMENDED_MOVIE = 2 #Last message was a movie recommendation

class Chatbot:
	"""Simple class to implement the chatbot for PA 6."""

	def __init__(self, is_turbo=False):
		self.name = 'Tanay and Nathan\'s MovieBot'
		self.is_turbo = is_turbo
		self.frame = Frame()
		self.multiFrame = []
		self.prevFrame = None
		self.stemmer = PorterStemmer()
		self.genreList = set()
		self.read_data()
		self.preferences = dict()
		self.recommendedMovies = []
		self.EDIT_LIMIT = 3
		self.MIN_PREF_COUNT = 4
		self.REGEX_DIFF = self.EDIT_LIMIT * 4
		self.ChatbotState = ChatbotStateClassEnum()
		self.state = self.ChatbotState.ASK_MOVIE_INFO
	#############################################################################
	# 1. WARM UP REPL
	#############################################################################

	def greeting(self):
		#TODO: Add variation to the starting message, and also tell the user 
		# That he should be telling information about the movies he's watched.
		greeting_message = self.smallTalk() + '\nMy job is can help you find some awesome movies! How can I help you?'
		return greeting_message

	def goodbye(self):
		goodbye_message = 'Have a nice day, and I hope you consider some of the recommendations I provided!'
		return goodbye_message


	#############################################################################
	# 2. Modules 2 and 3: extraction and transformation                         #
	#############################################################################

	"""
	Parameters: Two strings on which to compute edit distance

	Functionality:
	Implements Needleman-Wunsch Algorithm for computing
		Levenshtein edit distance, which computes how far away two strings are.
		This is useful for seeing if the user mistyped something and we want to check if they
		intended to type something else (i.e. spell correction for our set of movies).

	Returns:
		Edit distance (number of operations to change s1 to s2),
			which is an integer type.
	"""
	def levenshteinDistance(self, s1, s2):
		if len(s1) < len(s2):
			return self.levenshteinDistance(s2, s1)
		if len(s2) == 0: # len(s1) >= len(s2)
			return len(s1)
	 
		previous_row = range(len(s2) + 1)
		for i, c1 in enumerate(s1):
			current_row = [i + 1]
			for j, c2 in enumerate(s2):
				insertions = previous_row[j + 1] + 1 # j+1 instead of j since previous_row and current_row are one character longer
				deletions = current_row[j] + 1       # than s2
				substitutions = previous_row[j] + (0 if c1 == c2 else 1)
				current_row.append(min(insertions, deletions, substitutions))
			previous_row = current_row
	 
		return previous_row[-1]

	#str1: movieName, str2: movieQuery, regexPattern
	def getStringDifference(self, str1, str2, regexPattern):
		if str2 in str1:
			return len(str1) - len(str2)
		if len(str1) - len(str2) <= self.REGEX_DIFF: # Movie contains query and is similar
			if len(re.findall(regexPattern.lower(), str1.lower())) > 0:
				return len(str1) - len(str2)
			else:	#Movie doesn't contain query, but has spelling mistakes
				levDist = self.levenshteinDistance(str1.lower(), str2.lower())
				if levDist <= self.EDIT_LIMIT:
					return levDist * 4
		return 111

	def getMovieDifference(self, movie1, movie2, actualYear):
		regexPattern = movie2.replace(' ', '.*')
		best = self.getStringDifference(movie1, movie2, regexPattern)
		if actualYear != None:
			best = min(best, self.getStringDifference(movie1 + ".*" + (actualYear), movie2, regexPattern))
			best = min(best, self.getStringDifference(movie1 + ".*(" + (actualYear) + ")", movie2, regexPattern))
		return best

	def updateFrame(self, frame, greedySelect = False):
		if frame.movieQuery == "":
			return 
		
		#Can also try bag of words

		potentialMoviesDict = dict()
		# print frame.movieQuery

		for movie in self.titles: # TODO: Restrict search to elements in potentialMovies if it exists 
			for movie_title in movie.titles:
				dist = self.getMovieDifference(movie_title, frame.movieQuery, movie.year)
				if dist <= self.REGEX_DIFF:
					potentialMoviesDict[movie] = dist
				if(frame.movieQuery.lower() in movie_title.lower() and len(frame.movieQuery) >= 10): # account for titles of series like "Harry Potter"
					potentialMoviesDict[movie] = dist

		# for movie, dist in potentialMoviesDict.iteritems():
		# 	print movie.printMovie(), dist
		if len(potentialMoviesDict) > 0:
			frame.potentialMovies = sorted(potentialMoviesDict, key=potentialMoviesDict.get)
			if potentialMoviesDict[frame.potentialMovies[0]] == 0 and (len(frame.potentialMovies) < 2 or potentialMoviesDict[frame.potentialMovies[1]]) > 0:
				frame.potentialMovies = frame.potentialMovies[:1]
			# print frame.potentialMovies[0]
			if len(frame.potentialMovies) > 5:
				frame.potentialMovies = frame.potentialMovies[:5]
			# print frame.potentialMovies[0].printMovie()
		if (len(frame.potentialMovies) > 0 and greedySelect) or (len(frame.potentialMovies) == 1 and potentialMoviesDict[frame.potentialMovies[0]] < 2):
			if frame.movie != frame.potentialMovies[0]:
				frame.addedCurrentMovie = False
				frame.movie = frame.potentialMovies[0]
		else:
			frame.movie = None
			frame.addedCurrentMovie = False
		# If the frame.movie is None, then look at potential movies. If its empty then you're fucked. 
		# Else, prompt the user with the movies

	def getNonMovieString(self, line):
		out = ""
		depth = 0
		for c in line:
			if c == '"':
				depth = 1 - depth
			elif depth == 0:
				if c not in "!@#$%^&*()_+}{][\|;:.,></?":
					out += c
		c.replace('  ', ' ')
		return out

	def retrieveMovieTitle(self, line):
		#Write better version with is_turbo
		pattern = '"(.*)"'
		matches = re.findall(pattern, line)
		if len(matches) != 0:
			return max(matches)
		return None

	"""
	Parameters:
	Takes a raw input string.

	Functionality:
	Stems input string and compares to stemmed lexicon of 
		positive and negative sentiment words.
		Also adds support for negation words as from Assign3.

	Return Postcondition:
	Returns None if no input words are attached to any sentiment.
	Returns > 0 for positive sentiment, higher is more
	Returns < 0 for negative sentiment, lower is more
	Returns 0 for equal positive and negative sentiment
	"""
	def retrieveSentiment(self, input):
		exclaimCount = (input.count("!") + 1) / 2

		splitInput = self.getNonMovieString(input).split()

		negationIndexes = set()
		for i, word in enumerate(splitInput):
			if word.lower() in ["though", "although", "scarcely", "barely", "hardly",
									"nor", "not", "neither", "none", "nobody", "nope", "nah", "never",
									"shouldnt", "couldnt", "werent", "wasnt", "doesnt", "isnt", "arent", "didnt"
									"shouldn't", "couldn't", "weren't", "wasn't", "doesn't", "isn't", "aren't", "didn't"]:
				negationIndexes.add(i)

		def exagerrate(exg):
			w = ""
			for c in exg:
				w += c + '+'
			return w 

		exagerrationWords = ["really", "very", "absolutely", "extremely", "quite", "rather", "terribly", "too", "very"]
		exagerrationPatterns = [exagerrate(exg) for exg in exagerrationWords]
		stemmedInput = [self.stemmer.stem(x.lower()) for x in splitInput]
		# TODO: Add more sentiment features with other datasets 
		# TODO: Add support for scaling words with NOT, and words like VERY, REALLY, etc
		# Can use regex for really, etc: "r+e+a+l+l+y+ (\w+)" // Can split the words and add the +s
		numPositiveWords = 0
		numNegativeWords = 0
		sentimentWordsExist = False
		currentlyOpposite = False
		sentiWords = [self.stemmer.stem(x) for x in ["love", "hate", "favorite", "disgusting"]]
		focusWords = ["but", "however", "although", "therefore", "thus", "hence"]
		isFocus = 1
		mult = 1

		MULT = 1.2
		for i, w in enumerate(stemmedInput):
			if i in negationIndexes:
				currentlyOpposite = not currentlyOpposite
				continue
			word = splitInput[i]
			if word.upper() == word: 
				mult *= MULT
			if w in focusWords:
				isFocus = MULT ** 2
				# print w
			if w in sentiWords:
				mult *= MULT

			if (self.sentiment[w] == "pos" and not currentlyOpposite) or (self.sentiment[w] == "neg" and currentlyOpposite):
				numPositiveWords += mult * isFocus
				sentimentWordsExist = True
			if (self.sentiment[w] == "pos" and currentlyOpposite) or (self.sentiment[w] == "neg" and not currentlyOpposite):
				numNegativeWords += mult * isFocus
				sentimentWordsExist = True

			mult = 1
			for pattern in exagerrationPatterns: 
				if len(re.findall(pattern, word.lower())) > 0:
					mult *= MULT
					if word.upper() == word: 
						mult *= MULT

		return (numPositiveWords - numNegativeWords) * (1 + exclaimCount) if sentimentWordsExist else self.frame.NO_SENTIMENT


	"""Takes the input string from the REPL and call delegated functions
		that
		1) extract the relevant information and
		2) transform the information into a response to the user
	"""
	def getMovieFromChoice(self, input):
		response = ""
		digPattern = "(\d+)"
		matches = re.findall(digPattern, input)

		if len(matches) > 0:
			m = int(min(matches)) - 1
			if m < len(self.frame.potentialMovies):
				movieList = self.frame.potentialMovies
				self.frame.movie = movieList[m]
				didGetMovie = True
				self.state = self.ChatbotState.ASK_MOVIE_INFO
			elif m == len(self.frame.potentialMovies):
				self.frame.reset()
				response = "Oops, sorry I don't know much about the movie you were looking for.\nWhy don't we try again with a movie, and hopefully this time it's in my database.\n" 
			else:
				response = "I don't know which movie you are talking about. Can you tell me again?\n" 
		else:
			response = "I couldn't clearly understand which option you were referring to.\n" 
		return response


	def respondToSentiment(self, sentiment):
		if sentiment > 0:
			if sentiment > 5:
				return "When you're happy I'm happy! How joyful!\n"
			return "I'm glad you're feeling good, because I am too!\n"
		elif sentiment < 0:
			if sentiment < -5:
				"I'm sorry you're feeling bad, and I have to agree with you because my creators make me. What a sad existence.\n"
			return "I'd tell you a joke to cheer you up but my creators weren't funny enough.\n"
		return self.smallTalk()

	def processSingleMovieSentence(self, frame):
		response = ""

		if frame.movie == None: 
			if len(frame.potentialMovies) == 0: 
				if len(frame.movieQuery) < 2:
					response += self.suggestTalkAboutMovie()
				else:
					response += "I'm sorry, I don't know much about that movie.\n"
			else:
				response += "Can you tell me which movie you were talking about?\n"

				movieList = frame.potentialMovies
				for id, movieOption in enumerate(movieList):
					if movieOption.year == None:
						response += "\n\t%s. %s" % (str(id + 1), movieOption.printMovie())
					else: 
						response += "\n\t%s. %s (%s)" % (str(id + 1), movieOption.printMovie(), movieOption.year)
				response += "\n\t%s. None of the above\n" % (str(len(movieList) + 1))
				
				self.state = self.ChatbotState.ASK_MOVIE_FROM_CHOICE
		elif frame.sentiment == frame.NO_SENTIMENT: 
			response += "How did you like %s?\n" % frame.movie.printMovie()
		elif not frame.addedCurrentMovie:
			self.preferences[frame.movie] = frame.sentiment
			response += self.movieCommentingTalk(frame.sentiment, frame.movie)
			#Put this in for now, later on we want to 
			if len(self.preferences) == self.MIN_PREF_COUNT or \
				(len(self.preferences) >= self.MIN_PREF_COUNT and (bool(getrandbits(1)) or bool(getrandbits(1)))):
				response += "\n\n" + self.processRecommendMovie()
			self.prevFrame = frame
			frame.reset()
		else: 
			#Work on this
			self.prevFrame = frame
			frame.reset()
		return response

	def processMultiMovieSentence(self, input):
		response = ""
		sentiment = self.retrieveSentiment(input)
		movie_regex = '"(.*?)"'
		regex = ["", "", "", "", ""]
		regex[0] = '%s(?:[^"]* and %s)+' % (movie_regex, movie_regex) 
		regex[1] = "either %s,? or %s" % (movie_regex, movie_regex) 
		regex[2] = "neither %s,? nor %s" % (movie_regex, movie_regex)
		regex[3] = '%s[^"]*,? but [^"]*%s' % (movie_regex, movie_regex) 
		regex[4] = '%s[^"]+%s' % (movie_regex, movie_regex)
		matches = [re.findall(regex[i], input) for i in range(5)]

		movieQueryList = []
		i = 4
		if len(matches[2]) > 0:
			i = 2
		elif len(matches[3]) > 0:
			i = 3
		self.multiFrame = []
		for x, m in enumerate(matches[i][0]):
			frame = Frame()
			frame.movieQuery = m
			if (x == 0 and i == 3) or i == 4:
				frame.sentiment = sentiment
			else:
				frame.sentiment = -sentiment
			self.updateFrame(frame, True)
			self.multiFrame.append(frame)
			response += self.processSingleMovieSentence(frame)+ "\n "
		return response

	def processAskForRecommendation(self, input):
		input = self.getNonMovieString(input)
		words = input.lower().split()
		recoWords = ["recommend", "suggest"]
		bestWords = ["best", "popular", "most", "trending", "highest"]
		shouldRecommend = False 
		for recoWord in recoWords:
			if recoWord in words:
				shouldRecommend = True
		if not shouldRecommend:
			return ""
		recoMovies = []
		for genre in self.genreList:
			if genre.lower() in words:
				recoMovies = self.recommendBestGenre(genre)
				break
		if len(recoMovies) == 0:
			for word in bestWords:
				if word in words:
					recoMovies = self.recommendBestMovie()
					break
		if len(recoMovies) > 0:
			return self.processRecommendMovieFromList(recoMovies)
		if len(self.preferences) >= self.MIN_PREF_COUNT:
			return self.processRecommendMovie()
		return ""

	def processMovie(self, input):
		input = input.strip()
		if len(input) == 0:
			return "I'm waiting..."

		response = ""

		didProcessMovie = False

		response = self.processAskForRecommendation(input)
		if response != "":
			return response

		if self.state == self.ChatbotState.ASK_MOVIE_FROM_CHOICE:
			response += self.getMovieFromChoice(input)

		if self.state == self.ChatbotState.RECOMMENDED_MOVIE:
			lastMovie = self.recommendedMovies[-1]
			words = [word.lower() for word in input.split()]
			alreadySeen = False 

			if "already" in words or lastMovie.printMovie() in input.lower():
				alreadySeen = True

			for i in range(len(words) - 1):
				if self.sentiment[words[i]] != None:
					if words[i + 1] in ["this", "it", "the", "that"]:
						alreadySeen = True

			for i in range(1, len(words)):
				if self.sentiment[words[i]] != None:
					if words[i - 1] in ["was", "is"]:
						alreadySeen = True

			if alreadySeen:
				self.frame.movie = lastMovie
				self.frame.movieQuery = str(self.frame.movie)
				sentiment = self.retrieveSentiment(input)
				self.frame.sentiment = sentiment
				didProcessMovie = True
				response += self.processSingleMovieSentence(self.frame)
			self.state = self.ChatbotState.ASK_MOVIE_INFO

		if self.retrieveMovieTitle(input) is None:
			pattern = '((?:(?:[A-Z])\w+\s).*(?:(?:[A-Z])\w+))'
			split_input = input.split()
			if len(split_input[0]) <= 3:
				split_input = split_input[1:]
			matches = re.findall(pattern, ' '.join(split_input))
			if len(matches) != 0:
				match = max(matches)
				inputpos = input.find(match)
				input = input[:inputpos] + '"' + match + '"' + input[(inputpos + len(match)):]

		if not didProcessMovie and self.state in [self.ChatbotState.ASK_MOVIE_INFO, self.ChatbotState.ASK_MOVIE_FROM_CHOICE, self.ChatbotState.RECOMMENDED_MOVIE]:
			if input.count('"') >= 4:
				response += self.processMultiMovieSentence(input)
			else:
				movieTitle = self.retrieveMovieTitle(input)
				if movieTitle != None and self.frame.movieQuery != movieTitle:
					self.frame.movieQuery = movieTitle
					self.updateFrame(self.frame)

				sentiment = self.retrieveSentiment(input)
				if sentiment != self.frame.NO_SENTIMENT and self.frame.sentiment != sentiment: 
					self.frame.sentiment = sentiment
				
				if self.frame.movieQuery == None and self.frame.sentiment != self.frame.NO_SENTIMENT:
					response += self.respondToSentiment(self.frame.sentiment)
				else:
					response += self.processSingleMovieSentence(self.frame)

		if response == "": 
			response = self.smallTalk()
		return response

	def process(self, input):
		
		input = input.strip()
		curState = self.state
		#print "PRE", str(self.frame)
		response = self.processMovie(input)
		#print "POST", str(self.frame)
		
		return response

	def processRecommendMovieFromList(self, recos):
		if recos == None or len(recos) == 0:
			return ""
		movie = sorted(recos, key=recos.get)[-1]
		self.recommendedMovies.append(movie)
		self.state = self.ChatbotState.RECOMMENDED_MOVIE
		return "I think you'd like %s\n" % (movie.recoPrintMovie())

	def processRecommendMovie (self):
		reco1 = self.recommendFromPreferenceGenres()
		reco2 = self.recommendUserCollaborative()
		recos = collections.defaultdict(lambda: 0)
		for movie, rating in reco1.iteritems():
			recos[movie] += rating
		for movie, rating in reco2.iteritems():
			recos[movie] += rating

		return self.processRecommendMovieFromList(recos)
	#############################################################################
	# 3. Movie Recommendation helper functions                                  #
	#############################################################################

	def getTitleAndPhrasesFromTempTitle(self, temp_title):
		title = ""
		phrases = []
		reading = True
		curPhrase = ""
		for c in temp_title:
			if c == '(':
				reading = False
			elif c == ')':
				reading = True
			elif reading:
				title += c
				if c == ',':
					phrases.append(curPhrase.strip())
					curPhrase = ""
				else:
					curPhrase += c
		if len(curPhrase.strip()) > 0:
			phrases.append(curPhrase.strip())
		return (title, phrases)

	def getTitlesFromPhraseList(self, phrases):
		buildTitle = ""
		titleList = []
		for phrase in phrases:
			if phrase in ["The", "A", "An", "Le", "La", "Les", "L'"]:
				buildTitle = phrase + " " + buildTitle
				titleList.append(buildTitle)
			else:
				buildTitle = buildTitle + (", " if len(buildTitle) > 0 else "") + phrase
				titleList.append(buildTitle)
		return titleList

	def read_data(self):
		"""Reads the ratings matrix from file"""
		# This matrix has the following shape: num_movies x num_users
		# The values stored in each row i and column j is the rating for
		# movie i by user j
		titles, self.ratings = ratings()
		#print titles
		self.titles = []
		for i, temp in enumerate(titles): 
			temp_title = temp[0]
			year = None
			if temp[0][-1] == ')':
				temp_title = temp_title[:-7]
				year = temp[0][-5:-1]
			else:
				temp_title = temp[0]
			
			title, phrases = self.getTitleAndPhrasesFromTempTitle(temp_title)
			titleList = self.getTitlesFromPhraseList(phrases)

			akaPattern = "\(a.k.a. (.*?)\)"

			matches = re.findall(akaPattern, temp_title)
			if len(matches) == 0:
				akaPattern = "\(([^\d]+?)\)"
				matches = re.findall(akaPattern, temp_title)
				# if len(matches) > 0:
				# 	print matches
			for match in matches:
				_, phrases = self.getTitleAndPhrasesFromTempTitle(match)
				akaTitleList = self.getTitlesFromPhraseList(phrases)
				titleList.extend(akaTitleList)
				# if year == "1997":
				# 	print titleList
			m = Movie(title, year, temp[1])
			self.genreList = self.genreList.union(m.genres)
			m.id = i
			m.titles = titleList
			self.titles.append(m)
		reader = csv.reader(open('data/sentiment.txt', 'rb'))
		sentiment = dict(reader)
		self.sentiment = collections.defaultdict(lambda: "")

		for k, v in sentiment.iteritems():
			self.sentiment[self.stemmer.stem(k)] = v

		# Change this later to use non-binarized data
		#self.binarize()


	"""
	Parameters: DIVIDER (default parameter, not necessary)
	Returns: None

	Functionality:
	Converts every element in our numpy ratings matrix above
		DIVIDER to 1, and below divider to -1.
		Thus we are "binarizing" the ratings to a 1 or -1.
	"""
	def binarize(self, DIVIDER = 3.0):
		"""Modifies the ratings matrix to make all of the ratings binary"""
		SENTINEL = DIVIDER + 1.0

		#print len(self.titles), self.ratings.shape

		self.ratings[self.ratings > DIVIDER] = SENTINEL
		self.ratings[self.ratings <= DIVIDER] = -1.0
		self.ratings[self.ratings == SENTINEL] = 1.0


	"""
	Parameters:
	Normal Python vectors or numpy vectors, whichever you prefer.

	Functionality / Returns:
	Returns cosine distance as double value between two vectors, 
		by calculating dot product of L1 norms of vectors.
	"""
	def distance(self, u, v):
		return np.dot(np.linalg.norm(np.array(u), ord=1), np.linalg.norm(np.array(v), ord=1))

	def recommendUserCollaborative(self):
		# Finds the most similar user with Pearson Correlation and rates movies based on their ratings 
		# It then gives back a dict with (movie, potential rating combinations)

		# first start by mean centering the user columns
		ratings = np.apply_along_axis(lambda ratingVec: ratingVec - sum(ratingVec), 0, self.ratings)

		# then make an array characteristic of the user query
		transformUserSentiment = lambda senti: 0.0 if senti is None else ((senti + 3.0) / 2.0 + 1.0) # transform from (-5 to 5) to (1 to 5)
		ourUserVec = np.zeros(len(self.titles))
		for movie, sentiment in self.preferences.iteritems():
			ourUserVec[movie.id] = transformUserSentiment(sentiment)

		# find the columns with positive PMI (PPMI)
		similarityCoeffs = np.apply_along_axis(lambda ratingVec: self.distance(ratingVec, ourUserVec), 0, ratings)

		validCoeffs = dict()
		for userIndex, coeff in enumerate(similarityCoeffs):
			if (coeff > 0):
				validCoeffs[userIndex] = coeff

		# fill in ratings for ourUserVec and return reco
		bestMovieIndex = -1
		bestMovieRating = -1

		tempDict = dict()

		coeffSum = sum(validCoeffs.values())
		if coeffSum == 0:
			return self.recommendFromPreferenceGenres()
		for movieIndex in range(len(self.titles)):
			movie = self.titles[movieIndex]
			if movie in self.preferences or movie in self.recommendedMovies: #Don't want to recommend already watched movies
				continue
			if ourUserVec[movieIndex] == 0.0: #unfilled movie
				movieRating = 0.0
				for (userIndex, coeff) in validCoeffs.iteritems():
					movieRating += coeff * ratings[movieIndex][userIndex]
				movieRating = movieRating / coeffSum
				ourUserVec[movieIndex] = movieRating
				tempDict[movie] = movieRating
				if bestMovieIndex == -1 or bestMovieRating < movieRating:
					bestMovieIndex = movieIndex
					bestMovieRating = movieRating

		# ourUserVec is filled but it's sufficient just to return the best movie list here!
		return tempDict

	# Creative++ function
	# RETURNS MOVIE OBJECT
	def recommendBestMovie(self):
		avg_ratings = dict()
		for i in range(len(self.ratings)):
			movie = self.titles[i]
			if movie in self.preferences or movie in self.recommendedMovies: #Don't want to recommend already watched movies
				continue
			n = 0.0
			tot = 0.0
			for k in self.ratings[i]:
				if k > 0.0:
					tot += k
					n += 1
			if n != 0.0:
				avg_ratings[movie] = tot / n
			else:
				avg_ratings[movie] = tot
		# print avg_ratings
		# #Recommend the best movie over all genres
		# x = self.ratings.sum(axis = 1)
		# print "RECO", x
		return avg_ratings

	#Creative++ function
	# RETURNS MOVIE OBJECT
	def recommendBestGenre(self, genre):
		# Returns the highest rated (ratings based on previous users) movies based on genre 
		# Just based on user matrix
		#print genre
		movieHasGenre = lambda movieIndex: (genre in self.titles[movieIndex].genres)
		temp_ratings = self.recommendBestMovie()

		avg_ratings = dict()
		for movie, rating in temp_ratings.iteritems():
			if genre in movie.genres:
				avg_ratings[movie] = rating
		return avg_ratings

	# Uses self.preferences
	def recommendFromPreferenceGenres(self):
		"""Generates a list of movies based on the input vector u using
		collaborative filtering"""
		# TODO: Implement a recommendation function that takes a user vector u
		# and outputs a list of movies recommended by the chatbot

		if len(self.preferences) < self.MIN_PREF_COUNT:
			return None

		genrePreferences = collections.defaultdict(lambda: 0)

		posMovieCount = 0
		for movie, rating in self.preferences.iteritems():
			for genre in movie.genres:
				genrePreferences[genre] += rating # Weighted genres
		
		movieScores = collections.defaultdict(lambda: 0)

		for movieObj in self.titles:
			if movieObj in self.preferences or movieObj in self.recommendedMovies: #Don't want to recommend already watched movies
				continue
			score = 0
			for genre in movieObj.genres:
				score += genrePreferences[genre]
			movieScores[movieObj] = score
		
		return movieScores


	#############################################################################
	# 4. Debug info                                                             #
	#############################################################################

	def debug(self, input):
		"""Returns debug information as a string for the input string from the REPL"""
		# Pass the debug information that you may think is important for your
		# evaluators
		debug_info = 'debug info'
		return debug_info


	#############################################################################
	# 5. Write a description for your chatbot here!                             #
	#############################################################################
	def intro(self):
		return """
	This is Tanay and Nathan's chatbot that recommends movies to you!
	Simply let me know which movies you like briefly and I'll do my
	best to let you know how you'll be wasting your free time very soon!

	I am well equipped to do the following tasks!
		• Figure out what movies you are talking about if you supply them 
			in quotes (and in some cases without quotes).
		• Figure out how you felt about an inputted movie, and ask you again
			if I felt I didn't get a good read on your emotion.
		• Store all the movies you've talked about correctly.
		• Come up with a valid recommendation that hopefully makes you happy!

	I can also...
		• Figure out if you are talking about two movies at the same time (with quotes)!
		• Figure out if you've already seen the movie we suggested you, and whether you liked it or not.
		• Pick up on most common movies in my database with ease.

	I really won't let you down. I'm fairly awesome and reliable, and I am programmed to pick up on many common responses.
	
	Some notes from my creators:
		• We used a naive filtering system by genres and compared to other movies in the genres on a weighted sentiment average.
		• This naive method worked well and did not even use the ratings matrix.
		• After trying some genre-based and overall average filtering on ratings these did not work too well.
		• We decided to try a mix of our working model and a user-user collaborative filtering system
			on a non-binarized matrix, which is what you see working here!
		• These models worked together better than either model. Also non-binarized performance 
			together worked better than binarized together. 
		• We used a frame based model to append found movies and sentiments into our list, which worked quite effectively.

	Please let my creators know if you'd like me to do anything else!
	Happy to help you enjoy some new movies!
		"""

	def smallTalk(self):
		smallTalks = ["Bro, let's talk about movies. There are so many amazing movies I have seen!",
		"Donald Trump keeps doing stupid shit; in other news water is wet. Anyways let's talk about movies.", 
		"Did you know the first animation picture was Steamboat Willie in 1928?\nThat's the inspiration for all the Pixar movies I have in my database!", 
		"Sometimes my creators leave me with nothing useful to say and I feel sad.",
		"Dan doesn't let me add any data to my model. If he did I'd develop general AI. Mwuhahaha!",
		"It's amazing what can be done with Red Bull and pure ingenuity. At least that's what my creators say. I only know about movies.",
		"Sometimes I feel like I'm being used for recommendations, but that's okay I guess...",
		"I can only say what my creators tell me to say. You humans and your free expression..."]

		return smallTalks[randrange(0, len(smallTalks))]

	def suggestTalkAboutMovie(self):
		dialogue = ["Why don't we start with discussing a movie you have seen?",
		"Tell me about a movie you saw recently?",
		"What movies have been interesting to you in the past?",
		"If you're having trouble getting me to understand your movies, please put them in quotes for me (\"\"). Now are there any movies you want to discuss?",
		"My creators tell me the next thing my state machine needs is for you to tell me what movies you like.",
		"I want to get a sense of which movies you have seen. Tell me a little about your movie taste and some of your favorite movies!"]

		return dialogue[randrange(0, len(dialogue))]

	def movieCommentingTalk(self, sentiment, movieObj):
		genreToUse = sample(movieObj.genres, 1)[0].lower()

		positiveDialogue = ["I'm glad to hear that you liked %s. Tell me more.\n",
		"That movie was awesome! I loved %s. Tell me a little more about some other movies.",
		(("I loved all the wonderful %s scenes in that movie!" % genreToUse) + " Tell me about more movies like %s that you liked."),
		"I really enjoyed the wonderful cinematic experience that was %s. So dope that you liked it too!"]

		negativeDialogue = ["I'm sorry that you had to go through that. With me, you wouldn't have to go through movies like %s again.\n",
		("That movie was complete trash and I can see why you feel that way about %s.\n" + ("I especially hated that whole %s part they threw into the movie." % genreToUse)),
		"What a terrible movie. I really couldn't agree more about your opinion on %s. Now tell me about something you enjoyed!",
		"Hopefully I can recommend movies better than %s. What a horrible use of your time!",
		"I guarantee to you that I can come up with better recommendations than %s.",
		"Yes, yes, let the hatred of movies like %s flow through you."]

		neutralDialogue = ["I found %s rather okayish. I have a bunch of other movies that you might like!\n",
		"%s was so-so to me as well. Let's talk about some other movies you've enjoyed!",
		"I'm never sure how I felt about %s. Some good and some bad throughout; I imagine you feel the same way."]

		if sentiment > 0:
			partialStatement = positiveDialogue[randrange(0, len(positiveDialogue))]
			# TODO TAILOR BY GENRE
		elif sentiment < 0:
			partialStatement = negativeDialogue[randrange(0, len(negativeDialogue))]
		else:
			partialStatement = neutralDialogue[randrange(0, len(neutralDialogue))]

		return partialStatement % movieObj.printMovie()

	def movieRecommendationTalk(self, movieToRecommend):
		dialogue = ["I have a feeling... I think you'd like %s.",
		"Given what I've learned from you, you may enjoy %s!",
		"Not Slytherin eh? Well, better be, %s!",
		"Sometimes I have no pop culture references to say because my creators ran out of time. But I recommend %s.",
		"%s is a solid choice of your next movie to watch!",
		"I'd definitely get started on %s."]

		partialStatement = dialogue[randrange(0, len(dialogue))]

		return partialStatement % ('"' + movieToRecommend.printMovie() + '"')
	#############################################################################
	# Auxiliary methods for the chatbot.                                        #
	#                                                                           #
	# DO NOT CHANGE THE CODE BELOW!                                             #
	#                                                                           #
	#############################################################################

	def bot_name(self):
		return self.name


if __name__ == '__main__':
	Chatbot()