# -*- coding: utf-8 -*-
declaration = r'''# note use of raw string when embedding in python code...

FILTER          := OGROUP / EMPTY_GROUP / GROUP / STATEMENT / IDENTIFIER

GROUP           := TS, '(', TS, ( OGROUP / EMPTY_GROUP / GROUP / STATEMENT / IDENTIFIER ), TS, ')', TS
EMPTY_GROUP     := '(', TS, ')'

STATEMENT       := EQUALITY / UNEQUALITY / GREATER / LESSER

OGROUP          := ( GROUP / STATEMENT ), (GROUP_OPS, (GROUP / STATEMENT))+
GROUP_OPS       := TS, (ANDOP / OROP), TS
ANDOP           := 'AND'
OROP            := 'OR'

EQUALITY        := TS, (IDENTIFIER/GROUP), TS, '=', '='?, TS, (IDENTIFIER/IDENTIFIED/GROUP), TS
UNEQUALITY      := TS, (IDENTIFIER/GROUP), TS, '!=',      TS, (IDENTIFIER/IDENTIFIED/GROUP), TS
GREATER         := TS, (IDENTIFIER/GROUP), TS, '>', '='?, TS, (IDENTIFIER/IDENTIFIED/GROUP), TS
LESSER          := TS, (IDENTIFIER/GROUP), TS, '<', '='?, TS, (IDENTIFIER/IDENTIFIED/GROUP), TS


IDENTIFIED          :=  ('"',STRING,'"')/NUMBER
IDENTIFIER          := [a-zA-Z], ([a-zA-Z0-9])* 

NUMBER              :=  [0-9]+
STRING              :=  (CHAR/ESCAPEDCHAR)*
SPECIALESCAPEDCHAR  :=  [\\abfnrtv"']
OCTALESCAPEDCHAR    :=  [0-7],[0-7]?,[0-7]?
HEXESCAPEDCHAR      :=  [0-9a-fA-F],[0-9a-fA-F]
CHAR                :=  -[\\"]
CHARNODBLQUOTE      :=  -[\\"]+
CHARNOSNGLQUOTE     :=  -[\\']+
UCODEESCAPEDCHAR_16 := [0-9a-fA-F],[0-9a-fA-F],[0-9a-fA-F],[0-9a-fA-F]
UCODEESCAPEDCHAR_32 := [0-9a-fA-F],[0-9a-fA-F],[0-9a-fA-F],[0-9a-fA-F],[0-9a-fA-F],[0-9a-fA-F],[0-9a-fA-F],[0-9a-fA-F]
ESCAPEDCHAR         :=  '\\',( SPECIALESCAPEDCHAR / ('x',HEXESCAPEDCHAR) / ("u",UCODEESCAPEDCHAR_16) /("U",UCODEESCAPEDCHAR_32)/OCTALESCAPEDCHAR  )
TS                  :=  [ \t]*
DIGITS_NO_ZERO      := [1-9]*
DIGITS              := DIGITS_NO_ZERO, [0-9]*
INTEGER             := ('-'?, DIGITS_NO_ZERO, DIGITS*) / '0'
'''

testdata = []
testdata.append('( cn==test ) AND ( dob <= (dob2) )')
testdata.append('cn=="Klaus Müller" AND (dob <= dob2) OR (dob == 2000) AND (gender != "M")')
testdata.append('  (  (  (  test  ==  (  test  )  )  )  )  ')
testdata.append('peter == "test"')
testdata.append('cn="Klaus Müller" AND (dob < dob2 OR dob = 2000) AND gender != "M"')
testdata.append('test')
testdata.append('(test)')
testdata.append('((test))')
testdata.append('test==test')
testdata.append('()')
testdata.append('(test')
testdata.append('cn="Klaus Müller" AND (dob < 1975 OR dob = 2000) AND gender != "M"')



from simpleparse.parser import Parser
import pprint

parser = Parser(declaration, "FILTER")
if __name__ =="__main__":
    for entry in testdata: 
        res = parser.parse(entry);

        print '-' * 90
        if(res[2] != len(entry)): 
            print "FAILED: ", entry
            pprint.pprint(parser.parse(entry))
            print len(entry), res[2]
        else:
            print "OK: ", entry

