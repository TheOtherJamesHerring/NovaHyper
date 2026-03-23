import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import type { AuthUser, JwtClaims, UserRole } from '../types'

/* ── JWT helper ─────────────────────────────────────────────────────────── */
function decodeJwt(token: string): JwtClaims | null {
  try {
    const payload = token.split('.')[1]
    const b64     = payload.replace(/-/g, '+').replace(/_/g, '/')
    return JSON.parse(atob(b64)) as JwtClaims
  } catch {
    return null
  }
}

function userFromToken(token: string): AuthUser | null {
  const claims = decodeJwt(token)
  if (!claims) return null
  return { id: claims.sub, tenant_id: claims.tenant_id, role: claims.role }
}

/* ── Context shape ───────────────────────────────────────────────────────── */
interface AuthContextValue {
  user:            AuthUser | null
  isAuthenticated: boolean
  isMspAdmin:      boolean
  canManage:       boolean   // operator+ can mutate resources
  login:           (access: string, refresh: string) => void
  logout:          () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

/* ── Provider ────────────────────────────────────────────────────────────── */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => {
    const token = sessionStorage.getItem('access_token')
    return token ? userFromToken(token) : null
  })

  const loginFn = useCallback((access: string, refresh: string) => {
    sessionStorage.setItem('access_token',  access)
    sessionStorage.setItem('refresh_token', refresh)
    setUser(userFromToken(access))
  }, [])

  const logoutFn = useCallback(() => {
    sessionStorage.removeItem('access_token')
    sessionStorage.removeItem('refresh_token')
    setUser(null)
  }, [])

  const MANAGE_ROLES: UserRole[] = ['msp_admin', 'tenant_admin', 'operator']

  const value: AuthContextValue = {
    user,
    isAuthenticated: user !== null,
    isMspAdmin:      user?.role === 'msp_admin',
    canManage:       user !== null && MANAGE_ROLES.includes(user.role),
    login:           loginFn,
    logout:          logoutFn,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

/* ── Hook ────────────────────────────────────────────────────────────────── */
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
