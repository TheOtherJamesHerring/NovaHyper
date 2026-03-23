import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { KeyRound, Mail } from 'lucide-react'
import { login } from '../api/auth'
import { useAuth } from '../contexts/AuthContext'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'

export function LoginPage() {
  const navigate = useNavigate()
  const { login: setTokens } = useAuth()

  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState<string | null>(null)

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const tokens = await login(email, password)
      setTokens(tokens.access_token, tokens.refresh_token)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-full w-full grid place-items-center bg-[radial-gradient(1200px_500px_at_20%_-10%,rgba(79,142,247,0.25),transparent),radial-gradient(900px_450px_at_80%_110%,rgba(56,217,169,0.2),transparent)] dark:bg-dark-bg">
      <form
        onSubmit={onSubmit}
        className="w-[360px] max-w-[90vw] p-6 rounded-2xl border border-black/[0.08] dark:border-white/[0.1] bg-white/95 dark:bg-dark-bg2/95 backdrop-blur shadow-xl"
      >
        <h1 className="font-display text-[24px] font-bold tracking-[-0.5px] text-slate-900 dark:text-gray-100">
          Nova<span className="text-accent">Hyper</span>
        </h1>
        <p className="text-[12px] text-slate-500 dark:text-gray-400 mt-1 mb-5">
          MSP Hypervisor Control Plane
        </p>

        <div className="space-y-3">
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            startIcon={<Mail size={13} />}
            placeholder="admin@example.com"
            autoComplete="username"
          />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            startIcon={<KeyRound size={13} />}
            placeholder="********"
            autoComplete="current-password"
          />
        </div>

        {error && (
          <div className="mt-3 text-[12px] text-nova-danger bg-nova-danger/10 border border-nova-danger/20 rounded-md px-2.5 py-2">
            {error}
          </div>
        )}

        <Button type="submit" variant="primary" className="w-full mt-4" loading={loading}>
          Sign in
        </Button>
      </form>
    </div>
  )
}
