import { CloseOutlined, PlusOutlined } from '@ant-design/icons'
import { App, Button, Form, Input, Modal, Segmented, Select } from 'antd'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { PERMISSIONS, useAuth } from '../../auth/context'
import { UserAvatar } from '../../components/UserAvatar'
import { showServerErrors } from '../../components/showServerErrors'
import { useCreateParty, type PartyType } from '../parties/api'
import { PARTY_ROLES, type PartyRole } from './api'
import { PartySelect } from './pickers'

export interface PartyRow {
  id: string
  display_name: string
  party_type: PartyType
  role: PartyRole
}

interface QuickParty {
  party_type: PartyType
  display_name: string
}

/** Contract form, section 3 (design screen 5): the contract's parties and each one's role (FR-PARTY-03, BR-02). */
export function PartiesField({
  value = [],
  onChange,
  disabled,
}: {
  value?: PartyRow[]
  onChange?: (rows: PartyRow[]) => void
  disabled?: boolean
}) {
  const { t } = useTranslation()
  const { can } = useAuth()
  const { message } = App.useApp()
  const [creating, setCreating] = useState(false)
  const [quickForm] = Form.useForm<QuickParty>()
  const createParty = useCreateParty()

  const add = (row: Omit<PartyRow, 'role'>) =>
    onChange?.([
      ...value,
      { ...row, role: value.length === 0 ? 'landlord' : value.length === 1 ? 'tenant' : 'other' },
    ])
  const update = (id: string, role: PartyRole) =>
    onChange?.(value.map((row) => (row.id === id ? { ...row, role } : row)))
  const remove = (id: string) => onChange?.(value.filter((row) => row.id !== id))

  const createQuickly = async (values: QuickParty) => {
    try {
      const party = await createParty.mutateAsync(values)
      add(party)
      message.success(t('parties.created'))
      setCreating(false)
      quickForm.resetFields()
    } catch (err) {
      showServerErrors(err, quickForm, message, t)
    }
  }

  return (
    <div className="parties-field">
      {!disabled && (
        <PartySelect
          placeholder={t('contracts.searchParties')}
          ariaLabel={t('contracts.searchParties')}
          exclude={value.map((row) => row.id)}
          value={null}
          onChange={(_, party) => party && add(party)}
        />
      )}
      {value.map((row) => (
        <div key={row.id} className="party-row">
          <UserAvatar name={row.display_name} />
          <span className="person-text party-row-name">
            <bdi className="person-name">{row.display_name}</bdi>
            <span className="person-email">{t(`partyTypes.${row.party_type}`)}</span>
          </span>
          <Select<PartyRole>
            className="party-role"
            aria-label={t('contracts.roleOf', { name: row.display_name })}
            value={row.role}
            disabled={disabled}
            onChange={(role) => update(row.id, role)}
            options={PARTY_ROLES.map((role) => ({ value: role, label: t(`partyRoles.${role}`) }))}
          />
          {!disabled && (
            <Button
              type="text"
              icon={<CloseOutlined />}
              aria-label={t('contracts.removeParty', { name: row.display_name })}
              onClick={() => remove(row.id)}
            />
          )}
        </div>
      ))}
      {!disabled && can(PERMISSIONS.partyManage) && (
        <Button
          type="link"
          icon={<PlusOutlined />}
          className="link-button-inline"
          onClick={() => setCreating(true)}
        >
          {t('contracts.createParty')}
        </Button>
      )}
      <Modal
        open={creating}
        title={t('parties.new')}
        okText={t('common.save')}
        cancelText={t('common.cancel')}
        confirmLoading={createParty.isPending}
        onOk={() => quickForm.submit()}
        onCancel={() => setCreating(false)}
        destroyOnHidden
      >
        <Form<QuickParty>
          form={quickForm}
          layout="vertical"
          onFinish={createQuickly}
          initialValues={{ party_type: 'organization' }}
        >
          <Form.Item name="party_type" label={t('parties.type')}>
            <Segmented<PartyType>
              options={[
                { value: 'organization', label: t('partyTypes.organization') },
                { value: 'individual', label: t('partyTypes.individual') },
              ]}
            />
          </Form.Item>
          <Form.Item
            name="display_name"
            label={t('contracts.partyName')}
            extra={t('contracts.partyNameHelp')}
            rules={[{ required: true, whitespace: true, message: t('validation.required') }]}
          >
            <Input maxLength={300} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
