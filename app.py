import asyncio, os, json, secrets, hmac, base64
from pathlib import Path
from html import escape
from functools import wraps
import discord
from discord import app_commands
from aiohttp import web
from core import day, draw, credits

guild_id = int(os.environ['GUILD_ID'])
secret = os.environ['ADMIN_PASSWORD']
if len(secret)<16: raise RuntimeError("ADMIN_PASSWORD は16文字以上にしてください")
db = Path('events.json')
events = json.loads(db.read_text()) if db.exists() else {}
def save():
    tmp = db.with_suffix('.tmp')
    tmp.write_text(json.dumps(events,ensure_ascii=False))
    tmp.replace(db)

intents = discord.Intents.default()
intents.members = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)
scope = discord.Object(id=guild_id)
lock = asyncio.Lock()
csrf = secrets.token_urlsafe()
def guild(): return bot.get_guild(guild_id)
def esc(x): return escape(str(x), quote=True)
def view(*buttons):
    v=discord.ui.View(timeout=None)
    for label, key in buttons:
        v.add_item(discord.ui.Button(label=label,custom_id=key,style=discord.ButtonStyle.primary))
    return v

@tree.command(name="クラ活募集", description="出欠・賞金・集合チャンネルを設定して募集", guild=scope)
@app_commands.checks.has_permissions(manage_guild=True)
async def recruit(it:discord.Interaction, 日付:str, 時刻:str, 対象:discord.Role, 出欠:discord.TextChannel, 賞金:discord.TextChannel, 集合:discord.VoiceChannel):
    from datetime import datetime
    try: datetime.strptime(日付+' '+時刻,'%Y-%m-%d %H:%M')
    except ValueError: return await it.response.send_message('日付 YYYY-MM-DD、時刻 HH:MM で入力してください。',ephemeral=True)
    await it.response.defer(ephemeral=True)
    key=secrets.token_hex(5)
    events[key]=dict(date=日付,time=時刻,role=対象.id,voice=集合.id,channel=出欠.id,prize=賞金.id,attendance={},rounds=[],matches=[],paid={},rules=[],names={})
    save()
    try:
        await 出欠.send(f'{日付} {時刻} クラ活｜{対象.name}｜集合 {集合.mention}',view=view(('参加',f'in:{key}'),('欠席',f'out:{key}')))
    except discord.HTTPException:
        del events[key]; save()
        return await it.followup.send('募集を投稿できません。出欠チャンネルの送信権限を確認してください。',ephemeral=True)
    await it.followup.send('募集を開始しました。',ephemeral=True)

@bot.event
async def on_interaction(it):
    if it.type!=discord.InteractionType.component or it.guild_id!=guild_id: return
    parts=it.data['custom_id'].split(':')
    if len(parts)<2 or parts[1] not in events: return
    act,key,*args=parts
    await it.response.defer(ephemeral=True)
    async with lock:
        e=events[key]; p=str(it.user.id)
        if act in ('in','out'):
            if e.get('closed'): msg='出欠は締め切りました。変更は運営へ。'
            elif e['role'] not in [r.id for r in it.user.roles]: msg='対象ロールのメンバーのみ回答できます。'
            else:
                e['attendance'][p]=act; e['names'][p]=it.user.display_name
                save(); msg='参加で登録しました。' if act=='in' else '欠席で登録しました。'
        elif act=='win':
            m=e['matches'][int(args[0])]
            idx=next((i for i,t in enumerate(m['teams']) if p in t),None)
            if idx is None: msg='この試合の出場者のみ申告できます。'
            elif 'winner' in m: msg='この試合は承認済みです。'
            elif idx in m['claims']: msg='チームの申告は受付済みです。'
            else: m['claims'].append(idx); save(); msg='勝利申告を受け付けました。'
        else: return
    await it.followup.send(msg,ephemeral=True)

def roster(e):
    g=guild()
    return {str(m.id):m for m in g.members if not m.bot and g.get_role(e['role']) in m.roles}
def present(m,e): return bool(m.voice and m.voice.channel and m.voice.channel.id==e['voice'])
def name(e,p):
    m=guild().get_member(int(p))
    return esc(m.display_name if m else e['names'].get(p,p))
def teams_html(e,r):
    return ''.join(f'<p><b>TEAM {i:02}</b>　'+' ／ '.join(name(e,p) for p in t)+'</p>' for i,t in enumerate(r['teams'],1))+'<small>待機　'+('、'.join(name(e,p) for p in r['wait']) or 'なし')+'</small>'
