"""Verify the installed native Code Mode host executes JavaScript through its public IPC."""
import json
import os
from pathlib import Path
import select
import struct
import subprocess
import tempfile
import time

assert os.environ.get('MT_STACK_VM_TEST') == '1', 'Run only inside the disposable test VM'
messages = [
    ({'type': 'connection/hello', 'supportedVersions': [1],
      'requiredCapabilities': [], 'optionalCapabilities': []}, 'connection/ready'),
    ({'type': 'operation/request', 'id': 1,
      'request': {'method': 'session/open', 'sessionId': 'mt-stack-check'}}, 'session/ready'),
    ({'type': 'operation/request', 'id': 2,
      'request': {'method': 'session/execute', 'sessionId': 'mt-stack-check',
                  'request': {'tool_call_id': 'vm-arithmetic', 'enabled_tools': [],
                              'source': 'text(6 * 7)', 'yield_time_ms': 10000,
                              'max_output_tokens': 100}}}, 'execute/initialResponse'),
    ({'type': 'operation/request', 'id': 3,
      'request': {'method': 'session/shutdown', 'sessionId': 'mt-stack-check'}}, 'session/closed'),
]
with tempfile.TemporaryFile() as errors:
    process = subprocess.Popen([str(Path.home()/'.local/bin/codex-code-mode-host'), '--listen', 'stdio'],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors)
    try:
        for message, expected in messages:
            payload = json.dumps(message).encode()
            process.stdin.write(struct.pack('<I', len(payload))+payload)
            process.stdin.flush()
            deadline = time.monotonic()+30
            while True:
                chunks = []
                for length in (4, None):
                    count = length if length is not None else struct.unpack('<I', chunks[0])[0]
                    assert count <= 1024*1024, count
                    data = b''
                    while len(data) < count:
                        remaining = deadline-time.monotonic()
                        assert remaining > 0 and select.select([process.stdout], [], [], remaining)[0], ('host timeout', message)
                        part = os.read(process.stdout.fileno(), count-len(data))
                        assert part, ('host exited', message)
                        data += part
                    chunks.append(data)
                reply = json.loads(chunks[1])
                print(reply)
                assert reply.get('result', {}).get('status') != 'error', reply
                assert reply['type'] != 'connection/rejected', reply
                value = reply.get('result', {}).get('value', {})
                if expected in (reply['type'], value.get('type')):
                    break
            if expected == 'connection/ready':
                assert reply['selectedVersion'] == 1, reply
            elif expected == 'execute/initialResponse':
                result = value['Result']
                assert result['error_text'] is None, result
                assert result['content_items'] == [{'type': 'input_text', 'text': '42'}], result
        process.stdin.close()
        process.wait(timeout=10)
        assert process.returncode == 0, process.returncode
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        errors.seek(0)
        print(errors.read().decode(errors='replace'))
print('PASS: installed Code Mode host negotiates, opens, evaluates 6*7=42 and closes a session')
