# Progress of improving rotki's experience on windows

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