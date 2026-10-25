# PC全体の監視データ収集

Web画面は `/scrape/status`。CPU・メモリ・ディスクのゲージ、リソース推移、取得進捗、実行履歴を表示します。
計測値は画面を閉じていても保存されます。初回は計測開始後にグラフが蓄積されます。

## アプリの反映

リポジトリルートで実行します。DBへの監視用テーブル追加はAPI起動時のマイグレーションで行います。

```bash
docker compose up -d --build api scraper web
```

scraperの再起動で実行中の処理は中断されます。定期取得は既存の完了状態を使用して再開し、
監視記録に残る未完了ジョブは中断として表示します。

## 1. 実ホストの確認

`services/monitor/collector.py` はLinuxの実ホスト上で起動します（Python 3標準ライブラリのみ）。
コンテナ内では起動しません。WSL/VM内で動かす場合は `MONITOR_SCOPE=vm` とし、
表示がVM全体の値であることを明示します。Windows/macOS本体の収集には別のOS対応が必要です。

送信せずに計測だけを確認できます。

```bash
python3 services/monitor/collector.py --once --disk 'OS=/' --disk "取得データ=$PWD/services/scraper/data"
```

保存先は実際のファイルシステムを参照できるホスト側のパスを指定します。
DBが別ディスクの場合は、DBデータがあるディスク上の読み取り可能なディレクトリも指定します。
同じファイルシステムの保存先はラベルを統合して表示します。

## 2. 専用のサービス認証

管理者でログインし、既存の OAuth Clients 画面で収集専用クライアントを作成します。
名前は任意（例: `host-monitor`）、scopeは **`monitor:write`** のみとします。
返却されたclient IDとsecretを次の設定ファイルへ保存します。
閲覧は通常のユーザーログインを利用し、サービス閲覧を使う場合のみ `monitor:read` を付与します。
ユーザートークンや閲覧専用サービスでは計測値を送信できません。

```bash
mkdir -p ~/.config
cp -n deploy/monitor/monitor.env.example ~/.config/keiba-monitor.env
chmod 600 ~/.config/keiba-monitor.env
```

設定ファイルの `MONITOR_COLLECTOR_PATH`、ID、secret、保存先を編集してください。
`MONITOR_API_URL` はホストからアクセス可能な既存Web入口の `/api`（例: `http://localhost/api`）です。
外部通信用NICを自動検出できない場合は `MONITOR_INTERFACES=eth0` のように指定します。
Dockerブリッジ・veth・loopbackを含めると通信量が重複するため指定しません。
secretをGitへ登録しないでください。

## 3. 常駐起動（systemdユーザーサービス）

```bash
mkdir -p ~/.config/systemd/user
cp deploy/monitor/keiba-monitor.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now keiba-monitor
systemctl --user status keiba-monitor
```

ログは `journalctl --user -u keiba-monitor`、停止は `systemctl --user stop keiba-monitor`。
ユーザーサービスをログアウト後やOS起動直後も動かす場合は、OSのユーザーサービス運用方針に従いlingerを設定します。
systemdを使用しない場合は、同じ設定を環境変数として設定してcollectorを常駐起動してください。

## 警告・保持期間

- CPU: 80%以上5分で注意、95%以上5分で異常。
- メモリ: 80%以上5分で注意、90%以上5分で異常。
- ディスク: 80%以上で注意、90%以上で異常。
- 閾値未満が60秒続いたら解除。欠測中は解除と判定しません。
- 最終計測から30秒で情報遅延、60秒で監視不能。
- 10秒値24時間、1分集計7日、解消済み警告30日。画面では期間に合わせて平均・最大値を再集計します。
- 送信失敗時は最大10分をメモリ内に保持して再送します。収集プロセス自体の停止中は欠測になります。

警告閾値はルート `.env` の `MONITOR_CPU_WARNING` / `MONITOR_CPU_CRITICAL`、
`MONITOR_MEMORY_WARNING` / `MONITOR_MEMORY_CRITICAL`、`MONITOR_DISK_WARNING` / `MONITOR_DISK_CRITICAL` で変更できます。
`MONITOR_DISK_MIN_FREE_BYTES` を設定すると監視対象の保存先に共通の最低空き容量も検査します（既定は無効）。
設定変更後はAPIコンテナを再作成してください。

スケジューラは処理中・待機中も生存確認を更新し、最終進捗とは別に表示します。
ジョブの保存件数が0の場合は成功扱いせず、スキップとして表示します。
PC警告はリソースグラフに縦線で表示し、取得失敗の縦線は現在の履歴フィルター・ページに表示中のジョブが対象です。
サービスごとのCPU・メモリ、外部通知、再起動操作は今回の対象外です。
