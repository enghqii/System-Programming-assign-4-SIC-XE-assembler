
# returns opCode dict
def initInstFile(instFileName):
	
	opCodeDict = {};

	inst = open(instFileName, 'r');
	lines = inst.readlines();

	for line in lines:
		tokens = line.split("|");
		opData = {};

		opData["type"] = int(tokens[1], 16);
		opData["opcode"] = int(tokens[2], 16);
		opData["nops"] = int(tokens[3], 16);

		opCodeDict[tokens[0]] = opData;

	inst.close();

	return opCodeDict;

# read input file, returns lines except comment
def initInputFile(inputFileName):

	inputFile = open(inputFileName, 'r');
	lines = inputFile.read().splitlines();

	linesWithoutComment = [];

	for line in lines:
		if line[0] != '.' :
			linesWithoutComment.append(line);

	inputFile.close();

	return linesWithoutComment;

def isOperator(opCodeDict, operator):

	if operator[0] == '+':
		operator = operator[1:];

	return (operator in opCodeDict);

def isDirective(directive):
	return directive in ["START", "END", "WORD", "BYTE", "RESW", "RESB", "LTORG", "EQU", "CSECT", "EXTREF", "EXTDEF"];

def getOpData(opCodeDict, operator):

	if isOperator(opCodeDict, operator):

		if operator[0] == '+':
			operator = operator[1:];

		return opCodeDict[operator];

	return False;

def assemPass1(opCodeDict, lines):

	# token list
	tokenList = [];
	locctr = 0;

	for line in lines:
		token = {};
		slices = line.split("\t");

		# separate operands (if there's)
		if len(slices) >= 3:
			slices[2] = slices[2].split(",");

		token["slice"] = slices;
		token["address"] = locctr;
		token["size"] = 0;

		## get size and increase locctr

		# operator
		if isOperator(opCodeDict, slices[1]):

			opData = getOpData(opCodeDict, slices[1]);

			if opData is not False:
				token["size"] = int(opData["type"]);

				if slices[1][0] == '+':
					token["size"] += 1;

			locctr += token["size"];

		# directive
		elif isDirective(slices[1]):

			if slices[1] == "BYTE" :
				token["size"] = len(slices[2][0])/2;
			elif slices[1] == "WORD" :
				token["size"] = 3;
			elif slices[1] == "RESW" :
				token["size"] = int(slices[2][0]) * 3;
			elif slices[1] == "RESB" :
				token["size"] = int(slices[2][0]);
			elif slices[1] == "CSECT" :
				token["address"] = 0;
				token["size"] = 0;
				locctr = 0;

			locctr += token["size"];

		print( ( "0x%04X" % token["address"]) + " " + str(token["slice"]));
		tokenList.append(token);

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