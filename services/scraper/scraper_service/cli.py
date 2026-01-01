from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from scraper_service.config import Settings, settings
from scraper_service.fixtures.downloader import FixtureDownloader
from scraper_service.http.client import HttpClient
from scraper_service.scheduler.runner import ScrapeRunner
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


def _resolve_race_date(race_date: Optional[str]) -> str:
    return race_date or today_jst_str()


@fixtures_app.command("download")
def fixtures_download(
    manifest: Path = typer.Option(..., "--manifest", exists=True, readable=True),
    fixtures_root: Path = typer.Option(Path("./fixtures"), "--fixtures-root"),
    no_api: bool = typer.Option(True, "--no-api", help="(deprecated) no-op"),
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
    no_api: bool = typer.Option(True, "--no-api", help="(deprecated) no-op"),
) -> None:
    race_date = _resolve_race_date(race_date)
    cfg = settings
    http = _build_http(cfg)
    raw_logger = RawFetchLogger(cfg.local_log_dir / "raw_fetch_logs.csv")
    runner = ScrapeRunner(settings=cfg, http=http, raw_logger=raw_logger)
    runner.run_once(race_date=race_date, baba_codes=baba_code or None, race_no=race_no)
    typer.echo("ok")


@sync_app.command("run")
def sync_run(
    force: bool = typer.Option(False, "--force", help="同期インターバルの判定を無視して実行"),
) -> None:
    _ = force
    typer.echo("sync is handled by api-service; this command is deprecated")
    raise typer.Exit(code=2)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
