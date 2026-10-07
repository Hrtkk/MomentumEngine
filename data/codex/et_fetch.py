import urllib.request,urllib.error,json,datetime,pathlib,concurrent.futures,sys
BASE=pathlib.Path(__file__).resolve().parent
LOG=BASE/'et_retrieval_log.json'
def fetch(pair):
 label,url=pair[:2]
 body=pair[2] if len(pair)>2 else None
 r={'url':url,'method':'POST' if body is not None else 'GET','request_body':body,'retrieved_ist':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5,minutes=30))).isoformat()}
 try:
  req=urllib.request.Request(url,data=json.dumps(body).encode() if body is not None else None,headers={'User-Agent':'Mozilla/5.0','Accept':'text/html,application/json','Content-Type':'application/json','Origin':'https://economictimes.indiatimes.com','Referer':'https://economictimes.indiatimes.com/'})
  with urllib.request.urlopen(req,timeout=35) as f: data=f.read();r.update(status=f.status,final_url=f.url,headers=dict(f.headers))
 except urllib.error.HTTPError as e:data=e.read();r.update(status=e.code,final_url=e.url,headers=dict(e.headers))
 except Exception as e:data=b'';r.update(error=repr(e))
 p=BASE/(label+'.html');p.write_bytes(data);r.update(body_file=str(p),bytes=len(data));return r
def batch(pairs):
 rs=list(concurrent.futures.ThreadPoolExecutor(max_workers=5).map(fetch,pairs))
 old=json.loads(LOG.read_text()) if LOG.exists() else [];LOG.write_text(json.dumps(old+rs,indent=2))
 for r in rs:print({k:v for k,v in r.items() if k!='headers'})
 return rs
if __name__=='__main__':batch([tuple(x.split('=',1)) for x in sys.argv[1:]])
