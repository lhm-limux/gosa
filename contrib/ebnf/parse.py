# -*- coding: utf-8 -*-
declaration = r'''# note use of raw string when embedding in python code...
FILTER              :=  GROUP+/STATEMENT/('(',STATEMENT,')')
STATEMENT           := (TS,';',COMMENT,'\n')/EQUALITY/UNEQUALITY/GREATER/LESSER/NULLLINE
NULLLINE            :=  TS,'\n'
COMMENT             :=  -'\n'*
EQUALITY            :=  TS,IDENTIFIER,TS,'=',TS,IDENTIFIED,TS
UNEQUALITY          :=  TS,IDENTIFIER,TS,'!=',TS,IDENTIFIED,TS
GREATER             :=  TS,IDENTIFIER,TS,'>',TS,IDENTIFIED,TS
LESSER              :=  TS,IDENTIFIER,TS,'<',TS,IDENTIFIED,TS
IDENTIFIER          :=  [a-zA-Z], [a-zA-Z0-9_]*
IDENTIFIED          :=  ('"',STRING,'"')/NUMBER
TS                  :=  [ \t]*
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
OP                  := (ANDOP/OROP),(STATEMENT/GROUP)
GROUP               := OPGROUP/('(',OPGROUP,')')
OPGROUP             := STATEMENT,OP+
ANDOP               := TS,'AND',TS
OROP                := TS,'OR',TS
'''

testdata = 'cn="Klaus Müller" AND (dob < 1975 OR dob = 2000) AND gender != "M"'

from simpleparse.parser import Parser
import pprint

parser = Parser(declaration, "FILTER")
if __name__ =="__main__":
    print "In:", testdata
    pprint.pprint(parser.parse(testdata))
