type IconProps = {
  size?: number;
};

export function UserStrokeIcon({ size = 18 }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden="true" focusable="false">
      <circle cx="12" cy="8" r="3.1" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path
        d="M5.4 19.1c1.5-3.2 3.7-4.8 6.6-4.8s5.1 1.6 6.6 4.8"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function ArrowStrokeIcon({ size = 18 }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden="true" focusable="false">
      <path
        d="M5 12h12.5M13.5 7.5 18.5 12l-5 4.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function BackStrokeIcon({ size = 18 }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden="true" focusable="false">
      <path
        d="M19 12H6.5M10.5 7.5 6.5 12l4 4.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function EyeStrokeIcon({ size = 18 }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden="true" focusable="false">
      <path
        d="M2.8 12s3.4-6.2 9.2-6.2S21.2 12 21.2 12s-3.4 6.2-9.2 6.2S2.8 12 2.8 12Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="12" r="2.4" fill="none" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  );
}

export function EyeOffStrokeIcon({ size = 18 }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden="true" focusable="false">
      <path
        d="M3 3.6 20.4 21M9.2 9.4A3 3 0 0 0 12 15.2M14.7 14.3A3 3 0 0 0 9.8 9.6"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <path
        d="M4.2 8.2C2.9 9.6 2.2 11 2.2 11s3.4 6.2 9.8 6.2c1.4 0 2.6-.3 3.7-.7M19.4 15.4c1.1-1.2 1.8-2.4 1.8-2.4S18 6.8 12 6.8c-.6 0-1.2 0-1.7.1"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function BreadStrokeIcon({ size = 16 }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden="true" focusable="false">
      <path
        d="M6.2 10.2c.4-3 2.8-5 5.8-5s5.4 2 5.8 5c2.1.4 3.4 2.2 3.2 4.3-.3 2.4-2.4 3.9-5.1 3.9H8.1c-2.7 0-4.8-1.5-5.1-3.9-.2-2.1 1.1-3.9 3.2-4.3Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="M8.4 11.2c.7-.6 1.8-.6 2.4.1M13.2 11.1c.7-.6 1.8-.5 2.4.2"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function CartStrokeIcon({ size = 18 }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden="true" focusable="false">
      <path
        d="M4 5h1.6l1.5 10.2h10.2L19.2 8H7"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="10" cy="19" r="1.2" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="16.4" cy="19" r="1.2" fill="none" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  );
}
