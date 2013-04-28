#!/usr/bin/python

import csv

##############################################################################
### INPUT
##############################################################################

# Expects your standard one-word-per-line word list
# 
# Suggested word list: http://directory.fsf.org/wiki/Yawl
def read_word_list(filename):
	print("Reading word list from %s" % filename)

	f = open(filename, 'r')
	words = []
	for line in f:
		words.append(line.strip())
	return words

# Reads the ratings.list file from IMDB's data dumps
#
# You can retrieve this file from the IMDB FTP sites,
# found here: http://www.imdb.com/interfaces
def read_imdb_ratings(filename, read_movies=True, read_tv=False):
	print("Reading IMDB ratings from %s" % filename)

	# Determines when we are in the movies section of the file
	past_start = False
	read_items = False

	f = open(filename, 'r')
	items = []
	for line in f:
		# Get rid of the newline
		line = line[:-1]

		if line.startswith("MOVIE RATINGS REPORT"):
			past_start = True
		elif past_start and line.startswith("New  Distribution  Votes  Rank  Title"):
			read_items = True
		elif len(line) == 0:
			read_items = False
		elif read_items:
			# Skip all TV shows
			is_tv = line.endswith("}") or line.startswith('"')
			if (not read_tv and is_tv) or (not read_movies and not is_tv):
				continue

			# Still not sure how "new" items work, but let's find out eventually
			if not line.startswith(" "):
				print(line)
				continue

			split = line.split()
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

			items.append({
				"votes": votes,
				"rating": rating,
				"name": name
			})

	return items

# Filters out items below a certain threshold votes/rating
# Good for getting rid of results we won't care about
def filter_items(items, votes=0, rating=0):
	print("Filtering out items with votes lower than %s and rating less than %s" % (votes, rating))

	filtered_items = []
	for item in items:
		if item["votes"] > votes and item["rating"] > rating:
			filtered_items.append(item)

	print("Went from %s to %s items" % (len(items), len(filtered_items)))

	return filtered_items

##############################################################################
### CALCULATIONS
##############################################################################

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

# Retrieves all items that match the text in a trie
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

		# We only use the first or last word (no point in comparing)
		# past a space for a before & after
		if suffix:
			text = split[-1][::-1]
		else:
			text = split[0]

		if text.lower() in dictionary:
			add_to_trie(root, text, item)

	return root

# Recursive method for adding text to a trie.
#
# For this use case, we add the item to each node
# in the trie (so that we match on substrings)
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

##############################################################################
### OUTPUT
##############################################################################

# A comparator for sorting results
#
# We rank pairs on two values: minimum votes and a weighted difference in
# rating.
#
# The reason we use minimum votes is so that we have a baseline popularity
# in both items.  Average is bad, because a highly voted movie can bring
# up a bunch of unknown items.
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

# Simple method for printing results
def print_pairs(pairs):
	for pair in pairs:
		word = pair[0]
		one = pair[1]
		two = pair[2]
		vote_avg = (pair[1]["votes"] + pair[2]["votes"]) / 2
		vote_min = min(pair[1]["votes"], pair[2]["votes"])
		rating_diff = abs(pair[1]["rating"] - pair[2]["rating"])
		print("%s (%s, %s): %s" % (word, rating_diff, vote_min, combine_pair(pair)))

# This is good for exporting the data
def write_pairs_csv(filename, pairs):
	print("Writing pairs file to %s" % filename)

	writer = csv.writer(open(filename, "wb"))

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

# Combines two items into one glorious before & after name
def combine_pair(pair):
	return "%s%s" % (pair[1]["name"], pair[2]["name"][len(pair[0]):])

##############################################################################
### MAIN
##############################################################################

# TODO: This could be command-line-ized but I'm being lazy and just hardcoding
# the process here.
if __name__ == "__main__":
	words = read_word_list("word.list")
	items = read_imdb_ratings("ratings.list")
	filtered_items = filter_items(items, 5000, 0)
	pairs = sorted(combine(words, filtered_items, 4), cmp=pair_compare)
	print_pairs(pairs)
	write_pairs_csv("pairs.csv", pairs)
