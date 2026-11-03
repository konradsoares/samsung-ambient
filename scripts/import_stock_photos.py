#!/usr/bin/env python3
"""Populate 8 x 25 licensed landscape photos from Wikimedia Commons.

Requires Pillow and outbound HTTPS. Run from repo root; designed for GitHub Actions.
Output: docs/images/<group>/*.jpg, docs/attribution.json, docs/ATTRIBUTION.md.
Only chooses photographic files with explicitly recognized free licenses.
"""
import argparse
import html
import io
import json
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from PIL import Image, ImageOps, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
API = 'https://commons.wikimedia.org/w/api.php'
AGENT = 'SamsungAmbientGallery/3.0 (personal noncommercial photo display; contact via GitHub repository issue tracker) Python-urllib'
# Wikimedia categories verified from Commons featured-landscape index.
GROUPS = {
    'mountains': ['Featured pictures of mountains', 'Featured pictures of landscapes'],
    'forests': ['Featured pictures of forests', 'Featured pictures of landscapes'],
    'coasts': ['Featured pictures of coasts', 'Featured pictures of landscapes'],
    'water': ['Featured pictures of bodies of water', 'Featured pictures of landscapes'],
    'islands': ['Featured pictures of islands', 'Featured pictures of landscapes'],
    'volcanoes': ['Featured pictures of volcanoes', 'Featured pictures of landscapes'],
    'countryside': ['Featured pictures of agriculture', 'Featured pictures of landscapes'],
    'landscapes': ['Featured pictures of landscapes', 'Quality images of landscapes'],
}
ALLOWED = re.compile(r'^(?:CC0|Public domain|CC BY(?:-SA)?(?: [234]\.?[0-9])?(?: [a-z]{2})?)$',re.I)

def req(url, params=None, binary=False):
    if params: url += ('&' if '?' in url else '?')+urlencode(params)
    err = None
    for attempt in range(5):
        try:
            with urlopen(Request(url, headers={'User-Agent': AGENT,'Accept':'application/json' if not binary else 'image/*'}),timeout=35) as r:
                payload = r.read(15_000_000 if binary else 4_000_000)
                return payload if binary else json.loads(payload)
        except (HTTPError, URLError, TimeoutError, ValueError) as e:
            err=e
            if isinstance(e,HTTPError) and e.code in (400,401,403,404): break
            time.sleep(min(2**attempt,12))
    raise RuntimeError(f'HTTP fetch failed: {url[:160]} ({err})')

def titles_for_category(name, limit=160):
    titles=[]; cont={}
    while len(titles)<limit:
        d=req(API,{'action':'query','format':'json','list':'categorymembers','cmtitle':'Category:'+name,'cmtype':'file','cmlimit':100,**cont})
        titles += [i['title'] for i in d.get('query',{}).get('categorymembers',[]) if i.get('title','').lower().endswith(('.jpg','.jpeg','.png'))]
        if 'continue' not in d: break
        cont=d['continue']
    return titles[:limit]

def info_for_titles(titles):
    out=[]
    for start in range(0,len(titles),20):
        d=req(API,{'action':'query','format':'json','prop':'imageinfo','titles':'|'.join(titles[start:start+20]),'iiprop':'url|size|mime|extmetadata','iiurlwidth':1920,'iiextmetadatafilter':'LicenseShortName|LicenseUrl|Artist|Credit|AttributionRequired|Restrictions','formatversion':2})
        for pg in d.get('query',{}).get('pages',[]):
            if pg.get('imageinfo'): out.append((pg['title'],pg['imageinfo'][0]))
        time.sleep(.1)
    return out

def meta_value(info,key): return html.unescape(re.sub(r'<[^>]*>',' ',info.get('extmetadata',{}).get(key,{}).get('value',''))).strip()

