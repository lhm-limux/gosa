# -*- coding: utf-8 -*-
"""
The GOsa shell can be called in different ways.

 * Interactive mode::

     $ gosa-shell
     Searching service provider...
     Connected to amqps://amqp.example.net:5671/org.gosa
     Username [cajus]:
     Password:
     GOsa service shell. Use Ctrl+D to exit.
     >>>

   The shell will automatically try to find the service by DNS
   or zeroconf and will ask for your credentials. Sometimes, you
   may need to connect a special system or even provide your
   credentials in the URI like ::

     $ gosa-shell amqps://user:password@amqp.example.net/org.gosa

   but keep in mind that this will expose your credentials in the
   history, and maybe in the history or the process list.

   Nevertheless you're presented a python prompt which can be used
   to get the list of commands using the *gosa* object::

     >>> gosa.help()
     createDistribution()
         Create a new distribution based on type, mirror and installation
         method

     getTimezones(self)
         Get supported time zones
     ...

   The *gosa* object acts as a proxy for the commands, so you can i.e. start
   asking for the registered GOsa clients ::

     >>> gosa.getClients()
     {u'2daf7cbf-75c2-4ea3-bfec-606fe9f07051': {
         u'received': 1313159425.0,
         u'name': u'dyn-10'},
      u'eb5e72d4-c53f-4612-81a3-602b14a8da69': {
          u'received': 1313467229.0,
          u'name': u'ws-2'},
      u'4f0dbdaa-05de-4632-bcba-b6fe8a9e2e09': {
          u'received': 1313463859.0,
          u'name': u'dyn-85'}}

   or just do simple multi-liners::

     >>> for client, info in gosa.getClients().items():
     ...   print info['name']
     ...
     dyn-10
     ws-2
     dyn-85

   You can leave the interactive mode by pressing "Ctrl+D".

 * CLI mode

   .. requirement::
      :status: todo

      Fix shell CLI mode and provide docs

 * Here document mode

   .. requirement::
      :status: todo

      Fix shell here document mode and provide docs
"""
__import__('pkg_resources').declare_namespace(__name__)
__version__ = __import__('pkg_resources').get_distribution('gosa.shell').version
