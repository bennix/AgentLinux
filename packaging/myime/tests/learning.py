import subprocess,json,os,tempfile,sqlite3
from pathlib import Path
root=Path(tempfile.mkdtemp())
env=dict(os.environ,XDG_DATA_HOME=str(root),XDG_CONFIG_HOME=str(root/'config'))
host='/usr/lib/myime/MyIMEHost'
def start(): return subprocess.Popen([host],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
def call(op,**kw):
 p.stdin.write(json.dumps(dict(op=op,**kw))+'\n');p.stdin.flush()
 return json.loads(p.stdout.readline())
def stop():
 p.stdin.close();assert p.wait()==0
def words(result): return [w.split(" · ")[0] for w in result["words"]]
p=start()
r=call('append',text='nihao')
assert '你好' in words(r)
r=call('select',index=words(r).index('你好'))
assert r['commit']=='你好' and r['suggesting'] and r['words']
print('你好 ->',words(r)[:5],flush=True)
r=call('select',index=0)
assert r['commit']
call('reset')
r=call('append',text='shi')
orig=words(r)
target=orig[3]
for _ in range(12):
 r=call('select',index=words(r).index(target)); assert r['commit']==target
 call('reset')
 r=call('append',text='shi')
stop()
p=start()
r=call('append',text='shi')
print(target, 'rank before/after restart', orig.index(target)+1, words(r).index(target)+1,flush=True)
assert words(r).index(target)<orig.index(target)
stop()