def license_approved(i):
    lic=meta_value(i,'LicenseShortName').replace('CC BY-SA 4.0 International','CC BY-SA 4.0')
    if not ALLOWED.match(lic): return False
    if meta_value(i,'Restrictions'): return False
    return True

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--per-group',type=int,default=25)
    ap.add_argument('--width',type=int,default=1920)
    ap.add_argument('--height',type=int,default=1080)
    ap.add_argument('--dry-run',action='store_true',help='only print category plan without API calls')
    a=ap.parse_args()
    if a.per_group<1 or a.width<320 or a.height<240: ap.error('Invalid dimensions or photo count')
    if a.dry_run:
        print(json.dumps({'groups':GROUPS,'target_per_group':a.per_group,'total':len(GROUPS)*a.per_group},indent=2));return
    records=[]; used=set(); imgs=DOCS/'images'; imgs.mkdir(parents=True,exist_ok=True)
    for group,categories in GROUPS.items():
        folder=imgs/group;folder.mkdir(exist_ok=True)
        # Idempotence: clear our numbered downloads and rebuild attribution from actual selection.
        for old in folder.glob('stock-*.jpg'): old.unlink()
        got=0
        for category in categories:
            if got>=a.per_group: break
            print(f'{group}: querying {category}',flush=True)
            try: titles=titles_for_category(category)
            except RuntimeError as e:
                print(f'WARNING: {e}',file=sys.stderr);continue
            try: entries=info_for_titles([t for t in titles if t not in used])
            except RuntimeError as e:
                print(f'WARNING: {e}',file=sys.stderr);continue
            for title,i in entries:
                if got>=a.per_group: break
                if title in used or not license_approved(i): continue
                w,h=i.get('width',0),i.get('height',0)
                if w<1600 or h<900 or w<=h or i.get('mime') not in ('image/jpeg','image/png'):continue
                imgurl=i.get('thumburl') or i.get('url')
                if not imgurl or not imgurl.startswith('https://'):continue
                try:
                    content=req(imgurl,binary=True)
                    im=Image.open(io.BytesIO(content))
                    im=ImageOps.exif_transpose(im).convert('RGB')
                    if im.width<=im.height:continue
                    im=ImageOps.fit(im,(a.width,a.height),method=Image.Resampling.LANCZOS,centering=(.5,.5))
                    target=folder/f'stock-{got+1:03}.jpg'
                    im.save(target,'JPEG',quality=83,optimize=True,progressive=True)
                except (RuntimeError,OSError,UnidentifiedImageError) as e:
                    print(f'SKIP {title}: {e}',file=sys.stderr);continue
                used.add(title);got+=1
                records.append({'group':group,'file':f'images/{group}/{target.name}','title':title.removeprefix('File:'),'source':i.get('descriptionurl',''),'artist':meta_value(i,'Artist'),'credit':meta_value(i,'Credit'),'license':meta_value(i,'LicenseShortName'),'license_url':meta_value(i,'LicenseUrl'),'modified':'Cropped/resized for 16:9 TV display'})
                print(f'  {got:02d}/{a.per_group} {title[:70]} ({target.stat().st_size//1024} KB)',flush=True)
        if got!=a.per_group:
            raise RuntimeError(f'Only {got}/{a.per_group} usable licensed photos found for {group}. Retry or adjust categories.')
    (DOCS/'attribution.json').write_text(json.dumps(records,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    lines=['# Photo credits and licenses','',f'{len(records)} photographs from Wikimedia Commons. Each photo was resized/cropped to 16:9.','','Photographs are redistributed under their respective individual licenses; application code has separate licensing.','']
    for n,r in enumerate(records,1):
        lines += [f'## {n}. {r["group"]} — {r["title"]}',f'- Local file: `{r["file"]}`',f'- Source: {r["source"]}',f'- Artist: {r["artist"] or "See source file page"}',f'- License: {r["license"]} — {r["license_url"]}',f'- Modification: {r["modified"]}','']
    (DOCS/'ATTRIBUTION.md').write_text('\n'.join(lines),encoding='utf-8')
    print(f'DONE: {len(records)} images, 8 groups. See docs/ATTRIBUTION.md',flush=True)

if __name__=='__main__':main()
