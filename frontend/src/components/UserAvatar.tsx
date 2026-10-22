const PALETTE = [
  ['#DBEAFE', '#1D4ED8'],
  ['#FCE7F3', '#BE185D'],
  ['#DCFCE7', '#15803D'],
  ['#FEF3C7', '#B45309'],
  ['#E0F2FE', '#0369A1'],
  ['#EDE9FE', '#6D28D9'],
  ['#F1F5F9', '#475569'],
] as const

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  const letters = parts.length > 1 ? parts[0][0] + parts[parts.length - 1][0] : (parts[0] ?? '?').slice(0, 2)
  return letters.toUpperCase()
}

/** Initials in a soft colour picked from the name, so the same person always gets the same colour. */
export function UserAvatar({
  name,
  size = 32,
  muted = false,
}: {
  name: string
  size?: number
  muted?: boolean
}) {
  const hash = [...name].reduce((sum, ch) => (sum * 31 + ch.charCodeAt(0)) >>> 0, 7)
  const [bg, fg] = muted ? PALETTE[6] : PALETTE[hash % (PALETTE.length - 1)]
  return (
    <span
      className="user-avatar"
      style={{ width: size, height: size, background: bg, color: fg, fontSize: size * 0.38 }}
      aria-hidden="true"
    >
      {initials(name)}
    </span>
  )
}