def select(key,options,selected=None):
    return f'<select name="{key}">'+''.join(f'<option value="{esc(v)}" {"selected" if str(v)==str(selected) else ""}>{esc(s)}</option>' for v,s in options)+'</select>'
def form(act,body,label):
    return f'<form method="post"><input type="hidden" name="csrf" value="{csrf}"><input type="hidden" name="act" value="{act}">{body}<button>{label}</button></form>'
def page(content):
    return web.Response(content_type='text/html',text='''<!doctype html><html lang="ja"><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>宙AIM｜クラ活運営</title><style>
    *{box-sizing:border-box}body{margin:0;background:#10131b;color:#edf2fb;font:16px/1.65 system-ui}main{max-width:1040px;margin:auto;padding:30px 18px}header{color:#9eaefb;font-weight:800;letter-spacing:.12em}section{background:#1b2030;border:1px solid #373e56;border-radius:14px;padding:20px;margin:16px 0}h1,h2{margin:0 0 12px}h2{font-size:20px}form{display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin:10px 0}button,input,select{font:inherit;border-radius:7px;border:1px solid #586183;padding:7px;max-width:100%}button{background:#b0bcff;color:#121626;font-weight:700;cursor:pointer}a,small,b{color:#b5c6ff}p{margin:6px 0}details{margin:10px 0}@media(prefers-reduced-motion:no-preference){.draw p{animation:reveal .45s both}.draw p:nth-child(2){animation-delay:.18s}.draw p:nth-child(n+3){animation-delay:.36s}@keyframes reveal{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}}</style><main><header>宙AIM ／ CLAN ACTIVITY</header>'''+content+'</main></html>')
@web.middleware
async def auth(req,handler):
    expected='Basic '+base64.b64encode(('admin:'+secret).encode()).decode()
    if not hmac.compare_digest(req.headers.get('Authorization','').encode(),expected.encode()):
        return web.Response(status=401,headers={'WWW-Authenticate':'Basic realm="SORA AIM"'})
    if not bot.is_ready() or not guild(): return web.Response(status=503,text='BOT 接続待ち。設定を確認して再読み込みしてください。')
    return await handler(req)
async def home(req):
    return page('<h1>クラ活一覧</h1>'+(''.join(f'<section><a href="/e/{k}">{esc(e["date"])}　{esc(e["time"])} のクラ活</a></section>' for k,e in reversed(events.items())) or '<p>Discordで /クラ活募集 を実行してください。</p>'))
