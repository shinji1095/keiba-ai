import React from "react";

export type MarkdownViewProps = {
  content: string;
};

/**
 * GFM テーブルを含む Markdown を HTML に変換して表示する軽量コンポーネント。
 * 本格的なレンダリングは react-markdown + remark-gfm を導入して拡張可能。
 * 現状は<table>のみ対応（テーブル行を <tr><td> に変換）。
 */
export function MarkdownView({ content }: MarkdownViewProps): React.JSX.Element {
  const html = React.useMemo(() => {
    // 簡易実装: ## 見出し、テーブル、コードブロックをそのまま表示
    // 本格対応は react-markdown + remark-gfm に置き換える
    const lines = content.split("\n");
    const out: string[] = [];
    let inTable = false;
    let inCodeBlock = false;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      // コードブロック
      if (line.startsWith("```")) {
        if (inCodeBlock) {
          out.push("</code></pre>");
          inCodeBlock = false;
        } else {
          out.push('<pre style="background: rgba(255,255,255,0.05); padding: 8px; border-radius: 6px; overflow: auto;"><code>');
          inCodeBlock = true;
        }
        continue;
      }
      if (inCodeBlock) {
        out.push(escapeHtml(line) + "\n");
        continue;
      }

      // 見出し
      if (line.startsWith("## ")) {
        out.push(`<h2 style="margin-top: 1.5em; margin-bottom: 0.5em; font-size: 1.1em; font-weight: 700;">${escapeHtml(line.slice(3))}</h2>`);
        continue;
      }
      if (line.startsWith("# ")) {
        out.push(`<h1 style="margin-top: 1.5em; margin-bottom: 0.5em; font-size: 1.3em; font-weight: 700;">${escapeHtml(line.slice(2))}</h1>`);
        continue;
      }

      // テーブル
      if (line.startsWith("|") && !inTable) {
        out.push('<table class="table" style="margin-top: 1em; margin-bottom: 1em;">');
        inTable = true;
      }
      if (inTable) {
        if (!line.startsWith("|")) {
          out.push("</table>");
          inTable = false;
          out.push(`<p>${escapeHtml(line)}</p>`);
          continue;
        }
        // 区切り行はスキップ
        if (line.match(/^\|[\s\-:|]+\|$/)) {
          continue;
        }
        const cells = line
          .split("|")
          .slice(1, -1)
          .map((c) => c.trim());
        // ヘッダ判定（先頭行かどうか）
        const isHeader = i === 0 || (i > 0 && !lines[i - 1].startsWith("|"));
        const tag = isHeader ? "th" : "td";
        out.push(`<tr>${cells.map((c) => `<${tag}>${escapeHtml(c)}</${tag}>`).join("")}</tr>`);
        continue;
      }

      // 通常行
      if (line.trim() === "") {
        out.push("<br/>");
      } else {
        out.push(`<p style="margin: 0.5em 0;">${escapeHtml(line)}</p>`);
      }
    }

    if (inTable) out.push("</table>");
    if (inCodeBlock) out.push("</code></pre>");

    return out.join("");
  }, [content]);

  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}



