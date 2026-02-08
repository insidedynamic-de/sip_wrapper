#!/usr/bin/env python3
"""
ESL Event Subscriber for FreeSWITCH
Real-time event streaming via Event Socket Library

All communication with FreeSWITCH goes through ESL - no file access needed.
Uses gevent for async operations (required by greenswitch).
"""

import os
import time
import threading
from datetime import datetime
from collections import deque

# ESL connection settings (from environment)
FS_HOST = os.environ.get('FS_HOST', '127.0.0.1')
FS_PORT = int(os.environ.get('FS_PORT', '8021'))
FS_PASS = os.environ.get('FS_PASS', 'ClueCon')

# Try to import greenswitch (requires gevent)
try:
    import gevent
    from greenswitch import InboundESL
    ESL_AVAILABLE = True
except ImportError:
    ESL_AVAILABLE = False
    gevent = None
    print("WARNING: greenswitch not installed - ESL events will not work")


class ESLEventBuffer:
    """Thread-safe circular buffer for ESL events"""

    def __init__(self, max_size=1000):
        self.buffer = deque(maxlen=max_size)
        self.lock = threading.Lock()
        self.event_count = 0

    def add(self, event):
        """Add event to buffer"""
        with self.lock:
            self.buffer.append(event)
            self.event_count += 1

    def get_recent(self, count=100):
        """Get last N events"""
        with self.lock:
            events = list(self.buffer)
            return events[-count:] if len(events) > count else events

    def get_since(self, timestamp):
        """Get events since timestamp"""
        with self.lock:
            return [e for e in self.buffer if e.get('timestamp', 0) > timestamp]

    def clear(self):
        """Clear all events"""
        with self.lock:
            self.buffer.clear()
            self.event_count = 0

    def stats(self):
        """Get buffer statistics"""
        with self.lock:
            return {
                'total_events': self.event_count,
                'buffer_size': len(self.buffer),
                'max_size': self.buffer.maxlen
            }


