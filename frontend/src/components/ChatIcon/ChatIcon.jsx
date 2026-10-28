const paths = {
  play: <path d="m9 5 11 7-11 7V5Z" fill="currentColor" stroke="none" />,
  pause: <path d="M8 5v14M16 5v14" strokeWidth="4" />,
  volume: <><path d="m11 4-6 5H2v6h3l6 5V4ZM15 8a6 6 0 0 1 0 8M18 5a10 10 0 0 1 0 14" /></>,
  muted: <><path d="m11 4-6 5H2v6h3l6 5V4ZM16 9l6 6M22 9l-6 6" /></>,
  message: <path d="M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.4 8.4 0 0 1 3.8-.9h.5a8.5 8.5 0 0 1 8 8v.5Z" />,
  send: <><path d="m22 2-7 20-4-9-9-4 20-7Z" /><path d="M22 2 11 13" /></>,
  microphone: <><rect x="9" y="2" width="6" height="12" rx="3" /><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3M8 22h8" /></>,
  stop: <rect x="6" y="6" width="12" height="12" rx="2" />,
  food: <><path d="M4 3v5a3 3 0 0 0 6 0V3M7 3v18M17 13h4V3c-4 3-4 6-4 10ZM21 13v8" /></>,
  coffee: <><path d="M4 9h13v6a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5V9ZM17 10h2a3 3 0 0 1 0 6h-2M3 22h16M7 3v2M11 2v3M15 3v2" /></>,
  history: <><path d="m3 8 9-5 9 5H3ZM3 21h18M5 18V11M10 18V11M14 18V11M19 18V11" /></>
};

export function ChatIcon({ name, className = '' }) {
  return (
    <svg
      className={`chat-icon ${className}`}
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {paths[name]}
    </svg>
  );
}
