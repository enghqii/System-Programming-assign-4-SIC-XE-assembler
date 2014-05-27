
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

# parse a literal constant
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

def generateObjectCode(regDict, opCodeDict, symbolDict, literalDict, extref, controlSection, token):

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
			if (opType != 4) and (not immediate) and (len(operands) >= 1 and operands[0] != "") and ( (operands[0] in symbolDict) or (operands[0][0] == '=') ) :
				xbpe |= 1 << 1;
			# E
			if opType == 4 :
				xbpe |= 1 << 0;

			objCode |= xbpe;
			objCode <<= 12 if (opType == 3) else 20;

			# disp
			disp = 0;

			if opType is 4 :
				disp = 0;

				# add modif
				MStr = "M%06X05+%s"%(token["address"] + 1, operands[0]);
				controlSection["MODIFICATIONS"].append(MStr);

			elif immediate:
				disp = int(operands[0]);

			elif (len(operands) >= 1 and operands[0] != "") :

				# symbol
				if operands[0] in symbolDict :
					addr = symbolDict[operands[0]];
					disp = addr - (token["address"] + opType);
				# external symbol
				elif operands[0] in extref :
					pass
				# literal
				elif operands[0][0] == '=':
					addr = literalDict[operands[0]];
					disp = addr - (token["address"] + opType);


			if opType is 3 :
				objCode |= (0x00FFF & disp);
			elif opType is 4 :
				objCode |= (0xFFFFF & disp);

			return objCode;

	elif isDirective(operator):

		if (operator == "WORD") or (operator == "BYTE") :
			objCode = parseConst(operands[0]);
			return objCode;

	# LITERAL OBJ
	elif token["slice"][0] == '*' :
		operands[0] = operands[0][1:];
		objCode = parseConst(operands[0]);
		return objCode;

	return None;

def assemPass1(opCodeDict, lines):

	# token list
	tokenList = [];
	locctr = 0;

	#  SYMTAB
	symbolDict = {};

	# literal Pool , literal Table
	literalList = [];
	literalDict = {};

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
				
				for literal in literalList:
					# make a new token
					ltrToken = {};
					ltrToken["slice"] = ["*", "", [literal]];
					ltrToken["size"] = getLiteralSize(literal);
					ltrToken["address"] = locctr;

					tokenList.append(ltrToken);

					# literal table
					literalDict[literal] = ltrToken["address"];

					locctr += ltrToken["size"];
				#clear the list	
				literalList = [];
				
				# end token append
				if slices[1] == "END" :
					tokenList.append(token);

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

	# pass 1 out
	out = {};
	out["SYMTAB"] = symbolDict;
	out["OPTAB"] = opCodeDict;
	out["TOKEN"] = tokenList;
	out["LITTAB"] = literalDict;

	return out;

