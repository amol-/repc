import redis, traceback, sys, os

try:
    import json
except:
    import simplejson as json

class RepcServer(object):
    def __init__(self, server, namespace, sid=0, serverdb=0, lockpath='/tmp'):
        self.namespace = namespace
        self.server = server
        self.sid = sid
        self.obj = None

        self.lock_file = os.path.join(lockpath, 'repc-lock-%s' % self.sid)
        if os.path.exists(self.lock_file):
            self.lock_file = None
            raise Exception("A Repc Server with this SID is already running")
        else:
            open(self.lock_file, 'w').close()
        
        self.redis = redis.Redis(self.server[0], self.server[1], serverdb)
        self.run_queue = self.namespace+'-run-'+str(self.sid)

    def __del__(self):
        if self.lock_file:
            os.remove(self.lock_file)
            
    def register(self, obj):
        self.obj = obj

    def get_call(self):
        call = self.redis.blpop(self.namespace)
        call = json.loads(call[1])
        call['params'] = json.loads(call['params'])
        self.send_answer(call['client'], 'Runqueued', self.sid)
        return call

    def answer_queue_for_client(self, client):
        return self.namespace+'-ans-'+str(client)

    def send_answer(self, client, atype, answer):
        ans = json.dumps({'type':atype, 'ans':answer})
        self.redis.rpush(self.answer_queue_for_client(client), ans)

    def exec_call(self, call):
        m = getattr(self.obj, call['action'], None)
        if not m and not call['async']:
            self.send_answer(call['client'], 'NotFoundError', call['action'])
            return

        try:
            res = m(*call['params']['args'], **call['params']['kw'])
        except Exception, e:
            if not call['async']:
                tb = traceback.extract_tb(sys.exc_info()[2])
                self.send_answer(call['client'], 'Exception', {'class':e.__class__.__name__,
                                                                'msg': str(e),
                                                                'args':e.args,
                                                                'tb':tb})
        else:
            if not call['async']:
                self.send_answer(call['client'], 'Return', res)
        

    def run(self):
        while self.redis.llen(self.run_queue):
            print 'Recovering Tasks'
            pending_task = self.redis.lindex(self.run_queue, 0)
            if pending_task:
                pending_task = json.loads(pending_task)
                self.exec_call(pending_task)
                self.redis.lpop(self.run_queue)
        
        while True:
            call = self.get_call()
            self.exec_call(call)
            self.redis.lpop(self.run_queue)
              
if __name__ == '__main__':
    class TestClass(object):
        def inc(self, num):
            return num+1

        def excp(self):
            raise Exception('remote')

    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-s", "--sid", dest="sid", default="0", metavar="SID", 
                                     help="set unique server instance identificator")
    (options, args) = parser.parse_args()

    srv = RepcServer(('localhost', 6379), 'test', sid=options.sid)
    srv.register(TestClass())
    srv.run()