async def dashboard(req):
    e=events.get(req.match_info['key'])
    if not e: raise web.HTTPNotFound()
    members=roster(e); att=e['attendance']; g=guild()
    yes=[p for p in members if att.get(p)=='in']
    here=[p for p in yes if present(members[p],e)]
    h=f'<a href="/">クラ活一覧</a><h1>{esc(e["date"])}　{esc(e["time"])} のクラ活</h1><section><h2>出欠・集合</h2><b>参加 {len(yes)}人　集合済み {len(here)}人</b>'
    for label,ids in [('集合済み',here),('未集合',[p for p in yes if p not in here]),('欠席',[p for p in members if att.get(p)=='out']),('未回答',[p for p in members if p not in att])]:
        h+='<p>'+label+'　'+('、'.join(name(e,p) for p in ids) or '—')+'</p>'
    h+=form('attendance',select('p',[(p,m.display_name) for p,m in members.items()])+select('status',[('in','参加'),('out','欠席')]),'出欠を修正')+'<a href="">最新の状況に更新</a></section><section><h2>チーム抽選</h2>'
    roles=[(r.id,r.name) for r in g.roles if not r.is_default()]
    for i,(a,b) in enumerate(e['rules']):
        h+=form('remove',esc(g.get_role(a) or a)+' × '+esc(g.get_role(b) or b)+f'<input type=hidden name=i value={i}>','条件を削除')
    h+=form('rule',select('a',roles)+' × '+select('b',roles),'同じ組にしない')
    h+=form('draw',select('size',[(2,'デュオ'),(3,'トリオ')])+select('source',[('all','参加予定者全員'),('vc','集合済みのみ')])+select('history',[('none','履歴制限なし'),('last','直前の抽選'),('today','開催日の全履歴'),('recent','直近N回のクラ活')])+'N <input type=number name=n value=3 min=1 max=100 style="width:5em">','くじを引く')
    if 'draft' in e: h+='<h3>抽選候補</h3><div class=draw>'+teams_html(e,e['draft'])+'</div>'+form('confirm','','この組み合わせで確定')
    if e['rounds']:
        h+='<h3>確定チーム</h3>'+teams_html(e,e['rounds'][-1])+form('post','','チーム表をDiscordへ掲載')
        h+=form('move',''.join(f'<label>Team {i+1} '+select('vc',[(c.id,c.name) for c in g.voice_channels if c.id!=e['voice']],(e.get('destinations',[])+[None]*len(e['rounds'][-1]['teams']))[i])+'</label>' for i in range(len(e['rounds'][-1]['teams']))),'既存VCへ一括移動')
    h+='</section><section><h2>マップ・賞金</h2>'+form('map','<input name=name placeholder="マップ名" required maxlength=80><input name=amount type=number min=0 max=10000000 placeholder="賞金（円）" required>'+select('unit',[('person','1人あたり'),('team','チーム総額')]),'試合を追加')
    for i,m in enumerate(e['matches']):
        h+=f'<p>第{i+1}試合　{esc(m["name"])}　{m["amount"]:,}円（'+('各自' if m['unit']=='person' else 'チーム総額')+'）</p>'
        if 'teams' not in m: continue
        if 'winner' in m: h+=f'<small>承認済み　Team {m["winner"]+1}</small>'
        else:
            for c in m['claims']:
                h+=form('approve',f'<input type=hidden name=i value={i}><input type=hidden name=c value={c}>Team {c+1}　'+' ／ '.join(name(e,p) for p in m['teams'][c]),'勝利を承認')
    h+=form('start','','クラ活スタート・未開始試合を投稿')+'</section><section><h2>支払い一覧</h2>'
    for p,items in credits(e).items():
        total=sum(v for _,v in items); paid=e['paid'].get(p,0)
        h+=f'<p><b>{name(e,p)}</b>　獲得 {total:,}円 ／ 残り {total-paid:,}円</p><small>'+ ' ＋ '.join(f'{esc(n)} {v}円' for n,v in items)+'</small>'
        if total>paid: h+=form('pay',f'<input type=hidden name=p value="{p}"><input type=hidden name=total value="{total}">','支払い済みにする')
    return page(h+'</section>')
