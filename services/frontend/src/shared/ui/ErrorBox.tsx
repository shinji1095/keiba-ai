import React from "react";
import { ApiHttpError } from "@/api/http";

const messages = new Map<string, string>([
  ["invalid username or password", "ユーザー名またはパスワードが正しくありません。"],
  ["invalid credentials", "ユーザー名またはパスワードが正しくありません。"],
  ["username already exists", "このユーザー名は既に使用されています。"],
  ["registration failed", "ユーザー登録に失敗しました。"],
  ["invalid client credentials", "連携先IDまたは認証キーが正しくありません。"],
  ["requested scope is not allowed", "指定した権限は許可されていません。"],
  ["scraper is busy", "収集処理が実行中です。しばらく待ってから再試行してください。"],
  ["Failed to fetch", "サーバーに接続できません。接続状況を確認してください。"],
  ["NetworkError when attempting to fetch resource.", "サーバーに接続できません。接続状況を確認してください。"],
]);

function localize(message: string): string {
  return messages.get(message) ?? message;
}

export function ErrorBox({ error }: { error: unknown }): React.JSX.Element {
  const msg = React.useMemo(() => {
    if (!error) return "原因不明のエラーが発生しました。";
    if (typeof error === "string") return localize(error);
    if (error instanceof ApiHttpError) return `${localize(error.message)} (HTTP ${error.status})`;
    if (error instanceof Error) return localize(error.message);
    return "原因不明のエラーが発生しました。";
  }, [error]);

  return <div className="alert">{msg}</div>;
}
