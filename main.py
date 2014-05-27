
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

	if len(operator) < 1:
		return False;

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

def getLiteralSize(literal):
	if literal[0] == '=':
		literal = literal[1:];

	if literal[0] == 'C':
		return len(literal)-3;
	elif literal[0] == 'X':
		return (len(literal)-3)/2;
	return 0;

def parseConst(const):
	if (len(const) > 0):

		value = 0;

		if const[0] == 'C':

			for i in range(2,len(const)-1):

				c = const[i];
				value <<= 8;
				value |= ord(c);

		elif const[0] == 'X':

			hxStr = const[2:-1];
			value = int(hxStr, 16);
			pass

		return value;

def generateObjectCode(regDict, opCodeDict, symbolDict, token):

	operator = token["slice"][1];
	operands = token["slice"][2];

	if isOperator(opCodeDict, operator) :

		opData = getOpData(opCodeDict, operator);
		opType = opData["type"];

		# extended ?
		if operator[0] == '+' :
			opType = 4;

		# for type 1 and 2
		if (opType == 1) or (opType == 2) :
			objCode = int(opData["opcode"]);

			if opType == 2 :
				objCode <<= 8;

				if len(operands) >= 1 :

					r1 = regDict[operands[0]];
					r1 <<= 4;
					objCode |= r1;

				if len(operands) >= 2 :

					r2 = regDict[operands[1]];
					objCode |= r2;

			return objCode;

		# for type 3 and 4
		elif (opType == 3) or (opType == 4) :
			objCode = int(opData["opcode"]);

			indirect = False;
			immediate = False;

			if (len(operands) >= 1 and operands[0] != "") and (operands[0][0] == '@') :
				
				objCode |= 0x0002;
				indirect = True;

				operands[0] = operands[0][1:];

			elif (len(operands) >= 1 and operands[0] != "") and (operands[0][0] == '#') :
				
				objCode |= 0x0001;
				immediate = True;

				operands[0] = operands[0][1:];

			else :
				objCode |= 0x0003;

			objCode <<= 4;

			# XBPE
			xbpe = 0;

			# X
			if (len(operands) >= 2) and (operands[1] == "X") :
				xbpe |= 1 << 3;
			# P
			if (opType != 4) and (not immediate) and (len(operands) >= 1 and operands[0] != "") and ( (token['slice'][0] in symbolDict) or (operands[0][0] == '=') ) :
				xbpe |= 1 << 1;
			# E
			if opType == 4 :
				xbpe |= 1 << 0;

			objCode |= xbpe;
			objCode <<= 12 if (opType == 3) else 20;

			# disp
			disp = 0;

			if immediate:
				disp = int(operands[0]);

			elif (len(operands) >= 1 and operands[0] != "") :

				# symbol
				if operands[0] in symbolDict :
					addr = symbolDict[operands[0]];
					disp = addr - (token["address"] - opType);
				# external symbol
				# literal

			if opType is 3 :
				objCode |= (0x00FFF & disp);
			elif opType is 4 :
				objCode |= (0xFFFFF & disp);

			return objCode;

	elif isDirective(operator):

		if (operator is "WORD") or (operator is "BYTE") :
			objCode = parseConst(operands[0]);
			return objCode;

	return None;

def assemPass1(opCodeDict, lines):

	# token list
	tokenList = [];
	locctr = 0;

	#  SYMTAB
	symbolDict = {};

	# literal Pool
	literalList = [];

	for line in lines:

		token = {};
		slices = line.split("\t");

		# separate operands (if there's)
		if len(slices) >= 3:
			slices[2] = slices[2].split(",");

		# delete comment
		if len(slices) >= 4:
			slices.pop(3);

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

		# directive
		elif isDirective(slices[1]):

			if slices[1] == "BYTE" :
				token["size"] = ( len( slices[2][0] ) -3 ) / 2;

			elif slices[1] == "WORD" :
				token["size"] = 3;

			elif slices[1] == "RESW" :
				token["size"] = int(slices[2][0]) * 3;

			elif slices[1] == "RESB" :
				token["size"] = int(slices[2][0]);

			elif slices[1] == "EQU" :
				# TODO
				pass

			elif slices[1] == "CSECT" :
				token["address"] = 0;
				token["size"] = 0;
				locctr = 0;

			elif slices[1] == "END" or slices[1] == "LTORG" :
				# end token append
				if slices[1] == "END" :
					tokenList.append(token);

				for literal in literalList:
					# make a new token
					ltrToken = {};
					ltrToken["slice"] = ["*", "", [literal]];
					ltrToken["size"] = getLiteralSize(literal);
					ltrToken["address"] = locctr;

					tokenList.append(ltrToken);

					locctr += ltrToken["size"];
				#clear the list	
				literalList = [];
				continue;

		# symbol
		if (slices[0] != '') and (slices[0] not in symbolDict) :
			symbolDict[slices[0]] = locctr;

		# gathering literal
		if len(slices) >= 3 :
			if ( slices[2][0] != '' ) and (slices[2][0][0] == '=') and (slices[2][0] not in literalList):
				literalList.append(slices[2][0]);

		locctr += token["size"];
		tokenList.append(token);

	#print(symbolDict);
	#print(literalList);

	#for token in tokenList:
	#	print( ( "0x%04X" % token["address"] ) + " " + str(token["slice"]));

	# pass 1 out
	out = {};
	out["SYMTAB"] = symbolDict;
	out["OPTAB"] = opCodeDict;
	out["TOKEN"] = tokenList;

	return out;

def assemPass2(pass1out):

	# generate objCode
	pass2out = [];
	opCodeDict 	= pass1out["OPTAB"];
	symbolDict 	= pass1out["SYMTAB"];
	regDict 	= pass1out["REGTAB"];

	for token in pass1out["TOKEN"] :

		slices = token["slice"];

		if token["size"] != 0 :
			# make objCode
			objCode = generateObjectCode(regDict, opCodeDict, symbolDict, token);

			if objCode is not None :
				token['objCode'] = objCode;
				print( str(slices) + " " + "\t\t%X"%token['objCode'] );
			else :
				print(str(slices) + " " + "*NONE*");

	pass

# main routine
def main():

	registerDict = {};
	registerDict['A'] = 0; registerDict['X'] = 1; registerDict['L'] = 2; registerDict['B'] = 3;
	registerDict['S'] = 4; registerDict['T'] = 5; registerDict['F'] = 6;

	opCodeDict = initInstFile("inst.txt");
	#print(opCodeDict);
	lines = initInputFile("input.txt");
	#print(lines);

	pass1out = assemPass1(opCodeDict, lines);

	pass1out["REGTAB"] = registerDict;
	#print(pass1out);
	pass2out = assemPass2(pass1out);

main();