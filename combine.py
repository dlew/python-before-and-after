#!/usr/bin/python

import csv

def read_word_list(filename):
	print("Reading word list from %s" % filename)

	f = open(filename, 'r')
	words = []
	for line in f:
		words.append(line.strip())
	return words

def read_ratings(filename):
	print("Reading ratings from %s" % filename)

	# Determines when we are in the movies section of the file
	past_start = False
	read_movies = False

	f = open(filename, 'r')
	movies = []
	for line in f:
		# Get rid of the newline
		line = line[:-1]

		if line.startswith("MOVIE RATINGS REPORT"):
			past_start = True
		elif past_start and line.startswith("New  Distribution  Votes  Rank  Title"):
			read_movies = True
		elif len(line) == 0:
			read_movies = False
		elif read_movies:
			# Skip all TV shows
			if line.endswith("}") or line.startswith('"'):
				continue

			# Still not sure how "new" movies work, but let's find out eventually
			if not line.startswith(" "):
				print(line)
				continue

			split = line.split()
			distribution = split[0]
			votes = int(split[1])
			rating = float(split[2])

			last_paren = -1
			while (split[last_paren].startswith("(")):
				last_paren -= 1
			name = ' '.join(split[3:last_paren + 1])

			# Get rid of quote marks (if we're parsing TV shows)
			if name.startswith('"'):
				name = name[1:-1]

			# This can happen if the title has parens in it.  I don't care
			if len(name) == 0:
				continue

			movies.append({
				"distribution": distribution,
				"votes": votes,
				"rating": rating,
				"name": name
			})

	return movies

def filter_movies(movies, votes=0, rating=0):
	print("Filtering out movies with votes lower than %s and rating less than %s" % (votes, rating))
	filtered_movies = []
	for movie in movies:
		if movie["votes"] > votes and movie["rating"] > rating:
			filtered_movies.append(movie)

	return filtered_movies

def combine(words, items, min_word_length=4):
	print("Combining items...")

	forward_trie = generate_trie(items, True, words)
	backwards_trie = generate_trie(items, False, words)

	pairs = []
	for word in words:
		if len(word) < min_word_length:
			continue

		forward = get_items(forward_trie, word[::-1])
		backward = get_items(backwards_trie, word)

		if forward is not None and backward is not None:
			for one in forward:
				for two in backward:
					# Check that neither title is just the word itself, as that would suck
					if one["name"].lower() != word and two["name"].lower() != word:
						pairs.append((word, one, two))

	return pairs

# We rank pairs on two values: minimum votes and a weighted difference in
# rating.
#
# The reason we use minimum votes is so that we have a baseline popularity
# in both movies.  Average is bad, because a highly voted movie can bring
# up a bunch of unknown movies.
#
# Difference in rating is based on the idea that pairing a good movie with
# a bad movie is hilarious.
def pair_compare(pair1, pair2):
	diff_weight = 10000

	min_votes1 = min(pair1[1]["votes"], pair1[2]["votes"])
	min_votes2 = min(pair2[1]["votes"], pair2[2]["votes"])
	rating_diff1 = abs(pair1[1]["rating"] - pair1[2]["rating"])
	rating_diff2 = abs(pair2[1]["rating"] - pair2[2]["rating"])

	points1 = min_votes1 + (rating_diff1 * diff_weight)
	points2 = min_votes2 + (rating_diff2 * diff_weight)

	if points1 > points2:
		return -1
	elif points1 < points2:
		return 1
	else:
		return 0

def print_pairs(pairs):
	for pair in pairs:
		word = pair[0]
		one = pair[1]
		two = pair[2]
		vote_avg = (pair[1]["votes"] + pair[2]["votes"]) / 2
		vote_min = min(pair[1]["votes"], pair[2]["votes"])
		rating_diff = abs(pair[1]["rating"] - pair[2]["rating"])
		print("%s (%s, %s): %s%s" % (word, rating_diff, vote_min, one["name"], two["name"][len(word):]))

def combine_pair(pair):
	return "%s%s" % (pair[1]["name"], pair[2]["name"][len(pair[0]):])

def write_csv(pairs):
	writer = csv.writer(open("pairs.csv", "wb"))

	# Header
	writer.writerow([
		"Combined Name",
		"Common Word",
		"Name1",
		"Votes1",
		"Rating1",
		"Name2",
		"Votes2",
		"Rating2"
	])

	# Pairs
	for pair in pairs:
		writer.writerow([
			combine_pair(pair),
			pair[0],
			pair[1]["name"],
			pair[1]["votes"],
			pair[1]["rating"],
			pair[2]["name"],
			pair[2]["votes"],
			pair[2]["rating"],
		])


def get_items(node, text):
	if len(text) == 0:
		return node["items"]

	search = text[0].lower()
	if search in node:
		return get_items(node[search], text[1:])
	else:
		return None

# Trie format: has a key for each letter, plus 
# a key "items" which links to all items matching
def generate_trie(items, suffix=True, words=[]):
	root = {}

	# If words were provided, then only accept text where it's
	# in the dictionary
	dictionary = {}
	for word in words:
		dictionary[word] = True
		dictionary[word[::-1]] = True

	for item in items:
		split = item["name"].split()
		text = ""
		if suffix:
			text = split[-1][::-1]
		else:
			text = split[0]

		if text.lower() in dictionary:
			add_to_trie(root, text, item)

	return root

def add_to_trie(node, text, item):
	if len(text) == 0:
		return

	to_add = text[0].lower()
	next_node = None
	if to_add not in node:
		next_node = { "items" : [] }
		node[to_add] = next_node
	else:
		next_node = node[to_add]

	next_node["items"].append(item)

	add_to_trie(next_node, text[1:], item)

if __name__ == "__main__":
	words = read_word_list("word.list")
	movies = read_ratings("ratings.list")

	filtered_movies = filter_movies(movies, 5000, 0)

	pairs = combine(words, filtered_movies, 4)
	pairs = sorted(pairs, cmp=pair_compare)
	print_pairs(pairs)
	write_csv(pairs)

	# print("# movies: %s, # filtered movies: %s" % (len(movies), len(filtered_movies)))

	#brute_force_combine(words, filtered_movies)