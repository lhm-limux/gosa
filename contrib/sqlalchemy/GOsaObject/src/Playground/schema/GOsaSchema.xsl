<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" 
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
	<xsl:output method="html" indent="yes" />
	
	<xsl:template match="/">
		<html>
		<head>
			<title>GOsa schema file</title>
			<style type="text/css">
				@media screen{
					body {
						font-family: sans					
					}
					
					div.head {
						border-radius: 6px;
						-moz-border-radius: 6px;
						font-weight: bold;
						left:10px;
						right:10px;
						padding:10px;
						border: 1px solid black;
						background-color: lightblue;
					}
					
					div.classItem {
						font-weight: bold;
						border-radius: 4px;
						-moz-border-radius: 4px;
						margin-top:25px;
						left:10px;
						right:10px;
						padding:5px;
						margin-left:10px;
						border: 1px solid black;
						background-color: lightyellow;
					}
					
					div.classProperties {
						border-radius: 4px;
						-moz-border-radius: 4px;
						padding:5px;
						margin-left:15px;
						margin-top: 5px;
						border: 1px solid black;
						background-color: lightgrey;
					}
					
					div.classPropertyName {
						font-size: 0.8em;
						width: 350px;
						float: left;
					}
					div.classPropertyType {
						font-size: 0.8em;
						float:none;
					}
				}
			</style>
		</head>
		<body>
		
			<div class='head'>GOsa Schema information file</div>
			
			<xsl:apply-templates select="Classes/Class"></xsl:apply-templates>
			
		</body>
		</html>
	</xsl:template>
	
	<xsl:template match="Class">
	
		<div class="classItem">
			Class: 
			<xsl:value-of select="name" />
			<xsl:if test="extends">
				-  <i>Extends (<xsl:value-of select="extends" />)</i>
			</xsl:if>
		</div>
		
		
		<xsl:apply-templates select="properties"></xsl:apply-templates>
	</xsl:template>
	
	<xsl:template match="properties">
		<div class="classProperties">
			<xsl:for-each select="property">
				 <div class="classPropertyName">
				 	<xsl:value-of select="name" />
				 </div>
				 <div class="classPropertyType">
				 	<xsl:value-of select="type" />
				 </div>
			</xsl:for-each>
		</div>
	</xsl:template>
	
</xsl:stylesheet>