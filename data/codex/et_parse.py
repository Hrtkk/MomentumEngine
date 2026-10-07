import re,json,pathlib
BASE=pathlib.Path(__file__).resolve().parent
def parse(label):
 s=(BASE/(label+'.html')).read_text();chunks=[]
 for m in re.finditer(r'self\.__next_f\.push\((.*?)\)</script>',s):
  try:
   a=json.loads(m[1])
   if len(a)>1 and isinstance(a[1],str):chunks.append(a[1])
  except ValueError:pass
 refs={}
 for line in ''.join(chunks).splitlines():
  try:
   k,v=line.split(':',1);refs[k]=json.loads(v)
  except ValueError:pass
 def resolve(x,seen=frozenset()):
  if isinstance(x,str) and re.fullmatch(r'\$[0-9a-f]+',x) and x[1:] in refs and x not in seen:return resolve(refs[x[1:]],seen|{x})
  if isinstance(x,list):return [resolve(y,seen) for y in x]
  if isinstance(x,dict):return {k:resolve(v,seen) for k,v in x.items()}
  return x
 def walk(x):
  if isinstance(x,dict):
   if 'tableData' in x or ('company' in x and isinstance(x['company'],dict)):yield resolve(x)
   else:
    for v in x.values():yield from walk(v)
  elif isinstance(x,list):
   for v in x:yield from walk(v)
 found=[]
 for obj in refs.values():found.extend(walk(obj))
 if not found:
  text=''.join(chunks)
  for m in re.finditer(r'"company":',text):
   try:
    company,_=json.JSONDecoder().raw_decode(text[m.end():])
    if isinstance(company,dict) and 'nse' in company:found.append({'company':company})
   except ValueError:pass
 return found
if __name__=='__main__':
 for n in ['gainers','sma','et_probe_2']:
  d=parse(n);(BASE/(n+'_parsed.json')).write_text(json.dumps(d,indent=2));print(n,len(d))
  for x in d:
   if 'tableData' in x:print('KEYS',list(x));print('FIRST',x['tableData'][0]);print('LAST',x['tableData'][-1]);print('OTHER',{k:v for k,v in x.items() if any(t in k.lower() for t in ['date','time','payload','summary'])})
   else:print('KEYS',list(x),'NSE',x['company']['nse'])
