import { LogoutOutlined } from '@ant-design/icons'
import { Dropdown, type MenuProps } from 'antd'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/context'
import { primaryRole } from '../auth/roles'
import { UserAvatar } from './UserAvatar'

/** Avatar, name and role in the top bar; opens the account menu. */
export function UserMenu() {
  const { t } = useTranslation()
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  if (!user) return null
  const role = primaryRole(user.roles)

  const items: MenuProps['items'] = [
    { key: 'logout', icon: <LogoutOutlined />, label: t('nav.logout'), danger: true },
  ]
  const onClick: MenuProps['onClick'] = async ({ key }) => {
    if (key === 'logout') {
      await logout()
      navigate('/login', { replace: true })
    }
  }

  return (
    <Dropdown menu={{ items, onClick }} trigger={['click']} placement="bottomRight">
      <button type="button" className="user-menu" aria-label={t('nav.account')}>
        <UserAvatar name={user.full_name} size={34} />
        <span className="user-menu-text">
          <span className="user-menu-name">{user.full_name}</span>
          {role && <span className="user-menu-role">{t(`roles.${role}`)}</span>}
        </span>
      </button>
    </Dropdown>
  )
}
