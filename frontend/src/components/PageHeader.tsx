import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

interface Crumb {
  label: string
  to?: string
}

/** Page title, grey subtitle and actions on the right, with an optional breadcrumb above. */
export function PageHeader({
  title,
  subtitle,
  actions,
  breadcrumb,
}: {
  title: ReactNode
  subtitle?: ReactNode
  actions?: ReactNode
  breadcrumb?: Crumb[]
}) {
  return (
    <header className="page-header">
      <div className="page-header-text">
        {breadcrumb && (
          <nav className="breadcrumb" aria-label="breadcrumb">
            {breadcrumb.map((crumb, i) => (
              <span key={crumb.label}>
                {i > 0 && <span className="breadcrumb-sep">/</span>}
                {crumb.to ? <Link to={crumb.to}>{crumb.label}</Link> : <span>{crumb.label}</span>}
              </span>
            ))}
          </nav>
        )}
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  )
}
