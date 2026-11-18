from itertools import combinations
from random import shuffle
from time import monotonic
from datetime import datetime, timezone, timedelta

def day():
    return datetime.now(timezone(timedelta(hours=9))).date().isoformat()

def pairs(team):
    return {tuple(sorted(p)) for p in combinations(team, 2)}

def draw(players, size, rules, history):
    ids = list(players)
    if len(ids) < size:
        raise ValueError("参加人数が足りません。")
    shuffle(ids)
    blocked = set().union(*(pairs(t) for t in history))
    for a, b in combinations(ids, 2):
        if any((x in players[a] and y in players[b]) or
               (y in players[a] and x in players[b]) for x, y in rules):
            blocked.add(tuple(sorted((a,b))))
    end = monotonic() + 1.5
    def solve(rest, spare):
        if monotonic() > end:
            raise ValueError("探索時間内に見つかりませんでした。再抽選するか条件を調整してください。")
        if len(rest) == spare:
            return [], rest
        first, *others = rest
        for group in combinations(others, size-1):
            team = [first, *group]
            if pairs(team) & blocked:
                continue
            result = solve([p for p in others if p not in group], spare)
            if result is not None:
                teams, wait = result
                return [team, *teams], wait
        if spare:
            result = solve(others, spare-1)
            if result is not None:
                return result[0], [first, *result[1]]
    found = solve(ids, len(ids)%size)
    if found is None:
        raise ValueError("指定ロールとペア履歴の条件では全チームを編成できません。")
    return found

def credits(event):
    rows = {}
    for match in event['matches']:
        if 'winner' not in match:
            continue
        team = match['teams'][match['winner']]
        amount = match['amount']
        for i, p in enumerate(team):
            yen = amount if match['unit']=='person' else amount//len(team)+int(i<amount%len(team))
            rows.setdefault(p, []).append((match['name'], yen))
    return rows
