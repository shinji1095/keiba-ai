from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from scraper_service.api.client import ApiClient
from scraper_service.config import Settings, settings
from scraper_service.fixtures.downloader import FixtureDownloader
from scraper_service.http.client import HttpClient
from scraper_service.scheduler.runner import ScrapeRunner
from scraper_service.sync.runner import SyncRunner
from scraper_service.utils.raw_fetch_logger import RawFetchLogger
from scraper_service.utils.time import today_jst_str


app = typer.Typer(no_args_is_help=True)
fixtures_app = typer.Typer(no_args_is_help=True)
scrape_app = typer.Typer(no_args_is_help=True)
sync_app = typer.Typer(no_args_is_help=True)
app.add_typer(fixtures_app, name="fixtures")
app.add_typer(scrape_app, name="scrape")
app.add_typer(sync_app, name="sync")


def _build_http(cfg: Settings) -> HttpClient:
    return HttpClient(
        user_agent=cfg.user_agent,
        accept_language=cfg.accept_language,
        min_interval_sec=cfg.min_interval_sec,
        jitter_sec=cfg.jitter_sec,
        max_retries=cfg.max_retries,
        backoff_base_sec=cfg.backoff_base_sec,
        backoff_max_sec=cfg.backoff_max_sec,
    )


def _build_api(cfg: Settings, no_api: bool) -> Optional[ApiClient]:
    if no_api:
        return None
    if cfg.api_access_token or (cfg.api_username and cfg.api_password):
        return ApiClient(
            base_url=cfg.api_base_url,
            access_token=cfg.api_access_token,
            username=cfg.api_username,
            password=cfg.api_password,
        )
    return None


def _resolve_race_date(race_date: Optional[str]) -> str:
    return race_date or today_jst_str()


@fixtures_app.command("download")
def fixtures_download(
    manifest: Path = typer.Option(..., "--manifest", exists=True, readable=True),
    fixtures_root: Path = typer.Option(Path("./fixtures"), "--fixtures-root"),
    no_api: bool = typer.Option(True, "--no-api", help="fixtures は api-service へは送信しない（既定）"),
) -> None:
    cfg = settings
    http = _build_http(cfg)
    dl = FixtureDownloader(http=http)
    summary = dl.download_manifest(manifest_path=manifest, fixtures_root=fixtures_root)
    typer.echo(f"done: total={summary.total} ok={summary.ok} ng={summary.ng}")


@scrape_app.command("once")
def scrape_once(
    race_date: Optional[str] = typer.Option(None, "--race-date", help="YYYY-MM-DD (JST). default: today (JST)"),
    baba_code: list[int] = typer.Option([], "--baba-code", help="指定した開催場のみ（複数可）"),
    race_no: Optional[int] = typer.Option(None, "--race-no", help="指定したレース番号のみ"),
    no_api: bool = typer.Option(False, "--no-api", help="api-service に送信しない（HTML保存のみ）"),
) -> None:
    race_date = _resolve_race_date(race_date)
    cfg = settings
    http = _build_http(cfg)
    api = _build_api(cfg, no_api=no_api)
    raw_logger = RawFetchLogger(cfg.local_log_dir / "raw_fetch_logs.csv")
    runner = ScrapeRunner(settings=cfg, http=http, api=api, raw_logger=raw_logger)
    runner.run_once(race_date=race_date, baba_codes=baba_code or None, race_no=race_no)
    typer.echo("ok")


@sync_app.command("run")
def sync_run(
    force: bool = typer.Option(False, "--force", help="同期インターバルの判定を無視して実行"),
) -> None:
    cfg = settings
    api = _build_api(cfg, no_api=False)
    if api is None:
        typer.echo("API settings are required for sync (API_ACCESS_TOKEN or API_USERNAME/API_PASSWORD)")
        raise typer.Exit(code=2)
    runner = SyncRunner(settings=cfg, api=api)
    summary = runner.run(force=force)
    if not summary.due:
        typer.echo("skip: sync interval not reached")
        return
    typer.echo(f"synced={summary.synced} skipped={summary.skipped} errors={summary.errors}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
