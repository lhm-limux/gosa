#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-
from jsonrpc import JsonRpcApp, Export
from paste import httpserver
from paste.auth.digest import digest_password, AuthDigestHandler
from model import Statistics, Instance, Contact, User, Plugin,  \
                    Role, Activation, RoleMappings, get_session

import time
import calendar
import re
import random
import string
from datetime import date, datetime, timedelta
from time import mktime

from util import isMailAddress

from sqlalchemy import func, cast, Date, desc

# To be able to send the activation mail
import smtplib
from email.mime.text import MIMEText


# Allows to send mails
def send_mail(from_addr, to_addr, subject, text):
    msg = MIMEText(text)
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_addr

    smtp = smtplib.SMTP("localhost")
    smtp.sendmail(from_addr, [to_addr], msg.as_string())
    smtp.quit()


class Service(object):

    @Export(allow="ALL", pass_user=True)
    def listChannels(self, user=None):
        return []

    # ----

    """
    Register a new GOsa-Instance with a user.

    """

    @Export(allow="REGISTERED_USER", pass_user=True)
    def registerInstance(self, user, uuid):

        # First check if this instance is already registered
        if self.isInstanceRegistered(uuid):
            raise Exception("Uuid already registered!")
            return None
        else:

            # Generate the instance password
            pwd = ''.join(random.Random().sample(string.ascii_letters + string.digits + "./_%-+", 8))

            # Open session and create instance
            session = get_session()
            instance = Instance(
                        uuid=uuid,
                        password=digest_password("GCS authentication", uuid, pwd))

            # Query for the user and append the instance.
            user = session.query(User).filter(User.uid == user).first()
            user.instances.append(instance)
            session.commit()

            #message = "Das Passwort lautet: " + pwd
            #send_mail("gosa@gonicus.de", "hickert@gonicus.de", "GOsa Instanz Aktivierung", message)
            return pwd

    @Export(allow="REGISTERED_USER", pass_user=True)
    def listInstances(self, user=None):
        pass

    @Export(allow="REGISTERED_USER", pass_user=True)
    def unregisterInstance(self):
        pass

    @Export(allow="REGISTERED_USER", pass_user=True)
    def updateInstanceProfile(self):
        pass

    """
    Check whether an instance is registered or not.
    """
    @Export(allow="ALL")
    def isInstanceRegistered(self, uuid):
        session = get_session()
        return(session.query(Instance).filter(Instance.uuid == uuid).count() != 0)

    # ---

    @Export(allow="USER_ADMIN", pass_user=True)
    def listUsers(self, user=None):
        pass

    """
    Check whether a given 'uid' is already used or not.

    """
    @Export(allow="ALL")
    def uidInUse(self, uid):
        session = get_session()
        return session.query(User).filter(User.uid == uid).count() != 0

    """
    Registers a new user.

    """
    @Export(allow="ALL")
    def registerUser(self, data):

        uid = data['uid']
        session = get_session()

        # First check if the choosen uid is alredy used.
        if session.query(User).filter(User.uid == uid).count() != 0:
            raise Exception("Uid already in use")
        elif session.query(User).filter(User.mail == data['mailAddress']).count() != 0:
            raise Exception("Mail address already in use")
        else:

            # Check for required values
            reqAttrs = ['mailAddress', 'surname', 'givenName', 'password', 'restoreQuestion', 'restoreAnswer']
            for attr in reqAttrs:
                if attr not in data:
                    raise Exception("Missing value: " + attr)

                attrVal = data[attr]
                if attrVal == "":
                    raise Exception("Value: " + attr + " is empty!")

            # Validate the mail address
            if not isMailAddress(data['mailAddress']):
                raise Exception("Invalid mail address")

            # Convert numeric values to int
            try:
                data['employees'] = int(data['employees'])
            except ValueError:
                data['employees'] = 0

            try:
                data['client'] = int(data['client'])
            except ValueError:
                data['client'] = 0

            # Add Contact information
            contact = Contact(
                    phone=data['phone'],
                    contact_mail=data['contact_mail'],
                    company=data['company'],
                    street=data['street'],
                    postal_code=data['postal_code'],
                    city=data['city'],
                    trade=data['trade'],
                    employees=data['employees'],
                    clients=data['clients'],
                    knownFrom=data['knownFrom'],
                    sector=data['sector'])
            session.add(contact)
            session.commit()

            # Add new user
            user = User(
                        mail=data['mailAddress'],
                        surname=data['surname'],
                        lang=data['lang'],
                        givenname=data['givenName'],
                        password=digest_password('GCS authentication', uid, data['password']),
                        restore_question=data['restoreQuestion'],
                        restore_answer=data['restoreAnswer'],
                        uid=uid,
                        newsletter=data['newsletter'],
                        contact_id=contact.id)
            session.add(user)
            session.commit()

            # Queue user for activation
            self.queueUserForActivation(user.id)

        return True

    """
    Queues a user to be activated

    """

    @Export(allow="NONE", pass_user=True)
    def queueUserForActivation(self, id):

        # First: Remove all old activation requests.
        session = get_session()
        session.query(Activation).filter(Activation.user_id == id).delete()
        session.commit()

        # Generate an activation key
        key = ''.join(random.Random().sample(string.letters + string.digits, 32))

        # Get the user object
        user = session.query(User).filter(User.id == id).first()

        # Create activation
        activation = Activation(
                    user_id=id,
                    activation_code=key,
                    datetime=func.now())
        session.add(activation)
        session.commit()

        # Send mail with activation link
        message = "Dear %s %s,\n\n" % (user.givenname, user.surname)
        message += "your account was successfully created. You can now activate your account browsing to this link:\n\nhttp://gosa-playground.intranet.gonicus.de/GOsaPortal/html/activate.php?id=" + key
        message += "\n\nHave fun,\nthe GOsa team"
        send_mail('gosa_portal@gonicus.de', user.mail, 'GOsa account activation', message)

    """
    Activates a user

    """

    @Export(allow="ALL")
    def activateUser(self, id):

        # First: Remove all old activation requests.
        session = get_session()

        # Check if such a key is really used
        activation = session.query(Activation).filter(Activation.activation_code == id).first()
        if not activation:
            raise Exception("Invalid activation id")
            return False

        # Get role if registered users
        role = session.query(Role).filter(Role.name == 'REGISTERED_USER').first()
        if not role:
            raise Exception("Role wasn't found")
            return False

        # Check if the corresponding user still exists. (It should, due to table policies)
        user = session.query(User).filter(User.id == activation.user_id).first()
        if not user:
            raise Exception("Invalid user")
            return False

        # Get user object
        user.active = True
        user.roles.append(role)

        # Remove activation code from table
        session.query(Activation).filter(Activation.activation_code == id).delete()
        session.commit()

        return True

    @Export(allow="REGISTERED_USER", pass_user=True)
    def unregisterUser(self):
        pass

    @Export(allow="REGISTERED_USER", pass_user=True)
    def updateUserProfile(self):
        pass

    @Export(allow="USER_ADMIN", pass_user=True)
    def setUserRoles(self):
        pass

    @Export(allow="REGISTERED_USER", pass_user=True)
    def setUserPassword(self):
        pass

    @Export(allow="ALL")
    def recoverUserPassword(self, mail):
        pass

    """

    Returns a list of dates for which we've received statisitcs


    @rtype: array
    @return: A list of iso conform date strings

    """
    @Export(allow="REGISTERED_INSTANCE", pass_user=True)
    def getInstanceStatDates(self, user):

        # Are we an instance?
        session = get_session()
        if session.query(Instance).filter(Instance.uuid == user).count() == 1:

            # Get current instance
            instance = session.query(Instance).                     \
                filter(Instance.uuid == user).first()

            # Collect dates now.
            dates = []
            for entry in session.query(                             \
                func.DISTINCT(                                      \
                func.DATE(Statistics.date)).label('date')).         \
                filter(Statistics.instance == instance).         \
                order_by('date'):
                dates.append(entry[0].isoformat())

            return dates
        return None

    """
    Returns a GOsa instance usage statistic.
    This statistic includes:
        category usage count        (Pie graph)
        category usage over time    (Line graph)

    @type id: unix-timestamp (integer)
    @param id: A unix-timestamp to start the report from

    @type sn: unix-timestamp (integer)
    @param sn: a unix-timestamp which specifies the report end time

    @rtype: dict
    @return: A dictionary with the generated report
    """
    @Export(allow="REGISTERED_INSTANCE", pass_user=True)
    def getInstanceStats(self, user, fromTimestamp=0, toTimestamp=2147483647):

        # Ensure that we've integer values here, else we may to calculate strings...
        fromTimestamp = int(fromTimestamp)
        toTimestamp = int(toTimestamp)

        # Create datetime objects
        toTimestamp = datetime.fromtimestamp(toTimestamp)
        fromTimestamp = datetime.fromtimestamp(fromTimestamp)

        # Clean stamp from hours, minutes... we calculate with days here.
        toTimestamp = datetime(toTimestamp.year, toTimestamp.month, toTimestamp.day)
        fromTimestamp = datetime(fromTimestamp.year, fromTimestamp.month, fromTimestamp.day)

        # Ensure that we've at least two measured values to get a valid result.
        if fromTimestamp + timedelta(days=1) > toTimestamp:
            toTimestamp = fromTimestamp + timedelta(days=1)

        # Are we an instance?
        session = get_session()
        if session.query(Instance).filter(Instance.uuid == user).count() == 1:

            # Get current instance
            instance = session.query(Instance).                     \
                filter(Instance.uuid == user).first()

            # Initialize arrays and dicts used later.
            categories = []
            actionsGraph = {}
            actionTypeGraph = {}
            errorsPerInterval = {}
            dates = {}
            usagePerInterval = {}
            usedPasswordHashes = {}

            # Count the number of action per plugin-category
            # - used to render the pie graph
            actionsPerCategory = {}
            relevantActTypes = ['plugin', 'management', 'global']
            for entry in session.query(Statistics.category,         \
                func.count(Statistics.category).label('cnt')).      \
                filter(Statistics.act_type.in_(relevantActTypes)).  \
                filter(Statistics.category != "").                  \
                filter(Statistics.date >= fromTimestamp).           \
                filter(Statistics.date <= toTimestamp).             \
                filter(Statistics.instance == instance).            \
                group_by(Statistics.category).                      \
                order_by('cnt'):
                actionsPerCategory[entry[0]] = entry[1]

            # Count the of action done plugin-action
            # This allow us to render a graph which show how often
            #  an object was modified or removed during the
            #  the given time period.
            # - used to render a pie graph
            relevantActions = ['add', 'copy', 'edit', 'change_password', 'modify', 'move', 'open', 'remove']
            relevantActTypes = ['plugin', 'management', 'global']
            actionsPerPluginAction = {}
            for entry in session.query(
                Statistics.action,                                  \
                func.count(Statistics.action).label('cnt')).        \
                filter(Statistics.date >= fromTimestamp).           \
                filter(Statistics.date <= toTimestamp).             \
                filter(Statistics.instance == instance).            \
                filter(Statistics.action.in_(relevantActions)).     \
                filter(Statistics.act_type.in_(relevantActTypes)).  \
                group_by(Statistics.action).                        \
                order_by('cnt'):
                actionsPerPluginAction[entry[0]] = entry[1]

            # Collect all categories used for objectCount.
            # This is nescessary to create the object-count per day
            #  report later.
            #
            # act_type 'objectCount' is used to keep track of the
            #  number of objects stored in the ldap, per category.
            # Everytime a report was transmitted, GOsa additionally
            #  transmits this objectCount entries.
            objectCountCategories = []
            relevantActTypes = ['objectCount']
            objectCountPerInterval = {}
            for entry in session.query(                             \
                Statistics.category).                               \
                filter(Statistics.act_type.in_(relevantActTypes)).  \
                filter(Statistics.instance == instance).            \
                filter(Statistics.act_type == 'objectCount'):
                objectCountCategories.append(entry[0])
                objectCountPerInterval[entry[0]] = {}

            # Collect a list of categories used for plugins,
            #  management dialogs and global usage.
            # This allows us to create a plugin activity graph
            #  (actionsGraph) later on.
            relevantActTypes = ['plugin', 'management', 'global']
            for entry in session.query(                             \
                func.DISTINCT(Statistics.category),                 \
                func.COUNT(Statistics.category).label('cnt')).      \
                filter(Statistics.instance == instance).            \
                filter(Statistics.date >= fromTimestamp).           \
                filter(Statistics.date <= toTimestamp).             \
                filter(Statistics.category != "").                  \
                filter(Statistics.act_type.in_(relevantActTypes)).  \
                group_by(Statistics.category).                      \
                order_by(desc('cnt')).                              \
                limit(6):

                actionsGraph[entry[0]] = {}
                categories.append(entry[0])

            # Add empty categories to the result set.
            actionsGraph[''] = {}
            categories.append('')

            # Walk through days from (fromTimestamp) to (toTimestamp)
            #  and collect amount of transmitted log entries per category
            # This list will later be completed with missing values.
            startTimestamp = fromTimestamp

            # Detect days between start and end time
            tmp = (toTimestamp - startTimestamp).days

            # Calculate the interval period in days.
            interval = 50
            daysPerInterval = int(tmp / interval)
            if daysPerInterval <= 0:
                daysPerInterval = 1

            relevantActTypes = ['plugin', 'management', 'global']
            while startTimestamp <= toTimestamp:

                # Create the date string, which will be used later in reports
                date = startTimestamp.isoformat()
                dates[date] = date
                errorsPerInterval[date] = 0
                usagePerInterval[date] = {}

                # Fill in missing values.
                for category in categories:
                    actionsGraph[category][date] = 0

                # Fill in missing values.
                for category in objectCountCategories:
                    objectCountPerInterval[category][date] = 0

                # Calculate 'from' an 'to' dates for the query
                fromQuery = startTimestamp
                toQuery = startTimestamp + timedelta(days=daysPerInterval)

                # Collect amount of occured errors.
                # This will be a seperate graph later.
                for entry in session.query(                         \
                    func.SUM(Statistics.amount).label('cnt')).      \
                    filter(Statistics.date >= fromQuery).           \
                    filter(Statistics.date < toQuery).              \
                    filter(Statistics.act_type == 'ERROR').         \
                    filter(Statistics.instance == instance).        \
                    group_by('category'):
                    errorsPerInterval[date] = int(entry[0])

                # Count password changes by hash-type
                for entry in session.query(                         \
                    Statistics.info,                                \
                    func.SUM(Statistics.amount).label('cnt')).      \
                    filter(Statistics.date >= fromQuery).           \
                    filter(Statistics.date < toQuery).              \
                    filter(Statistics.action == 'change_password'). \
                    filter(Statistics.act_type == 'global').        \
                    filter(Statistics.info != '').                  \
                    group_by('info'):

                    if entry[0] not in usedPasswordHashes:
                        usedPasswordHashes[entry[0]] = {}

                    usedPasswordHashes[entry[0]][date] = int(entry[1])

                # Check if we've at least ony category activity in the database
                if len(categories):

                    # Query database for entries which were made on the given date
                    for entry in session.query(                             \
                        (Statistics.category).label('category'),            \
                        func.COUNT(Statistics.category).label('cnt')).      \
                        filter(Statistics.date >= fromQuery).               \
                        filter(Statistics.date < toQuery).                  \
                        filter(Statistics.instance == instance).            \
                        filter(Statistics.category.in_(categories)).        \
                        filter(Statistics.act_type.in_(relevantActTypes)).  \
                        group_by('category'):

                        # Append entry
                        category = entry[0]
                        count = entry[1]
                        actionsGraph[category][date] = count

                    # Collect amount of actions per category.
                    #
                    # We will later render a graph which
                    #  allows to select an action type
                    # This graph will then render
                    #  a line graph showing the amount of this action
                    #  done per category.
                    actions = ['open', 'view', 'modify', 'move', 'remove', 'copy', 'cut', 'change_password']
                    for entry in session.query(                             \
                        Statistics.action,                                  \
                        Statistics.category,                                \
                        func.SUM(Statistics.amount)).                       \
                        filter(Statistics.date >= fromQuery).               \
                        filter(Statistics.date < toQuery).                  \
                        filter(Statistics.instance == instance).            \
                        filter(Statistics.category.in_(categories)).        \
                        filter(Statistics.action.in_(actions)).             \
                        filter(Statistics.act_type.in_(relevantActTypes)).  \
                        group_by('category', 'action'):

                        action = entry[0]
                        category = entry[1]
                        count = int(entry[2])

                        # Ensure that we've initialized the array keys
                        if action not in actionTypeGraph:
                            actionTypeGraph[action] = {}
                        if category not in actionTypeGraph[action]:
                            actionTypeGraph[action][category] = {}
                        if date not in actionTypeGraph[action][category]:
                            actionTypeGraph[action][category][date] = {}

                        actionTypeGraph[action][category][date] = count

                # Collect object count per category
                for entry in session.query(                             \
                    Statistics.category.label('category'),              \
                    Statistics.amount.label('cnt')).                    \
                    filter(Statistics.date >= fromQuery).               \
                    filter(Statistics.date < toQuery).                  \
                    filter(Statistics.instance == instance).            \
                    filter(Statistics.category.in_(categories)).        \
                    filter(Statistics.act_type == 'objectCount'):
                    objectCountPerInterval[entry[0]][date] = entry[1]

                # Collect memory/cpu/render time/duration stats per interval
                for entry in session.query(                             \
                   func.IFNULL(func.MIN(Statistics.duration), 0).label('min_dur'),     \
                   func.IFNULL(func.MAX(Statistics.duration), 0).label('max_dur'),     \
                   func.IFNULL(func.AVG(Statistics.duration), 0).label('avg_dur'),     \
                   func.IFNULL(func.MIN(Statistics.load), 0).label('min_load'),        \
                   func.IFNULL(func.MAX(Statistics.load), 0).label('max_load'),        \
                   func.IFNULL(func.AVG(Statistics.load), 0).label('avg_load'),        \
                   func.IFNULL(func.MIN(Statistics.mem_usage), 0).label('min_mem'),    \
                   func.IFNULL(func.MAX(Statistics.mem_usage), 0).label('max_mem'),    \
                   func.IFNULL(func.AVG(Statistics.mem_usage), 0).label('avg_mem'),    \
                   func.IFNULL(func.MIN(Statistics.render_time), 0).label('min_render'),    \
                   func.IFNULL(func.MAX(Statistics.render_time), 0).label('max_render'),    \
                   func.IFNULL(func.AVG(Statistics.render_time), 0).label('avg_render')).   \
                    filter(Statistics.instance == instance).            \
                    filter(Statistics.date >= fromQuery).               \
                    filter(Statistics.date < toQuery).                  \
                    filter(Statistics.category.in_(categories)).        \
                    filter(Statistics.act_type.in_(relevantActTypes)):

                    entry = [e for e in entry]

                    usagePerInterval[date]['min_dur'] = float(entry[0])
                    usagePerInterval[date]['max_dur'] = float(entry[1])
                    usagePerInterval[date]['avg_dur'] = float(entry[2])
                    usagePerInterval[date]['min_load'] = float(entry[3])
                    usagePerInterval[date]['max_load'] = float(entry[4])
                    usagePerInterval[date]['avg_load'] = float(entry[5])
                    usagePerInterval[date]['min_mem'] = int(entry[6])
                    usagePerInterval[date]['max_mem'] = int(entry[7])
                    usagePerInterval[date]['avg_mem'] = int(entry[8])
                    usagePerInterval[date]['min_render'] = int(entry[9])
                    usagePerInterval[date]['max_render'] = int(entry[10])
                    usagePerInterval[date]['avg_render'] = int(entry[11])

                # Inrement requested time
                startTimestamp += timedelta(days=daysPerInterval)

            # Create result array
            result = {'actionsPerCategory': actionsPerCategory,                 \
                      'actionsGraph': actionsGraph,                 \
                      'objectCountPerInterval': objectCountPerInterval,         \
                      'actionTypeGraph': actionTypeGraph,   \
                      'usagePerInterval': usagePerInterval,                     \
                      'usedPasswordHashes': usedPasswordHashes,                 \
                      'actionsPerPluginAction': actionsPerPluginAction,         \
                      'errorsPerInterval': errorsPerInterval}

            return result

        return None

    @Export(allow="REGISTERED_INSTANCE", pass_user=True)
    def updateInstanceStatus(self, user, data):
        session = get_session()

        # Are we an instance?
        if session.query(Instance).filter(Instance.uuid == user).count() == 1:

            # Get Instance object
            instance = session.query(Instance).     \
                filter(Instance.uuid == user).first()

            # Collect dates we've already collected reports for.
            dates = []
            for entry in session.query(                        \
                func.DISTINCT(func.DATE(Statistics.date))).    \
                filter(Statistics.instance == instance).       \
                order_by(Statistics.date):
                dates.append(entry[0].strftime('%Y-%m-%d'))

            # Walk through received entries and check which of those are new.
            insertCount = 0
            for entry in data:

                # An valid entry consists of 12 values.
                if len(entry) != 12:
                    print 'Invalid list length!'
                    continue

                # Check if the date has a valid syntax 'YYYY-MM-DD'
                if not re.match('^[0-9]{4}-[0-1][0-9]-[0-3][0-9]$', entry[5]):
                    print "Invalid date format, please use '%Y-%m-%d'"
                    continue

                # Convert the date string to time_struct and back to a string
                #  if it is still the same, then everything is fine.
                if entry[5] != time.strftime('%Y-%m-%d', time.strptime(entry[5], '%Y-%m-%d')):
                    print "Invalid date format, please use '%Y-%m-%d'"
                    continue

                # Check if we've already commited entries for this date.
                if entry[5] not in dates:

                    # We should add some checks here!
                    statistics = Statistics(
                        act_type=entry[0],
                        plugin=entry[1],
                        category=entry[2],
                        action=entry[3],
                        uuid=entry[4],
                        date=entry[5],
                        duration=entry[6],
                        render_time=entry[7],
                        amount=entry[8],
                        mem_usage=entry[9],
                        load=float(entry[10]),
                        info=entry[11],
                        instance=instance)
                    session.add(statistics)
                    insertCount += 1
            session.commit()
            return insertCount
        return None

    # ----

    @Export(allow="REGISTERED_USER", pass_user=True)
    def createTicket(self):
        pass

    @Export(allow="REGISTERED_USER", pass_user=True)
    def resolveTicket(self):
        pass

    @Export(allow="REGISTERED_USER", pass_user=True)
    def updateTicket(self):
        pass

    @Export(allow="REGISTERED_USER", pass_user=True)
    def getTicketStatus(self):
        pass


