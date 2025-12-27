import React from "react";

export function JsonView({ value }: { value: unknown }): React.JSX.Element {
  const text = React.useMemo(() => JSON.stringify(value, null, 2), [value]);
  return (
    <pre
      style={{
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
        fontSize: 12,
        lineHeight: 1.45,
        margin: 0,
      }}
    >
      {text}
    </pre>
  );
}
