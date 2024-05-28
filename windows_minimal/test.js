const { spawn } = require('node:child_process');
const process = spawn('./dist/test.exe');
const delay = ms => new Promise(resolve => setTimeout(function(){process.kill()}, ms))
delay(5000);
process.kill();