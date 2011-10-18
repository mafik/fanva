'''
Created on 2010-11-02

@author: Marek Rogalski
'''

from os import path
import pickle
from poliqarp import *

pid = '/tmp/translator.pid'

pid_exists = path.exists(pid)
corpus_path = 'default'

conn = None

if not pid_exists:
    conn = Connection()
    try:
        s_id = conn.make_session()
    except:
        print("Couldn't connect to poliqarp. Is the daemon running?")
        exit(1)
    conn.open_corpus(corpus_path)
    conn.set_retrieve_tags(False, True, False, False)
    with open(pid, 'wb') as pid_file:
        pickle.dump(s_id, pid_file)
else:
    with open(pid, 'rb') as pid_file:
        s_id = pickle.load(pid_file)
        conn = Connection()
        conn.make_session(session_id=s_id)
        
def query(q):
    print('[Poliqarp] "{}"'.format(q))
    conn.make_query(q)
    conn.run_query(1, timeout=100)
    if conn.get_n_spotted_results() == 0: return None
    return conn.get_results(0, 0)[0][1][1]
    
