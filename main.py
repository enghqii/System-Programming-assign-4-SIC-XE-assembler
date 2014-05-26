
# returns opCode dict
def initInstFile(instFileName):
	opCodeDict = {};

	inst = open(instFileName, 'r');
	lines = inst.readlines();

	for line in lines:
		tokens = line.split("|");
		opData = [];

		opData.append(int(tokens[1], 16));
		opData.append(int(tokens[2], 16));
		opData.append(int(tokens[3], 16));

		opCodeDict[tokens[0]] = opData;

	inst.close();

	return opCodeDict;

# read input file, returns lines except comment
def initInputFile(inputFileName):
	inputFile = open(inputFileName, 'r');
	lines = inputFile.readlines();

	for line in lines:
		if line[0] == '.' :
			lines.remove(line);

	inputFile.close();

	return lines;

def assemPass1(opCodeDict, lines):

	for line in lines:
		token = line.split("\t");
		print(token);

	pass

def assemPass2():
	pass

# main routine
def main():

	opCodeDict = initInstFile("inst.txt");
	#print(opCodeDict);
	lines = initInputFile("input.txt");
	#print(lines);

	assemPass1(opCodeDict, lines);

main();