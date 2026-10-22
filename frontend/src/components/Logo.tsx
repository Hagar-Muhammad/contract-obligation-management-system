/**
 * ConTrack logo: an open "C" (the track a contract runs along) closing on a check (an obligation fulfilled).
 * `dark` is for dark backgrounds such as the app header; colours are tuned for contrast on each.
 * Source files: docs/brand/.
 */
const PALETTE = {
  light: { track: '#1D4ED8', check: '#059669', con: '#0B2545', word: '#047857' },
  dark: { track: '#3B82F6', check: '#4ADE80', con: '#FFFFFF', word: '#4ADE80' },
} as const

interface LogoProps {
  variant?: 'light' | 'dark'
  size?: number
  withWordmark?: boolean
  className?: string
}

export function LogoMark({ variant = 'light', size = 32 }: Pick<LogoProps, 'variant' | 'size'>) {
  const c = PALETTE[variant]
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true" focusable="false">
      <path
        d="M48.85 17.86A22 22 0 1 0 48.85 46.14"
        fill="none"
        stroke={c.track}
        strokeWidth="9"
        strokeLinecap="round"
      />
      <path
        d="M22 32.5l7 7 13.5-14.5"
        fill="none"
        stroke={c.check}
        strokeWidth="7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function Logo({ variant = 'light', size = 32, withWordmark = true, className }: LogoProps) {
  const c = PALETTE[variant]
  return (
    <span className={['logo', className].filter(Boolean).join(' ')} role="img" aria-label="ConTrack">
      <LogoMark variant={variant} size={size} />
      {withWordmark && (
        <span className="logo-wordmark" style={{ fontSize: size * 0.68, color: c.con }} aria-hidden="true">
          Con<span style={{ color: c.word }}>Track</span>
        </span>
      )}
    </span>
  )
}
