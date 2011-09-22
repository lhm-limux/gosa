# -*- coding: utf-8 -*-
import win32serviceutil
import win32service
import win32event
import win32api
import servicemanager
import pythoncom
import traceback

from gosa.common import Environment
from gosa.common.components.registry import PluginRegistry
from gosa.common.event import EventMaker


class GOsaClientService(win32serviceutil.ServiceFramework):
    _svc_name_ = "GCS"
    _svc_display_name_ = "GOsa client service"
    _svc_description_ = "This service enables AMQP GOsa client communication for this host"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        # Create an event which we will use to wait on.
        # The "service stop" request will set this event.
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        # Before we do anything, tell the SCM we are starting the stop process.
        #pylint: disable=E1101
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.env.active = False

        # Set stop event
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        pythoncom.CoInitialize()
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ''))

        # Start main loop thread here
        Environment.config = "C:/gosa-client.conf"
        Environment.noargs = True
        self.env = Environment.getInstance()
        self.env.log.info("GOsa client is starting up")
        env = self.env

        try:
            # Load plugins
            PluginRegistry(component='gosa_client.modules')
            amqp = PluginRegistry.getInstance("AMQPClientHandler")

            #TODO:
            # Check if we're a client
            # -> no: shutdown, client should be joined by administrator before
            #        calling the client

            # Sleep and slice
            wait = 2
            while True:
                # Threading doesn't seem to work well with python...
                for p in env.threads:

                    # Bail out if we're active in the meanwhile
                    if not env.active:
                        break

                    p.join(wait)

                # No break, go to main loop
                else:
                    continue

                # Break, leave main loop
                break

        except Exception as detail:
            env.log.critical("unexpected error in mainLoop")
            env.log.exception(detail)
            env.log.debug(traceback.format_exc())
        finally:
            pythoncom.CoUninitialize()

        # Signalize main thread to shut down
        win32api.Sleep(500)

        # Pull down system
        amqp = PluginRegistry.getInstance("AMQPClientHandler")
        amqp_service = PluginRegistry.getInstance("AMQPClientService")

        # Tell others that we're away now
        e = EventMaker()
        goodbye = e.Event(e.ClientLeave(e.Id(amqp_service.id)))
        amqp.sendEvent(goodbye)

        # Shutdown plugins
        PluginRegistry.shutdown()

        # Write another event log record.
        servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STOPPED,
                (self._svc_name_, '' ))


if __name__=='__main__':
    win32serviceutil.HandleCommandLine(GOsaClientService)
