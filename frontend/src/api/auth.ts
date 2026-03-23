import { request } from './client'
import type { TokenResponse } from '../types'

export function login(email: string, password: string): Promise<TokenResponse> {
  return request<TokenResponse>('/api/v1/auth/login', {
    method: 'POST',
    body:   JSON.stringify({ email, password }),
  })
}
