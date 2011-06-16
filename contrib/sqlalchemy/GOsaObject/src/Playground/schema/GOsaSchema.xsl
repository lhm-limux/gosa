<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" 
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
	<xsl:output method="html" indent="yes" />
	
	<xsl:template match="/">
		<html>
		<body>
			<h2>Schema information</h2>
			
			<xsl:apply-templates select="Classes/Class"></xsl:apply-templates>
			
		</body>
		</html>
	</xsl:template>
	
	<xsl:template match="Class">
		<h3><xsl:value-of select="name" /></h3>
		<xsl:apply-templates select="properties"></xsl:apply-templates>
	</xsl:template>
	
	<xsl:template match="properties">
		<b>Properties</b>
		<ul>
			<xsl:for-each select="property">
				 <li><xsl:value-of select="name" /></li>
			</xsl:for-each>
		</ul>
	</xsl:template>
	
</xsl:stylesheet>