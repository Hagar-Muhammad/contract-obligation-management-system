import { Button, Result } from 'antd'
import { Component, type ErrorInfo, type ReactNode } from 'react'
import i18n from '../i18n'

interface State {
  failed: boolean
}

/** Keeps the rest of the app usable when one page throws while rendering. */
export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { failed: false }

  static getDerivedStateFromError(): State {
    return { failed: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Page crashed', error, info.componentStack)
  }

  render() {
    if (!this.state.failed) return this.props.children
    return (
      <Result
        status="error"
        title={i18n.t('errors.generic')}
        extra={
          <Button type="primary" onClick={() => window.location.reload()}>
            {i18n.t('errors.reload')}
          </Button>
        }
      />
    )
  }
}
