import redis, traceback, time

try:
    import json
except:
    import simplejson as json

class RemoteException(Exception):
    """
    Keeps track of an exception raised on a remote side
    of the communication
    """
    def __init__(self, reclass, reargs, remsg, retb):
        super(RemoteException, self).__init__(reargs)
        self.message = '%s: %s' % (reclass, remsg)
        self.exception_class = reclass
        self.tb = retb

    def __str__(self):
        s = '\n'
        s += "Traceback (most recent call last):\n"
        s += ''.join(traceback.format_list (self.tb))
        s += self.message
        return s

class ServerError(object):
    pass
ServerError = ServerError()

class RepcClient(object):
    def __init__(self, server, namespace, serverdb=0):
        self.namespace = namespace
        self.server = server
        self.server_db = serverdb
        
        self.client_id = self.determine_client_id()
        self.ans_queue = self.namespace+'-ans-'+str(self.client_id)

    def determine_client_id(self):
        self.redis = redis.Redis(self.server[0], self.server[1], self.server_db)
        self.redis.expire(self.ans_queue, 60*5)
        return self.redis.incr(self.namespace+'-clients')

    def run_queue_for_server(self, server):
        return self.namespace+'-run-'+str(server)

    def get_running_server(self):
        running_on = self.redis.blpop(self.ans_queue, 1)
        if not running_on:
            return False
        else:
            running_on = json.loads(running_on[1])
            if running_on['type'] != 'Runqueued':
                return False
            return running_on['ans']
        
    def call(self, action, args, parameters, async=False):
        data = json.dumps({'args':args, 'kw':parameters})
        call_data = json.dumps({'client': self.client_id, 'action':action, 'params':data, 'async':async})

        running = False
        while not running:
            while self.redis.llen(self.namespace):
                time.sleep(1)
            self.redis.rpush(self.namespace, call_data)
            running = self.get_running_server()

        self.redis.rpush(self.run_queue_for_server(running), call_data)
        self.redis.expire(self.run_queue_for_server(running), 60*15)

        if not async:
            ans = self.redis.blpop(self.ans_queue)
            ans = json.loads(ans[1])
            if ans['type'] == 'Return':
                return ans['ans']
            elif ans['type'] == 'NotFoundError':
                raise Exception('Method not found %s' % ans['ans'])
            elif ans['type'] == 'Exception':
                raise RemoteException(ans['ans']['class'], ans['ans']['args'],
                                      ans['ans']['msg'], ans['ans']['tb'])
            

    def close(self):
        self.redis.delete(self.namespace+'-ans-'+str(self.client_id))

    def __del__(self):
        self.close()

    def __getattr__(self, attr):
        class RemoteMethod (object):
            def __init__ (self, client, method_name):
                super (RemoteMethod, self).__init__()
                self.client = client
                self.name = method_name

            def __getattr__ (self, name):
                return RemoteMethod (self.client, '%s.%s' % (self.name, name))

            def __call__ (self, *args, **kw):
                return self.client.call(self.name, args, kw)

        return RemoteMethod(self, attr)

if __name__ == '__main__':
    import threading

    class TestThread(threading.Thread):
        def run(self):            
            cli = RepcClient(('localhost', 6379), 'test')
            self.x = 0
            for i in xrange(2500):
                self.x = cli.inc(num=self.x)
                self.x = cli.inc(self.x)

    t = []
    for ti in xrange(2):
        t.append(TestThread())
        t[-1].start()

    for ti in t:
        ti.join()
        print ti.x