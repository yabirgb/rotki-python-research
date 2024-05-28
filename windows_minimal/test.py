import sys
import os
import gevent
import signal

class Test:

    def __init__(self):
        self.should_run = True

    def shutdown(self, *args, **kwargs):
        print("shutdown")
        self.should_run = False
        sys.exit(signal.SIGTERM)

    def run(self):
        hub = gevent.hub.get_hub()
        hub.exception_stream = None
        # we don't use threadpool much so go to 2 instead of default 10
        hub.threadpool_size = 2
        hub.threadpool.maxsize = 2
        if os.name != 'nt':
            gevent.hub.signal(signal.SIGQUIT, shutdown)  # type: ignore[attr-defined,unused-ignore]  # pylint: disable=no-member  # linters don't understand the os.name check
        gevent.hub.signal(signal.SIGINT, self.shutdown)
        gevent.hub.signal(signal.SIGTERM, self.shutdown)

        if sys.platform == 'win32':
            import win32api  # pylint: disable=import-outside-toplevel  # isort:skip
            win32api.SetConsoleCtrlHandler(self.shutdown, True)
            gevent.hub.signal(signal.SIGABRT, self.shutdown)

        print(sys.platform)
        counter = 0
        while self.should_run:
            print(f'{counter=}')
            counter += 1
            gevent.sleep(2)

if __name__ == '__main__':
    test = Test()
    test.run()