class ESLEventSubscriber:
    """Background ESL event subscriber

    Subscribes to FreeSWITCH events and stores them in a buffer.
    Runs in a separate thread, automatically reconnects on disconnect.
    """

    # Events to subscribe to
    SUBSCRIBE_EVENTS = [
        'CHANNEL_CREATE',
        'CHANNEL_ANSWER',
        'CHANNEL_HANGUP',
        'CHANNEL_HANGUP_COMPLETE',
        'CHANNEL_BRIDGE',
        'CHANNEL_STATE',
        'SOFIA::REGISTER',
        'SOFIA::UNREGISTER',
        'SOFIA::REGISTER_ATTEMPT',
        'SOFIA::REGISTER_FAILURE',
        'SOFIA::GATEWAY_STATE',
        'CUSTOM sofia::register',
        'CUSTOM sofia::unregister',
        'CUSTOM sofia::register_failure',
        'CUSTOM sofia::gateway_add',
        'CUSTOM sofia::gateway_delete',
        'CUSTOM sofia::gateway_state',
        'HEARTBEAT',
        'RE_SCHEDULE',
        'API',
        'LOG',
    ]

    def __init__(self, host=None, port=None, password=None, buffer_size=1000):
        self.host = host or FS_HOST
        self.port = port or FS_PORT
        self.password = password or FS_PASS

        self.buffer = ESLEventBuffer(max_size=buffer_size)
        self.esl = None
        self.running = False
        self.connected = False
        self.greenlet = None
        self.reconnect_delay = 5  # seconds
        self.last_error = None
        self.connection_attempts = 0
        self.last_event_time = None

    def start(self):
        """Start the event subscriber using gevent greenlet"""
        if self.running:
            return

        if not ESL_AVAILABLE:
            print("[ESL] Cannot start - greenswitch not installed")
            return

        self.running = True
        # Use gevent.spawn for proper async operation with greenswitch
        self.greenlet = gevent.spawn(self._run)
        print(f"[ESL] Event subscriber started for {self.host}:{self.port}")

    def stop(self):
        """Stop the event subscriber"""
        self.running = False
        if self.esl:
            try:
                self.esl.stop()
            except:
                pass
        if self.greenlet:
            try:
                self.greenlet.kill(timeout=5)
            except:
                pass
        print("[ESL] Event subscriber stopped")

    def _run(self):
        """Main subscriber loop with auto-reconnect"""
        while self.running:
            try:
                self._connect_and_subscribe()
            except Exception as e:
                self.last_error = str(e)
                self.connected = False
                print(f"[ESL] Connection error: {e}")

            # Wait before reconnecting (use gevent.sleep!)
            if self.running:
                gevent.sleep(self.reconnect_delay)

    def _connect_and_subscribe(self):
        """Connect to FreeSWITCH and subscribe to events"""
        if not ESL_AVAILABLE:
            raise Exception("greenswitch not installed")

        self.connection_attempts += 1
        print(f"[ESL] Connecting to {self.host}:{self.port} (attempt {self.connection_attempts})")

        self.esl = InboundESL(host=self.host, port=self.port, password=self.password)
        self.esl.connect()
        self.connected = True
        self.last_error = None

        print(f"[ESL] Connected! esl.connected={self.esl.connected}")

        # Register event handler for all events
        self.esl.register_handle('*', self._on_event)

        # Subscribe to ALL events (simpler, more reliable)
        result = self.esl.send('event plain all')
        print(f"[ESL] Subscribed to all events, result={result}")

        # Add initial connection event
        self._add_event({
            'type': 'SYSTEM',
            'subtype': 'CONNECTED',
            'text': f'ESL connected to {self.host}:{self.port}',
            'level': 'info'
        })

        # Start receiving events (blocking call)
        self._receive_events()

    def _on_event(self, event):
        """Callback for incoming ESL events"""
        try:
            self._process_event(event)
        except Exception as e:
            print(f"[ESL] Event handler error: {e}")

    def _receive_events(self):
        """Receive and process events using greenswitch's event loop"""
        try:
            # greenswitch uses gevent - start_event_handlers spawns:
            # - _receive_events_greenlet (reads socket, puts in queue)
            # - _process_events_greenlet (calls handlers from queue)
            print(f"[ESL] Starting event handlers, esl.connected={self.esl.connected}")
            self.esl.start_event_handlers()
            print(f"[ESL] Event handlers started, esl.connected={self.esl.connected}")

            # Wait for the receive greenlet to finish (it runs while connected)
            # This blocks until disconnect or error
            if hasattr(self.esl, '_receive_events_greenlet') and self.esl._receive_events_greenlet:
                print(f"[ESL] Joining receive greenlet...")
                self.esl._receive_events_greenlet.join()
                print(f"[ESL] Receive greenlet finished")
            else:
                print(f"[ESL] No receive greenlet, polling connected status")
                # Fallback: poll connected status
                while self.running and self.esl.connected:
                    gevent.sleep(1)

            print(f"[ESL] Event loop ended, esl.connected={self.esl.connected}")

            # Add disconnect event
            if self.running:
                self._add_event({
                    'type': 'SYSTEM',
                    'subtype': 'DISCONNECTED',
                    'text': f'ESL disconnected from {self.host}:{self.port}',
                    'level': 'warning'
                })

        except Exception as e:
            if self.running:
                print(f"[ESL] Receive error: {e}")
                self._add_event({
                    'type': 'SYSTEM',
                    'subtype': 'ERROR',
                    'text': f'ESL error: {e}',
                    'level': 'error'
                })
        finally:
            self.connected = False

    def _process_event(self, event):
        """Process incoming ESL event"""
        try:
            event_name = event.headers.get('Event-Name', 'UNKNOWN')
            event_subclass = event.headers.get('Event-Subclass', '')

            # Parse event into our format
            parsed = {
                'type': event_name,
                'subtype': event_subclass,
                'timestamp': time.time(),
                'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'level': self._get_event_level(event_name),
                'text': self._format_event_text(event),
                'headers': dict(event.headers) if hasattr(event, 'headers') else {},
            }

            # Extract useful fields based on event type
            if event_name in ('CHANNEL_CREATE', 'CHANNEL_ANSWER', 'CHANNEL_HANGUP', 'CHANNEL_HANGUP_COMPLETE'):
                parsed['caller_id'] = event.headers.get('Caller-Caller-ID-Number', '')
                parsed['callee'] = event.headers.get('Caller-Destination-Number', '')
                parsed['uuid'] = event.headers.get('Unique-ID', '')
                parsed['direction'] = event.headers.get('Call-Direction', '')

            elif 'SOFIA::REGISTER' in event_name or 'register' in event_subclass:
                parsed['user'] = event.headers.get('from-user', event.headers.get('user', ''))
                parsed['ip'] = event.headers.get('network-ip', event.headers.get('ip', ''))
                parsed['profile'] = event.headers.get('profile-name', '')

            elif event_name == 'SOFIA::GATEWAY_STATE' or 'gateway' in event_subclass:
                parsed['gateway'] = event.headers.get('Gateway', '')
                parsed['state'] = event.headers.get('State', '')

            elif event_name == 'LOG':
                parsed['log_level'] = event.headers.get('Log-Level', '')
                parsed['log_file'] = event.headers.get('Log-File', '')
                parsed['log_line'] = event.headers.get('Log-Line', '')
                # Body contains the actual log message
                if hasattr(event, 'body') and event.body:
                    parsed['text'] = event.body[:500]

            self._add_event(parsed)
            self.last_event_time = time.time()

        except Exception as e:
            print(f"[ESL] Event processing error: {e}")

    def _get_event_level(self, event_name):
        """Determine log level from event type"""
        if 'HANGUP' in event_name:
            return 'warning'
        elif 'FAILURE' in event_name or 'ERROR' in event_name:
            return 'error'
        elif 'REGISTER' in event_name:
            return 'info'
        elif event_name == 'LOG':
            return 'debug'
        elif event_name == 'HEARTBEAT':
            return 'debug'
        else:
            return 'info'

    def _format_event_text(self, event):
        """Format event into readable text"""
        event_name = event.headers.get('Event-Name', 'UNKNOWN')
        event_subclass = event.headers.get('Event-Subclass', '')

        if event_name == 'CHANNEL_CREATE':
            caller = event.headers.get('Caller-Caller-ID-Number', 'unknown')
            dest = event.headers.get('Caller-Destination-Number', 'unknown')
            direction = event.headers.get('Call-Direction', '')
            return f"Call {direction}: {caller} -> {dest}"

        elif event_name == 'CHANNEL_ANSWER':
            caller = event.headers.get('Caller-Caller-ID-Number', 'unknown')
            dest = event.headers.get('Caller-Destination-Number', 'unknown')
            return f"Answered: {caller} -> {dest}"

        elif event_name == 'CHANNEL_HANGUP' or event_name == 'CHANNEL_HANGUP_COMPLETE':
            caller = event.headers.get('Caller-Caller-ID-Number', 'unknown')
            cause = event.headers.get('Hangup-Cause', 'unknown')
            return f"Hangup: {caller} ({cause})"

        elif 'REGISTER' in event_name or 'register' in event_subclass:
            user = event.headers.get('from-user', event.headers.get('user', 'unknown'))
            ip = event.headers.get('network-ip', event.headers.get('ip', ''))
            profile = event.headers.get('profile-name', '')
            if 'FAILURE' in event_name or 'failure' in event_subclass:
                return f"Register FAILED: {user}@{ip} [{profile}]"
            elif 'UNREGISTER' in event_name or 'unregister' in event_subclass:
                return f"Unregister: {user}@{ip} [{profile}]"
            else:
                return f"Register: {user}@{ip} [{profile}]"

        elif event_name == 'SOFIA::GATEWAY_STATE' or 'gateway' in event_subclass:
            gw = event.headers.get('Gateway', 'unknown')
            state = event.headers.get('State', 'unknown')
            return f"Gateway {gw}: {state}"

        elif event_name == 'HEARTBEAT':
            uptime = event.headers.get('Up-Time', '')
            sessions = event.headers.get('Session-Count', '0')
            return f"Heartbeat: {sessions} sessions, uptime: {uptime}"

        elif event_name == 'LOG':
            if hasattr(event, 'body') and event.body:
                return event.body[:300]
            return f"[LOG] {event.headers.get('Log-File', '')}"

        else:
            return f"{event_name} {event_subclass}".strip()

    def _add_event(self, event):
        """Add event to buffer"""
        self.buffer.add(event)

    def get_events(self, count=100):
        """Get recent events"""
        return self.buffer.get_recent(count)

    def get_events_since(self, timestamp):
        """Get events since timestamp"""
        return self.buffer.get_since(timestamp)

    def get_status(self):
        """Get subscriber status"""
        return {
            'connected': self.connected,
            'host': f'{self.host}:{self.port}',
            'running': self.running,
            'last_error': self.last_error,
            'connection_attempts': self.connection_attempts,
            'last_event_time': self.last_event_time,
            'buffer_stats': self.buffer.stats(),
            'esl_available': ESL_AVAILABLE
        }

    def send_command(self, command):
        """Send API command to FreeSWITCH"""
        if not ESL_AVAILABLE:
            return {'success': False, 'error': 'ESL not available'}

        try:
            # Use a separate connection for commands
            esl = InboundESL(host=self.host, port=self.port, password=self.password)
            esl.connect()
            result = esl.send(f'api {command}')
            esl.stop()

            if result:
                data = result.data if hasattr(result, 'data') else None
                if data:
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')
                    return {'success': True, 'output': data.strip()}

            return {'success': True, 'output': ''}

        except Exception as e:
            return {'success': False, 'error': str(e)}


# Global subscriber instance
_subscriber = None

def get_subscriber():
    """Get or create the global ESL subscriber"""
    global _subscriber
    if _subscriber is None:
        _subscriber = ESLEventSubscriber()
    return _subscriber

def start_subscriber():
    """Start the global ESL subscriber"""
    sub = get_subscriber()
    if not sub.running:
        sub.start()
    return sub

def stop_subscriber():
    """Stop the global ESL subscriber"""
    global _subscriber
    if _subscriber:
        _subscriber.stop()
        _subscriber = None
