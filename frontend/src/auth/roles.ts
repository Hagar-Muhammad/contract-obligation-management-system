/** Display helpers for roles (codes come from backend/app/modules/users/rbac.py). */

export const ROLE_CODES = [
  'admin',
  'contract_manager',
  'legal',
  'property_manager',
  'employee',
  'management',
] as const
export type RoleCodeName = (typeof ROLE_CODES)[number]

/** The role shown next to a person's name when they hold several: the most powerful one. */
const PRIORITY: RoleCodeName[] = [
  'admin',
  'contract_manager',
  'legal',
  'property_manager',
  'management',
  'employee',
]

export function primaryRole(roles: readonly string[]): RoleCodeName | undefined {
  return PRIORITY.find((role) => roles.includes(role))
}

/** "Scope" column of Users & roles: what the person's widest role lets them see. */
export function scopeKey(roles: readonly string[]): string {
  if (roles.some((r) => ['admin', 'contract_manager', 'legal'].includes(r))) return 'scope.all'
  if (roles.includes('property_manager')) return 'scope.assigned_properties'
  if (roles.includes('management')) return 'scope.reports'
  return 'scope.assigned_obligations'
}

export const ROLE_TAG_CLASS: Record<RoleCodeName, string> = {
  admin: 'role-tag role-admin',
  contract_manager: 'role-tag role-contract-manager',
  legal: 'role-tag role-legal',
  property_manager: 'role-tag role-property-manager',
  employee: 'role-tag role-employee',
  management: 'role-tag role-management',
}