async def action(req):
    d=await req.post()
    if d.get('csrf')!=csrf: raise web.HTTPForbidden()
    k=req.match_info['key']
    if k not in events: raise web.HTTPNotFound()
    e=events[k]; g=guild(); a=d['act']; note=''
    async with lock:
        try:
            members=roster(e)
            if a=='attendance':
                if d['p'] not in members or d['status'] not in ('in','out'): raise ValueError('対象外の回答です。')
                e['attendance'][d['p']]=d['status']; e.pop('draft',None)
            elif a=='rule':
                rule=[int(d['a']),int(d['b'])]
                if not all(g.get_role(r) for r in rule): raise ValueError('ロールを確認してください。')
                if rule not in e['rules'] and rule[::-1] not in e['rules']: e['rules'].append(rule)
                e.pop('draft',None)
            elif a=='remove':
                e['rules'].pop(int(d['i'])); e.pop('draft',None)
            elif a=='draw':
                size=int(d['size'])
                if size not in (2,3): raise ValueError('人数設定を確認してください。')
                players={p:{r.id for r in m.roles} for p,m in members.items() if e['attendance'].get(p)=='in' and (d['source']=='all' or present(m,e))}
                sessions=sorted((s for s in events.values() if s['rounds']),key=lambda s:s['rounds'][-1]['ts'])
                rounds=sorted((r for s in sessions for r in s['rounds']),key=lambda r:r['ts'])
                mode=d['history']
                if mode=='last': rounds=rounds[-1:]
                elif mode=='today': rounds=[r for s in sessions if s['date']==e['date'] for r in s['rounds']]
                elif mode=='recent': rounds=[r for s in sessions[-max(1,int(d['n'])):] for r in s['rounds']]
                else: rounds=[]
                teams,wait=await asyncio.to_thread(draw,players,size,e['rules'],[t for r in rounds for t in r['teams']])
                from time import time
                e['draft']=dict(drawn=time(),teams=teams,wait=wait,source=d['source'],snapshot={p:sorted(rs) for p,rs in players.items()})
            elif a=='confirm':
                from time import time
                r=e.get('draft')
                if not r: raise ValueError('再抽選してください。')
                current={p:sorted(role.id for role in m.roles) for p,m in members.items() if e['attendance'].get(p)=='in' and (r['source']=='all' or present(m,e))}
                if current!=r['snapshot'] or any(s['rounds'] and s['rounds'][-1]['ts']>r.get('drawn',0) for s in events.values()):
                    raise ValueError('参加者または抽選履歴が更新されました。再抽選してください。')
                e['names'].update({p:m.display_name for p,m in members.items() if p in current})
                r=e.pop('draft'); r['ts']=time(); e['rounds'].append(r); save()
                await post_teams(e)
            elif a=='post': await post_teams(e)
            elif a=='move':
                teams=e['rounds'][-1]['teams']; dest=d.getall('vc',[])
                if len(dest)!=len(teams) or len(set(dest))!=len(dest): raise ValueError('各チームに別々の移動先VCを選んでください。')
                e['destinations']=dest; save()
                for team,channel in zip(teams,dest):
                    vc=g.get_channel(int(channel))
                    if not isinstance(vc,discord.VoiceChannel) or vc.id==e['voice']: raise ValueError('移動先VCを確認してください。')
                    for p in team:
                        m=g.get_member(int(p))
                        if m and m.voice and m.voice.channel==vc: status='移動済み'
                        elif not m or not present(m,e): status='集合VCにいません'
                        else:
                            try: await m.move_to(vc); status='移動完了'
                            except discord.HTTPException as err: status=f'移動失敗（Discord {err.code}）'
                        note+='<p>'+name(e,p)+'　'+status+'</p>'
            elif a=='map':
                amount=int(d['amount']); title=d['name'].strip()
                if not title or len(title)>80 or not 0<=amount<=10000000 or d['unit'] not in ('person','team'): raise ValueError('マップ名・金額を確認してください。')
                e['matches'].append(dict(name=title,amount=amount,unit=d['unit'],claims=[]))
            elif a=='start':
                if not e['rounds'] or not e['matches']: raise ValueError('チーム確定と試合の追加を先に行ってください。')
                for i,m in enumerate(e['matches']):
                    if m.get('posted'): continue
                    m.setdefault('teams',e['rounds'][-1]['teams'])
                    unit='1人あたり' if m['unit']=='person' else 'チーム総額'
                    save()
                    await channel_for(e['prize']).send(f'第{i+1}試合｜{m["name"]}｜{unit} {m["amount"]:,}円',view=view(('このマップで勝利を申告',f'win:{k}:{i}')),allowed_mentions=discord.AllowedMentions.none())
                    m['posted']=True; e['closed']=True; save()
            elif a=='approve':
                m=e['matches'][int(d['i'])]; c=int(d['c'])
                if c not in m['claims'] or 'winner' in m: raise ValueError('申告状況を更新してください。')
                m['winner']=c
            elif a=='pay':
                p=d['p']; total=sum(v for _,v in credits(e)[p])
                if total!=int(d['total']): raise ValueError('賞金額が更新されました。一覧を確認してください。')
                e['paid'][p]=total
            else: raise ValueError('操作が見つかりません。')
            save()
        except (ValueError,IndexError,KeyError,discord.HTTPException) as err:
            note=esc(err)
    if note: return page('<section>'+note+'</section><a href="/e/'+k+'">クラ活に戻る</a>')
    raise web.HTTPSeeOther(location='/e/'+k)

def channel_for(cid):
    ch=guild().get_channel(cid)
    if not ch: raise ValueError('設定チャンネルが見つかりません。')
    return ch
async def post_teams(e):
    r=e['rounds'][-1]
    lines=[f'Team {i+1}　'+' ／ '.join(e['names'].get(p,p) for p in t) for i,t in enumerate(r['teams'])]
    lines+=['待機　'+('、'.join(e['names'].get(p,p) for p in r['wait']) or 'なし')]
    content='クラ活 チーム表'
    for line in lines:
        if len(content)+len(line)>1850:
            await channel_for(e['channel']).send(content,allowed_mentions=discord.AllowedMentions.none()); content=''
        content+='\n'+line
    await channel_for(e['channel']).send(content,allowed_mentions=discord.AllowedMentions.none())

async def main():
    await bot.login(os.environ['DISCORD_TOKEN'])
    await tree.sync(guild=scope)
    app=web.Application(middlewares=[auth])
    app.add_routes([web.get('/',home),web.get('/e/{key}',dashboard),web.post('/e/{key}',action)])
    runner=web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner,'127.0.0.1',int(os.getenv('PORT','8765'))).start()
    try: await bot.connect()
    finally: await runner.cleanup(); await bot.close()
if __name__=='__main__': asyncio.run(main())
