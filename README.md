# Progress of improving rotki's experience

Regarding pyinstaller for windows we use the [one file approach](https://pyinstaller.org/en/stable/feature-notes.html#onefile-mode-and-temporary-directory-cleanup)
that spawns a bootstrapped process that later spawns our python main script.

Our approach is using node's `spawn` to spawn the bootloader .exe (1) file and then it creates a process with our python main script (2).
electron keeps track of the PID for (1).

## Problem 1

Windows doesn't share the signal mechanism and there are two special signal in windows that python can handle. For this we need
the library `win32api` that allows to add handlers for those. Is documented in [pyinstaller](https://pyinstaller.org/en/stable/feature-notes.html#example-of-console-control-signal-handling-in-python-application) along an example.

In the requirements we add

```
pywin32==306; sys_platform == 'win32'
```

and then in `rotkehlchen/server.py`

```diff
        if sys.platform == 'win32':
            import win32api  # pylint: disable=import-outside-toplevel  # isort:skip
            win32api.SetConsoleCtrlHandler(self.shutdown, True)
```

Using the test script this seems to not be required since we got twice the shutdown logic called.

## Testing script

I created the scripts in ./windows_minimal with logic simulating what we do have in the main process and it seems to kill the processes correctly.

### Interesting findings

in https://github.com/rotki/rotki/blob/f7884138b2079ab966fa0faa4ffaa4e86d1b6182/rotkehlchen/server.py#L47 we don't have any logic shutting down the process (`sys.exit`). If there was some thread executing logic the program won't exit. I've added
it to our logic via `os._exit(0)` since `sys.exit` doesn't seem to work in windows
under the frozen binary but still I didn't manage to kill all the processes (follow).

## Problem 2

Checking the logs from the main app seems that:

1. Electron correctly spawns the bootloader process
2. Gets the id of the bootloader correctly
3. when closing we call `childProcess.kill()`
4. the bootloader finishes but not our script

From the tests in script the signals get handled from the bootloader and sent to the child process so maybe is something special in the node logic.

At https://nodejs.org/api/child_process.html#subprocesskillsignal it states that 

```
On Windows, where POSIX signals do not exist, the signal argument will be ignored, and the process will be killed forcefully and abruptly (similar to 'SIGKILL'). See Signal Events for more details.
```

The effect is that under node it doesn't seem to propagate the kill to the child process so it might be related to hot it kills the process.

## Problem 3

We get a series of errors that says, could not get any response from server 30000ms timeout. Especially when doing something heavy like decoding a lot of transaction, generating PnL report, etc.

This happens because at one point there are too many greenlets doing different tasks, many are making remore calls, some are doing very CPU intensive tasks like decoding transactions. In between of that if the greenlet serving the REST API doesn't run (is not switched to), then it effectively becomes unresponsive for a few seconds.

### Tried Approach
#### Use threads for async queries/tasks and Greenlet only for the REST API
This could work because when we have a bunch of CPU intensive tasks that doesn't cooperate with gevent, we can run them on different threads. This way the greenlet serving the API will still have the chance to run. [Here's a script to check that](https://gist.github.com/OjusWiZard/4f3d01a0335f52733ea10a915bd28ccd). Implemented it in [this branch](https://github.com/OjusWiZard/rotki/tree/refactor/api) but some things did not work:

- "greenlet.error: cannot switch to a different thread": Explained and [tracked here](https://github.com/gevent/gevent/issues/2047)
- Random and rare deadlocks happening probably because we use gevent Semaphores in some places. This can be worked on and solved.
- VCR cassettes failing

## Problem 4

In order to achieve parallelism, we first need a process to hold the connections to the DBs. And then other processes will communicate with this process to interact with the DBs.

### Approach 1

We tried using multiprocessing's `SyncManager` to create shared memory and interact between two processes. It worked well but failed with monkey patching.
This is because monkey patching patches the standard library `socket` and the multiprocessing is dependent on it. multiprocessing's `SyncManager` doesn't work with `gevent.socket` module.

Code: https://github.com/OjusWiZard/rotki/tree/feat/db_process/wip
Usage:
- Start the server with `python rotkehlchen/db/drivers/server.py`
- Start the client with `python rotkehlchen/globaldb/client.py`

Try including/commenting out the monkey patch lines at the start of `client.py` file. It works without monkey patching, but fails with it.
