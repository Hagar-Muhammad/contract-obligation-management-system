import { useTranslation } from 'react-i18next'
import { Link, NavLink } from 'react-router-dom'
import { useAuth } from '../auth/context'
import { Logo } from './Logo'
import { NAV_SECTIONS } from './nav'

/** Dark navigation column: sections and links filtered by the user's permissions (NFR-UX-01). */
export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { t } = useTranslation()
  const { can } = useAuth()

  return (
    <div className="sidebar">
      <Link to="/" className="sidebar-brand" onClick={onNavigate}>
        <Logo variant="dark" size={30} />
      </Link>
      <nav aria-label={t('nav.mainNavigation')}>
        {NAV_SECTIONS.map((section) => {
          const items = section.items.filter((item) => !item.permission || can(item.permission))
          if (!items.length) return null
          return (
            <div key={section.titleKey} className="sidebar-section">
              <div className="sidebar-section-title">{t(section.titleKey)}</div>
              <ul>
                {items.map((item) => (
                  <li key={item.path}>
                    <NavLink
                      to={item.path}
                      end={item.path === '/'}
                      className={({ isActive }) => (isActive ? 'sidebar-link active' : 'sidebar-link')}
                      onClick={onNavigate}
                    >
                      <span className="sidebar-icon" aria-hidden="true">
                        {item.icon}
                      </span>
                      {t(item.labelKey)}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </nav>
    </div>
  )
}