def assemPass2(pass1out):

	pass2out = {};
	pass2out["CSECT"] = [];
	pass2out["SYMTAB"] = pass1out["SYMTAB"];

	opCodeDict 	= pass1out["OPTAB"];
	symbolDict 	= pass1out["SYMTAB"];
	regDict 	= pass1out["REGTAB"];
	literalDict = pass1out["LITTAB"];

	controlSection = {};

	extdef = [];
	extref = [];

	lineFeed = False;
	lastToken = None;

	txtRecord = {};

	for token in pass1out["TOKEN"] :

		slices = token["slice"];

		# process directive
		if isDirective(slices[1]) :

			if slices[1] == "START" :
				
				# initialise a new Control Section
				controlSection = {};
				controlSection["name"] = slices[0];
				controlSection["startAddr"] = token["address"];
				controlSection["TEXT"] = [];
				controlSection["MODIFICATIONS"] = [];

				extdef = [];
				extref = [];

				txtRecord = {};
				txtRecord["startAddr"] = controlSection["startAddr"];
				txtRecord["text"] = "";

			elif slices[1] == "EXTDEF" :
				# setting external definition

				for sym in slices[2]:
					extdef.append(sym);
					controlSection["EXTDEF"] = extdef;

				pass
			elif slices[1] == "EXTREF" :
				# setting external references
				
				for sym in slices[2]:
					extref.append(sym);
					controlSection["EXTREF"] = extref;
				pass
			elif slices[1] == "CSECT" or slices[1] == "END" :
				# finalise a new Control section

				controlSection["TEXT"].append(txtRecord);
				controlSection["sectionSize"] = lastToken["address"] - controlSection["startAddr"] + lastToken["size"];
				
				pass2out["CSECT"].append(controlSection);

				controlSection = {};
				controlSection["name"] = slices[0];
				controlSection["startAddr"] = token["address"];
				controlSection["TEXT"] = [];
				controlSection["MODIFICATIONS"] = [];

				extdef = [];
				extref = [];

				txtRecord = {};
				txtRecord["startAddr"] = controlSection["startAddr"];
				txtRecord["text"] = "";

				pass
			elif (slices[1] == "RESW") or (slices[1] == "RESB") :
				# force Line feed
				lineFeed = True;
				pass
			elif slices[1] == "EQU" :
				pass

			elif slices[1] == "END" :
				# ends up and break
				break;
			pass

		# Generate objCode
		if token["size"] != 0 :

			objCode = generateObjectCode(regDict, opCodeDict, symbolDict, literalDict, extref, controlSection, token);

			if objCode is not None :
				token['objCode'] = objCode;

				objStr = ( "%0" + str(token["size"]*2) + "X" ) % token['objCode'];

				if lineFeed == False and len(txtRecord["text"]) + (token["size"]) <= 0x1D *2 :	
					txtRecord["text"] += objStr;
				else:
					# set line feed True
					lineFeed = True;

				if lineFeed :
					controlSection["TEXT"].append(txtRecord);
					txtRecord = {};
					txtRecord["startAddr"] = token["address"];
					txtRecord["text"] = objStr;
					lineFeed = False;


				#print( str(slices) + " " + objStr );
			#else :
				#print(str(slices) + " " + "*NONE*");

		lastToken = token;

	return pass2out;

def makeOutput(pass2out):

	sections = pass2out["CSECT"];
	symbolDict = pass2out["SYMTAB"];

	_1st = True;
	for section in sections :
		print("H%-6s%06X%06X" % (section["name"], section["startAddr"], section["sectionSize"]));

		if "EXTDEF" in section:
			DRecord = "D";
			for sym in section["EXTDEF"]:
				DRecord += "%-6s%06X"%(sym, symbolDict[sym]);
			print(DRecord);

		if "EXTREF" in section:
			RRecord = "R";
			for sym in section["EXTREF"]:
				RRecord += "%-6s" % sym;
			print(RRecord);

		for txtRecord in section["TEXT"]:
			print( "T%06X%02X%s" % (txtRecord["startAddr"], len(txtRecord["text"])/2, txtRecord["text"]));

		if "MODIFICATIONS" in section:
			for mstr in section["MODIFICATIONS"]:
				print(mstr);

		if _1st:
			print( "E%06X" % section["startAddr"] );
			_1st = False;
		else:
			print("E");
		print("");

	pass

# main routine
def main():

	registerDict = {};
	registerDict['A'] = 0; registerDict['X'] = 1; registerDict['L'] = 2; registerDict['B'] = 3;
	registerDict['S'] = 4; registerDict['T'] = 5; registerDict['F'] = 6;

	opCodeDict = initInstFile("inst.txt");
	lines = initInputFile("input.txt");

	pass1out = assemPass1(opCodeDict, lines);
	
	pass1out["REGTAB"] = registerDict;

	#print(pass1out["SYMTAB"]);

	pass2out = assemPass2(pass1out);

	makeOutput(pass2out);

	print(pass2out);


main();