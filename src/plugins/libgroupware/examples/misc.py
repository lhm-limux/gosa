#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: misc.py 1175 2010-10-18 16:43:16Z cajus $$

 This is a test file.

 See LICENSE for more information about the licensing.
"""
import sys
from time import sleep
from libgroupware.exchange.main import MSExchange, SMTP, HTTP, POP, PENDING, ACTIVE

import os, shutil
from gosa.common.env import Environment

def main():
    Environment.config="../libgroupware.conf"
    Environment.noargs=True
    env = Environment.getInstance()

    # Get management instance
    gw = MSExchange()
#    print gw.folderAdd("user/tmustermann/geilomat")
    print "del", gw.distDel("muffat1")
    print "add", gw.distAdd("muffat1", "kumpel1@gonicus.de")
#    print "getPrimaryMailAddress", gw.distGetPrimaryMailAddress('muffat1')
#    print "setAlternateMailAddress", gw.distSetAlternateMailAddresses('muffat1', ['kumpel2@gonicus.de'])
    print "addAlternateMailAddress", gw.distAddAlternateMailAddress('muffat1', 'kumpel2@gonicus.de')
    print "Alt:", gw.distGetAlternateMailAddresses('muffat1')
    print "delAlternateMailAddress", gw.distDelAlternateMailAddress('muffat1', 'kumpel2@gonicus.de')
#    print "getAlternateMailAddress", gw.distGetAlternateMailAddresses('muffat1')
#    print gw.getCapabilities()
    print "Alt:", gw.distGetAlternateMailAddresses('muffat1')
#    print gw.distSetAlternateMailAddresses('kopie4', ['cajus8@gonicus.de'])
#    print gw.distGetAlternateMailAddresses('kopie4')

    ## Create user
    #try:
    #    print "Create:", gw.acctAdd('klaus', 'klaus@exdom.intranet.gonicus.de')
    #except:
    #    print "failed"

    ## Wait, to be sure
    #print "Waiting..."
    #sys.stdout.flush()
    #for i in range(0, 60):
    #    if gw.acctGetStatus('klaus')['status'] != PENDING:
    #        break
    #    sleep(1)
    #else:
    #    raise Exception("Account didn't change state from PENDING to OK")

    #exit(1)
    
    ## Check if user exists
    #print "Exists:", gw.acctExists('klaus')

    ## Status
    ##print "Status:", gw.acctGetStatus('klaus')

    ## Location
    #print "Location:", gw.acctGetLocation('klaus')
    
    ## Add alternative mailadress
    #print gw.acctAddAlternateMailAddress('klaus', 'talt2@exdom.intranet.gonicus.de')
    ##print gw.acctSetAlternateMailAddresses('klaus', ['talt2@exdom.intranet.gonicus.de'])
    #
    ## Get alternative mailaddress
    ##print gw.acctGetAlternateMailAddresses('klaus')
    #
    ## Del alternative mailaddress
    ##print gw.acctDelAlternateMailAddress('klaus', 'talt3@exdom.intranet.gonicus.de')
    #
    ## Add forward address
    ##print "Add forward address:", gw.acctSetMailForwardAddresses('klaus', {'aduser2@exdom.intranet.gonicus.de': False})

    ## Del forward address
    ##print "Del forward address:", gw.acctDelMailForwardAddress('klaus', 'aduser2@exdom.intranet.gonicus.de')
    #
    ## Set quota on user
    ##print "Set quota:", gw.acctSetQuota('klaus', 2047, 2048, 2048, hold=10)

    ## Get quota on user
    #print "Quota:", gw.acctGetQuota('tmustermann')

    ## Set mail limit on user
    ##print "Set limit:", gw.acctSetMailLimit('klaus' , 12345, 5014)
    #
    ## Get mail limit on user
    ##print "Limits:", gw.acctGetMailLimit('klaus')
    #
    ## Get quota on user
    ##print "Quota:", gw.acctGetQuota('klaus')

    ## Add Public Folder
    ##print "Add public folder:", gw.folderAdd('testordner1')

    ## Del Folder - noch kaputt
    ##print "Delete folder:", gw.folderDel('testgruppe')

    ## Get Folder Members
    ##print "Get folder members:", gw.folderGetMembers('testgruppe')

    ## Add Folder Members
    ##print "Add folder members:", gw.folderAddMember('testgruppe,','hape')

    ## Enable or Disable User
    #print "Mail enable:", gw.acctSetEnabled('klaus', True)

    ## Status
    #print "Status:", gw.acctGetStatus('klaus')
    #
    ## Properties
    ##print "Set properties:", gw.acctSetProperties('klaus', SMTP | HTTP | POP)

    ### Properties
    ##print "Get properties:", gw.acctGetProperties('klaus')
    ##
    ### Change primary mail address
    ##print "Change:", gw.acctSetPrimaryMailAddress('klaus', 'tmusterma@exdom.intranet.gonicus.de')

    # Delete user
    #print "Delete:", gw.acctDel('klaus')

if __name__ == '__main__':
    main()
