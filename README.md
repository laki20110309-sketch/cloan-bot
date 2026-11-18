# 宙AIM クラ活運営
単一Discordサーバー用。管理画面とBOTを同じプロセスで起動します。既存BOTとは別のアプリを用意してください。

## 1. Discord側
Discord Developer PortalでApplicationを作成し、BotページでServer Members Intentを有効化。Bot Tokenを控えます。OAuth2でbot・applications.commandsを選び、サーバーに招待。BOTに「チャンネルを見る」「メッセージを送信」「接続」「メンバーを移動」の権限を対象テキスト・集合VC・移動先VCで付与してください。Discordの開発者モードからサーバーIDをコピーします。募集コマンドはサーバー管理権限のある人が使えます。

## 2. Windows PowerShell → VPS
ZIPをダウンロードフォルダーに保存。接続確認は以下。
```powershell
ssh -i "$HOME\Downloads\6000-soraAIM-debian.key" -o IdentitiesOnly=yes -p 10003 debian@vps.yuyuttinetworks.com
```
転送は別のWindows PowerShellから。
```powershell
scp -i "$HOME\Downloads\6000-soraAIM-debian.key" -o IdentitiesOnly=yes -P 10003 "$HOME\Downloads\sora-clan.zip" debian@vps.yuyuttinetworks.com:~/
```
## 3. VPSで初回セットアップ
```bash
cd ~
python3 -m zipfile -e sora-clan.zip .
cd clan
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
umask 077
read -rsp 'Discord Bot Token: ' token; echo
read -rp 'Discord Server ID: ' server
adminpass=$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')
printf 'DISCORD_TOKEN=%s\nGUILD_ID=%s\nADMIN_PASSWORD=%s\n' "$token" "$server" "$adminpass" > .env
printf '管理画面パスワード: %s\n' "$adminpass"
unset token adminpass
pm2 start start.sh --interpreter bash --name sora-clan
pm2 save
pm2 logs sora-clan --lines 25
```
venv作成に失敗した場合は sudo apt install python3-venv の後にやり直してください。表示されたパスワードを保管。ログ表示はCtrl+Cで終了できます。

## 4. 管理画面を開く
Windows PowerShellで次を実行し、このウィンドウを開いたまま http://127.0.0.1:8765 にアクセス。ユーザー名 admin、上記パスワードでログイン。
```powershell
ssh -N -L 8765:127.0.0.1:8765 -i "$HOME\Downloads\6000-soraAIM-debian.key" -o IdentitiesOnly=yes -p 10003 debian@vps.yuyuttinetworks.com
```

## 当日の操作
1. Discordで /クラ活募集 を選び、開催日・時刻（日本時間）・対象ロール・出欠チャンネル・賞金チャンネル・集合VCを指定。全員対象なら @everyone。参加者はボタンで回答を変更できます。
2. サイトから開催回を開きます。最新の状況に更新すると、出欠・集合状況・勝利申告が反映されます。運営による出欠修正も可能。
3. 禁止ロールを必要な数だけ追加。同一ロール同士も可。抽選対象・デュオ／トリオ・履歴対象を選びます。「直前」はサーバー内で最後に確定した編成。「直近N回」は確定履歴がある直近N開催（現在回を含む）。余りは待機。候補を確定するとチーム表が出欠チャンネルに投稿されます。掲載失敗時は再掲載ボタンを使用。
4. 各チームに異なる既存VCを選び一括移動。移動元は集合VCのみ。再抽選前に参加者に集合VCへ戻ってもらってください。
5. マップ名・金額・単位を登録。クラ活スタートで未開始の試合それぞれに勝利申告ボタンを投稿し、その時のチームを固定します。別編成の試合はチームを再確定してからマップを追加し、もう一度スタート。初回開始後はBOT出欠締切、運営修正はできます。
6. チームの誰かが勝利を申告。運営が正しいチームを承認すると賞金一覧に反映。チーム総額の端数は抽選の表示順に1円ずつ配分します。支払い後に「支払い済みにする」。追加獲得分は残額に反映されます。送金は運営が行います。
7. 記録は clan/events.json に保存。PM2は1プロセスで起動し、バックアップにはこのファイルをコピーしてください。

パスワードt83S-haVa8k2tDNJQsVS7RYvE9lAxaHn