def authenticator(environ, realm, username):
    session = get_session()

    # Default credentials for unregistered instances
    if username == "gosa":
        return digest_password(realm, username, "gosa")

    # Look for incoming instance
    if session.query(Instance).filter(Instance.uuid == username).count() == 1:
        for password, in session.query(Instance.password).filter_by(uuid=username):
            return password

    # Look for incoming user
    if session.query(User).filter(User.uid == username).count() == 1:
        for password, in session.query(User.password).filter_by(uid=username):
            return password

    return None


def main():
    host = "amqp.intranet.gonicus.de"
    port = 4000

    session = get_session()

    ## Add roles on demand
    if session.query(Role).count() == 0:
        session.add_all([
            Role(name="ALL", description="Permission for everyone"),
            Role(name="ADMIN", description="Administrator for everything"),
            Role(name="REGISTERED_USER", description="Registerd users"),
            Role(name="FEED_ADMIN", description="Administrator for news feeds"),
            Role(name="USER_ADMIN", description="Administrator for users"),
            Role(name="CHANNEL_ADMIN", description="Administrator for channels")])
        session.commit()

   ## Remove dummy user tester.
   #if session.query(User).filter(User.uid == 'tester').count:
   #    tester = session.query(User).filter(User.uid == 'tester').first()
   #    session.query(RoleMappings).filter(RoleMappings.user == tester.id).delete()
   #    session.query(User).filter(User.uid == 'tester').delete()
   #    session.commit()

   ### Add dummy user 'tester'
   #if session.query(User).filter(User.uid == 'tester').count() == 0:
   #    tester = User(
   #            mail="tester@gonicus.de",
   #            surname="tester",
   #            givenname="tester",
   #            uid="tester",
   #            password=digest_password("GCS authentication", "tester", "tester"),
   #            restore_question="",
   #            restore_answer="",
   #            newsletter=False,
   #            active=True)
   #    session.add(tester)
   #    session.commit()

   #    role = session.query(Role).filter(Role.name == "REGISTERED_USER").first()
   #    tester.roles = [role]
   #    session.commit()

    # Add anonymous sample instance
    #uuid="65717fe6-9e3e-11df-b010-5452005f1250", password="WyukwauWoid2"
    #instance = Instance(uuid="65717fe6-9e3e-11df-b010-5452005f1250", password="ab951947072230a62d212fd3ee9742f3")
    #session.add(instance)
    #session.commit()

    #for instance in session.query(Instance).order_by(Instance.id):
    #    print instance.uuid

    # Start web service
    app = JsonRpcApp(Service())
    app = AuthDigestHandler(app, "GCS authentication", authenticator)
    srv = httpserver.serve(app, host, port, start_loop=True)
    #, ssl_pem=self.ssl_pem)

if __name__ == '__main__':
    main()
