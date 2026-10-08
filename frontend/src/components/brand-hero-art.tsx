export function BrandHeroArt({ className = "h-28 w-44" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 320 220"
      role="img"
      aria-label="TumorXpert abstract visualization"
      className={className}
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="txWave" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0%" stopColor="#0f4c5c" stopOpacity="0.95" />
          <stop offset="100%" stopColor="#6fa5b2" stopOpacity="0.9" />
        </linearGradient>
        <radialGradient id="txGlow" cx="50%" cy="50%" r="65%">
          <stop offset="0%" stopColor="#a6d4cf" stopOpacity="0.75" />
          <stop offset="100%" stopColor="#a6d4cf" stopOpacity="0" />
        </radialGradient>
      </defs>

      <ellipse cx="160" cy="110" rx="130" ry="86" fill="url(#txGlow)" />

      <path
        d="M30 120c26-54 66-88 130-88 54 0 96 20 130 61-20 58-74 95-145 95-53 0-96-23-115-68z"
        fill="url(#txWave)"
        opacity="0.93"
      />

      <path
        d="M68 135c20-37 53-61 97-61 42 0 73 16 96 49-14 36-53 61-103 61-41 0-73-16-90-49z"
        fill="#f5fbfb"
        opacity="0.68"
      />

      <circle cx="160" cy="110" r="38" fill="#0f4c5c" opacity="0.95" />
      <circle cx="160" cy="110" r="24" fill="#d4ece9" opacity="0.95" />
      <circle cx="160" cy="110" r="11" fill="#0f4c5c" />

      <g stroke="#0f4c5c" strokeOpacity="0.58" strokeWidth="2.5" fill="none">
        <path d="M45 78c39 12 72 9 112-12" />
        <path d="M166 62c44 2 76 20 108 56" />
        <path d="M66 168c33 16 69 20 112 13" />
      </g>
    </svg>
  );
}
