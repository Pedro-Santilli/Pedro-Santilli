"""Generate profile cards and an animated contribution snake from public GitHub data."""
from pathlib import Path
from html import escape
from html.parser import HTMLParser
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import json, os, re, urllib.request
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parent
ASSETS=ROOT/'assets'
USER='Pedro-Santilli'
COLORS={'Swift':'#F05138','Dart':'#00B4AB','TypeScript':'#3178C6','JavaScript':'#F1E05A','HTML':'#E34C26','CSS':'#563D7C','Python':'#3572A5','Kotlin':'#A97BFF','Java':'#B07219','Go':'#00ADD8'}
def fetch(url):
 headers={'User-Agent':'Pedro-Santilli-profile','Accept':'application/vnd.github+json' if 'api.github.com' in url else 'text/html'}
 if 'api.github.com' in url and os.getenv('GH_TOKEN'):headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
 with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=40) as r:return r.read()
def api(path):return json.loads(fetch('https://api.github.com'+path))
def svg(w,h,body):
 return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img"><rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="12" fill="#0d1117" stroke="#303b54"/>{body}</svg>'
def text(x,y,s,size=14,color='#a9b1d6',bold=False):
 return f'<text x="{x}" y="{y}" fill="{color}" font-family="Segoe UI,Arial,sans-serif" font-size="{size}" font-weight="{700 if bold else 400}">{escape(str(s))}</text>'
class Calendar(HTMLParser):
 def __init__(self):super().__init__();self.days=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if a.get('data-date') and a.get('data-level') is not None:self.days.append((a['data-date'],int(a['data-level'])))
def generate():
 ASSETS.mkdir(exist_ok=True)
 user=api('/users/'+USER)
 repos=[];page=1
 while True:
  batch=api(f'/users/{USER}/repos?per_page=100&page={page}')
  repos+=batch
  if len(batch)<100:break
  page+=1
 html=fetch(f'https://github.com/users/{USER}/contributions').decode()
 cal=Calendar();cal.feed(html)
 if not cal.days:raise ValueError('Contribution calendar was empty')
 match=re.search(r'id="js-contribution-activity-description"[^>]*>\s*([\d,]+)',html)
 if not match:raise ValueError('Contribution total not found')
 contributions=int(match.group(1).replace(',',''))
 originals=[r for r in repos if not r['fork']]
 langs={}
 with ThreadPoolExecutor(max_workers=4) as pool:
  for obj in pool.map(lambda r:api('/repos/'+r['full_name']+'/languages'),originals):
   for k,v in obj.items():langs[k]=langs.get(k,0)+v
 stamp=datetime.now(timezone.utc).strftime('%Y-%m-%d')
 rows=[('Public repositories',user['public_repos']),('Contributions · last year',contributions),('Stars earned',sum(r['stargazers_count'] for r in originals)),('Repository forks',sum(r['forks_count'] for r in originals)),('Followers',user['followers'])]
 body=text(24,34,"Pedro's GitHub stats",18,'#7aa2f7',True)
 for i,(label,val) in enumerate(rows):
  y=70+i*29
  body+=f'<circle cx="28" cy="{y-5}" r="3" fill="#bb9af7"/>'+text(42,y,label,13)+text(284,y,val,14,'#c0caf5',True)
 body+='<circle cx="405" cy="124" r="48" fill="none" stroke="#242b43" stroke-width="7"/><circle cx="405" cy="124" r="48" fill="none" stroke="#7aa2f7" stroke-width="7" stroke-dasharray="220 302" transform="rotate(-90 405 124)"/>'
 body+=text(387,122,'</>',23,'#bb9af7',True)+text(381,143,'BUILD',11,'#7dcfff',True)+text(24,239,'Public GitHub data · '+stamp,10,'#737c9b')
 (ASSETS/'stats.svg').write_text(svg(500,255,body))
 top=sorted(langs.items(),key=lambda kv:kv[1],reverse=True)[:6]
 total=sum(langs.values())
 body=text(24,34,'Most used languages',18,'#7aa2f7',True)
 for i,(lang,v) in enumerate(top):
  row=i//2;col=i%2;x=24+col*239;y=72+row*51;pct=v/total*100
  body+=text(x,y,lang,13,'#c0caf5',True)+text(x+142,y,f'{pct:.1f}%',12)
  body+=f'<rect x="{x}" y="{y+9}" width="204" height="7" rx="3" fill="#242b43"/><rect x="{x}" y="{y+9}" width="{max(2,204*pct/100):.1f}" height="7" rx="3" fill="{COLORS.get(lang,"#bb9af7")}"/>'
 body+=text(24,239,'By code bytes · public non-fork repositories',10,'#737c9b')
 (ASSETS/'languages.svg').write_text(svg(500,255,body))
 # Real calendar levels, animated with a decorative snake following a complete path.
 from datetime import date,timedelta
 days=dict(cal.days);start=date.fromisoformat(min(days));start-=timedelta(days=(start.weekday()+1)%7)
 end=date.fromisoformat(max(days));cols=(end-start).days//7+1
 path=[]
 for x in range(cols):
  for y in (range(7) if x%2==0 else range(6,-1,-1)):path.append((x,y))
 palette=['#161b22','#283457','#445a91','#7aa2f7','#bb9af7']
 frames=[];steps=range(0,len(path)+16,3)
 for step in steps:
  im=Image.new('RGB',(cols*17+32,151),'#0d1117');d=ImageDraw.Draw(im)
  consumed=set(path[:max(0,step-7)])
  for x in range(cols):
   for y in range(7):
    day=(start+timedelta(days=x*7+y)).isoformat();lv=days.get(day,0)
    color=palette[0] if (x,y) in consumed else palette[lv]
    xx=16+x*17;yy=16+y*17
    d.rounded_rectangle((xx,yy,xx+12,yy+12),radius=3,fill=color)
  for j in range(7):
   idx=step-j
   if 0<=idx<len(path):
    x,y=path[idx];xx=16+x*17;yy=16+y*17
    d.rounded_rectangle((xx,yy,xx+12,yy+12),radius=3,fill='#7dcfff' if j==0 else '#7aa2f7')
    if j==0:d.rectangle((xx+8,yy+3,xx+9,yy+5),fill='#0d1117')
  frames.append(im)
 frames[0].save(ASSETS/'contributions.gif',save_all=True,append_images=frames[1:],duration=[1000]+[65]*(len(frames)-2)+[600],loop=0,optimize=True,disposal=2)
 (ASSETS/'data.json').write_text(json.dumps({'user':USER,'updated_at':stamp,'public_repositories':user['public_repos'],'contributions_last_year':contributions,'languages_bytes':langs},indent=2))
 print('Updated cards and contribution snake:',stamp,contributions,'contributions')
if __name__=='__main__':generate()
