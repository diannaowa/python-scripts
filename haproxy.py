#!/usr/bin/env python

"""zwliu@thouthworks.com
   I get this code from ansible 
   url:https://github.com/ansible/ansible-modules-extras/blob/8449fb3c900f1c20f7a39af713210c355ef2f27b/network/haproxy.py
"""
import socket
import csv
import time
from string import Template


RECV_SIZE = 1024
WAIT_RETRIES=25
WAIT_INTERVAL=5

class TimeoutException(Exception):
  pass

class HAProxy(object):
    """
    Used for communicating with HAProxy through its local UNIX socket interface.
    Perform common tasks in Haproxy related to enable server and
    disable server.
    The complete set of external commands Haproxy handles is documented
    on their website:
    http://haproxy.1wt.eu/download/1.5/doc/configuration.txt#Unix Socket commands
    """

    def __init__(self, socket):

        self.socket = socket
        self.shutdown_sessions = True
        self.fail_on_not_found = 'no'
        self.wait = 'yes'
        self.wait_retries = 2
        self.wait_interval = 3
        self.command_results = {}

    def execute(self, cmd, timeout=200, capture_output=True):
        """
        Executes a HAProxy command by sending a message to a HAProxy's local
        UNIX socket and waiting up to 'timeout' milliseconds for the response.
        """
        self.client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.client.connect(self.socket)
        self.client.sendall('%s\n' % cmd)
        result = ''
        buf = ''
        buf = self.client.recv(RECV_SIZE)
        while buf:
            result += buf
            buf = self.client.recv(RECV_SIZE)
        if capture_output:
            self.capture_command_output(cmd, result.strip())
        self.client.close()
        return result


    def capture_command_output(self, cmd, output):
        """
        Capture the output for a command
        """
        if not 'command' in self.command_results.keys():
            self.command_results['command'] = []
        self.command_results['command'].append(cmd)
        if not 'output' in self.command_results.keys():
            self.command_results['output'] = []
        self.command_results['output'].append(output)


    def discover_all_backends(self):
        """
        Discover all entries with svname = 'BACKEND' and return a list of their corresponding
        pxnames
        """
        data = self.execute('show stat', 200, False).lstrip('# ')
	print data
        r = csv.DictReader(data.splitlines())
        return map(lambda d: d['pxname'], filter(lambda d: d['svname'] == 'BACKEND', r))


    def execute_for_backends(self, cmd, pxname, svname, wait_for_status = None):
        """
        Run some command on the specified backends. If no backends are provided they will
        be discovered automatically (all backends)
        """
        # Discover backends if none are given
        if pxname is None:
            backends = self.discover_all_backends()
        else:
            backends = [pxname]

        # Run the command for each requested backend
        for backend in backends:
            # Fail when backends were not found
            state = self.get_state_for(backend, svname)
            if (self.fail_on_not_found or self.wait) and state is None:
            	assert False,"The specified backend '%s/%s' was not found!" % (backend, svname)

            self.execute(Template(cmd).substitute(pxname = backend, svname = svname))
            if self.wait:
                self.wait_until_status(backend, svname, wait_for_status)


    def get_state_for(self, pxname, svname):
        """
        Find the state of specific services. When pxname is not set, get all backends for a specific host.
        Returns a list of dictionaries containing the status and weight for those services.
        """
        data = self.execute('show stat', 200, False).lstrip('# ')
        r = csv.DictReader(data.splitlines())
        state = map(lambda d: { 'status': d['status'], 'weight': d['weight'] }, filter(lambda d: (pxname is None or d['pxname'] == pxname) and d['svname'] == svname, r))
        return state or None


    def wait_until_status(self, pxname, svname, status):
        """
        Wait for a service to reach the specified status. Try RETRIES times
        with INTERVAL seconds of sleep in between. If the service has not reached
        the expected status in that time, the module will fail. If the service was 
        not found, the module will fail.
        """
	print pxname,svname,status
        for i in range(1, self.wait_retries):
            state = self.get_state_for(pxname, svname)
	    print state
            # We can assume there will only be 1 element in state because both svname and pxname are always set when we get here
            if state[0]['status'] == status:
                return True
            else:
                time.sleep(self.wait_interval)

        assert False,"server %s/%s not status '%s' after %d retries. Aborting." % (pxname, svname, status, self.wait_retries)


    def enabled(self, host, backend, weight):
        """
        Enabled action, marks server to UP and checks are re-enabled,
        also supports to get current weight for server (default) and
        set the weight for haproxy backend server when provides.
        """
        cmd = "get weight $pxname/$svname; enable server $pxname/$svname"
        if weight:
            cmd += "; set weight $pxname/$svname %s" % weight
        self.execute_for_backends(cmd, backend, host, 'UP')


    def disabled(self, host, backend, shutdown_sessions):
        """
        Disabled action, marks server to DOWN for maintenance. In this mode, no more checks will be
        performed on the server until it leaves maintenance,
        also it shutdown sessions while disabling backend host server.
        """
        cmd = "get weight $pxname/$svname; disable server $pxname/$svname"
        if shutdown_sessions:
            cmd += "; shutdown sessions server $pxname/$svname"
        self.execute_for_backends(cmd, backend, host, 'MAINT')




if __name__ == '__main__':

	h = HAProxy('/var/run/haproxy/admin.sock')
	print h.discover_all_backends()
	#print h.disabled('web1','web','yes')
	print h.enabled('web1','web',10)
	#print h.get_state_for('web','BACKEND')
	print h.discover_all_backends()
